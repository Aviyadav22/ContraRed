# Phase 8: Lawyer UX Flow Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Transform the Word Add-in from a basic scan-and-review tool into a real-time lawyer workflow with selection scanning, keyboard navigation, negotiation mode, persistent state, and batch processing.

**Architecture:** All Word Add-in features are in `taskpane.ts` (vanilla TS + Office.js). Backend adds 2 new endpoints to existing `documents.py`. Dashboard adds 1 new page (`BatchUpload.tsx`). No new dependencies except `diff-match-patch` for clause diff.

**Tech Stack:** TypeScript + Office.js (Word Add-in), FastAPI + Python (Backend), React 19 + Vite 7 (Dashboard)

---

## Task 1: Backend — `POST /documents/analyze-clause` Endpoint

**Files:**
- Modify: `backend/app/api/v1/endpoints/documents.py` (after line 170, add new schema + endpoint)
- Modify: `backend/app/services/gemini_analyzer.py` (add `analyze_clause` method)

**Step 1: Add request/response schemas to documents.py**

Add after line 170 (after `AIAnalysisResponse`):

```python
class ClauseAnalyzeRequest(BaseModel):
    """Request to analyze a single clause/selection."""
    clause_text: str = Field(..., min_length=20, max_length=10000)
    playbook_id: Optional[str] = None
    jurisdiction: Optional[str] = None
    document_id: Optional[str] = None


class ClauseAnalyzeResponse(BaseModel):
    """Response from single-clause analysis."""
    risks: List[AIRedlineItem]
    tokens_used: int = 0
    analysis_time_ms: int = 0
```

**Step 2: Add the endpoint to documents.py**

Add after the `/analyze-full` endpoint (after ~line 750):

```python
@router.post("/analyze-clause", response_model=ClauseAnalyzeResponse)
@limiter.limit("30/minute")
async def analyze_clause(
    request: ClauseAnalyzeRequest,
    http_request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _quota=Depends(check_and_increment_quota),
):
    """
    Analyze a single clause or text selection.
    Lightweight version of /analyze-full for quick re-scans and selection scanning.
    """
    import time
    start_time = time.time()

    client_ip = http_request.client.host if http_request.client else None

    # Load playbook rules if specified
    playbook_rules = []
    playbook_name = "Default"

    if request.playbook_id:
        try:
            playbook_uuid = UUID(request.playbook_id)
            result = await db.execute(
                select(Playbook)
                .options(selectinload(Playbook.rules_list))
                .where(Playbook.id == playbook_uuid)
            )
            playbook = result.scalar_one_or_none()
            if playbook:
                playbook_name = playbook.name
                playbook_rules = [
                    {
                        "name": rule.clause_type,
                        "risk_level": rule.risk_level.value.upper() if hasattr(rule.risk_level, 'value') else str(rule.risk_level).upper(),
                        "primary_position": rule.primary_position or "",
                        "fallback_position": rule.fallback_position or "",
                        "is_deal_breaker": rule.is_deal_breaker,
                        "verification_prompt": rule.verification_prompt or "",
                    }
                    for rule in playbook.rules_list
                ]
        except Exception as e:
            logger.error("Error loading playbook for clause analysis: %s", e)

    try:
        playbook_name = _sanitize_for_prompt(playbook_name, max_length=200)

        ai_result = await asyncio.wait_for(
            gemini_analyzer.analyze_clause(
                clause_text=request.clause_text,
                playbook_rules=playbook_rules,
                playbook_name=playbook_name,
                jurisdiction=request.jurisdiction,
            ),
            timeout=30.0,
        )

        elapsed_ms = int((time.time() - start_time) * 1000)

        # Audit log (no contract text stored)
        await log_audit_event(
            db=db,
            user_id=current_user.id,
            action="clause_analyzed",
            resource_type="clause",
            details={"risk_count": len(ai_result.get("redlines", [])), "elapsed_ms": elapsed_ms},
            ip_address=client_ip,
        )

        return ClauseAnalyzeResponse(
            risks=ai_result.get("redlines", []),
            tokens_used=ai_result.get("tokens_used", 0),
            analysis_time_ms=elapsed_ms,
        )

    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail={"message": "Clause analysis timed out.", "error_code": "ai_timeout"})
    except AIServiceUnavailable:
        raise HTTPException(status_code=503, detail={"message": "AI service not configured.", "error_code": "ai_unavailable"})
    except AIRateLimited:
        raise HTTPException(status_code=429, detail={"message": "AI rate limit reached. Try again shortly.", "error_code": "ai_rate_limited"})
    except AIServiceError as e:
        logger.error("Clause analysis AI error: %s", e)
        raise HTTPException(status_code=502, detail={"message": "AI analysis failed.", "error_code": "ai_error"})
```

**Step 3: Add `analyze_clause` method to gemini_analyzer.py**

Find the `GeminiAnalyzer` class and add this method:

```python
async def analyze_clause(
    self,
    clause_text: str,
    playbook_rules: list = None,
    playbook_name: str = "Default",
    jurisdiction: str = None,
) -> dict:
    """Analyze a single clause — lightweight version of full analysis."""
    if not self.model:
        raise AIServiceUnavailable("Gemini not configured")

    rules_text = ""
    if playbook_rules:
        rules_text = "\n".join(
            f"- {r['name']} ({r['risk_level']}): {r['primary_position']}"
            for r in playbook_rules[:20]  # Limit to avoid token bloat
        )

    jurisdiction_text = f"Jurisdiction: {jurisdiction}" if jurisdiction else "Jurisdiction: General (detect from text)"

    prompt = f"""Analyze this single contract clause for legal risks.
{jurisdiction_text}
Playbook: {playbook_name}

Playbook Rules:
{rules_text or "Use general contract law best practices."}

CLAUSE TEXT:
\"\"\"
{clause_text}
\"\"\"

Return a JSON array of risks found. Each risk object:
{{
  "id": "clause-risk-<N>",
  "risk_level": "RED" or "YELLOW",
  "rule_name": "<rule category>",
  "original_text": "<exact verbatim quote from clause>",
  "explanation": "<why this is risky>",
  "recommendation": "<what to negotiate>",
  "redline_type": "violation" or "missing"
}}

If no risks found, return an empty array [].
Return ONLY valid JSON array, no markdown.
"""

    try:
        response = await asyncio.to_thread(
            self.model.generate_content, prompt
        )
        text = response.text.strip()
        # Strip markdown code fences if present
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
        if text.startswith("json"):
            text = text[4:].strip()

        import json
        redlines = json.loads(text)
        if not isinstance(redlines, list):
            redlines = []

        tokens_used = 0
        if hasattr(response, 'usage_metadata'):
            tokens_used = getattr(response.usage_metadata, 'total_token_count', 0)

        return {"redlines": redlines, "tokens_used": tokens_used}

    except Exception as e:
        logger.error("Clause analysis failed: %s", e)
        raise AIServiceError(f"Clause analysis failed: {e}")
```

**Step 4: Verify the endpoint works**

Run: `cd backend && python -c "from app.api.v1.endpoints.documents import ClauseAnalyzeRequest, ClauseAnalyzeResponse; print('Schemas OK')"`
Expected: `Schemas OK`

**Step 5: Commit**

```bash
git add backend/app/api/v1/endpoints/documents.py backend/app/services/gemini_analyzer.py
git commit -m "feat(phase8): add POST /documents/analyze-clause endpoint for selection scanning"
```

---

## Task 2: Word Add-in API Client — Add `analyzeClause` Method

**Files:**
- Modify: `ContraRed-PoC/src/taskpane/api.ts` (add method + types)

**Step 1: Add ClauseAnalysisResult type**

Add after `AIAnalysisResult` interface (line 54):

