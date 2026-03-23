# ContraRed Text Replacement Fix Proposal

## The Problem

When applying AI-suggested fixes to contract clauses in Word, the system can destroy paragraph content and create double-tracked revision marks. This is a **P0 severity** issue affecting an estimated 30-50% of fix applications.

### Root Causes (from OOXML-1 through OOXML-9 audit)

1. **PRIMARY**: `findTextInDocument()` Tier 3 (Fuse.js fuzzy) returns `paragraph.getRange()` — the entire paragraph. When `insertOoxml(replace)` replaces this range with OOXML covering only the AI's quoted fragment, the rest of the paragraph is permanently destroyed.

2. **SECONDARY**: Backend OOXML is generated from the AI's quoted `original_text` (e.g., 60 chars), not the full paragraph (e.g., 400 chars). The OOXML simply doesn't contain the surrounding text.

3. **TERTIARY**: `changeTrackingMode = trackAll` is enabled BEFORE `insertOoxml()`, causing Word to double-track: Word's live tracking wraps the OOXML's embedded `<w:del>`/`<w:ins>` markup.

4. **COMPOUNDING**: The 255-character `body.search()` limit causes truncated matches and wrong-instance selection for long clauses.

---

## Option A: Surgical Search+Replace (RECOMMENDED)

### Approach
For each word-level diff, use `paragraph.search(oldWord)` to get a tight Range of ONLY the changing text, then `range.insertText(newWord, "Replace")` with Track Changes enabled. Word natively handles the revision marks.

### Implementation
```typescript
async function applySurgicalFix(paragraph: Word.Paragraph, diffs: WordDiff[], context: Word.RequestContext) {
  // Enable Track Changes — Word handles revision marks natively
  context.document.changeTrackingMode = Word.ChangeTrackingMode.trackAll;
  await context.sync();

  // Process diffs in REVERSE order to avoid position shifting
  for (const diff of diffs.reverse()) {
    if (diff.type === 'replace') {
      const results = paragraph.search(diff.oldText, { matchCase: true });
      results.load('items');
      await context.sync();
      if (results.items.length > 0) {
        results.items[0].insertText(diff.newText, Word.InsertLocation.replace);
      }
    } else if (diff.type === 'delete') {
      const results = paragraph.search(diff.oldText, { matchCase: true });
      results.load('items');
      await context.sync();
      if (results.items.length > 0) {
        results.items[0].delete();
      }
    } else if (diff.type === 'insert') {
      // Insert after the preceding context
      const results = paragraph.search(diff.precedingText, { matchCase: true });
      results.load('items');
      await context.sync();
      if (results.items.length > 0) {
        results.items[0].insertText(diff.newText, Word.InsertLocation.after);
      }
    }
  }
  await context.sync();

  // Add ContraRed comment for attribution
  paragraph.insertComment('ContraRed AI: Applied contract revision');
}
```

### Pros
- **No paragraph destruction** — each search returns a tight range of only the changing text
- **No double-tracking** — Word handles Track Changes natively, one set of revision marks
- **Works in Word Online** — `insertText` is reliable across all platforms (unlike `insertOoxml`)
- **Preserves formatting** — replacement text inherits the formatting of the replaced range
- **Eliminates backend OOXML API call** — word-level diff can be computed frontend-side or sent as structured data instead of OOXML string
- **Individual diffs are <255 chars** — the 255-char search limit is a non-issue for word-level operations

