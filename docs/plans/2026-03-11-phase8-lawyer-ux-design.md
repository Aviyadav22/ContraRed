# Phase 8: Lawyer UX Flow Design (5/10 → 10/10)

**Date**: 2026-03-11
**Status**: Approved
**Scope**: All 6 sub-features (8.1–8.6)

---

## 8.1 Scan Selection (P0, Small)

**Word Add-in change.** New "Scan Selection" button next to existing "Scan Document" button. Uses `context.document.getSelection().load('text')` to grab highlighted text, sends to new backend endpoint.

**Backend endpoint:** `POST /documents/analyze-clause`
- Request: `{ clause_text: str, document_id?: UUID, playbook_id?: UUID, jurisdiction?: str }`
- Response: `{ risks: AIRedlineItem[], tokens_used: int, analysis_time_ms: int }`
- Uses `GeminiAnalyzer` with focused single-clause prompt
- Counts against quota via `check_and_increment_quota()`
- Minimum 20 chars, maximum 10KB clause text

**Frontend flow:**
1. User highlights text in Word
2. Clicks "Scan Selection" (or Ctrl+Shift+S)
3. Taskpane shows inline loading state
4. Results appear in risk list (merged with any existing scan results, or standalone)

---

## 8.2 Keyboard Shortcuts (P0, Small)

**Approach:** Taskpane-level `document.addEventListener('keydown', ...)` — works when taskpane has focus. No manifest changes needed.

| Shortcut | Action | Implementation |
|---|---|---|
| Ctrl+Shift+S | Scan selection | Calls scanSelection() |
| Ctrl+Shift+D | Scan full document | Calls scanDocument() |
| Ctrl+Shift+N | Toggle negotiation mode | Calls toggleNegotiationMode() |
| Alt+ArrowUp | Navigate to previous risk card | Decrements currentRiskIndex |
| Alt+ArrowDown | Navigate to next risk card | Increments currentRiskIndex |
| Alt+H | Highlight current risk in doc | Calls highlightAIText() on focused card |
| Alt+G | Generate fix for current risk | Calls generateFix() on focused card |
| Alt+A | Apply fix for current risk | Calls applyFix() on focused card |
| Alt+R | Research current risk | Calls researchClause() on focused card |

**State:** `currentRiskIndex: number = -1` tracks focused card. Visual focus ring (2px accent border + scroll-into-view).

---

## 8.3 Quick Re-Scan (Medium)

After applying a fix, a "Re-Scan" button appears on the risk card. Clicking it:

1. Extracts ~500 chars around the fix location from the document
2. Calls `POST /documents/analyze-clause` with the updated text
3. Updates the card in-place (risk_level may change, e.g., RED → GREEN)
4. Card animates the transition (border color change + brief pulse)

Reuses the same backend endpoint as 8.1.

---

## 8.4 Live Negotiation Mode (Large — Moat Feature)

`Ctrl+Shift+N` toggles compact UI for live calls:

**UI changes in negotiation mode:**
- Risk cards collapse to single-line: `[RED] Liability Cap — Uncapped exposure`
- Click to expand full details
- Pinned quick-scan bar at top of results area
- Auto-scan on text selection (1.5s debounce) via `Office.context.document.addHandlerAsync(Office.EventType.DocumentSelectionChanged, ...)`
- Per-card action buttons: Accept / Counter / Escalate
- Session timer (top bar, starts on mode activation)
- Free-text notes field (top bar, below timer)

**Decision tracking:**
- Each risk gets a `negotiation_decision: 'accept' | 'counter' | 'escalate' | null`
- Counter stores free-text counter-proposal
- Decisions persist in `localStorage['contrared_negotiation_session']`

**Export:** Negotiation decisions included in report export as additional columns.

---

## 8.5 Quality of Life (Medium)

### SSE Progress Updates
**Backend:** `POST /documents/analyze-full` returns SSE stream when `Accept: text/event-stream` header is present.
Events: `{ stage: 'parsing' | 'playbook' | 'analyzing' | 'verifying' | 'complete', progress: 0-100, message: string }`

**Frontend:** Multi-step progress indicator replaces spinner:
```
[✓ Parsing] → [✓ Playbook] → [● Analyzing...] → [ Verifying] → [ Complete]
```

### Persistent Scan State
Save to localStorage on every scan completion:
- `contrared_scan_state`: `{ documentName, results: AIAnalysisResult, fixedRisks: string[], timestamp }`
- On taskpane reopen: restore if < 24 hours old and same document name
- Clear on logout

### Clause Diff View
Before applying a fix, show inline word-level diff:
- Split original and suggested text into words
- Highlight removed words (red strikethrough) and added words (green underline)
- Custom implementation (no external dependency needed — simple word-diff algorithm)

### Smart Tooltips
- First-time detection: `localStorage['contrared_onboarded']`
- Tooltip targets: Scan button, playbook selector, first risk card, negotiation mode toggle
- Dismiss individually (×) or "Got it, skip all"
- CSS-only tooltips with arrow pointer

---

## 8.6 Batch Processing (XL — Dashboard)

### Dashboard Page: `BatchUpload.tsx`
- Route: `/batch-upload`
- Drag-and-drop zone for multiple .docx files (max 10)
- Playbook selector dropdown
- "Analyze All" button
- Progress grid: filename | status (queued/processing/done/error) | risk counts
- Click any completed file to see full results

### Backend Endpoints
`POST /documents/batch-analyze`
- Multipart form data (up to 10 .docx files)
- Returns `{ batch_id: UUID }`
- Processes concurrently (3 parallel via asyncio.Semaphore)

`GET /documents/batch/{batch_id}/status`
- Returns `{ files: [{ filename, status, document_id?, risk_summary? }], overall_progress: 0-100 }`

`GET /documents/batch/{batch_id}/summary`
- Cross-document risk pattern analysis
- Aggregate risk counts, common issues across documents

### API Client additions (dashboard `client.ts`)
- `batchAnalyze(files: File[], playbookId?: string): Promise<{ batch_id: string }>`
- `getBatchStatus(batchId: string): Promise<BatchStatus>`
- `getBatchSummary(batchId: string): Promise<BatchSummary>`

---

## Files Changed

### Backend (Modified)
- `app/api/v1/endpoints/documents.py` — new analyze-clause + batch endpoints
- `app/api/v1/router.py` — register new routes
- `app/services/gemini_analyzer.py` — add `analyze_clause()` method

### Backend (New)
- (No new files — all endpoints go in existing documents.py)

### Word Add-in (Modified)
- `src/taskpane/taskpane.ts` — scan selection, keyboard shortcuts, negotiation mode, QoL features
- `src/taskpane/taskpane.html` — new UI elements (scan selection button, negotiation mode panel, progress stepper, tooltips)
- `src/taskpane/api.ts` — new `analyzeClause()` method

### Dashboard (Modified)
- `src/App.tsx` — add batch-upload route
- `src/api/client.ts` — add batch API methods

### Dashboard (New)
- `src/pages/BatchUpload.tsx` — batch processing page

### Migration (New)
- `backend/migrations/011_batch_processing.sql` — batch_jobs table