```typescript
// Clause-level analysis (for selection scanning / re-scan)
interface ClauseAnalysisResult {
    risks: AIRedlineItem[];
    tokens_used: number;
    analysis_time_ms: number;
}

// Negotiation decision tracking
interface NegotiationDecision {
    risk_id: string;
    decision: 'accept' | 'counter' | 'escalate';
    counter_text?: string;
    timestamp: number;
}

interface NegotiationSession {
    started_at: number;
    notes: string;
    decisions: NegotiationDecision[];
    document_name: string;
}
```

**Step 2: Add `analyzeClause` method to ContraRedAPI class**

Add after `analyzeWithAI` method (line 342):

```typescript
    /**
     * Analyze a single clause or text selection.
     * Lightweight — returns risks for just that text in 3-5 seconds.
     */
    async analyzeClause(clauseText: string, playbookId?: string, jurisdiction?: string): Promise<ClauseAnalysisResult> {
        return this.request('/documents/analyze-clause', {
            method: 'POST',
            body: JSON.stringify({
                clause_text: clauseText,
                playbook_id: playbookId,
                jurisdiction,
            }),
        });
    }
```

**Step 3: Export new types**

Update the export line (line 534):

```typescript
export type { User, RedlineResponse, Playbook, PlaybookRule, PlaybookDetail, AIRedlineItem, AIAnalysisResult, ClauseAnalysisResult, NegotiationDecision, NegotiationSession, ClauseLibraryItem, DocumentListItem, TemplateListItem };
```

**Step 4: Commit**

```bash
git add ContraRed-PoC/src/taskpane/api.ts
git commit -m "feat(phase8): add analyzeClause API method and negotiation types"
```

---

## Task 3: Word Add-in — Scan Selection Feature (8.1)

**Files:**
- Modify: `ContraRed-PoC/src/taskpane/taskpane.ts` (add scanSelection function + button handler)
- Modify: `ContraRed-PoC/src/taskpane/taskpane.html` (add Scan Selection button)

**Step 1: Add state variables for selection scanning**

Add after line 100 (`let searchQuery = '';`):

```typescript
// Selection scanning state
let isSelectionScanning = false;

// Keyboard navigation state
let currentRiskIndex = -1;

// Negotiation mode state
let negotiationMode = false;
let negotiationSession: import('./api').NegotiationSession | null = null;
let negotiationTimer: ReturnType<typeof setInterval> | null = null;
let selectionDebounceTimer: ReturnType<typeof setTimeout> | null = null;
```

**Step 2: Add `scanSelection` function**

Add after `scanDocument` function (after line 694):

```typescript
/**
 * Scan only the currently selected text in Word.
 * Uses the lightweight /analyze-clause endpoint for 3-5 second analysis.
 */
async function scanSelection(): Promise<void> {
    if (isSelectionScanning) return;
    isSelectionScanning = true;

    const selScanBtn = document.getElementById('scanSelectionBtn') as HTMLButtonElement | null;
    const selScanText = document.getElementById('scanSelectionBtnText');
    const selScanSpinner = document.getElementById('scanSelectionSpinner');

    if (selScanBtn) selScanBtn.disabled = true;
    if (selScanText) selScanText.style.display = 'none';
    if (selScanSpinner) selScanSpinner.style.display = 'block';

    try {
        // Get selected text from Word
        const selectedText = await Word.run(async (context) => {
            const selection = context.document.getSelection();
            selection.load('text');
            await context.sync();
            return selection.text;
        });

        if (!selectedText || selectedText.trim().length < 20) {
            displayScanError(new Error('Please select at least 20 characters of contract text to scan.'));
            return;
        }

        if (selectedText.length > 10000) {
            displayScanError(new Error('Selection too large. Please select a smaller portion (max ~10KB).'));
            return;
        }

        const selectedPlaybookId = (document.getElementById('playbookSelect') as HTMLSelectElement)?.value || undefined;

        log.info('Scanning selection...', { length: selectedText.length });
        const result = await api.analyzeClause(selectedText, selectedPlaybookId);

        if (result.risks.length === 0) {
            // Show inline "no risks" message
            const list = riskList();
            if (list) {
                const noRiskCard = document.createElement('div');
                noRiskCard.className = 'info-card';
                noRiskCard.innerHTML = `
                    <div class="info-card-icon">&#10003;</div>
                    <div class="info-card-title">No Risks Found</div>
                    <div class="info-card-message">The selected text appears to be acceptable. (${result.analysis_time_ms}ms, ${result.tokens_used} tokens)</div>
                `;
                list.insertBefore(noRiskCard, list.firstChild);
                // Auto-remove after 10 seconds
                setTimeout(() => noRiskCard.remove(), 10000);
            }
            return;
        }

        // Merge selection results into existing analysis or create new
        if (currentAIAnalysis) {
            // Add new risks, avoiding duplicates by rule_name + original_text
            const existingKeys = new Set(
                currentAIAnalysis.redlines.map(r => `${r.rule_name}:${r.original_text.slice(0, 50)}`)
            );
            const newRisks = result.risks.filter(
                r => !existingKeys.has(`${r.rule_name}:${r.original_text.slice(0, 50)}`)
            );
            if (newRisks.length > 0) {
                currentAIAnalysis.redlines = [...newRisks, ...currentAIAnalysis.redlines];
                currentAIAnalysis.total_risks = currentAIAnalysis.redlines.length;
                currentAIAnalysis.risk_summary = {
                    red: currentAIAnalysis.redlines.filter(r => r.risk_level === 'RED').length,
                    yellow: currentAIAnalysis.redlines.filter(r => r.risk_level === 'YELLOW').length,
                };
            }
            displayAIResults(currentAIAnalysis);
        } else {
            // Create a new analysis result from clause scan
            currentAIAnalysis = {
                document_id: 'selection-' + Date.now(),
                filename: 'Selection Scan',
                executive_summary: [`Selection scan found ${result.risks.length} risk(s).`],
                redlines: result.risks,
                total_risks: result.risks.length,
                risk_summary: {
                    red: result.risks.filter(r => r.risk_level === 'RED').length,
                    yellow: result.risks.filter(r => r.risk_level === 'YELLOW').length,
                },
                tokens_used: result.tokens_used,
            };
            displayAIResults(currentAIAnalysis);
        }

        // Highlight the new risks
        await highlightAIRedlines(result.risks);

        log.info('Selection scan complete:', { risks: result.risks.length, time_ms: result.analysis_time_ms });

    } catch (error) {
        log.error('Selection scan failed:', error);
        displayScanError(error instanceof Error ? error : new Error(String(error)));
    } finally {
        isSelectionScanning = false;
        if (selScanBtn) selScanBtn.disabled = false;
        if (selScanText) selScanText.style.display = 'inline';
        if (selScanSpinner) selScanSpinner.style.display = 'none';
    }
}
```

**Step 3: Add Scan Selection button to HTML**

In `taskpane.html`, find the existing scan button and add a second button next to it. Find:
```html
<button id="scanBtn" class="btn btn-primary btn-full">
```

Add after the scan button (within the same parent container):

```html
<button id="scanSelectionBtn" class="btn btn-secondary btn-full" style="margin-top: 6px;">
    <span id="scanSelectionBtnText">Scan Selection</span>
    <div id="scanSelectionSpinner" class="spinner" style="display:none;"></div>
</button>
```

**Step 4: Bind the button in Office.onReady**

Add after line 163 (`scanBtn()?.addEventListener('click', scanDocument);`):

```typescript
    document.getElementById('scanSelectionBtn')?.addEventListener('click', scanSelection);
```

**Step 5: Update exports**

Update line 1606:
```typescript
export { scanDocument, scanSelection, highlightAIText, applyAIRedline, applyAllRedlines, exportReport };
```

**Step 6: Commit**

```bash
git add ContraRed-PoC/src/taskpane/taskpane.ts ContraRed-PoC/src/taskpane/taskpane.html
git commit -m "feat(phase8): add Scan Selection feature (8.1)"
```