### Cons
- **Multiple API calls per fix** — a fix with 5 word changes requires 5 search+replace operations with `context.sync()` between each. Estimated 200-500ms per fix vs ~100ms for single `insertOoxml`.
- **No custom author name** — revisions attributed to current Word user, not "ContraRed AI". Mitigated by adding a comment.
- **No custom revision colors** — uses Word's default Track Changes colors instead of red/green. Mitigated: Word already has its own Track Changes color scheme.
- **Ordering sensitivity** — must process in reverse document order. Well-understood pattern.
- **Insert-only (missing clauses) harder** — needs anchor context text to find insertion point. Can use paragraph.insertText at end or after a found anchor phrase.
- **Edge case: existing Track Changes** — `paragraph.search()` returns 0 hits when search term is broken by a deleted revision (GitHub issue #5874).

### Effort: ~16 hours
- Modify `applyAIRedline()` to use search+replace instead of OOXML (8h)
- Compute word-level diffs frontend-side or restructure backend response (4h)
- Handle missing-clause insertion with anchor-based approach (2h)
- Test with long clauses, multiple instances, existing Track Changes (2h)

---

## Option B: Improved OOXML with Tighter Range

### Approach
Keep the current OOXML generation but fix `findTextInDocument()` to ALWAYS return the tightest possible range. After Fuse.js identifies the matching paragraph, do a secondary `paragraph.search()` to narrow the range. Disable live Track Changes before OOXML insertion.

### Implementation
```typescript
// In findTextInDocument(), replace Tier 3 return:
// BEFORE (broken):
const range = matchedParagraph.paragraph.getRange();

// AFTER (fixed):
// Search within the matched paragraph for the specific clause text
const searchResults = matchedParagraph.paragraph.search(
  searchText.substring(0, 255), { matchCase: false }
);
searchResults.load('items');
await context.sync();
if (searchResults.items.length > 0) {
  return { range: searchResults.items[0], method: 'fuzzy', confidence };
}
// Only fall back to paragraph range if sub-search also fails
return { range: matchedParagraph.paragraph.getRange(), method: 'fuzzy', confidence: confidence * 0.5 };
```

And disable live tracking before OOXML insertion:
```typescript
// Disable live tracking — OOXML has its own <w:del>/<w:ins>
context.document.changeTrackingMode = Word.ChangeTrackingMode.trackNone;
range.insertOoxml(ooxml, Word.InsertLocation.replace);
// Re-enable after
context.document.changeTrackingMode = Word.ChangeTrackingMode.trackAll;
```

### Pros
- **Single API call per fix** — one `insertOoxml()` operation
- **Custom author name** — OOXML `w:author="ContraRed AI"` preserved
- **Custom revision colors** — red strikethrough / green underline controlled by OOXML
- **Minimal code change** — fixes are localized to `findTextInDocument()` + `applyAIRedline()`
- **Backend OOXML generation already works** — proven word-level diff via SequenceMatcher

### Cons
- **Still fragile for long clauses** — if the sub-search within the paragraph fails (text >255 chars or not exact match), falls back to paragraph range. The root problem is only partially fixed.
- **OOXML + Word Online fragility** — `insertOoxml` has known issues in Word Online (GitHub #3271)
- **Track Changes toggle is visible** — briefly disabling/re-enabling tracking may confuse users or leave tracking in wrong state if an error occurs mid-operation
- **Still depends on AI quote accuracy** — the OOXML diffs the AI's quoted text, not the document's actual text. Misquotes still produce wrong diffs.
- **Numbering corruption risk** — `insertOoxml` can corrupt numbering in Word 2016 (GitHub #2991)

### Effort: ~8 hours
- Fix `findTextInDocument()` Tier 3 to narrow range (3h)
- Add Track Changes toggle around OOXML insertion (1h)
- Expand OOXML to include full paragraph content when range is paragraph-level (2h)
- Test edge cases (2h)

---

## Option C: Hybrid Approach

### Approach
Route based on diff complexity:
- **Simple word swaps** (1-3 word changes): Use Option A (search+insertText)
- **Complex rewrites** (>3 changes or >30% text different): Use Option B (improved OOXML)
- **Missing clauses**: Use `insertText` with Track Changes for insertion after anchor

### Implementation
```typescript
async function applyFix(redline, fixText, context) {
  const diffs = computeWordDiffs(redline.original_text, fixText);
  const changeRatio = diffs.filter(d => d.type !== 'keep').length / diffs.length;

  if (redline.redline_type === 'missing') {
    // Missing clause: insert with Track Changes
    await applyMissingClause(redline, fixText, context);
  } else if (changeRatio < 0.3 && diffs.filter(d => d.type !== 'keep').length <= 3) {
    // Simple swap: surgical search+replace (Option A)
    await applySurgicalFix(paragraph, diffs, context);
  } else {
    // Complex rewrite: improved OOXML (Option B)
    await applyOoxmlFix(redline, fixText, context);
  }
}
```

### Pros
- **Best of both worlds** — uses the right tool for each situation
- **Simple swaps (majority of fixes) get native Track Changes** — clean, reliable
- **Complex rewrites still get full OOXML control** — author name, colors, formatting
- **Graceful degradation** — if one path fails, can fall back to the other

### Cons
- **Two code paths to maintain** — doubles testing surface, doubles potential bugs
- **Routing logic adds complexity** — the threshold for "simple vs complex" needs tuning
- **Inconsistent user experience** — some fixes show native Track Changes (user's name, default colors), others show OOXML Track Changes ("ContraRed AI", red/green). Lawyers may be confused by the inconsistency.
- **Both Option A and B cons still apply** to their respective paths

### Effort: ~24 hours
- Implement Option A path for simple swaps (8h)
- Implement Option B fixes for complex rewrites (4h)
- Build routing logic with complexity detection (4h)
- Handle missing clause insertion (2h)
- Test both paths with edge cases (4h)
- Ensure consistent UX across both paths (2h)

---

## Recommendation: Option A (Surgical Search+Replace)

### Why Option A?

1. **Eliminates the root cause entirely** — paragraph-level ranges are never used for replacement. Every search+replace operation targets only the specific text being changed.

2. **Simplest architecture** — one code path, no OOXML generation, no Track Changes toggling, no routing logic. Fewer moving parts = fewer bugs.

3. **Best cross-platform compatibility** — `insertText` works reliably in Word desktop, Word Online, and Word for Mac. `insertOoxml` has documented failures in Word Online.

4. **The cons are manageable**:
   - Multiple API calls: 200-500ms per fix is acceptable for a lawyer reviewing changes one at a time
   - No custom author: Comments provide attribution
   - No custom colors: Word's native Track Changes colors are what lawyers expect to see
   - Ordering: Reverse processing is a well-understood pattern

5. **Aligns with Microsoft's intended usage** — `insertText` with `changeTrackingMode = trackAll` is exactly how Microsoft designed the Track Changes integration for add-ins.

6. **The performance trade-off is worth it** — a fix that takes 500ms but works correctly is infinitely better than a fix that takes 100ms but destroys paragraph content.

### Migration Path
1. **Phase 1** (Week 1): Implement Option A for new fixes, keep Option B (current) as fallback
2. **Phase 2** (Week 2): Remove OOXML path once Option A is validated in production
3. **Phase 3** (Week 3): Restructure backend to return structured word diffs instead of OOXML strings, reducing payload size

### Risk Mitigation
- Keep current OOXML path as fallback during Phase 1 (feature flag)
- If `paragraph.search()` fails due to existing Track Changes (GitHub #5874), fall back to OOXML path
- Add telemetry to track which path succeeds/fails in production