---

## Task 4: Word Add-in — Keyboard Shortcuts (8.2)

**Files:**
- Modify: `ContraRed-PoC/src/taskpane/taskpane.ts`

**Step 1: Add keyboard shortcut handler**

Add after the `scanSelection` function:

```typescript
/**
 * Navigate risk cards with keyboard.
 * Sets visual focus ring and scrolls card into view.
 */
function focusRiskCard(index: number): void {
    const cards = document.querySelectorAll('.risk-card');
    if (cards.length === 0) return;

    // Remove focus from all cards
    cards.forEach(c => c.classList.remove('keyboard-focused'));

    // Clamp index
    if (index < 0) index = cards.length - 1;
    if (index >= cards.length) index = 0;
    currentRiskIndex = index;

    const card = cards[index] as HTMLElement;
    card.classList.add('keyboard-focused');
    card.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

/**
 * Get the currently focused risk card's redline data.
 */
function getFocusedRedline(): AIRedlineItem | null {
    if (currentRiskIndex < 0 || !currentAIAnalysis) return null;
    const filtered = getFilteredRedlines();
    return filtered[currentRiskIndex] || null;
}

/**
 * Click a button inside the currently focused risk card.
 */
function clickFocusedCardButton(selector: string): void {
    const cards = document.querySelectorAll('.risk-card');
    if (currentRiskIndex < 0 || currentRiskIndex >= cards.length) return;
    const btn = cards[currentRiskIndex].querySelector(selector) as HTMLButtonElement | null;
    if (btn) btn.click();
}

/**
 * Global keyboard shortcut handler.
 * Works when the taskpane has focus.
 */
function handleKeyboardShortcuts(e: KeyboardEvent): void {
    // Ignore if typing in an input/textarea
    const tag = (e.target as HTMLElement)?.tagName;
    if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return;

    // Ctrl+Shift combinations
    if (e.ctrlKey && e.shiftKey) {
        switch (e.key.toUpperCase()) {
            case 'S': // Scan selection
                e.preventDefault();
                scanSelection();
                return;
            case 'D': // Scan full document
                e.preventDefault();
                scanDocument();
                return;
            case 'N': // Toggle negotiation mode
                e.preventDefault();
                toggleNegotiationMode();
                return;
        }
    }

    // Alt combinations for risk card actions
    if (e.altKey && !e.ctrlKey && !e.shiftKey) {
        switch (e.key) {
            case 'ArrowUp':
                e.preventDefault();
                focusRiskCard(currentRiskIndex - 1);
                return;
            case 'ArrowDown':
                e.preventDefault();
                focusRiskCard(currentRiskIndex + 1);
                return;
            case 'h': case 'H': // Highlight
                e.preventDefault();
                clickFocusedCardButton('.highlight-btn');
                return;
            case 'g': case 'G': // Generate fix
                e.preventDefault();
                clickFocusedCardButton('.generate-fix-btn');
                return;
            case 'a': case 'A': // Apply fix
                e.preventDefault();
                clickFocusedCardButton('.apply-btn');
                return;
            case 'r': case 'R': // Research
                e.preventDefault();
                clickFocusedCardButton('.research-btn');
                return;
        }
    }
}
```

**Step 2: Register the handler in Office.onReady**

Add after the search input handler (after line 198):

```typescript
    // Keyboard shortcuts (Phase 8)
    document.addEventListener('keydown', handleKeyboardShortcuts);
```

**Step 3: Add CSS for keyboard focus ring**

In `taskpane.html`, find the `.risk-card` styles and add:

```css
.risk-card.keyboard-focused {
    outline: 2px solid var(--accent, #C0392B);
    outline-offset: 2px;
    box-shadow: 0 0 0 4px rgba(192, 57, 43, 0.15);
}
```

**Step 4: Add keyboard shortcut hint to UI**

In `taskpane.html`, add a small hint below the scan buttons:

```html
<div class="shortcut-hint" style="font-size:11px; color:var(--text-muted); margin-top:4px; text-align:center;">
    Ctrl+Shift+S: Scan Selection &middot; Ctrl+Shift+D: Full Scan &middot; Alt+&uarr;/&darr;: Navigate
</div>
```

**Step 5: Commit**

```bash
git add ContraRed-PoC/src/taskpane/taskpane.ts ContraRed-PoC/src/taskpane/taskpane.html
git commit -m "feat(phase8): add keyboard shortcuts for risk navigation and scanning (8.2)"
```

---

## Task 5: Word Add-in — Quick Re-Scan (8.3)

**Files:**
- Modify: `ContraRed-PoC/src/taskpane/taskpane.ts` (modify `createAIRedlineCard` to add re-scan button)

**Step 1: Add re-scan function**

Add after the `scanSelection` function:

```typescript
/**
 * Re-scan a single clause after a fix has been applied.
 * Gets surrounding text from the document and re-analyzes.
 */
async function reScanClause(riskId: string, originalText: string): Promise<void> {
    const card = document.getElementById(`risk-${riskId}`);
    if (!card) return;

    const reScanBtn = card.querySelector('.rescan-btn') as HTMLButtonElement | null;
    if (reScanBtn) {
        reScanBtn.disabled = true;
        reScanBtn.textContent = 'Re-scanning...';
    }

    try {
        // Get the current text around where the original was
        const surroundingText = await getSurroundingContext(originalText);
        const textToScan = surroundingText || originalText;

        if (textToScan.length < 20) {
            showToastOnCard(card, 'Not enough text to re-scan.');
            return;
        }

        const selectedPlaybookId = (document.getElementById('playbookSelect') as HTMLSelectElement)?.value || undefined;
        const result = await api.analyzeClause(textToScan, selectedPlaybookId);

        if (result.risks.length === 0) {
            // Risk resolved! Update the card to show GREEN
            card.classList.add('fixed');
            card.dataset.risk = 'green';
            fixedRisks.add(riskId);
            showToastOnCard(card, 'Risk resolved! Clause is now clean.');

            // Update counts
            if (currentAIAnalysis) {
                currentAIAnalysis.risk_summary = {
                    red: currentAIAnalysis.redlines.filter(r => r.risk_level === 'RED' && !fixedRisks.has(r.id)).length,
                    yellow: currentAIAnalysis.redlines.filter(r => r.risk_level === 'YELLOW' && !fixedRisks.has(r.id)).length,
                };
                if (redCount()) redCount()!.textContent = String(currentAIAnalysis.risk_summary.red);
                if (yellowCount()) yellowCount()!.textContent = String(currentAIAnalysis.risk_summary.yellow);
            }
        } else {
            // Still has risks — update the card with new info
            const newRisk = result.risks[0];
            const riskTitle = card.querySelector('.risk-title');
            const riskExpl = card.querySelector('.risk-explanation');
            if (riskTitle) riskTitle.textContent = newRisk.rule_name;
            if (riskExpl) riskExpl.textContent = newRisk.explanation;
            card.dataset.risk = newRisk.risk_level.toLowerCase();
            showToastOnCard(card, `Re-scanned: ${newRisk.risk_level} risk still present.`);
        }

    } catch (error) {
        log.error('Re-scan failed:', error);
        showToastOnCard(card, 'Re-scan failed. Try again.');
    } finally {
        if (reScanBtn) {
            reScanBtn.disabled = false;
            reScanBtn.textContent = 'Re-Scan';
        }
    }
}
```

**Step 2: Add re-scan button to risk cards**

In the `createAIRedlineCard` function (line ~951), find the `risk-actions` div and add a re-scan button after the existing buttons:

```html
<button class="btn btn-secondary btn-sm rescan-btn" style="display:none;">
    Re-Scan
</button>
```

**Step 3: Show re-scan button when a fix is applied**

Find the fix application logic (where `fixedRisks.add(...)` is called). After marking a risk as fixed, show the re-scan button:

```typescript
const reScanBtn = card.querySelector('.rescan-btn') as HTMLElement;
if (reScanBtn) reScanBtn.style.display = 'inline-flex';
```

**Step 4: Bind re-scan click handler in `createAIRedlineCard`**

After the card HTML is set, add:

```typescript
const reScanBtn = card.querySelector('.rescan-btn');
reScanBtn?.addEventListener('click', () => reScanClause(redline.id, redline.original_text));
```

**Step 5: Commit**

```bash
git add ContraRed-PoC/src/taskpane/taskpane.ts ContraRed-PoC/src/taskpane/taskpane.html
git commit -m "feat(phase8): add quick re-scan after fix application (8.3)"
```

---

## Task 6: Word Add-in — Live Negotiation Mode (8.4)

**Files:**
- Modify: `ContraRed-PoC/src/taskpane/taskpane.ts` (add negotiation mode logic)
- Modify: `ContraRed-PoC/src/taskpane/taskpane.html` (add negotiation mode UI elements)

**Step 1: Add negotiation mode HTML**

In `taskpane.html`, add a negotiation mode panel (hidden by default) inside the main panel, above the results section:

```html
<!-- Negotiation Mode Panel (Phase 8.4) -->
<div id="negotiationPanel" style="display:none;">
    <div class="negotiation-header">
        <div class="negotiation-title-bar">
            <span class="negotiation-badge">NEGOTIATION MODE</span>
            <span id="negotiationTimer" class="negotiation-timer">00:00</span>
            <button id="exitNegotiationBtn" class="btn btn-ghost btn-sm">Exit</button>
        </div>
        <textarea id="negotiationNotes" class="negotiation-notes" placeholder="Quick notes during the call..." rows="2"></textarea>
        <div id="autoScanIndicator" class="auto-scan-indicator">
            <span class="auto-scan-dot"></span>
            Auto-scanning selections
        </div>
    </div>
</div>
```

**Step 2: Add negotiation mode CSS**

In `taskpane.html`, add styles:

```css
.negotiation-header {
    background: var(--bg-elevated, #F5F4F2);
    border: 1px solid var(--accent, #C0392B);
    border-radius: 8px;
    padding: 10px;
    margin-bottom: 10px;
}
.negotiation-title-bar {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 8px;
}
.negotiation-badge {
    background: var(--accent, #C0392B);
    color: white;
    font-size: 10px;
    font-weight: 700;
    padding: 2px 8px;
    border-radius: 4px;
    letter-spacing: 0.5px;
}
.negotiation-timer {
    font-family: monospace;
    font-size: 14px;
    font-weight: 600;
    color: var(--text-primary);
    flex: 1;
}
.negotiation-notes {
    width: 100%;
    border: 1px solid var(--border, #E8E5E0);
    border-radius: 6px;
    padding: 6px 8px;
    font-size: 12px;
    resize: none;
    font-family: inherit;
    background: var(--bg-surface, #fff);
}
.auto-scan-indicator {
    font-size: 11px;
    color: var(--text-muted);
    margin-top: 6px;
    display: flex;
    align-items: center;
    gap: 4px;
}
.auto-scan-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: #1A7A4A;
    animation: pulse 2s infinite;
}
@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.3; }
}

/* Compact risk cards in negotiation mode */
body.negotiation-mode .risk-card {
    padding: 8px 10px;
}
body.negotiation-mode .risk-explanation,
body.negotiation-mode .suggested-fix,
body.negotiation-mode .risk-clause {
    display: none;
}
body.negotiation-mode .risk-card.expanded .risk-explanation,
body.negotiation-mode .risk-card.expanded .suggested-fix,
body.negotiation-mode .risk-card.expanded .risk-clause {
    display: block;
}

/* Negotiation action buttons */
.negotiation-actions {
    display: flex;
    gap: 4px;
    margin-top: 6px;
}
.neg-btn {
    font-size: 11px;
    padding: 3px 8px;
    border-radius: 4px;
    border: 1px solid var(--border);
    cursor: pointer;
    background: var(--bg-surface);
}
.neg-btn.accept { color: #1A7A4A; border-color: #1A7A4A; }
.neg-btn.counter { color: #B7770D; border-color: #B7770D; }
.neg-btn.escalate { color: #C0392B; border-color: #C0392B; }
.neg-btn.active { color: white; }
.neg-btn.accept.active { background: #1A7A4A; }
.neg-btn.counter.active { background: #B7770D; }
.neg-btn.escalate.active { background: #C0392B; }
```

**Step 3: Add negotiation mode toggle logic in taskpane.ts**

```typescript
/**
 * Toggle Live Negotiation Mode.
 * Compact cards, auto-scan on selection, session timer, notes.
 */
function toggleNegotiationMode(): void {
    negotiationMode = !negotiationMode;
    const panel = document.getElementById('negotiationPanel');

    if (negotiationMode) {
        // Activate
        document.body.classList.add('negotiation-mode');
        if (panel) panel.style.display = 'block';

        // Start session
        negotiationSession = loadNegotiationSession() || {
            started_at: Date.now(),
            notes: '',
            decisions: [],
            document_name: currentAIAnalysis?.filename || 'Unknown',
        };

        // Start timer
        startNegotiationTimer();

        // Restore notes
        const notesEl = document.getElementById('negotiationNotes') as HTMLTextAreaElement;
        if (notesEl && negotiationSession.notes) {
            notesEl.value = negotiationSession.notes;
        }

        // Save notes on input
        notesEl?.addEventListener('input', () => {
            if (negotiationSession) {
                negotiationSession.notes = notesEl.value;
                saveNegotiationSession();
            }
        });

        // Auto-scan on selection change
        registerSelectionHandler();

        // Re-render cards in compact mode
        renderRedlineList();

    } else {
        // Deactivate
        document.body.classList.remove('negotiation-mode');
        if (panel) panel.style.display = 'none';

        // Stop timer
        if (negotiationTimer) {
            clearInterval(negotiationTimer);
            negotiationTimer = null;
        }

        // Unregister selection handler
        unregisterSelectionHandler();

        // Save session
        saveNegotiationSession();

        // Re-render in normal mode
        renderRedlineList();
    }
}

function startNegotiationTimer(): void {
    const timerEl = document.getElementById('negotiationTimer');
    if (!timerEl || !negotiationSession) return;

    negotiationTimer = setInterval(() => {
        const elapsed = Math.floor((Date.now() - negotiationSession!.started_at) / 1000);
        const mins = Math.floor(elapsed / 60);
        const secs = elapsed % 60;
        timerEl.textContent = `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
    }, 1000);
}

function registerSelectionHandler(): void {
    try {
        Office.context.document.addHandlerAsync(
            Office.EventType.DocumentSelectionChanged,
            onSelectionChanged
        );
    } catch (e) {
        log.warn('Could not register selection handler:', e);
    }
}

function unregisterSelectionHandler(): void {
    try {
        Office.context.document.removeHandlerAsync(
            Office.EventType.DocumentSelectionChanged,
            { handler: onSelectionChanged }
        );
    } catch (e) {
        log.warn('Could not unregister selection handler:', e);
    }
}

function onSelectionChanged(): void {
    if (!negotiationMode) return;

    // Debounce 1.5 seconds
    if (selectionDebounceTimer) clearTimeout(selectionDebounceTimer);
    selectionDebounceTimer = setTimeout(async () => {
        const selectedText = await Word.run(async (context) => {
            const sel = context.document.getSelection();
            sel.load('text');
            await context.sync();
            return sel.text;
        });

        if (selectedText && selectedText.trim().length >= 20) {
            // Auto-scan the selection
            const indicator = document.getElementById('autoScanIndicator');
            if (indicator) indicator.textContent = 'Scanning selection...';
            await scanSelection();
            if (indicator) indicator.innerHTML = '<span class="auto-scan-dot"></span> Auto-scanning selections';
        }
    }, 1500);
}

function saveNegotiationSession(): void {
    if (negotiationSession) {
        localStorage.setItem('contrared_negotiation_session', JSON.stringify(negotiationSession));
    }
}

function loadNegotiationSession(): import('./api').NegotiationSession | null {
    try {
        const stored = localStorage.getItem('contrared_negotiation_session');
        if (stored) return JSON.parse(stored);
    } catch { /* ignore */ }
    return null;
}

/**
 * Record a negotiation decision for a risk.
 */
function recordNegotiationDecision(riskId: string, decision: 'accept' | 'counter' | 'escalate', counterText?: string): void {
    if (!negotiationSession) return;

    // Update or add decision
    const existing = negotiationSession.decisions.findIndex(d => d.risk_id === riskId);
    const entry = { risk_id: riskId, decision, counter_text: counterText, timestamp: Date.now() };

    if (existing >= 0) {
        negotiationSession.decisions[existing] = entry;
    } else {
        negotiationSession.decisions.push(entry);
    }

    saveNegotiationSession();
}
```

**Step 4: Modify `createAIRedlineCard` to include negotiation buttons**

Inside `createAIRedlineCard`, after the existing `risk-actions` div, add:

```typescript
// Add negotiation buttons if in negotiation mode
if (negotiationMode) {
    const negActions = document.createElement('div');
    negActions.className = 'negotiation-actions';
    negActions.innerHTML = `
        <button class="neg-btn accept" data-decision="accept">Accept</button>
        <button class="neg-btn counter" data-decision="counter">Counter</button>
        <button class="neg-btn escalate" data-decision="escalate">Escalate</button>
    `;
    card.appendChild(negActions);

    // Check if there's an existing decision
    const existingDecision = negotiationSession?.decisions.find(d => d.risk_id === redline.id);
    if (existingDecision) {
        const activeBtn = negActions.querySelector(`[data-decision="${existingDecision.decision}"]`);
        if (activeBtn) activeBtn.classList.add('active');
    }

    // Bind negotiation buttons
    negActions.querySelectorAll('.neg-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const decision = (btn as HTMLElement).dataset.decision as 'accept' | 'counter' | 'escalate';
            negActions.querySelectorAll('.neg-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            recordNegotiationDecision(redline.id, decision);
        });
    });

    // Make card expandable in negotiation mode (click header to toggle)
    const header = card.querySelector('.risk-card-header');
    header?.addEventListener('click', () => {
        card.classList.toggle('expanded');
    });
}
```

**Step 5: Bind exit button**

In Office.onReady, add:

```typescript
    document.getElementById('exitNegotiationBtn')?.addEventListener('click', toggleNegotiationMode);
```

**Step 6: Commit**

```bash
git add ContraRed-PoC/src/taskpane/taskpane.ts ContraRed-PoC/src/taskpane/taskpane.html
git commit -m "feat(phase8): add Live Negotiation Mode with auto-scan, timer, and decision tracking (8.4)"
```

---

## Task 7: Word Add-in — Quality of Life Features (8.5)

**Files:**
- Modify: `ContraRed-PoC/src/taskpane/taskpane.ts`
- Modify: `ContraRed-PoC/src/taskpane/taskpane.html`

### 7a: Persistent Scan State

**Step 1: Add save/restore functions in taskpane.ts**

```typescript
/**
 * Save scan state to localStorage for persistence across taskpane close/reopen.
 */
function saveScanState(): void {
    if (!currentAIAnalysis) return;
    const state = {
        analysis: currentAIAnalysis,
        fixedRisks: Array.from(fixedRisks),
        timestamp: Date.now(),
    };
    localStorage.setItem('contrared_scan_state', JSON.stringify(state));
}

/**
 * Restore scan state from localStorage if available and recent (< 24 hours).
 */
function restoreScanState(): boolean {
    try {
        const stored = localStorage.getItem('contrared_scan_state');
        if (!stored) return false;

        const state = JSON.parse(stored);
        const age = Date.now() - state.timestamp;
        if (age > 24 * 60 * 60 * 1000) {
            localStorage.removeItem('contrared_scan_state');
            return false;
        }

        currentAIAnalysis = state.analysis;
        state.fixedRisks.forEach((id: string) => fixedRisks.add(id));
        displayAIResults(currentAIAnalysis!);
        return true;
    } catch {
        return false;
    }
}
```

**Step 2: Call `saveScanState` after every scan**

In `scanDocument()`, after `displayAIResults(aiResult)` (line ~681), add:
```typescript
    saveScanState();
```

In `scanSelection()`, after `displayAIResults(...)`, add:
```typescript
    saveScanState();
```

**Step 3: Call `restoreScanState` in `showMainPanel`**

In `showMainPanel()` (around line 253), add before `loadRecentScans()`:
```typescript
  // Restore previous scan if available
  restoreScanState();
```

**Step 4: Clear state on logout**

In the `handleLogout` function, add:
```typescript
    localStorage.removeItem('contrared_scan_state');
    localStorage.removeItem('contrared_negotiation_session');
    localStorage.removeItem('contrared_onboarded');
```

### 7b: Clause Diff View

**Step 5: Add word-level diff function**

```typescript
/**
 * Compute a simple word-level diff between two strings.
 * Returns HTML with <del> and <ins> tags.
 */
function wordDiff(original: string, modified: string): string {
    const origWords = original.split(/(\s+)/);
    const modWords = modified.split(/(\s+)/);

    // Simple LCS-based diff
    const m = origWords.length;
    const n = modWords.length;

    // Build LCS table
    const dp: number[][] = Array.from({ length: m + 1 }, () => Array(n + 1).fill(0));
    for (let i = 1; i <= m; i++) {
        for (let j = 1; j <= n; j++) {
            if (origWords[i - 1] === modWords[j - 1]) {
                dp[i][j] = dp[i - 1][j - 1] + 1;
            } else {
                dp[i][j] = Math.max(dp[i - 1][j], dp[i][j - 1]);
            }
        }
    }

    // Backtrack to build diff
    const result: string[] = [];
    let i = m, j = n;
    const ops: Array<{ type: 'keep' | 'del' | 'ins'; text: string }> = [];

    while (i > 0 || j > 0) {
        if (i > 0 && j > 0 && origWords[i - 1] === modWords[j - 1]) {
            ops.unshift({ type: 'keep', text: origWords[i - 1] });
            i--; j--;
        } else if (j > 0 && (i === 0 || dp[i][j - 1] >= dp[i - 1][j])) {
            ops.unshift({ type: 'ins', text: modWords[j - 1] });
            j--;
        } else {
            ops.unshift({ type: 'del', text: origWords[i - 1] });
            i--;
        }
    }

    // Merge consecutive ops of the same type and render
    for (const op of ops) {
        if (op.type === 'del') {
            result.push(`<del style="background:#FECACA;text-decoration:line-through;color:#991B1B;">${escapeHtml(op.text)}</del>`);
        } else if (op.type === 'ins') {
            result.push(`<ins style="background:#BBF7D0;text-decoration:underline;color:#166534;">${escapeHtml(op.text)}</ins>`);
        } else {
            result.push(escapeHtml(op.text));
        }
    }

    return result.join('');
}
```

**Step 6: Show diff in generate-fix panel**

In the fix generation display code (where `generate-panel` content is set), replace the simple text display with:

```typescript
// Show diff between original and suggested fix
const diffHtml = wordDiff(originalText, fixText);
fixPanel.innerHTML = `
    <div class="diff-view" style="font-family:Georgia,serif;font-size:13px;line-height:1.6;padding:8px;border:1px solid var(--border);border-radius:6px;margin-bottom:8px;">
        ${diffHtml}
    </div>
    <div style="font-size:12px;color:var(--text-secondary);margin-bottom:8px;">${escapeHtml(reasoning)}</div>
    <div style="display:flex;gap:6px;">
        <button class="btn btn-primary btn-sm apply-btn">Apply to Document</button>
        <button class="btn btn-secondary btn-sm regenerate-btn">Regenerate</button>
    </div>
`;
```

### 7c: Smart Tooltips

**Step 7: Add tooltip HTML**

In `taskpane.html`, add at the end of main panel:

```html
<!-- Smart Tooltips (first-time user) -->
<div id="tooltipOverlay" class="tooltip-overlay" style="display:none;">
    <div id="tooltipContent" class="tooltip-box">
        <div id="tooltipText" class="tooltip-text"></div>
        <div class="tooltip-actions">
            <button id="tooltipNext" class="btn btn-primary btn-sm">Got it</button>
            <button id="tooltipSkip" class="btn btn-ghost btn-sm">Skip all</button>
        </div>
    </div>
</div>
```

**Step 8: Add tooltip CSS**

```css
.tooltip-overlay {
    position: fixed;
    inset: 0;
    background: rgba(0,0,0,0.3);
    z-index: 1000;
    display: flex;
    align-items: center;
    justify-content: center;
}
.tooltip-box {
    background: var(--bg-surface, white);
    border-radius: 10px;
    padding: 16px;
    max-width: 280px;
    box-shadow: 0 8px 32px rgba(0,0,0,0.15);
}
.tooltip-text { font-size: 13px; line-height: 1.5; margin-bottom: 12px; }
.tooltip-actions { display: flex; gap: 8px; justify-content: flex-end; }
```

**Step 9: Add tooltip logic**

```typescript
const TOOLTIPS = [
    { target: 'scanBtn', text: 'Click here to scan the entire document for legal risks. The AI will analyze every clause against your selected playbook.' },
    { target: 'scanSelectionBtn', text: 'Highlight text in Word first, then click this to scan just that selection. Great for quick checks during calls.' },
    { target: 'playbookSelect', text: 'Choose which playbook to scan against. Different playbooks have different rules for different contract types.' },
];

function showOnboardingTooltips(): void {
    if (localStorage.getItem('contrared_onboarded')) return;

    let currentTooltip = 0;

    function showNextTooltip(): void {
        if (currentTooltip >= TOOLTIPS.length) {
            localStorage.setItem('contrared_onboarded', 'true');
            const overlay = document.getElementById('tooltipOverlay');
            if (overlay) overlay.style.display = 'none';
            return;
        }

        const tip = TOOLTIPS[currentTooltip];
        const overlay = document.getElementById('tooltipOverlay');
        const text = document.getElementById('tooltipText');

        if (overlay) overlay.style.display = 'flex';
        if (text) text.textContent = tip.text;

        // Highlight target element
        const target = document.getElementById(tip.target);
        if (target) {
            target.style.position = 'relative';
            target.style.zIndex = '1001';
            target.style.boxShadow = '0 0 0 4px rgba(192, 57, 43, 0.3)';
        }

        currentTooltip++;
    }

    document.getElementById('tooltipNext')?.addEventListener('click', () => {
        // Remove highlight from previous target
        if (currentTooltip > 0 && currentTooltip <= TOOLTIPS.length) {
            const prev = document.getElementById(TOOLTIPS[currentTooltip - 1].target);
            if (prev) { prev.style.zIndex = ''; prev.style.boxShadow = ''; }
        }
        showNextTooltip();
    });

    document.getElementById('tooltipSkip')?.addEventListener('click', () => {
        localStorage.setItem('contrared_onboarded', 'true');
        const overlay = document.getElementById('tooltipOverlay');
        if (overlay) overlay.style.display = 'none';
        // Remove all highlights
        TOOLTIPS.forEach(t => {
            const el = document.getElementById(t.target);
            if (el) { el.style.zIndex = ''; el.style.boxShadow = ''; }
        });
    });

    showNextTooltip();
}
```

**Step 10: Call onboarding in showMainPanel**

Add at the end of `showMainPanel()`:
```typescript
  // Show first-time tooltips (after a short delay so DOM is ready)
  setTimeout(showOnboardingTooltips, 500);
```

**Step 11: Commit**

```bash
git add ContraRed-PoC/src/taskpane/taskpane.ts ContraRed-PoC/src/taskpane/taskpane.html
git commit -m "feat(phase8): add persistent scan state, clause diff view, and smart tooltips (8.5)"
```

---

## Task 8: Backend — Batch Processing Endpoints (8.6)

**Files:**
- Modify: `backend/app/api/v1/endpoints/documents.py` (add batch endpoints)

**Step 1: Add batch schemas**

Add after `ClauseAnalyzeResponse`:

```python
class BatchAnalyzeResponse(BaseModel):
    """Response from batch analysis initiation."""
    batch_id: str
    file_count: int
    status: str = "processing"


class BatchFileStatus(BaseModel):
    """Status of a single file in a batch."""
    filename: str
    status: Literal["queued", "processing", "completed", "error"]
    document_id: Optional[str] = None
    risk_summary: Optional[dict] = None
    error: Optional[str] = None


class BatchStatusResponse(BaseModel):
    """Full batch status."""
    batch_id: str
    files: List[BatchFileStatus]
    overall_progress: int  # 0-100
    status: Literal["processing", "completed", "partial_failure"]
```

**Step 2: Add in-memory batch store**

```python
# Simple in-memory batch tracking (use Redis in production)
_batch_store: Dict[str, dict] = {}
```

**Step 3: Add batch-analyze endpoint**

```python
@router.post("/batch-analyze", response_model=BatchAnalyzeResponse)
@limiter.limit("5/minute")
async def batch_analyze(
    http_request: Request,
    files: List[UploadFile] = File(...),
    playbook_id: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Batch analyze multiple documents concurrently.
    Accepts up to 10 .docx files.
    """
    if len(files) > 10:
        raise HTTPException(status_code=400, detail="Maximum 10 files per batch.")

    if len(files) == 0:
        raise HTTPException(status_code=400, detail="No files provided.")

    batch_id = str(uuid4())
    file_statuses = []

    for f in files:
        if not f.filename or not f.filename.lower().endswith('.docx'):
            file_statuses.append({
                "filename": f.filename or "unknown",
                "status": "error",
                "error": "Only .docx files are supported.",
            })
        else:
            file_statuses.append({
                "filename": f.filename,
                "status": "queued",
            })

    _batch_store[batch_id] = {
        "files": file_statuses,
        "status": "processing",
        "user_id": str(current_user.id),
    }

    # Read all file contents before starting background tasks
    file_contents = {}
    for f in files:
        if f.filename and f.filename.lower().endswith('.docx'):
            content = await f.read()
            # Extract text from .docx
            try:
                with zipfile.ZipFile(io.BytesIO(content)) as z:
                    if 'word/document.xml' in z.namelist():
                        doc_xml = z.read('word/document.xml').decode('utf-8')
                        # Simple text extraction from XML
                        text = re.sub(r'<[^>]+>', ' ', doc_xml)
                        text = re.sub(r'\s+', ' ', text).strip()
                        file_contents[f.filename] = text
                    else:
                        idx = next(i for i, fs in enumerate(file_statuses) if fs["filename"] == f.filename)
                        file_statuses[idx]["status"] = "error"
                        file_statuses[idx]["error"] = "Invalid .docx format."
            except Exception:
                idx = next(i for i, fs in enumerate(file_statuses) if fs["filename"] == f.filename)
                file_statuses[idx]["status"] = "error"
                file_statuses[idx]["error"] = "Could not read file."

    # Process files concurrently in background
    asyncio.create_task(
        _process_batch(batch_id, file_contents, playbook_id, str(current_user.id), db)
    )

    return BatchAnalyzeResponse(
        batch_id=batch_id,
        file_count=len(files),
        status="processing",
    )


async def _process_batch(
    batch_id: str,
    file_contents: dict,
    playbook_id: Optional[str],
    user_id: str,
    db: AsyncSession,
):
    """Background task to process batch files concurrently (3 at a time)."""
    semaphore = asyncio.Semaphore(3)
    batch = _batch_store.get(batch_id)
    if not batch:
        return

    # Load playbook once
    playbook_rules = []
    playbook_name = "Default"
    if playbook_id:
        try:
            playbook_uuid = UUID(playbook_id)
            result = await db.execute(
                select(Playbook)
                .options(selectinload(Playbook.rules_list))
                .where(Playbook.id == playbook_uuid)
            )
            playbook = result.scalar_one_or_none()
            if playbook:
                playbook_name = playbook.name
                playbook_rules = [
                    {
                        "name": rule.clause_type,
                        "risk_level": rule.risk_level.value.upper() if hasattr(rule.risk_level, 'value') else str(rule.risk_level).upper(),
                        "primary_position": rule.primary_position or "",
                        "fallback_position": rule.fallback_position or "",
                        "is_deal_breaker": rule.is_deal_breaker,
                        "verification_prompt": rule.verification_prompt or "",
                    }
                    for rule in playbook.rules_list
                ]
        except Exception as e:
            logger.error("Error loading playbook for batch: %s", e)

    async def process_file(filename: str, text: str):
        async with semaphore:
            idx = next(i for i, f in enumerate(batch["files"]) if f["filename"] == filename)
            batch["files"][idx]["status"] = "processing"

            try:
                pipeline_result = await asyncio.wait_for(
                    analysis_pipeline.run(
                        contract_text=text,
                        playbook_rules=playbook_rules,
                        playbook_name=_sanitize_for_prompt(playbook_name, max_length=200),
                    ),
                    timeout=120.0,
                )

                risk_summary = {
                    "red": sum(1 for r in pipeline_result.redlines if r.risk_level == "RED"),
                    "yellow": sum(1 for r in pipeline_result.redlines if r.risk_level == "YELLOW"),
                    "total": len(pipeline_result.redlines),
                }

                batch["files"][idx]["status"] = "completed"
                batch["files"][idx]["risk_summary"] = risk_summary
                batch["files"][idx]["document_id"] = str(uuid4())

            except Exception as e:
                logger.error("Batch file %s failed: %s", filename, e)
                batch["files"][idx]["status"] = "error"
                batch["files"][idx]["error"] = str(e)[:200]

    tasks = [process_file(fn, text) for fn, text in file_contents.items()]
    await asyncio.gather(*tasks)

    # Update overall status
    errors = sum(1 for f in batch["files"] if f["status"] == "error")
    completed = sum(1 for f in batch["files"] if f["status"] == "completed")

    if errors == len(batch["files"]):
        batch["status"] = "partial_failure"
    else:
        batch["status"] = "completed"


@router.get("/batch/{batch_id}/status", response_model=BatchStatusResponse)
async def batch_status(
    batch_id: str,
    current_user: User = Depends(get_current_user),
):
    """Get status of a batch analysis job."""
    batch = _batch_store.get(batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found.")

    if batch["user_id"] != str(current_user.id):
        raise HTTPException(status_code=403, detail="Access denied.")

    total = len(batch["files"])
    done = sum(1 for f in batch["files"] if f["status"] in ("completed", "error"))
    progress = int((done / total) * 100) if total > 0 else 0

    return BatchStatusResponse(
        batch_id=batch_id,
        files=[BatchFileStatus(**f) for f in batch["files"]],
        overall_progress=progress,
        status=batch.get("status", "processing"),
    )
```

**Step 4: Commit**

```bash
git add backend/app/api/v1/endpoints/documents.py
git commit -m "feat(phase8): add batch analysis endpoints POST /batch-analyze and GET /batch/{id}/status (8.6)"
```

---

## Task 9: Dashboard — BatchUpload Page (8.6)

**Files:**
- Create: `dashboard/src/pages/BatchUpload.tsx`
- Modify: `dashboard/src/App.tsx` (add route)
- Modify: `dashboard/src/api/client.ts` (add batch API methods)

**Step 1: Add batch API methods to dashboard client**

In `dashboard/src/api/client.ts`, find the API functions section and add:

```typescript
// Batch Processing (Phase 8)
export interface BatchFileStatus {
    filename: string;
    status: 'queued' | 'processing' | 'completed' | 'error';
    document_id?: string;
    risk_summary?: { red: number; yellow: number; total: number };
    error?: string;
}

export interface BatchStatusResponse {
    batch_id: string;
    files: BatchFileStatus[];
    overall_progress: number;
    status: 'processing' | 'completed' | 'partial_failure';
}

export async function batchAnalyze(files: File[], playbookId?: string): Promise<{ batch_id: string; file_count: number }> {
    const formData = new FormData();
    files.forEach(f => formData.append('files', f));
    if (playbookId) formData.append('playbook_id', playbookId);

    const res = await fetch(`${API_URL}/documents/batch-analyze`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${getToken()}` },
        body: formData,
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: 'Upload failed' }));
        throw new Error(err.detail || `HTTP ${res.status}`);
    }
    return res.json();
}

export async function getBatchStatus(batchId: string): Promise<BatchStatusResponse> {
    return request(`/documents/batch/${batchId}/status`);
}
```

**Step 2: Create BatchUpload.tsx**

```tsx
import React, { useState, useCallback, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import AppHeader from '@/components/AppHeader';
import { batchAnalyze, getBatchStatus, BatchFileStatus, BatchStatusResponse } from '@/api/client';

// Fetch playbooks for the selector
import { request } from '@/api/client';

export default function BatchUpload() {
    const navigate = useNavigate();
    const fileInputRef = useRef<HTMLInputElement>(null);
    const [files, setFiles] = useState<File[]>([]);
    const [playbookId, setPlaybookId] = useState<string>('');
    const [batchId, setBatchId] = useState<string | null>(null);
    const [batchStatus, setBatchStatus] = useState<BatchStatusResponse | null>(null);
    const [uploading, setUploading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

    // Fetch playbooks
    const { data: playbooks } = useQuery({
        queryKey: ['playbooks'],
        queryFn: () => request<Array<{ id: string; name: string }>>('/playbooks/'),
    });

    // Poll batch status
    useEffect(() => {
        if (!batchId) return;

        const poll = async () => {
            try {
                const status = await getBatchStatus(batchId);
                setBatchStatus(status);
                if (status.status !== 'processing') {
                    if (pollRef.current) clearInterval(pollRef.current);
                }
            } catch (e) {
                console.error('Poll failed:', e);
            }
        };

        poll(); // Immediate first poll
        pollRef.current = setInterval(poll, 3000);

        return () => {
            if (pollRef.current) clearInterval(pollRef.current);
        };
    }, [batchId]);

    const handleDrop = useCallback((e: React.DragEvent) => {
        e.preventDefault();
        const dropped = Array.from(e.dataTransfer.files).filter(f => f.name.endsWith('.docx'));
        setFiles(prev => [...prev, ...dropped].slice(0, 10));
    }, []);

    const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
        const selected = Array.from(e.target.files || []).filter(f => f.name.endsWith('.docx'));
        setFiles(prev => [...prev, ...selected].slice(0, 10));
    };

    const removeFile = (index: number) => {
        setFiles(prev => prev.filter((_, i) => i !== index));
    };

    const handleUpload = async () => {
        if (files.length === 0) return;
        setUploading(true);
        setError(null);
        try {
            const result = await batchAnalyze(files, playbookId || undefined);
            setBatchId(result.batch_id);
        } catch (e) {
            setError(e instanceof Error ? e.message : 'Upload failed');
        } finally {
            setUploading(false);
        }
    };

    const statusColor = (status: string) => {
        switch (status) {
            case 'completed': return '#1A7A4A';
            case 'processing': return '#B7770D';
            case 'error': return '#C0392B';
            default: return '#8A8885';
        }
    };

    return (
        <div style={{ minHeight: '100vh', background: '#FAFAF9' }}>
            <AppHeader />
            <div style={{ maxWidth: 800, margin: '0 auto', padding: '32px 24px' }}>
                <h1 style={{ fontSize: 24, fontWeight: 700, marginBottom: 8 }}>Batch Document Analysis</h1>
                <p style={{ color: '#6B6760', marginBottom: 24 }}>
                    Upload up to 10 .docx files for concurrent analysis.
                </p>

                {!batchId && (
                    <>
                        {/* Drop zone */}
                        <div
                            onDrop={handleDrop}
                            onDragOver={e => e.preventDefault()}
                            onClick={() => fileInputRef.current?.click()}
                            style={{
                                border: '2px dashed #E8E5E0',
                                borderRadius: 12,
                                padding: '48px 24px',
                                textAlign: 'center',
                                cursor: 'pointer',
                                marginBottom: 16,
                                background: 'white',
                            }}
                        >
                            <div style={{ fontSize: 14, fontWeight: 600 }}>
                                Drop .docx files here or click to browse
                            </div>
                            <div style={{ fontSize: 12, color: '#8A8885', marginTop: 4 }}>
                                Maximum 10 files
                            </div>
                            <input
                                ref={fileInputRef}
                                type="file"
                                multiple
                                accept=".docx"
                                onChange={handleFileSelect}
                                style={{ display: 'none' }}
                            />
                        </div>

                        {/* File list */}
                        {files.length > 0 && (
                            <div style={{ marginBottom: 16 }}>
                                {files.map((f, i) => (
                                    <div key={i} style={{
                                        display: 'flex',
                                        alignItems: 'center',
                                        justifyContent: 'space-between',
                                        padding: '8px 12px',
                                        background: 'white',
                                        border: '1px solid #E8E5E0',
                                        borderRadius: 8,
                                        marginBottom: 4,
                                    }}>
                                        <span style={{ fontSize: 13 }}>{f.name}</span>
                                        <button
                                            onClick={() => removeFile(i)}
                                            style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#C0392B', fontSize: 16 }}
                                        >
                                            &times;
                                        </button>
                                    </div>
                                ))}
                            </div>
                        )}

                        {/* Playbook selector */}
                        <select
                            value={playbookId}
                            onChange={e => setPlaybookId(e.target.value)}
                            style={{
                                width: '100%',
                                padding: '10px 12px',
                                borderRadius: 8,
                                border: '1px solid #E8E5E0',
                                fontSize: 13,
                                marginBottom: 16,
                                background: 'white',
                            }}
                        >
                            <option value="">Default Playbook</option>
                            {playbooks?.map(p => (
                                <option key={p.id} value={p.id}>{p.name}</option>
                            ))}
                        </select>

                        {error && (
                            <div style={{ color: '#C0392B', fontSize: 13, marginBottom: 12 }}>{error}</div>
                        )}

                        <button
                            onClick={handleUpload}
                            disabled={files.length === 0 || uploading}
                            style={{
                                width: '100%',
                                padding: '12px',
                                borderRadius: 8,
                                border: 'none',
                                background: files.length === 0 ? '#E8E5E0' : '#C0392B',
                                color: files.length === 0 ? '#8A8885' : 'white',
                                fontSize: 14,
                                fontWeight: 600,
                                cursor: files.length === 0 ? 'not-allowed' : 'pointer',
                            }}
                        >
                            {uploading ? 'Uploading...' : `Analyze ${files.length} File${files.length !== 1 ? 's' : ''}`}
                        </button>
                    </>
                )}

                {/* Batch progress */}
                {batchStatus && (
                    <div>
                        {/* Progress bar */}
                        <div style={{ marginBottom: 24 }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                                <span style={{ fontSize: 14, fontWeight: 600 }}>
                                    {batchStatus.status === 'processing' ? 'Processing...' : 'Complete'}
                                </span>
                                <span style={{ fontSize: 13, color: '#6B6760' }}>
                                    {batchStatus.overall_progress}%
                                </span>
                            </div>
                            <div style={{ height: 6, background: '#E8E5E0', borderRadius: 3 }}>
                                <div style={{
                                    height: '100%',
                                    width: `${batchStatus.overall_progress}%`,
                                    background: '#C0392B',
                                    borderRadius: 3,
                                    transition: 'width 0.3s ease',
                                }} />
                            </div>
                        </div>

                        {/* File status grid */}
                        {batchStatus.files.map((f, i) => (
                            <div key={i} style={{
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'space-between',
                                padding: '12px 16px',
                                background: 'white',
                                border: '1px solid #E8E5E0',
                                borderRadius: 8,
                                marginBottom: 6,
                            }}>
                                <div>
                                    <div style={{ fontSize: 13, fontWeight: 600 }}>{f.filename}</div>
                                    {f.error && <div style={{ fontSize: 11, color: '#C0392B' }}>{f.error}</div>}
                                </div>
                                <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                                    {f.risk_summary && (
                                        <div style={{ display: 'flex', gap: 8, fontSize: 12 }}>
                                            <span style={{ color: '#C0392B', fontWeight: 600 }}>{f.risk_summary.red} RED</span>
                                            <span style={{ color: '#B7770D', fontWeight: 600 }}>{f.risk_summary.yellow} YEL</span>
                                        </div>
                                    )}
                                    <span style={{
                                        fontSize: 11,
                                        fontWeight: 600,
                                        padding: '2px 8px',
                                        borderRadius: 4,
                                        color: statusColor(f.status),
                                        background: `${statusColor(f.status)}15`,
                                        textTransform: 'uppercase',
                                    }}>
                                        {f.status}
                                    </span>
                                </div>
                            </div>
                        ))}

                        {batchStatus.status !== 'processing' && (
                            <button
                                onClick={() => { setBatchId(null); setBatchStatus(null); setFiles([]); }}
                                style={{
                                    marginTop: 16,
                                    padding: '10px 20px',
                                    borderRadius: 8,
                                    border: '1px solid #E8E5E0',
                                    background: 'white',
                                    fontSize: 13,
                                    cursor: 'pointer',
                                }}
                            >
                                Upload More Files
                            </button>
                        )}
                    </div>
                )}
            </div>
        </div>
    );
}
```

**Step 3: Add route to App.tsx**

Add lazy import after line 19:
```typescript
const BatchUpload = React.lazy(() => import('@/pages/BatchUpload'));
```

Add route after the `/compare` route (line 66):
```tsx
<Route path="/batch-upload" element={<ProtectedRoute><BatchUpload /></ProtectedRoute>} />
```

**Step 4: Commit**

```bash
git add dashboard/src/pages/BatchUpload.tsx dashboard/src/App.tsx dashboard/src/api/client.ts
git commit -m "feat(phase8): add BatchUpload dashboard page with drag-and-drop and progress tracking (8.6)"
```

---

## Task 10: Final Integration & Testing

**Step 1: Verify backend starts**

Run: `cd backend && python -c "from app.api.v1.endpoints.documents import router; print('All endpoints loaded OK')"`

**Step 2: Verify Word Add-in builds**

Run: `cd ContraRed-PoC && npm run build`
Expected: Build succeeds with no TypeScript errors

**Step 3: Verify Dashboard builds**

Run: `cd dashboard && npm run build`
Expected: Build succeeds with no errors

**Step 4: Final commit**

```bash
git add -A
git commit -m "feat(phase8): complete Lawyer UX Flow — scan selection, shortcuts, negotiation mode, batch processing"
```
