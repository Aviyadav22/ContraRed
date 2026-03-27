/**
 * ContraRed - Word Add-in Main Logic
 * 
 * Implements: Login, Document Scan, Risk Highlighting, Redline Application
 * Now with AI-First analysis using Gemini for holistic contract review.
 */

import { api, RedlineItem, AnalysisResult, ClauseAnalysisResult, NegotiationDecision, NegotiationSession, DocumentListItem } from './api';
import Fuse from 'fuse.js';

// ============================================================================
// Utility
// ============================================================================

/** Escape HTML entities to prevent XSS when interpolating into innerHTML. */
function escapeHtml(str: string): string {
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

/** Compute a simple numeric hash of text for document fingerprinting. */
function simpleHash(text: string): string {
    let hash = 0;
    const sample = text.substring(0, 500) + text.substring(Math.max(0, text.length - 500));
    for (let i = 0; i < sample.length; i++) {
        const chr = sample.charCodeAt(i);
        hash = ((hash << 5) - hash) + chr;
        hash |= 0; // Convert to 32-bit integer
    }
    return hash.toString(36) + '_' + text.length;
}

/** Show a temporary toast message on a risk card. */
function showToastOnCard(card: HTMLElement, message: string): void {
  const existing = card.querySelector('.card-toast');
  if (existing) existing.remove();
  const toast = document.createElement('div');
  toast.className = 'card-toast';
  toast.textContent = message;
  card.appendChild(toast);
  setTimeout(() => toast.remove(), 5000);
}

/** Debug logger — only outputs in development builds. */
// @ts-expect-error process.env injected by webpack DefinePlugin
const IS_DEV = typeof process !== 'undefined' && process.env?.NODE_ENV === 'development';
const log = {
  info: (...args: unknown[]) => { if (IS_DEV) console.log('[ContraRed]', ...args); },
  warn: (...args: unknown[]) => { if (IS_DEV) console.warn('[ContraRed]', ...args); },
  error: (...args: unknown[]) => { if (IS_DEV) console.error('[ContraRed]', ...args); },
};

// ============================================================================
// Persistent Scan State
// ============================================================================

/** Save current scan state to localStorage for session persistence. */
// Note: Scan state may contain contract excerpts. Cleared on logout and after 24h TTL.
function saveScanState(docFingerprint?: string): void {
    if (!currentAIAnalysis) return;
    try {
        const state = {
            analysis: currentAIAnalysis,
            fixedRisks: Array.from(fixedRisks),
            timestamp: Date.now(),
            docHash: docFingerprint || localStorage.getItem('contrared_doc_hash') || '',
        };
        localStorage.setItem('contrared_scan_state', JSON.stringify(state));
        log.info('Scan state saved to localStorage');
    } catch (e) {
        log.warn('Failed to save scan state:', e);
    }
}

/** Restore previous scan state from localStorage (if < 24h old and same document). */
async function restoreScanState(): Promise<boolean> {
    try {
        const stored = localStorage.getItem('contrared_scan_state');
        if (!stored) return false;
        const state = JSON.parse(stored);
        const age = Date.now() - state.timestamp;
        if (age > 24 * 60 * 60 * 1000) {
            localStorage.removeItem('contrared_scan_state');
            return false;
        }

        // Document identity check: compare fingerprint of current doc vs saved
        if (state.docHash) {
            try {
                const currentText = await getDocumentText();
                const currentHash = simpleHash(currentText);
                if (state.docHash !== currentHash) {
                    log.info('Document fingerprint mismatch — not restoring stale scan state');
                    localStorage.removeItem('contrared_scan_state');
                    return false;
                }
            } catch {
                // If we can't read the document, skip the check
            }
        }

        currentAIAnalysis = state.analysis;
        state.fixedRisks.forEach((id: string) => fixedRisks.add(id));
        displayAIResults(currentAIAnalysis!);
        log.info('Scan state restored from localStorage');
        return true;
    } catch {
        return false;
    }
}

// ============================================================================
// Word-Level Diff
// ============================================================================

/** Compute a word-level diff between original and modified text, returning HTML. */
function wordDiff(original: string, modified: string): string {
    const origWords = original.split(/(\s+)/);
    const modWords = modified.split(/(\s+)/);
    const m = origWords.length;
    const n = modWords.length;

    // LCS table
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

    // Backtrack
    const ops: Array<{ type: 'keep' | 'del' | 'ins'; text: string }> = [];
    let i = m, j = n;
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

    const result: string[] = [];
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

// ============================================================================
// Smart Tooltips (Onboarding)
// ============================================================================

const TOOLTIPS = [
    { target: 'scanBtn', text: 'Click here to scan the entire document for legal risks. The AI will analyze every clause against your selected playbook.' },
    { target: 'scanSelectionBtn', text: 'Highlight text in Word first, then click this to scan just that selection. Great for quick checks during calls.' },
    { target: 'playbookSelect', text: 'Choose which playbook to scan against. Different playbooks have different rules for different contract types.' },
];

function showOnboardingTooltips(): void {
    if (localStorage.getItem('contrared_onboarded')) return;
    let currentTooltip = 0;

    function showNextTooltip(): void {
        // Clear highlight from previous
        if (currentTooltip > 0 && currentTooltip <= TOOLTIPS.length) {
            const prev = document.getElementById(TOOLTIPS[currentTooltip - 1].target);
            if (prev) { prev.style.zIndex = ''; prev.style.boxShadow = ''; prev.style.position = ''; }
        }
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
        const target = document.getElementById(tip.target);
        if (target) {
            target.style.position = 'relative';
            target.style.zIndex = '1001';
            target.style.boxShadow = '0 0 0 4px rgba(192, 57, 43, 0.3)';
        }
        currentTooltip++;
    }

    document.getElementById('tooltipNext')?.addEventListener('click', showNextTooltip);
    document.getElementById('tooltipSkip')?.addEventListener('click', () => {
        localStorage.setItem('contrared_onboarded', 'true');
        const overlay = document.getElementById('tooltipOverlay');
        if (overlay) overlay.style.display = 'none';
        TOOLTIPS.forEach(t => {
            const el = document.getElementById(t.target);
            if (el) { el.style.zIndex = ''; el.style.boxShadow = ''; el.style.position = ''; }
        });
    });

    showNextTooltip();
}

/**
 * Read surrounding context (paragraph text) around a given text in the Word document.
 * Gives the AI model the full clause context for better fix generation.
 */
async function getSurroundingContext(originalText: string): Promise<string> {
  try {
    return await Word.run(async (context) => {
      // Use targeted search instead of loading ALL paragraphs
      const body = context.document.body;
      const searchText = originalText.substring(0, Math.min(50, originalText.length));
      const searchResults = body.search(searchText, { matchCase: false });
      searchResults.load('items');
      await context.sync();

      if (searchResults.items.length === 0) return '';

      // Get the paragraph containing the first match
      const matchRange = searchResults.items[0];
      const matchParas = matchRange.paragraphs;
      matchParas.load('items/text');
      await context.sync();

      if (matchParas.items.length === 0) return '';

      const matchedPara = matchParas.items[0];

      // Get the range that includes surrounding paragraphs
      // Use expandTo with paragraph before and after
      const texts: string[] = [];
      try {
        // Try to get previous paragraph
        const prevSearch = body.paragraphs;
        prevSearch.load('items/text');
        await context.sync();

        // Find our paragraph index efficiently by text match
        let foundIdx = -1;
        for (let i = 0; i < prevSearch.items.length; i++) {
          if (prevSearch.items[i].text === matchedPara.text && foundIdx === -1) {
            foundIdx = i;
            break;
          }
        }

        if (foundIdx > 0) texts.push(prevSearch.items[foundIdx - 1].text);
        if (foundIdx >= 0) texts.push(prevSearch.items[foundIdx].text);
        if (foundIdx >= 0 && foundIdx + 1 < prevSearch.items.length) texts.push(prevSearch.items[foundIdx + 1].text);
      } catch {
        // Fallback: just return the matched paragraph text
        texts.push(matchedPara.text);
      }

      const combined = texts.join('\n');
      return combined.length > 5000 ? combined.slice(0, 5000) : combined;
    });
  } catch (error) {
    log.warn('Failed to get surrounding context:', error);
    return '';
  }
}

// ============================================================================
// Read-Only Document Check
// ============================================================================

/** Check if the document is read-only or protected. */
async function isDocumentReadOnly(): Promise<boolean> {
  try {
    return await Word.run(async (context) => {
      const properties = context.document.properties;
      properties.load('security');
      await context.sync();
      // security: 0 = none, 1 = password protected, etc.
      return properties.security !== 0;
    });
  } catch {
    // If we can't check, assume writable
    return false;
  }
}

/** Show a notification banner at the top of the results area. */
function showNotification(message: string, type: 'error' | 'warning' | 'info' = 'info'): void {
  const results = document.getElementById('resultsSection') as HTMLElement | null;
  const target = results || document.querySelector('.container');
  if (!target) { alert(message); return; }

  const existing = target.querySelector('.contrared-notification');
  if (existing) existing.remove();

  const colors: Record<string, { bg: string; border: string; text: string }> = {
    error: { bg: '#FDECEA', border: '#F1948A', text: '#C0392B' },
    warning: { bg: '#FEF9EC', border: '#F0C060', text: '#B7770D' },
    info: { bg: '#EDF7F1', border: '#82C9A0', text: '#1A7A4A' },
  };
  const c = colors[type];

  const notif = document.createElement('div');
  notif.className = 'contrared-notification';
  notif.setAttribute('role', 'alert');
  notif.setAttribute('aria-live', 'assertive');
  notif.style.cssText = `padding:10px 14px;margin-bottom:12px;border-radius:8px;font-size:12px;background:${c.bg};border:1px solid ${c.border};color:${c.text};`;
  notif.textContent = message;
  target.prepend(notif);
  setTimeout(() => notif.remove(), 8000);
}

// ============================================================================
// State
// ============================================================================

let currentAIAnalysis: AnalysisResult | null = null;
let lastScannedText: string = '';  // Cache contract text for fix verification
const fixedRisks: Set<string> = new Set();
let isScanning = false;  // Guard against double-click race condition

// Tracks applied fixes with location info for precise undo targeting
const appliedFixesMap: Map<string, { originalText: string; fixText: string; paragraphIndex: number; contextHash: string }> = new Map();

// Filter & Sort state
let activeFilter: 'ALL' | 'RED' | 'YELLOW' | 'UNFIXED' = 'ALL';
let activeSort: 'risk_level' | 'rule_name' | 'confidence' = 'risk_level';
let searchQuery = '';

// Selection scanning state
let isSelectionScanning = false;

// Keyboard navigation state
let currentRiskIndex = -1;

// Negotiation mode state
let negotiationMode = false;
let negotiationSession: NegotiationSession | null = null;
let negotiationTimer: ReturnType<typeof setInterval> | null = null;
let selectionDebounceTimer: ReturnType<typeof setTimeout> | null = null;
let negotiationNotesListenerAttached = false;

// ============================================================================
// DOM Elements
// ============================================================================

const getEl = (id: string) => document.getElementById(id);

// Panels
const loginPanel = () => getEl('loginPanel');
const mainPanel = () => getEl('mainPanel');

// Login
const emailInput = () => getEl('email') as HTMLInputElement;
const passwordInput = () => getEl('password') as HTMLInputElement;
const loginBtn = () => getEl('loginBtn');
const loginBtnText = () => getEl('loginBtnText');
const loginSpinner = () => getEl('loginSpinner');
const loginError = () => getEl('loginError');

// User
const userAvatar = () => getEl('userAvatar');
const userName = () => getEl('userName');
const userTier = () => getEl('userTier');
const logoutBtn = () => getEl('logoutBtn');

// Scan
const scanBtn = () => getEl('scanBtn');
const scanBtnText = () => getEl('scanBtnText');
const scanSpinner = () => getEl('scanSpinner');

// Results
const resultsSection = () => getEl('resultsSection');
const redCount = () => getEl('redCount');
const yellowCount = () => getEl('yellowCount');
const greenCount = () => getEl('greenCount');
const riskCount = () => getEl('riskCount');
const riskList = () => getEl('riskList');
const emptyState = () => getEl('emptyState');

// Status
const statusIndicator = () => getEl('statusIndicator');
const statusText = () => getEl('statusText');

// ============================================================================
// Initialization
// ============================================================================

Office.onReady((info) => {
  if (info.host === Office.HostType.Word) {
    statusIndicator()?.classList.remove('offline');
    if (statusText()) statusText()!.textContent = `Connected to Word`;

    // Check if already logged in
    if (api.isLoggedIn()) {
      showMainPanel();
    } else {
      showLoginPanel();
    }

    // Bind event handlers
    loginBtn()?.addEventListener('click', handleLogin);
    logoutBtn()?.addEventListener('click', handleLogout);
    scanBtn()?.addEventListener('click', scanDocument);
    document.getElementById('scanSelectionBtn')?.addEventListener('click', scanSelection);
    document.getElementById('scanBtn')?.setAttribute('title', 'Scan Document (Ctrl+Shift+D)');
    document.getElementById('scanSelectionBtn')?.setAttribute('title', 'Scan Selection (Ctrl+Alt+S)');

    // Shortcuts help panel
    document.getElementById('shortcutsHelpBtn')?.addEventListener('click', toggleShortcutsPanel);
    document.getElementById('shortcutsPanelClose')?.addEventListener('click', () => {
      const panel = document.getElementById('shortcutsPanel');
      if (panel) panel.style.display = 'none';
      shortcutsPanelTrap?.deactivate();
    });

    // Template picker
    document.getElementById('templateBtn')?.addEventListener('click', toggleTemplatePicker);
    document.getElementById('templatePickerClose')?.addEventListener('click', () => {
      const picker = document.getElementById('templatePicker');
      if (picker) picker.style.display = 'none';
      templatePickerTrap?.deactivate();
    });

    // Allow Enter key to submit login
    passwordInput()?.addEventListener('keypress', (e) => {
      if (e.key === 'Enter') handleLogin();
    });

    // Filter buttons
    document.querySelectorAll('.filter-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        activeFilter = (btn as HTMLElement).dataset.filter as typeof activeFilter;
        renderRedlineList();
        updateApplyAllCount();
      });
    });

    // Search input with debounce
    let searchTimeout: ReturnType<typeof setTimeout>;
    const searchInput = document.getElementById('riskSearchInput') as HTMLInputElement;
    searchInput?.addEventListener('input', () => {
      clearTimeout(searchTimeout);
      searchTimeout = setTimeout(() => {
        searchQuery = searchInput.value;
        renderRedlineList();
        updateApplyAllCount();
      }, 200);
    });

    // Sort select
    const sortSelect = document.getElementById('sortSelect') as HTMLSelectElement;
    sortSelect?.addEventListener('change', () => {
      activeSort = sortSelect.value as typeof activeSort;
      renderRedlineList();
    });

    // Bulk apply all
    document.getElementById('applyAllBtn')?.addEventListener('click', applyAllRedlines);

    // Revert all applied fixes
    document.getElementById('revertAllBtn')?.addEventListener('click', revertAllFixes);

    // Export report
    document.getElementById('exportReportBtn')?.addEventListener('click', exportReport);

    // Keyboard shortcuts (Phase 8)
    document.addEventListener('keydown', handleKeyboardShortcuts);

    // Negotiation mode buttons (Phase 8.4)
    document.getElementById('negotiationBtn')?.addEventListener('click', toggleNegotiationMode);
    document.getElementById('exitNegotiationBtn')?.addEventListener('click', toggleNegotiationMode);
    document.getElementById('exportNegotiationBtn')?.addEventListener('click', exportNegotiationDecisions);

  } else {
    if (statusText()) statusText()!.textContent = 'Not running in Word';
  }
});

// ============================================================================
// Panel Management
// ============================================================================

function showLoginPanel(): void {
  loginPanel()?.classList.add('active');
  mainPanel()?.classList.remove('active');
  // Clear any previous errors
  hideLoginError();
}

function showMainPanel(): void {
  loginPanel()?.classList.remove('active');
  mainPanel()?.classList.add('active');

  // Update user info
  const user = api.getUser();
  if (user) {
    const initials = user.name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2);
    if (userAvatar()) userAvatar()!.textContent = initials;
    if (userName()) userName()!.textContent = user.name;
    if (userTier()) userTier()!.textContent = `${user.subscription_tier} tier`;

    // Show admin actions if user is admin or super_admin
    const adminActions = document.getElementById('adminActions');
    if (adminActions && (user.role === 'admin' || user.role === 'super_admin')) {
      adminActions.style.display = 'block';
      bindAdminActions();
    }
  }

  // Health check on init
  api.healthCheck().then(() => {
    if (statusText()) statusText()!.textContent = 'Connected to ContraRed';
    statusIndicator()?.classList.remove('offline');
  }).catch(() => {
    showNotification('Cannot connect to ContraRed server. Some features may be unavailable.', 'warning');
  });

  // Load available playbooks
  loadPlaybooks();

  // Restore previous scan state if available
  restoreScanState();

  // Load recent scans
  loadRecentScans();

  // Show onboarding tooltips for first-time users
  setTimeout(showOnboardingTooltips, 500);
}

/**
 * Load and display recent scan history.
 */
async function loadRecentScans(): Promise<void> {
  const section = document.getElementById('recentScansSection');
  const list = document.getElementById('recentScansList');
  const countBadge = document.getElementById('recentScansCount');
  if (!section || !list) return;

  try {
    const docs = await api.listDocuments(5);
    if (docs.length === 0) {
      section.style.display = 'none';
      return;
    }

    section.style.display = 'block';
    if (countBadge) countBadge.textContent = `(${docs.length})`;

    list.innerHTML = docs.map((doc: DocumentListItem) => {
      const date = new Date(doc.created_at);
      const dateStr = date.toLocaleDateString('en-IN', { day: 'numeric', month: 'short' });
      const red = doc.risk_summary?.red || 0;
      const yellow = doc.risk_summary?.yellow || 0;

      return `
        <div class="recent-scan-item" data-doc-id="${escapeHtml(doc.id)}" title="${escapeHtml(doc.filename)} — ${doc.total_risks} risks" style="cursor:pointer;">
          <span class="recent-scan-name">${escapeHtml(doc.filename)}</span>
          <div class="recent-scan-meta">
            <div class="recent-scan-risks">
              ${red > 0 ? `<span class="risk-dot red">${red}R</span>` : ''}
              ${yellow > 0 ? `<span class="risk-dot yellow">${yellow}Y</span>` : ''}
              ${red === 0 && yellow === 0 ? '<span class="risk-dot" style="color: #10B981;">Clean</span>' : ''}
            </div>
            <span>${dateStr}</span>
          </div>
        </div>
      `;
    }).join('');

    // Make recent scan items clickable
    list.querySelectorAll('.recent-scan-item').forEach(item => {
      item.addEventListener('click', () => {
        showNotification('Reloading previous scan results is coming soon. For now, please re-scan the document.', 'info');
      });
    });

    // Toggle collapse — bind once to prevent duplicate listeners
    const toggle = document.getElementById('recentScansToggle');
    const chevron = document.getElementById('recentScansChevron');
    if (toggle && !toggle.dataset.bound) {
      toggle.dataset.bound = '1';
      toggle.addEventListener('click', () => {
        const isHidden = list.style.display === 'none';
        list.style.display = isHidden ? 'flex' : 'none';
        if (chevron) {
          chevron.style.transform = isHidden ? 'rotate(0deg)' : 'rotate(-90deg)';
        }
      });
    }
  } catch (error) {
    log.warn('Could not load recent scans:', error);
    section.style.display = 'none';
  }
}

// ========================================================================
// Template Picker
// ========================================================================

async function toggleTemplatePicker(): Promise<void> {
  const picker = document.getElementById('templatePicker');
  if (!picker) return;

  if (picker.style.display === 'block') {
    templatePickerTrap?.deactivate();
    picker.style.display = 'none';
    return;
  }

  picker.style.display = 'block';
  templatePickerTrap = new FocusTrap(picker, () => { picker.style.display = 'none'; });
  templatePickerTrap.activate();
  const list = document.getElementById('templateList');
  if (!list) return;

  list.innerHTML = '<div class="clause-picker-loading">Loading templates...</div>';

  try {
    const templates = await api.listTemplates();
    if (templates.length === 0) {
      list.innerHTML = '<div class="clause-picker-empty">No templates available</div>';
      return;
    }

    list.innerHTML = templates.map(t => `
      <div class="template-item" data-template-id="${escapeHtml(t.id)}" data-playbook-id="${escapeHtml(t.paired_playbook_id || '')}">
        <div class="template-item-name">${escapeHtml(t.name)}</div>
        <div class="template-item-desc">${escapeHtml(t.description || '')}</div>
        <div class="template-item-meta">
          <span class="template-badge ${(t.category || '').replace(/[^a-zA-Z0-9_-]/g, '')}">${escapeHtml(t.category)}</span>
          ${t.is_premium ? '<span class="template-badge premium">premium</span>' : ''}
          ${t.paired_playbook_name ? `<span style="font-size:10px;color:var(--text-muted);">+ ${escapeHtml(t.paired_playbook_name)}</span>` : ''}
        </div>
      </div>
    `).join('');

    // Bind click handlers
    list.querySelectorAll('.template-item').forEach(item => {
      item.addEventListener('click', () => {
        const templateId = (item as HTMLElement).dataset.templateId;
        const playbookId = (item as HTMLElement).dataset.playbookId;
        if (templateId) applyTemplate(templateId, playbookId || undefined);
      });
    });
  } catch (error) {
    list.innerHTML = '<div class="generate-error">Failed to load templates</div>';
  }
}

async function applyTemplate(templateId: string, pairedPlaybookId?: string): Promise<void> {
  const picker = document.getElementById('templatePicker');
  if (picker) picker.style.display = 'none';

  // Office webview doesn't support window.confirm() — proceed directly

  try {
    const data = await api.downloadTemplate(templateId);

    // Insert template content into Word document
    await Word.run(async (context) => {
      const body = context.document.body;
      body.insertText(data.template_content || '', Word.InsertLocation.replace);
      await context.sync();
    });

    // Auto-select paired playbook if available
    if (pairedPlaybookId || data.paired_playbook_id) {
      const select = document.getElementById('playbookSelect') as HTMLSelectElement | null;
      if (select) {
        const pbId = pairedPlaybookId || data.paired_playbook_id || '';
        const option = Array.from(select.options).find(o => o.value === pbId);
        if (option) {
          select.value = pbId;
        }
      }
    }

    log.info(`Template "${data.name}" inserted`);
  } catch (error) {
    log.error('Template insert failed:', error instanceof Error ? error.message : 'Unknown error');
  }
}

// Focus trap instances for modal dialogs
let playBookModalTrap: FocusTrap | null = null;
let templatePickerTrap: FocusTrap | null = null;
let shortcutsPanelTrap: FocusTrap | null = null;

// Admin feature handlers — bind once to prevent duplicate listeners
let adminActionsBound = false;
function bindAdminActions(): void {
  if (adminActionsBound) return;
  adminActionsBound = true;

  const addPlaybookBtn = document.getElementById('addPlaybookBtn');
  const createSubmit = document.getElementById('createPlaybookSubmit');
  const createCancel = document.getElementById('createPlaybookCancel');

  addPlaybookBtn?.addEventListener('click', () => {
    const modal = document.getElementById('createPlaybookModal');
    if (modal) {
      modal.style.display = 'block';
      playBookModalTrap = new FocusTrap(modal, () => { modal.style.display = 'none'; clearPlaybookForm(); });
      playBookModalTrap.activate();
    }
  });

  createCancel?.addEventListener('click', () => {
    const modal = document.getElementById('createPlaybookModal');
    if (modal) modal.style.display = 'none';
    playBookModalTrap?.deactivate();
    clearPlaybookForm();
  });

  createSubmit?.addEventListener('click', handleCreatePlaybook);
}

async function handleCreatePlaybook(): Promise<void> {
  const nameInput = document.getElementById('newPlaybookName') as HTMLInputElement;
  const descInput = document.getElementById('newPlaybookDesc') as HTMLInputElement;
  const categorySelect = document.getElementById('newPlaybookCategory') as HTMLSelectElement;
  const errorDiv = document.getElementById('createPlaybookError');
  const submitBtn = document.getElementById('createPlaybookSubmit') as HTMLButtonElement;

  const name = nameInput?.value?.trim();
  if (!name) {
    if (errorDiv) { errorDiv.textContent = 'Name is required'; errorDiv.classList.add('show'); }
    return;
  }

  if (name.length > 100) {
    if (errorDiv) { errorDiv.textContent = 'Playbook name must be 100 characters or fewer'; errorDiv.classList.add('show'); }
    return;
  }

  if (errorDiv) errorDiv.classList.remove('show');
  if (submitBtn) submitBtn.disabled = true;

  try {
    await api.createPlaybook(name, descInput?.value?.trim() || undefined, categorySelect?.value || 'custom');
    // Close modal and refresh playbooks
    const modal = document.getElementById('createPlaybookModal');
    if (modal) modal.style.display = 'none';
    playBookModalTrap?.deactivate();
    clearPlaybookForm();
    await loadPlaybooks();
  } catch (error) {
    if (errorDiv) {
      errorDiv.textContent = (error instanceof Error ? error.message : String(error)) || 'Failed to create playbook';
      errorDiv.classList.add('show');
    }
  } finally {
    if (submitBtn) submitBtn.disabled = false;
  }
}

function clearPlaybookForm(): void {
  const nameInput = document.getElementById('newPlaybookName') as HTMLInputElement;
  const descInput = document.getElementById('newPlaybookDesc') as HTMLInputElement;
  const errorDiv = document.getElementById('createPlaybookError');
  if (nameInput) nameInput.value = '';
  if (descInput) descInput.value = '';
  if (errorDiv) errorDiv.classList.remove('show');
}

// Playbook selector element
const playbookSelect = () => document.getElementById('playbookSelect') as HTMLSelectElement | null;

async function loadPlaybooks(): Promise<void> {
  const select = playbookSelect();
  if (!select) return;

  // Reset to default option
  select.innerHTML = '<option value="">Default Rules</option>';

  try {
    const playbooks = await api.listPlaybooks();

    playbooks.forEach(playbook => {
      const option = document.createElement('option');
      option.value = playbook.id;
      option.textContent = playbook.name;
      if (playbook.is_default) {
        option.textContent += ' (Default)';
      }
      if (playbook.is_public) {
        option.textContent += ' 🌐';
      }
      select.appendChild(option);
    });
  } catch (error) {
    log.warn('Could not load playbooks:', error);
    // Keep default option, don't crash
  }
}

// ============================================================================
// Authentication
// ============================================================================

async function handleLogin(): Promise<void> {
  const email = emailInput()?.value?.trim();
  const password = passwordInput()?.value;

  if (!email || !password) {
    showLoginError('Please enter email and password');
    return;
  }

  if (!email.includes('@')) {
    showLoginError('Please enter a valid email address');
    return;
  }

  setLoginLoading(true);
  hideLoginError();

  try {
    await api.login(email, password);
    showMainPanel();
  } catch (error) {
    showLoginError((error instanceof Error ? error.message : String(error)) || 'Login failed');
  } finally {
    setLoginLoading(false);
  }
}

function handleLogout(): void {
  api.logout();

  // Clear all scan and analysis state
  currentAIAnalysis = null;
  fixedRisks.clear();
  currentRiskIndex = -1;
  isScanning = false;
  isSelectionScanning = false;

  // Clear negotiation state
  negotiationMode = false;
  negotiationSession = null;
  if (negotiationTimer) {
    clearInterval(negotiationTimer);
    negotiationTimer = null;
  }

  // Clear all persisted state (but keep onboarding — it's per-device, not per-session)
  // Note: Scan state may contain contract excerpts. Cleared on logout and after 24h TTL.
  localStorage.removeItem('contrared_scan_state');
  localStorage.removeItem('contrared_negotiation_session');
  localStorage.removeItem('contrared_doc_hash');

  // Reset UI
  if (resultsSection()) resultsSection()!.style.display = 'none';
  if (riskList()) riskList()!.innerHTML = '';

  showLoginPanel();
}

function setLoginLoading(loading: boolean): void {
  if (loginBtn()) (loginBtn() as HTMLButtonElement).disabled = loading;
  if (loginBtnText()) loginBtnText()!.style.display = loading ? 'none' : 'inline';
  if (loginSpinner()) loginSpinner()!.style.display = loading ? 'block' : 'none';
}

function showLoginError(message: string): void {
  if (loginError()) {
    loginError()!.textContent = message;
    loginError()!.classList.add('show');
  }
}

function hideLoginError(): void {
  if (loginError()) {
    loginError()!.classList.remove('show');
  }
}

// ============================================================================
// Document Scanning - AI-First Implementation
// ============================================================================

/**
 * Three-tier text search in Word document.
 * 1. Exact match using Word API
 * 2. Normalized match (strip punctuation/whitespace)
 * 3. Fuzzy match using fuse.js
 */
async function findTextInDocument(
  searchText: string,
  context: Word.RequestContext,
  expectedPosition?: number  // approximate paragraph index from AI analysis for position awareness
): Promise<{ range: Word.Range | null; method: 'exact' | 'normalized' | 'fuzzy' | 'none'; confidence: number }> {
  const body = context.document.body;
  const WORD_SEARCH_LIMIT = 255;

  // Tier 1: Exact search (Word API caps at 255 chars)
  const tier1Text = searchText.length <= WORD_SEARCH_LIMIT
    ? searchText
    : searchText.slice(0, WORD_SEARCH_LIMIT);
  const exactResults = body.search(tier1Text, { matchCase: false, matchWholeWord: false });
  exactResults.load('items');
  await context.sync();

  if (exactResults.items.length > 0) {
    // P0 #3: 255-char long clause handling — verify full text matches when truncated
    if (searchText.length > WORD_SEARCH_LIMIT && exactResults.items.length > 0) {
      // For each candidate match, expand range and verify full text
      for (const candidate of exactResults.items) {
        try {
          // Load the paragraph text and check if full text is contained
          const parentParagraph = candidate.paragraphs.getFirst();
          parentParagraph.load('text');
          await context.sync();
          const paraText = parentParagraph.text;
          // Normalize whitespace for comparison
          const normalizedSearch = searchText.replace(/\s+/g, ' ').trim();
          const normalizedPara = paraText.replace(/\s+/g, ' ').trim();
          if (normalizedPara.includes(normalizedSearch) || normalizedSearch.includes(normalizedPara)) {
            // Full text confirmed — select best match with position awareness
            return { range: candidate, method: 'exact', confidence: 1.0 };
          }
        } catch {
          // If expansion fails, fall through
        }
      }
      // If no candidate fully matched, still use best candidate (truncated match)
      // but with lower confidence — fall through to pick best by position
    }

    // P0 #2: Position awareness — pick closest match when multiple results
    if (exactResults.items.length > 1 && expectedPosition !== undefined) {
      try {
        // Load paragraph info for each result to determine position
        const paragraphs = body.paragraphs;
        paragraphs.load('items/text');
        await context.sync();

        let bestIdx = 0;
        let bestDist = Infinity;

        for (let ri = 0; ri < exactResults.items.length; ri++) {
          const resultRange = exactResults.items[ri];
          // Find which paragraph contains this result by checking paragraph containment
          const resultParent = resultRange.paragraphs.getFirst();
          resultParent.load('text');
          await context.sync();

          // Find paragraph index by matching text
          for (let pi = 0; pi < paragraphs.items.length; pi++) {
            if (paragraphs.items[pi].text === resultParent.text) {
              const dist = Math.abs(pi - expectedPosition);
              if (dist < bestDist) {
                bestDist = dist;
                bestIdx = ri;
              }
              break;
            }
          }
        }

        return { range: exactResults.items[bestIdx], method: 'exact', confidence: searchText.length <= WORD_SEARCH_LIMIT ? 1.0 : 0.9 };
      } catch {
        // If position detection fails, fall back to first match
      }
    }

    return { range: exactResults.items[0], method: 'exact', confidence: searchText.length <= WORD_SEARCH_LIMIT ? 1.0 : 0.9 };
  }

  // Tier 2: Normalized search (strip punctuation, try first 150 chars for better matching)
  const normalizedSearch = searchText.replace(/[^\w\s]/g, '').trim().slice(0, 150);
  if (normalizedSearch.length > 10) {
    const normResults = body.search(normalizedSearch, { matchCase: false });
    normResults.load('items');
    await context.sync();

    if (normResults.items.length > 0) {
      return { range: normResults.items[0], method: 'normalized', confidence: 0.8 };
    }
  }

  // Tier 3: Fuzzy match using fuse.js on paragraphs
  const paragraphs = body.paragraphs;
  paragraphs.load('items/text');
  await context.sync();

  const paragraphData = paragraphs.items.map((p, index) => ({
    text: p.text,
    index,
    paragraph: p
  })).filter(p => p.text.trim().length > 0);

  if (paragraphData.length === 0) {
    return { range: null, method: 'none', confidence: 0 };
  }

  const fuse = new Fuse(paragraphData, {
    keys: ['text'],
    threshold: 0.25,  // Require 75% similarity minimum
    distance: 1000,
    minMatchCharLength: 15,
    includeScore: true,
  });

  const fuzzyResults = fuse.search(searchText);

  if (fuzzyResults.length > 0 && fuzzyResults[0].score !== undefined) {
    const bestMatch = fuzzyResults[0];
    const confidence = 1 - (bestMatch.score || 0);  // Convert score to confidence

    // Reject fuzzy matches below minimum confidence to avoid highlighting wrong clauses
    const MIN_FUZZY_CONFIDENCE = 0.6;
    if (confidence < MIN_FUZZY_CONFIDENCE) {
      return { range: null, method: 'none', confidence: 0 };
    }

    // Get the range of the matched paragraph
    const matchedParagraph = paragraphData[bestMatch.refIndex];
    if (!matchedParagraph) {
      return { range: null, method: 'none' as const, confidence: 0 };
    }
    const range = matchedParagraph.paragraph.getRange();
    range.load();
    await context.sync();

    return { range, method: 'fuzzy', confidence };
  }

  return { range: null, method: 'none', confidence: 0 };
}

/**
 * AI-First document scanning using Gemini.
 * Sends full contract + playbook to Gemini for holistic analysis.
 */
async function scanDocument(): Promise<void> {
  if (isScanning) return;  // Prevent double-click race condition
  isScanning = true;
  setScanLoading(true);

  try {
    // Step 1: Get document text from Word
    const documentText = await getDocumentText();
    lastScannedText = documentText || '';

    if (!documentText || documentText.trim().length < 50) {
      displayScanError(new Error('Document appears to be empty or too short. Please add some contract text.'));
      return;
    }

    if (documentText.length > 500000) {
      displayScanError(new Error('Document too large — the document exceeds the maximum size of ~500KB of text. Try scanning a section at a time.'));
      return;
    }

    // Step 2: Call AI-First analysis API (with selected playbook)
    const selectedPlaybookId = playbookSelect()?.value || undefined;
    log.info('Starting analysis...');

    // Get actual document filename
    let docName = 'document.docx';
    try {
      await Word.run(async (ctx) => {
        const props = ctx.document.properties;
        props.load('title');
        await ctx.sync();
        if (props.title) docName = props.title;
      });
    } catch {
      // fallback to document.docx
    }

    const partySideSelect = document.getElementById('partySideSelect') as HTMLSelectElement;
    const selectedPartySide = partySideSelect?.value || 'buyer';
    const aiResult = await api.analyzeWithAI(documentText, docName, selectedPlaybookId, selectedPartySide);

    currentAIAnalysis = aiResult;
    fixedRisks.clear();

    // Store document fingerprint for identity check on restore
    const docFingerprint = simpleHash(documentText);
    localStorage.setItem('contrared_doc_hash', docFingerprint);

    // Step 3: Display AI results (executive summary + redlines)
    displayAIResults(aiResult);
    saveScanState(docFingerprint);

    // Step 4: Highlight risks in document using three-tier search
    await highlightAIRedlines(aiResult.risks);
    log.info('Analysis complete:', { risks: aiResult.risks?.length, tokens: aiResult.tokens_used });

  } catch (error) {
    log.error('Scan failed:', error);
    displayScanError(error instanceof Error ? error : new Error(String(error)));
  } finally {
    isScanning = false;
    setScanLoading(false);
  }
}

/**
 * Scan only the currently selected text in Word for risks.
 * Lighter-weight than full document scan — calls /documents/analyze-clause.
 * Merges results into existing analysis if one exists, or creates a new one.
 */
async function scanSelection(): Promise<void> {
  if (isSelectionScanning) return;  // Prevent double-click race condition
  isSelectionScanning = true;

  const btnText = document.getElementById('scanSelectionBtnText');
  const spinner = document.getElementById('scanSelectionSpinner');
  if (btnText) btnText.textContent = 'Scanning...';
  if (spinner) spinner.style.display = 'inline-block';

  try {
    // Step 1: Get selected text from Word
    const selectedText = await Word.run(async (context) => {
      const sel = context.document.getSelection();
      sel.load('text');
      await context.sync();
      return sel.text;
    });

    // Validate selection length
    if (!selectedText || selectedText.trim().length < 20) {
      displayScanError(new Error('Please select at least 20 characters of contract text to scan.'));
      return;
    }

    if (selectedText.length > 10240) {
      displayScanError(new Error('Selection too large (max ~10KB). Please select a smaller section of text.'));
      return;
    }

    // Step 2: Call clause analysis API
    const selectedPlaybookId = (document.getElementById('playbookSelect') as HTMLSelectElement)?.value || undefined;
    log.info('Starting selection scan...', { length: selectedText.length });

    const result: ClauseAnalysisResult = await api.analyzeClause(selectedText, selectedPlaybookId);

    // Step 3: Handle results
    if (!result.risks || result.risks.length === 0) {
      // Show temporary "No Risks Found" card that auto-removes after 10s
      const results = document.getElementById('resultsSection') as HTMLElement | null;
      if (results) {
        results.style.display = 'block';
        const noRiskCard = document.createElement('div');
        noRiskCard.className = 'risk-card';
        noRiskCard.style.borderLeft = '3px solid var(--risk-low, #1A7A4A)';
        noRiskCard.innerHTML = `
          <div style="padding: 12px;">
            <strong style="color: var(--risk-low, #1A7A4A);">No Risks Found</strong>
            <p style="margin: 4px 0 0; color: var(--text-secondary); font-size: 12px;">
              The selected text appears compliant. No issues detected.
            </p>
          </div>
        `;
        const riskList = document.getElementById('riskList');
        if (riskList) {
          riskList.prepend(noRiskCard);
        } else {
          results.appendChild(noRiskCard);
        }
        setTimeout(() => noRiskCard.remove(), 10000);
      }
      log.info('Selection scan complete: no risks found.');
      return;
    }

    // Step 4: Merge or create analysis results
    if (currentAIAnalysis) {
      // Dedup: skip risks with same rule_name AND clause_text prefix (first 50 chars)
      const existingKeys = new Set(
        currentAIAnalysis.risks.map(r => `${r.rule_name}::${r.clause_text.substring(0, 50)}`)
      );
      const newRisks = result.risks.filter(
        r => !existingKeys.has(`${r.rule_name}::${r.clause_text.substring(0, 50)}`)
      );

      if (newRisks.length > 0) {
        currentAIAnalysis.risks = [...currentAIAnalysis.risks, ...newRisks];
        currentAIAnalysis.total_risks = currentAIAnalysis.risks.length;
        currentAIAnalysis.risk_summary = {
          red: currentAIAnalysis.risks.filter(r => r.risk_level === 'RED').length,
          yellow: currentAIAnalysis.risks.filter(r => r.risk_level === 'YELLOW').length,
          green: currentAIAnalysis.risks.filter(r => r.risk_level === 'GREEN').length,
        };
        currentAIAnalysis.tokens_used += result.tokens_used;
        displayAIResults(currentAIAnalysis);
        saveScanState();
      }
    } else {
      // Create new AnalysisResult from clause results
      currentAIAnalysis = {
        document_id: 'selection-scan',
        filename: 'Selection Scan',
        executive_summary: ['Risks found in selected text.'],
        risks: result.risks,
        total_risks: result.risks.length,
        risk_summary: {
          red: result.risks.filter(r => r.risk_level === 'RED').length,
          yellow: result.risks.filter(r => r.risk_level === 'YELLOW').length,
          green: result.risks.filter(r => r.risk_level === 'GREEN').length,
        },
        tokens_used: result.tokens_used,
      };
      fixedRisks.clear();
      displayAIResults(currentAIAnalysis);
      saveScanState();
    }

    // Step 5: Highlight new risks in document
    await highlightAIRedlines(result.risks);
    log.info('Selection scan complete:', { risks: result.risks.length, tokens: result.tokens_used, time_ms: result.analysis_time_ms });

  } catch (error) {
    log.error('Selection scan failed:', error);
    displayScanError(error instanceof Error ? error : new Error(String(error)));
  } finally {
    isSelectionScanning = false;
    if (btnText) btnText.textContent = 'Scan Selection';
    if (spinner) spinner.style.display = 'none';
  }
}

// ============================================================================
// Quick Re-Scan (Phase 8.3)
// ============================================================================

/**
 * Re-scan a specific clause after a fix has been applied to verify it resolved the risk.
 * Updates the card in-place with new results or marks it as resolved.
 */
async function reScanClause(riskId: string, originalText: string): Promise<void> {
  const card = document.getElementById(`risk-${riskId}`);
  if (!card) return;

  const reScanBtn = card.querySelector('.rescan-btn') as HTMLButtonElement | null;
  if (reScanBtn) { reScanBtn.disabled = true; reScanBtn.textContent = 'Re-scanning...'; }

  try {
    const surroundingText = await getSurroundingContext(originalText);
    const textToScan = surroundingText || originalText;
    if (textToScan.length < 20) { showToastOnCard(card, 'Not enough text to re-scan.'); return; }

    const selectedPlaybookId = (document.getElementById('playbookSelect') as HTMLSelectElement)?.value || undefined;
    const result = await api.analyzeClause(textToScan, selectedPlaybookId);

    if (result.risks.length === 0) {
      card.classList.add('fixed');
      card.dataset.risk = 'green';
      fixedRisks.add(riskId);
      showToastOnCard(card, 'Risk resolved! Clause is now clean.');
      // Update counts
      if (currentAIAnalysis) {
        currentAIAnalysis.risk_summary = {
          red: currentAIAnalysis.risks.filter(r => r.risk_level === 'RED' && !fixedRisks.has(r.id)).length,
          yellow: currentAIAnalysis.risks.filter(r => r.risk_level === 'YELLOW' && !fixedRisks.has(r.id)).length,
          green: currentAIAnalysis.risks.filter(r => r.risk_level === 'GREEN' && !fixedRisks.has(r.id)).length,
        };
        const rc = document.getElementById('redCount');
        const yc = document.getElementById('yellowCount');
        if (rc) rc.textContent = String(currentAIAnalysis.risk_summary.red);
        if (yc) yc.textContent = String(currentAIAnalysis.risk_summary.yellow);
      }
    } else {
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
    if (reScanBtn) { reScanBtn.disabled = false; reScanBtn.textContent = 'Re-Scan'; }
  }
}

// ============================================================================
// Live Negotiation Mode (Phase 8.4)
// ============================================================================

/** Toggle negotiation mode on/off with timer, auto-scan, and compact card view. */
function toggleNegotiationMode(): void {
  negotiationMode = !negotiationMode;
  const panel = document.getElementById('negotiationPanel');

  const negBtn = document.getElementById('negotiationBtn') as HTMLButtonElement | null;
  const negBtnText = document.getElementById('negotiationBtnText');

  if (negotiationMode) {
    document.body.classList.add('negotiation-mode');
    if (panel) panel.style.display = 'block';
    if (negBtn) { negBtn.style.background = 'linear-gradient(135deg, #DC2626, #B91C1C)'; }
    if (negBtnText) negBtnText.textContent = 'End Negotiation';

    negotiationSession = loadNegotiationSession() || {
      started_at: Date.now(), notes: '', decisions: [], document_name: currentAIAnalysis?.filename || 'Unknown',
    };

    startNegotiationTimer();

    const notesEl = document.getElementById('negotiationNotes') as HTMLTextAreaElement;
    if (notesEl && !negotiationNotesListenerAttached) {
      notesEl.addEventListener('input', () => {
        if (negotiationSession) { negotiationSession.notes = notesEl.value; saveNegotiationSession(); }
      });
      negotiationNotesListenerAttached = true;
    }
    if (notesEl && negotiationSession.notes) notesEl.value = negotiationSession.notes;

    registerSelectionHandler();
    renderRedlineList();
  } else {
    document.body.classList.remove('negotiation-mode');
    if (panel) panel.style.display = 'none';
    if (negBtn) { negBtn.style.background = 'linear-gradient(135deg, #7C3AED, #6D28D9)'; }
    if (negBtnText) negBtnText.textContent = 'Live Negotiation';
    if (negotiationTimer) { clearInterval(negotiationTimer); negotiationTimer = null; }
    if (selectionDebounceTimer) { clearTimeout(selectionDebounceTimer); selectionDebounceTimer = null; }
    unregisterSelectionHandler();
    saveNegotiationSession();
    renderRedlineList();
  }
}

function startNegotiationTimer(): void {
  if (negotiationTimer) { clearInterval(negotiationTimer); negotiationTimer = null; }
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
    Office.context.document.addHandlerAsync(Office.EventType.DocumentSelectionChanged, onSelectionChanged);
  } catch (e) { log.warn('Could not register selection handler:', e); }
}

function unregisterSelectionHandler(): void {
  try {
    Office.context.document.removeHandlerAsync(Office.EventType.DocumentSelectionChanged);
  } catch (e) { log.warn('Could not unregister selection handler:', e); }
}

function onSelectionChanged(): void {
  if (!negotiationMode) return;
  if (selectionDebounceTimer) clearTimeout(selectionDebounceTimer);
  selectionDebounceTimer = setTimeout(async () => {
    const selectedText = await Word.run(async (context) => {
      const sel = context.document.getSelection();
      sel.load('text');
      await context.sync();
      return sel.text;
    });
    if (selectedText && selectedText.trim().length >= 20) {
      const indicator = document.getElementById('autoScanIndicator');
      if (indicator) indicator.textContent = 'Scanning selection...';
      await scanSelection();
      if (indicator) indicator.innerHTML = '<span class="auto-scan-dot"></span> Auto-scanning selections';
    }
  }, 1500);
}

function saveNegotiationSession(): void {
  try {
    if (negotiationSession) localStorage.setItem('contrared_negotiation_session', JSON.stringify(negotiationSession));
  } catch (e) {
    log.warn('Failed to save negotiation session:', e);
  }
}

function loadNegotiationSession(): NegotiationSession | null {
  try {
    const stored = localStorage.getItem('contrared_negotiation_session');
    if (stored) return JSON.parse(stored);
  } catch { /* ignore */ }
  return null;
}

function recordNegotiationDecision(riskId: string, decision: 'accept' | 'counter' | 'escalate', counterText?: string): void {
  if (!negotiationSession) return;
  const entry: NegotiationDecision = { risk_id: riskId, decision, counter_text: counterText, timestamp: Date.now() };
  const existing = negotiationSession.decisions.findIndex(d => d.risk_id === riskId);
  if (existing >= 0) negotiationSession.decisions[existing] = entry;
  else negotiationSession.decisions.push(entry);
  saveNegotiationSession();
}

// ============================================================================
// Negotiation Export (Phase 8.5)
// ============================================================================

/** Export negotiation decisions as a downloadable HTML report. */
async function exportNegotiationDecisions(): Promise<void> {
  if (!negotiationSession || !currentAIAnalysis) {
    showNotification('No negotiation session to export', 'warning');
    return;
  }

  const decisions = negotiationSession.decisions;
  const redlines = currentAIAnalysis.risks || [];

  // Build report content
  const now = new Date();
  const elapsed = Math.floor((Date.now() - negotiationSession.started_at) / 1000);
  const elapsedStr = elapsed >= 60
    ? `${Math.floor(elapsed / 60)}m ${elapsed % 60}s`
    : `${elapsed}s`;

  let reportHtml = `
    <h1 style="font-family:Calibri;font-size:20pt;color:#1E293B;">ContraRed Negotiation Report</h1>
    <p style="font-family:Calibri;font-size:11pt;color:#64748B;">
      Generated: ${now.toLocaleDateString()} ${now.toLocaleTimeString()}<br/>
      Negotiation Duration: ${elapsedStr}<br/>
      Document: ${escapeHtml(negotiationSession.document_name || 'Untitled')}
    </p>
    <hr/>
  `;

  // Summary counts
  let accepted = 0, countered = 0, escalated = 0, undecided = 0;

  redlines.forEach(r => {
    const dec = decisions.find(d => d.risk_id === r.id);
    if (dec?.decision === 'accept') accepted++;
    else if (dec?.decision === 'counter') countered++;
    else if (dec?.decision === 'escalate') escalated++;
    else undecided++;
  });

  reportHtml += `
    <h2 style="font-family:Calibri;font-size:14pt;">Summary</h2>
    <table style="border-collapse:collapse;width:100%;font-family:Calibri;font-size:11pt;">
      <tr>
        <td style="padding:6px 12px;background:#DCFCE7;border:1px solid #ddd;"><strong>Accepted</strong></td>
        <td style="padding:6px 12px;border:1px solid #ddd;text-align:center;">${accepted}</td>
      </tr>
      <tr>
        <td style="padding:6px 12px;background:#FEF3C7;border:1px solid #ddd;"><strong>Counter-proposed</strong></td>
        <td style="padding:6px 12px;border:1px solid #ddd;text-align:center;">${countered}</td>
      </tr>
      <tr>
        <td style="padding:6px 12px;background:#FEE2E2;border:1px solid #ddd;"><strong>Escalated</strong></td>
        <td style="padding:6px 12px;border:1px solid #ddd;text-align:center;">${escalated}</td>
      </tr>
      <tr>
        <td style="padding:6px 12px;background:#F1F5F9;border:1px solid #ddd;"><strong>Undecided</strong></td>
        <td style="padding:6px 12px;border:1px solid #ddd;text-align:center;">${undecided}</td>
      </tr>
    </table>
  `;

  // Detailed decisions table
  reportHtml += `
    <h2 style="font-family:Calibri;font-size:14pt;margin-top:20px;">Detailed Decisions</h2>
    <table style="border-collapse:collapse;width:100%;font-family:Calibri;font-size:10pt;">
      <tr style="background:#1E293B;color:#fff;">
        <th style="padding:8px;border:1px solid #ddd;text-align:left;">Clause</th>
        <th style="padding:8px;border:1px solid #ddd;text-align:center;">Risk</th>
        <th style="padding:8px;border:1px solid #ddd;text-align:center;">Decision</th>
        <th style="padding:8px;border:1px solid #ddd;text-align:left;">AI Recommendation</th>
      </tr>
  `;

  redlines.forEach(r => {
    const dec = decisions.find(d => d.risk_id === r.id);
    const decision = dec?.decision || 'undecided';
    const riskColor = r.risk_level === 'RED' ? '#FEE2E2' : r.risk_level === 'YELLOW' ? '#FEF3C7' : '#DCFCE7';
    const decisionColor = decision === 'accept' ? '#166534' : decision === 'counter' ? '#92400E' : decision === 'escalate' ? '#B91C1C' : '#64748B';
    const decisionLabel = decision.charAt(0).toUpperCase() + decision.slice(1);

    reportHtml += `
      <tr>
        <td style="padding:6px 8px;border:1px solid #ddd;">${escapeHtml(r.rule_name || 'Unknown')}</td>
        <td style="padding:6px 8px;border:1px solid #ddd;text-align:center;background:${riskColor};">${r.risk_level || 'N/A'}</td>
        <td style="padding:6px 8px;border:1px solid #ddd;text-align:center;color:${decisionColor};font-weight:bold;">${decisionLabel}</td>
        <td style="padding:6px 8px;border:1px solid #ddd;font-size:9pt;">${escapeHtml((r.recommendation || r.explanation || '').substring(0, 200))}</td>
      </tr>
    `;
  });

  reportHtml += '</table>';

  // Add notes if any
  const notes = negotiationSession.notes || '';
  if (notes.trim()) {
    reportHtml += `
      <h2 style="font-family:Calibri;font-size:14pt;margin-top:20px;">Notes</h2>
      <p style="font-family:Calibri;font-size:11pt;white-space:pre-wrap;">${escapeHtml(notes)}</p>
    `;
  }

  reportHtml += `
    <hr/>
    <p style="font-family:Calibri;font-size:9pt;color:#94A3B8;margin-top:20px;">
      Generated by ContraRed AI Contract Review<br/>
      This report is for internal use only and does not constitute legal advice.
    </p>
  `;

  // Download as HTML file
  const blob = new Blob([`<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>ContraRed Negotiation Report</title></head>
<body style="max-width:800px;margin:40px auto;padding:20px;">
${reportHtml}
</body></html>`], { type: 'text/html' });

  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `ContraRed_Negotiation_${now.toISOString().slice(0, 10)}.html`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);

  showNotification('Negotiation report exported', 'info');
}

// ============================================================================
// Keyboard Shortcuts (Phase 8)
// ============================================================================

/** Navigate to a risk card by index, wrapping around at boundaries. */
function focusRiskCard(index: number): void {
  const cards = document.querySelectorAll('.risk-card');
  if (cards.length === 0) return;

  // Remove existing focus
  cards.forEach(c => c.classList.remove('keyboard-focused'));

  // Wrap around
  if (index < 0) index = cards.length - 1;
  if (index >= cards.length) index = 0;

  currentRiskIndex = index;
  const card = cards[currentRiskIndex] as HTMLElement;
  card.classList.add('keyboard-focused');
  card.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

/** Returns the redline data for the currently focused card. */
function getFocusedRedline(): RedlineItem | null {
  const filtered = getFilteredRedlines();
  if (currentRiskIndex < 0 || currentRiskIndex >= filtered.length) return null;
  return filtered[currentRiskIndex];
}

/** Clicks a button inside the currently focused risk card. */
function clickFocusedCardButton(selector: string): void {
  const cards = document.querySelectorAll('.risk-card');
  if (currentRiskIndex < 0 || currentRiskIndex >= cards.length) return;
  const btn = cards[currentRiskIndex].querySelector(selector) as HTMLElement | null;
  if (btn) btn.click();
}

/** Global keyboard shortcut handler. */
function handleKeyboardShortcuts(e: KeyboardEvent): void {
  // Don't intercept when user is typing in form fields
  const tag = (e.target as HTMLElement)?.tagName;
  if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return;

  // ? key → Toggle shortcuts help
  if (e.key === '?') {
    e.preventDefault();
    toggleShortcutsPanel();
    return;
  }

  // Ctrl+Alt+S → Scan Selection (changed from Ctrl+Shift+S to avoid Save As conflict)
  if (e.ctrlKey && e.altKey && (e.key === 'S' || e.key === 's')) {
    e.preventDefault();
    scanSelection();
    return;
  }

  // Ctrl+Shift+D → Scan Document
  if (e.ctrlKey && e.shiftKey && (e.key === 'D' || e.key === 'd')) {
    e.preventDefault();
    scanDocument();
    return;
  }

  // Ctrl+Shift+N → Toggle Negotiation Mode
  if (e.ctrlKey && e.shiftKey && (e.key === 'N' || e.key === 'n')) {
    e.preventDefault();
    toggleNegotiationMode();
    return;
  }

  // Alt+ArrowUp → Previous risk card
  if (e.altKey && e.key === 'ArrowUp') {
    e.preventDefault();
    focusRiskCard(currentRiskIndex - 1);
    return;
  }

  // Alt+ArrowDown → Next risk card
  if (e.altKey && e.key === 'ArrowDown') {
    e.preventDefault();
    focusRiskCard(currentRiskIndex + 1);
    return;
  }

  // Ctrl+Shift+H → Highlight focused risk (changed from Alt+H to avoid Word ribbon conflict)
  if (e.ctrlKey && e.shiftKey && (e.key === 'H' || e.key === 'h')) {
    e.preventDefault();
    clickFocusedCardButton('.highlight-btn');
    return;
  }

  // Ctrl+Shift+G → Generate fix for focused risk (changed from Alt+G to avoid Word ribbon conflict)
  if (e.ctrlKey && e.shiftKey && (e.key === 'G' || e.key === 'g')) {
    e.preventDefault();
    clickFocusedCardButton('.generate-fix-btn');
    return;
  }

  // Ctrl+Alt+A → Apply fix for focused risk (changed from Ctrl+Shift+A to avoid All Caps conflict)
  if (e.ctrlKey && e.altKey && (e.key === 'A' || e.key === 'a')) {
    e.preventDefault();
    clickFocusedCardButton('.apply-btn');
    return;
  }

  // Ctrl+Shift+R → Research focused risk (changed from Alt+R to avoid Word ribbon conflict)
  if (e.ctrlKey && e.shiftKey && (e.key === 'R' || e.key === 'r')) {
    e.preventDefault();
    clickFocusedCardButton('.research-btn');
    return;
  }
}

function toggleShortcutsPanel(): void {
  const panel = document.getElementById('shortcutsPanel');
  if (!panel) return;
  const isVisible = panel.style.display !== 'none' && panel.style.display !== '';
  if (isVisible) {
    panel.style.display = 'none';
    shortcutsPanelTrap?.deactivate();
  } else {
    panel.style.display = 'flex';
    shortcutsPanelTrap = new FocusTrap(panel, () => { panel.style.display = 'none'; });
    shortcutsPanelTrap.activate();
  }
}

/**
 * Display scan error inline instead of using alert().
 */
function displayScanError(error: Error): void {
  const results = document.getElementById('resultsSection') as HTMLElement | null;
  if (!results) return;
  results.style.display = 'block';

  const msg = error.message || 'Unknown error';
  let title = 'Analysis Failed';
  let description = msg;
  let showRetry = true;

  if (msg.includes('Failed to fetch') || msg.includes('NetworkError') || msg.includes('TypeError')) {
    title = 'Cannot Reach Server';
    description = 'Please check your internet connection and ensure the ContraRed server is running.';
  } else if (msg.includes('not configured') || msg.includes('API key')) {
    title = 'AI Service Not Configured';
    description = 'The AI analysis service is not configured. Please contact your administrator.';
    showRetry = false;
  } else if (msg.includes('rate limit') || msg.includes('429')) {
    title = 'Rate Limited';
    description = 'Too many requests. Please wait a minute and try again.';
  } else if (msg.includes('timeout') || msg.includes('504')) {
    title = 'Analysis Timed Out';
    description = 'The document may be too long. Try scanning a shorter section.';
  }

  const redlinesList = riskList();
  if (redlinesList) {
    redlinesList.innerHTML = `
      <div class="error-card">
        <div class="error-card-icon">!</div>
        <div class="error-card-title">${escapeHtml(title)}</div>
        <div class="error-card-message">${escapeHtml(description)}</div>
        ${showRetry ? '<button class="error-retry-btn" id="retryBtn">Retry Analysis</button>' : ''}
      </div>
    `;
    const retryBtn = document.getElementById('retryBtn');
    retryBtn?.addEventListener('click', () => scanDocument());
  }

  // Clear counts
  if (redCount()) redCount()!.textContent = '0';
  if (yellowCount()) yellowCount()!.textContent = '0';
}

/**
 * Display AI analysis results in the UI.
 */
function displayAIResults(result: AnalysisResult): void {
  // Show results section (uses inline style, not class)
  const results = document.getElementById('resultsSection') as HTMLElement | null;

  if (results) {
    results.style.display = 'block';
  } else {
    log.error('resultsSection element not found in DOM');
    return;  // Can't continue if no results section
  }

  // Update risk counts
  if (redCount()) redCount()!.textContent = String(result.risk_summary.red || 0);
  if (yellowCount()) yellowCount()!.textContent = String(result.risk_summary.yellow || 0);
  // Green count: show actual value from risk_summary if available, otherwise hide
  const green = result.risk_summary.green || 0;
  if (greenCount()) {
    if (green > 0) {
      greenCount()!.textContent = String(green);
      greenCount()!.parentElement!.style.display = '';
    } else {
      greenCount()!.parentElement!.style.display = 'none';
    }
  }
  if (riskCount()) riskCount()!.textContent = String(result.total_risks);

  // Display executive summary in AI Summary section
  const summarySection = document.getElementById('aiSummarySection');
  const riskLevelBadge = document.getElementById('riskLevelBadge');
  const keyConcernsDiv = document.getElementById('keyConcerns');
  const recommendationDiv = document.getElementById('recommendation');

  if (summarySection) {
    summarySection.style.display = 'block';

    // Determine risk level from summary
    const level = result.risk_summary.red > 0 ? 'Critical' :
      result.risk_summary.yellow > 0 ? 'Medium' : 'Low';

    if (riskLevelBadge) {
      riskLevelBadge.textContent = level;
      riskLevelBadge.className = `risk-level-badge level-${level.toLowerCase()}`;
    }

    // Display executive summary points (safe DOM creation to prevent XSS)
    if (keyConcernsDiv && result.executive_summary.length > 0) {
      keyConcernsDiv.innerHTML = '';
      result.executive_summary.forEach(point => {
        const div = document.createElement('div');
        div.className = 'concern-item';
        div.textContent = '\u2022 ' + point;
        keyConcernsDiv.appendChild(div);
      });
    }

    if (recommendationDiv) {
      recommendationDiv.textContent = `${result.total_risks} clauses require attention.`;
    }
  }

  // Show export button
  const exportBtn = document.getElementById('exportReportBtn');
  if (exportBtn) exportBtn.style.display = 'inline-flex';

  // Show filter toolbar and render filtered list
  const filterToolbar = document.getElementById('filterToolbar');
  if (filterToolbar) filterToolbar.style.display = 'flex';

  // Show bulk actions bar if there are fixable redlines
  const bulkBar = document.getElementById('bulkActionsBar');
  if (bulkBar) bulkBar.style.display = result.risks.length > 0 ? 'block' : 'none';

  // Reset filters on new scan
  activeFilter = 'ALL';
  activeSort = 'risk_level';
  searchQuery = '';
  const searchInput = document.getElementById('riskSearchInput') as HTMLInputElement;
  if (searchInput) searchInput.value = '';
  document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
  document.querySelector('.filter-btn[data-filter="ALL"]')?.classList.add('active');

  renderRedlineList();
  updateApplyAllCount();
}

/**
 * Get filtered and sorted redlines based on current filter/sort state.
 */
function getFilteredRedlines(): RedlineItem[] {
  if (!currentAIAnalysis) return [];

  let filtered = [...currentAIAnalysis.risks];

  // Apply risk level filter
  if (activeFilter === 'RED') {
    filtered = filtered.filter(r => r.risk_level === 'RED');
  } else if (activeFilter === 'YELLOW') {
    filtered = filtered.filter(r => r.risk_level === 'YELLOW');
  } else if (activeFilter === 'UNFIXED') {
    filtered = filtered.filter(r => !fixedRisks.has(r.id));
  }

  // Apply search query
  if (searchQuery.trim()) {
    const q = searchQuery.toLowerCase();
    filtered = filtered.filter(r =>
      r.rule_name.toLowerCase().includes(q) ||
      r.clause_text.toLowerCase().includes(q) ||
      r.explanation.toLowerCase().includes(q)
    );
  }

  // Apply sort
  if (activeSort === 'risk_level') {
    const order: Record<string, number> = { RED: 0, YELLOW: 1 };
    filtered.sort((a, b) => (order[a.risk_level] ?? 2) - (order[b.risk_level] ?? 2));
  } else if (activeSort === 'rule_name') {
    filtered.sort((a, b) => a.rule_name.localeCompare(b.rule_name));
  } else if (activeSort === 'confidence') {
    filtered.sort((a, b) => (b.confidence || 0) - (a.confidence || 0));
  }

  return filtered;
}

/**
 * Render the redline list based on current filter/sort state.
 */
function renderRedlineList(): void {
  const filtered = getFilteredRedlines();
  let list = riskList();
  if (!list) return;

  // Clone to remove old event listeners
  const parent = list.parentNode;
  if (parent) {
    const newList = list.cloneNode(false) as HTMLElement;
    parent.replaceChild(newList, list);
    list = newList;
  }
  list.innerHTML = '';

  if (filtered.length === 0) {
    const empty = emptyState();
    if (empty) empty.style.display = 'block';
    if (riskCount()) riskCount()!.textContent = '0';
    return;
  }

  const empty = emptyState();
  if (empty) empty.style.display = 'none';
  if (riskCount()) riskCount()!.textContent = String(filtered.length);

  // Announce filtered count to screen readers
  if (list) {
    list.setAttribute('aria-label', `${filtered.length} risks found`);
  }

  const docId = currentAIAnalysis?.document_id || '';
  filtered.forEach((redline) => {
    const card = createAIRedlineCard(redline, docId);
    if (fixedRisks.has(redline.id)) card.classList.add('fixed');
    // Collapse LOW confidence items by default
    if (redline.confidence_level === 'LOW') {
      card.classList.add('low-confidence');
      const clause = card.querySelector('.risk-clause') as HTMLElement;
      const explanation = card.querySelector('.risk-explanation') as HTMLElement;
      const suggestedFix = card.querySelector('.suggested-fix') as HTMLElement;
      const actions = card.querySelector('.risk-actions') as HTMLElement;
      if (clause) clause.style.display = 'none';
      if (explanation) explanation.style.display = 'none';
      if (suggestedFix) suggestedFix.style.display = 'none';
      if (actions) actions.style.display = 'none';
      // Add expand toggle
      const toggle = document.createElement('div');
      toggle.className = 'low-confidence-toggle';
      toggle.style.cssText = 'font-size:11px;color:#6B7280;cursor:pointer;padding:4px 0;';
      toggle.textContent = 'Low confidence \u2014 click to expand';
      toggle.addEventListener('click', () => {
        if (clause) clause.style.display = '';
        if (explanation) explanation.style.display = '';
        if (suggestedFix) suggestedFix.style.display = '';
        if (actions) actions.style.display = '';
        toggle.remove();
        card.classList.remove('low-confidence');
      });
      card.querySelector('.risk-card-header')?.insertAdjacentElement('afterend', toggle);
    }
    list.appendChild(card);
  });
}

/**
 * Update the "Apply All" button text with current count.
 */
function updateApplyAllCount(): void {
  const unfixed = getFilteredRedlines().filter(r => !fixedRisks.has(r.id)).length;
  const generated = getFilteredRedlines().filter(r => !fixedRisks.has(r.id) && document.getElementById(`risk-${r.id}`)?.dataset.generatedFix).length;
  const btnText = document.getElementById('applyAllBtnText');
  const applyBtn = document.getElementById('applyAllBtn') as HTMLButtonElement;

  if (!btnText || !applyBtn) return;

  if (unfixed === 0) {
    btnText.textContent = 'All Fixed';
    applyBtn.disabled = true;
  } else if (generated === unfixed) {
    btnText.textContent = `Apply All Fixes (${generated})`;
    applyBtn.disabled = false;
  } else if (generated > 0) {
    btnText.textContent = `Apply ${generated} Ready / Generate ${unfixed - generated} More`;
    applyBtn.disabled = false;
  } else {
    btnText.textContent = `Generate All Fixes (${unfixed})`;
    applyBtn.disabled = false;
  }
  applyBtn.setAttribute('aria-label', btnText.textContent);
}

/**
 * Focus trap utility for modal dialogs.
 * Traps Tab/Shift+Tab within a container, handles Escape to close.
 */
class FocusTrap {
  private container: HTMLElement;
  private onClose: () => void;
  private previouslyFocused: Element | null;
  private keyHandler: (e: KeyboardEvent) => void;

  constructor(container: HTMLElement, onClose: () => void) {
    this.container = container;
    this.onClose = onClose;
    this.previouslyFocused = document.activeElement;

    this.keyHandler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        this.deactivate();
        this.onClose();
        return;
      }
      if (e.key !== 'Tab') return;

      const focusable = this.container.querySelectorAll<HTMLElement>(
        'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
      );
      if (focusable.length === 0) return;

      const first = focusable[0];
      const last = focusable[focusable.length - 1];

      if (e.shiftKey) {
        if (document.activeElement === first) {
          e.preventDefault();
          last.focus();
        }
      } else {
        if (document.activeElement === last) {
          e.preventDefault();
          first.focus();
        }
      }
    };
  }

  activate(): void {
    this.container.addEventListener('keydown', this.keyHandler);
    const first = this.container.querySelector<HTMLElement>(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    );
    if (first) first.focus();
  }

  deactivate(): void {
    this.container.removeEventListener('keydown', this.keyHandler);
    if (this.previouslyFocused instanceof HTMLElement) {
      this.previouslyFocused.focus();
    }
  }
}

/**
 * Create a risk card for an AI redline item.
 */
function createAIRedlineCard(redline: RedlineItem, _documentId: string): HTMLElement {
  const card = document.createElement('article');
  card.className = 'risk-card';
  card.id = `risk-${redline.id}`;
  card.dataset.risk = redline.risk_level.toLowerCase();
  card.setAttribute('tabindex', '0');
  card.setAttribute('role', 'article');
  card.setAttribute('aria-label', `${redline.risk_level} risk: ${redline.rule_name}`);

  const isMissing = redline.redline_type === 'missing';
  const truncatedClause = redline.clause_text.length > 100
    ? redline.clause_text.slice(0, 100) + '...'
    : redline.clause_text;
  const truncatedRec = redline.recommendation
    ? (redline.recommendation.length > 150 ? redline.recommendation.slice(0, 150) + '...' : redline.recommendation)
    : '';
  const clauseLabel = isMissing ? 'Insert after: ' : '';
  const typeBadge = isMissing
    ? '<span class="redline-type-badge type-missing">Missing</span>'
    : '<span class="redline-type-badge type-violation">Violation</span>';

  // Confidence badge — color-coded by level
  const confLevel = redline.confidence_level || '';
  const confScore = redline.confidence != null ? Math.round(redline.confidence * 100) : null;
  let confidenceBadge = '';
  if (confScore != null && confLevel) {
    const confColor = confLevel === 'HIGH' ? '#166534' : confLevel === 'MEDIUM' ? '#92400E' : '#991B1B';
    const confBg = confLevel === 'HIGH' ? '#DCFCE7' : confLevel === 'MEDIUM' ? '#FEF3C7' : '#FEE2E2';
    const verStatus = redline.verification_status ? ` (${escapeHtml(redline.verification_status)})` : '';
    confidenceBadge = `<span class="confidence-badge" style="font-size:10px;padding:1px 6px;border-radius:8px;background:${confBg};color:${confColor};margin-left:auto;" title="Confidence: ${confScore}%${verStatus}">${escapeHtml(confLevel)} ${confScore}%</span>`;
  }

  // Warn when a RED risk has LOW confidence — lawyer should verify manually
  const riskLevel = redline.risk_level.toLowerCase();
  let lowConfWarning = '';
  if (riskLevel === 'red' && confScore != null && confScore < 50) {
    lowConfWarning = '<div class="low-conf-warning" style="background:#FEF3C7;color:#92400E;font-size:10px;padding:4px 8px;margin-top:4px;border-radius:4px;border-left:3px solid #F59E0B;" role="alert">Low confidence — verify this risk manually</div>';
  }

  card.innerHTML = `
    <div class="risk-card-header">
      <h3 class="risk-title"></h3>
      ${typeBadge}
      ${confidenceBadge}
    </div>
    ${lowConfWarning}
    <div class="risk-clause"><span class="clause-label">${escapeHtml(clauseLabel)}</span><span class="clause-text"></span></div>
    <div class="risk-explanation"></div>
    ${redline.recommendation ? `
      <div class="suggested-fix">
        <strong>Recommendation:</strong> <span class="suggested-fix-text"></span>
      </div>
    ` : ''}
    <div class="risk-actions">
      <button class="btn btn-secondary btn-sm highlight-btn">
        <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" width="14" height="14" aria-hidden="true">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/>
        </svg>
        Highlight
      </button>
      <button class="btn btn-primary btn-sm generate-fix-btn">
        <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" width="14" height="14" aria-hidden="true">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/>
        </svg>
        Generate Fix
      </button>
      <button class="btn btn-secondary btn-sm research-btn">
        <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" width="14" height="14" aria-hidden="true">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"/>
        </svg>
        Research
      </button>
      <button class="btn btn-secondary btn-sm rescan-btn" style="display:none;">Re-Scan</button>
    </div>
    <div class="generate-panel" style="display:none;"></div>
    <div class="research-panel" style="display:none;"></div>
    <div class="fixed-badge">
      <span>\u2713 Fixed</span>
      <button class="undo-btn">
        <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" width="12" height="12">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 10h10a5 5 0 015 5v2M3 10l4-4M3 10l4 4"/>
        </svg>
        Undo
      </button>
    </div>
  `;

  // Set dynamic text content safely to prevent XSS
  const ruleNameEl = card.querySelector('.risk-title');
  if (ruleNameEl) ruleNameEl.textContent = redline.rule_name;
  const clauseTextEl = card.querySelector('.clause-text');
  if (clauseTextEl) clauseTextEl.textContent = '"' + truncatedClause + '"';
  const explanationEl = card.querySelector('.risk-explanation');
  if (explanationEl) explanationEl.textContent = redline.explanation;
  const suggestedFixEl = card.querySelector('.suggested-fix-text');
  if (suggestedFixEl) suggestedFixEl.textContent = truncatedRec;

  // ARIA labels for screen readers
  card.querySelector('.highlight-btn')?.setAttribute('aria-label', `Highlight in document: ${redline.rule_name}`);
  card.querySelector('.generate-fix-btn')?.setAttribute('aria-label', `Generate fix for: ${redline.rule_name}`);
  card.querySelector('.research-btn')?.setAttribute('aria-label', `Research case law: ${redline.rule_name}`);
  card.querySelector('.undo-btn')?.setAttribute('aria-label', `Undo fix: ${redline.rule_name}`);
  card.querySelector('.rescan-btn')?.setAttribute('aria-label', `Re-scan: ${redline.rule_name}`);

  // Bind button handlers
  const highlightBtn = card.querySelector('.highlight-btn');
  highlightBtn?.addEventListener('click', async () => {
    const matchResult = await highlightAIText(redline.clause_text, redline.risk_level, redline.redline_type);
    // Fix #17/#25: Show fuzzy match confidence indicator with percentage
    if (matchResult.method === 'fuzzy') {
      const existingIndicator = card.querySelector('.match-confidence-indicator');
      if (!existingIndicator) {
        const pct = Math.round(matchResult.confidence * 100);
        card.querySelector('.risk-card-header')?.insertAdjacentHTML('beforeend',
          `<span style="font-size: 10px; color: #D4A017; margin-left: 4px;" title="Approximate text match (${pct}% confidence)" class="match-confidence-indicator">~${pct}%</span>`);
      }
    }
  });

  // Undo button — reverts the applied fix and restores card buttons
  const undoBtn = card.querySelector('.undo-btn');
  undoBtn?.addEventListener('click', async (e) => {
    e.stopPropagation();
    const btn = e.currentTarget as HTMLButtonElement;
    btn.disabled = true;
    btn.textContent = 'Undoing...';
    try {
      const appliedFix = card.dataset.appliedFix;
      await undoRedlineFix(redline, appliedFix);
      fixedRisks.delete(redline.id);
      card.classList.remove('fixed');
      delete card.dataset.appliedFix;
      delete card.dataset.generatedFix;
      updateApplyAllCount();
    } catch (error) {
      log.error('Undo failed:', error);
      showToastOnCard(card, 'Undo failed — use Ctrl+Z in Word');
    } finally {
      btn.disabled = false;
      btn.innerHTML = `<svg fill="none" stroke="currentColor" viewBox="0 0 24 24" width="12" height="12"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 10h10a5 5 0 015 5v2M3 10l4-4M3 10l4 4"/></svg> Undo`;
    }
  });

  // Generate Fix button — calls AI to produce exact replacement text
  const generateFixBtn = card.querySelector('.generate-fix-btn');
  const generatePanel = card.querySelector('.generate-panel') as HTMLElement;

  generateFixBtn?.addEventListener('click', async () => {
    if (!generatePanel) return;

    // Toggle: if results exist, just show/hide without re-calling API
    if (generatePanel.querySelector('.generate-result')) {
      generatePanel.style.display = generatePanel.style.display === 'none' ? 'block' : 'none';
      return;
    }

    generatePanel.style.display = 'block';
    generatePanel.innerHTML = '<div class="generate-loading">Generating fix...</div>';

    try {
      // Get surrounding context from Word document for better fix quality
      const surroundingContext = await getSurroundingContext(redline.clause_text);
      const currentPlaybookId = playbookSelect()?.value || undefined;

      const result = await api.generateFix({
        originalText: redline.clause_text,
        recommendation: redline.recommendation,
        ruleName: redline.rule_name,
        redlineType: redline.redline_type || 'violation',
        surroundingContext,
        playbookId: currentPlaybookId,
        contractText: lastScannedText || undefined,
      });

      // Store generated fix on card element
      card.dataset.generatedFix = result.fix_text;

      generatePanel.innerHTML = '';

      const wrapper = document.createElement('div');
      wrapper.className = 'generate-result';

      const fixLabel = document.createElement('div');
      fixLabel.className = 'generate-label';
      fixLabel.textContent = 'Generated Fix:';
      wrapper.appendChild(fixLabel);

      // Show word-level diff between original and generated fix
      const diffView = document.createElement('div');
      diffView.className = 'diff-view';
      diffView.style.cssText = 'font-family:Georgia,serif;font-size:13px;line-height:1.6;padding:8px;border:1px solid var(--border,#E8E5E0);border-radius:6px;margin-bottom:8px;';
      diffView.innerHTML = wordDiff(redline.clause_text, result.fix_text);
      wrapper.appendChild(diffView);

      const reasoning = document.createElement('div');
      reasoning.className = 'generate-reasoning';
      reasoning.textContent = result.reasoning;
      wrapper.appendChild(reasoning);

      // Show verification warnings if any
      if (result.fix_warnings && result.fix_warnings.length > 0) {
        const warningsEl = document.createElement('div');
        warningsEl.style.cssText = 'margin:6px 0;padding:6px 8px;background:#FEF3C7;border-radius:6px;border:1px solid #F59E0B;';
        warningsEl.innerHTML = result.fix_warnings.map((w: string) =>
          `<div style="color:#92400E;font-size:11px;line-height:1.4;">\u26a0 ${escapeHtml(w)}</div>`
        ).join('');
        wrapper.appendChild(warningsEl);
      }
      if (result.fix_verified === false) {
        const errorEl = document.createElement('div');
        errorEl.style.cssText = 'margin:6px 0;padding:6px 8px;background:#FEE2E2;border-radius:6px;border:1px solid #EF4444;color:#991B1B;font-size:11px;';
        errorEl.textContent = 'Fix verification failed — review warnings above before applying.';
        wrapper.appendChild(errorEl);
      }

      const actions = document.createElement('div');
      actions.className = 'generate-actions';

      const applyBtn = document.createElement('button');
      applyBtn.className = 'btn btn-primary btn-sm';
      applyBtn.textContent = 'Apply to Document';
      applyBtn.setAttribute('aria-label', `Apply fix to document: ${redline.rule_name}`);
      applyBtn.addEventListener('click', async () => {
        applyBtn.disabled = true;
        applyBtn.textContent = 'Applying...';
        try {
          await applyAIRedline(redline, card, result.fix_text);
          generatePanel.style.display = 'none';
        } catch (err) {
          showToastOnCard(card, 'Apply failed: ' + (err instanceof Error ? err.message : String(err) || 'Unknown error'));
        } finally {
          applyBtn.disabled = false;
          applyBtn.textContent = 'Apply to Document';
        }
      });
      actions.appendChild(applyBtn);

      const regenBtn = document.createElement('button');
      regenBtn.className = 'btn btn-secondary btn-sm';
      regenBtn.textContent = 'Regenerate';
      regenBtn.addEventListener('click', () => {
        // Clear existing result so generateFixBtn doesn't toggle
        const existing = generatePanel.querySelector('.generate-result');
        if (existing) existing.remove();
        (generateFixBtn as HTMLElement)?.click();
      });
      actions.appendChild(regenBtn);

      const closeBtn = document.createElement('button');
      closeBtn.className = 'btn btn-ghost btn-sm';
      closeBtn.textContent = 'Close';
      closeBtn.addEventListener('click', () => {
        generatePanel.style.display = 'none';
      });
      actions.appendChild(closeBtn);

      wrapper.appendChild(actions);
      generatePanel.appendChild(wrapper);
    } catch (error) {
      generatePanel.innerHTML = '';
      const errDiv = document.createElement('div');
      errDiv.className = 'generate-error';
      errDiv.textContent = error instanceof Error ? error.message : 'Failed to generate fix';

      const retryBtn = document.createElement('button');
      retryBtn.className = 'btn btn-secondary btn-sm';
      retryBtn.style.marginTop = '8px';
      retryBtn.textContent = 'Retry';
      retryBtn.addEventListener('click', () => {
        (generateFixBtn as HTMLElement)?.click();
      });

      generatePanel.appendChild(errDiv);
      generatePanel.appendChild(retryBtn);
    }
  });

  // Research clause button
  const researchBtn = card.querySelector('.research-btn');
  const researchPanel = card.querySelector('.research-panel') as HTMLElement;

  researchBtn?.addEventListener('click', async () => {
    if (!researchPanel) return;

    // Toggle: if results exist, just show/hide without re-calling API
    if (researchPanel.querySelector('.research-result')) {
      researchPanel.style.display = researchPanel.style.display === 'none' ? 'block' : 'none';
      return;
    }

    researchPanel.style.display = 'block';
    researchPanel.innerHTML = '<div class="research-loading">Researching case law...</div>';

    try {
      const result = await api.researchClause(redline.clause_text, redline.rule_name);

      researchPanel.innerHTML = '';

      const wrapper = document.createElement('div');
      wrapper.className = 'research-result';

      // Disclaimer — always show first
      const disclaimer = document.createElement('div');
      disclaimer.className = 'research-disclaimer';
      disclaimer.textContent = result.disclaimer;
      wrapper.appendChild(disclaimer);

      // Legal principle
      if (result.legal_principle) {
        const principle = document.createElement('div');
        principle.className = 'research-principle';
        principle.textContent = result.legal_principle;
        wrapper.appendChild(principle);
      }

      // Cases
      if (result.cases.length === 0) {
        const empty = document.createElement('div');
        empty.className = 'research-empty';
        empty.textContent = 'No relevant cases found.';
        wrapper.appendChild(empty);
      } else {
        result.cases.forEach((c) => {
          const caseEl = document.createElement('div');
          caseEl.className = 'research-case';

          const nameEl = document.createElement('div');
          nameEl.className = 'research-case-name';
          nameEl.textContent = c.case_name;
          caseEl.appendChild(nameEl);

          const metaEl = document.createElement('div');
          metaEl.className = 'research-case-meta';
          metaEl.textContent = `${c.citation} | ${c.court} | ${c.year}`;
          caseEl.appendChild(metaEl);

          const holdingEl = document.createElement('div');
          holdingEl.className = 'research-case-holding';
          holdingEl.textContent = c.holding;
          caseEl.appendChild(holdingEl);

          const relevanceEl = document.createElement('div');
          relevanceEl.className = 'research-case-relevance';
          relevanceEl.textContent = c.relevance;
          caseEl.appendChild(relevanceEl);

          wrapper.appendChild(caseEl);
        });
      }

      // Close button
      const closeBtn = document.createElement('button');
      closeBtn.className = 'btn btn-ghost btn-sm';
      closeBtn.textContent = 'Close';
      closeBtn.style.marginTop = '8px';
      closeBtn.addEventListener('click', () => { researchPanel.style.display = 'none'; });
      wrapper.appendChild(closeBtn);

      researchPanel.appendChild(wrapper);
    } catch (error) {
      researchPanel.innerHTML = '';
      const errDiv = document.createElement('div');
      errDiv.className = 'generate-error';
      errDiv.textContent = error instanceof Error ? error.message : 'Failed to research clause';
      researchPanel.appendChild(errDiv);
    }
  });

  // Re-scan button handler
  const reScanBtn = card.querySelector('.rescan-btn');
  reScanBtn?.addEventListener('click', () => reScanClause(redline.id, redline.clause_text));

  // Negotiation mode: add accept/counter/escalate buttons and compact card behavior
  if (negotiationMode) {
    const negActions = document.createElement('div');
    negActions.className = 'negotiation-actions';
    negActions.innerHTML = `
      <button class="neg-btn accept" data-decision="accept">Accept</button>
      <button class="neg-btn counter" data-decision="counter">Counter</button>
      <button class="neg-btn escalate" data-decision="escalate">Escalate</button>
    `;
    card.appendChild(negActions);

    const existingDecision = negotiationSession?.decisions.find(d => d.risk_id === redline.id);
    if (existingDecision) {
      const activeBtn = negActions.querySelector(`[data-decision="${existingDecision.decision}"]`);
      if (activeBtn) activeBtn.classList.add('active');
    }

    negActions.querySelectorAll('.neg-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const decision = (btn as HTMLElement).dataset.decision as 'accept' | 'counter' | 'escalate';
        negActions.querySelectorAll('.neg-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        recordNegotiationDecision(redline.id, decision);
      });
    });

    // Make card expandable in negotiation mode
    const header = card.querySelector('.risk-card-header');
    header?.addEventListener('click', () => card.classList.toggle('expanded'));
  }

  return card;
}

/**
 * Highlight text found by AI using three-tier search.
 * Uses blue for missing clause anchors, red/yellow for violations.
 */
async function highlightAIText(searchText: string, riskLevel: 'RED' | 'YELLOW' | 'GREEN', redlineType?: string): Promise<{ method: string; confidence: number }> {
  try {
    return await Word.run(async (context) => {
      const result = await findTextInDocument(searchText, context);

      if (result.range) {
        let color: string;
        if (redlineType === 'missing') {
          color = '#93C5FD'; // Blue for missing clause insert points
        } else {
          color = riskLevel === 'RED' ? '#F87171' : riskLevel === 'GREEN' ? '#86EFAC' : '#FEF08A';
        }
        result.range.font.highlightColor = color;
        result.range.select();
        await context.sync();

        log.info(`Highlighted via ${result.method} match (confidence: ${result.confidence.toFixed(2)})`);
        return { method: result.method, confidence: result.confidence };
      } else {
        log.warn('Could not find text in document:', searchText.slice(0, 50) + '...');
        return { method: 'none', confidence: 0 };
      }
    });
  } catch (error) {
    log.error('Highlight error:', error);
    return { method: 'none', confidence: 0 };
  }
}

/**
 * Undo a previously applied redline fix.
 * For violations: finds the applied fix text and replaces it back with original_text.
 * For missing clauses: finds the inserted text and removes it.
 */
async function undoRedlineFix(redline: RedlineItem, appliedFix?: string): Promise<void> {
  await Word.run(async (context) => {
    const searchText = appliedFix || redline.recommendation;
    if (!searchText) return;

    // Use stored location info for precise undo targeting
    const fixInfo = appliedFixesMap.get(redline.id);
    let targetRange: Word.Range | null = null;

    if (fixInfo && fixInfo.paragraphIndex >= 0) {
      // Try paragraph-index-based matching first to avoid wrong-location undo
      try {
        const body = context.document.body;
        const allParas = body.paragraphs;
        allParas.load('items/text');
        await context.sync();

        if (fixInfo.paragraphIndex < allParas.items.length) {
          const para = allParas.items[fixInfo.paragraphIndex];
          // Verify context hash matches (paragraph content is still similar)
          if (para.text.substring(0, 100) === fixInfo.contextHash ||
              para.text.includes(searchText.substring(0, 50))) {
            // Search within this specific paragraph
            const paraRange = para.getRange();
            const searchResults = paraRange.search(searchText.substring(0, 255), { matchCase: false });
            searchResults.load('items');
            await context.sync();
            if (searchResults.items.length > 0) {
              targetRange = searchResults.items[0];
            }
          }
        }
      } catch (locErr) {
        log.warn('Paragraph-based undo lookup failed, falling back to global search:', locErr);
      }
    }

    // Fallback: global search
    if (!targetRange) {
      const result = await findTextInDocument(searchText, context);
      if (!result.range) {
        throw new Error('Could not locate the applied fix in the document');
      }
      targetRange = result.range;
    }

    if (redline.redline_type === 'missing') {
      targetRange.delete();
    } else {
      targetRange.insertText(redline.clause_text, Word.InsertLocation.replace);
    }
    await context.sync();

    // Clean up stored location
    appliedFixesMap.delete(redline.id);
    log.info(`Undid fix for: ${redline.rule_name}`);
  });
}

/**
 * Revert ALL applied fixes at once. Walks the appliedFixesMap and restores
 * each clause to its original text, then clears the map and resets UI.
 */
async function revertAllFixes(): Promise<void> {
  if (appliedFixesMap.size === 0) return;
  const entries = Array.from(appliedFixesMap.entries());
  let reverted = 0;
  for (const [id, fixInfo] of entries) {
    try {
      await Word.run(async (context) => {
        const searchText = fixInfo.fixText.substring(0, 255);
        const body = context.document.body;
        const searchResults = body.search(searchText, { matchCase: false });
        searchResults.load('items');
        await context.sync();
        if (searchResults.items.length > 0) {
          searchResults.items[0].insertText(fixInfo.originalText, Word.InsertLocation.replace);
          await context.sync();
          reverted++;
        }
      });
      appliedFixesMap.delete(id);
    } catch (err) {
      log.warn(`Failed to revert fix ${id}:`, err);
    }
  }
  // Reset fixed-risk UI state
  fixedRisks.clear();
  const cards = document.querySelectorAll('.risk-card.fixed');
  cards.forEach(c => c.classList.remove('fixed'));
  log.info(`Reverted ${reverted}/${entries.length} applied fixes`);
}

/**
 * Highlight all AI redlines in the document.
 * Batched approach: queues all searches in one sync, then applies all highlights in a second sync.
 * Reduces N+1 round-trips to just 2.
 */
async function highlightAIRedlines(redlines: RedlineItem[]): Promise<void> {
  if (!redlines.length) return;
  try {
    await Word.run(async (context) => {
      const body = context.document.body;
      // Batch all searches in one sync
      const searchSets = redlines.map(r => {
        const searchText = r.clause_text.slice(0, 255);
        const results = body.search(searchText, { matchCase: false, matchWholeWord: false });
        results.load('items');
        return { redline: r, results };
      });
      await context.sync();

      // Apply all highlights
      for (const { redline, results } of searchSets) {
        if (results.items.length > 0) {
          let highlightColor: string;
          if (redline.redline_type === 'missing') {
            highlightColor = '#93C5FD'; // Blue for insertion points
          } else {
            highlightColor = redline.risk_level === 'RED' ? '#F87171' : '#FEF08A';
          }
          results.items[0].font.highlightColor = highlightColor;
        }
      }
      await context.sync();
      log.info(`Highlighted ${redlines.length} redlines in document`);
    });
  } catch (error) {
    log.error('Bulk highlight error:', error);
  }
}

/**
 * Compute word-level diffs between original and replacement text.
 * Uses a greedy LCS-like approach to identify keep/replace/delete/insert operations.
 * Returns operations suitable for surgical Word API search+replace.
 */
function computeWordDiffs(original: string, replacement: string): Array<{type: 'keep'|'replace'|'delete'|'insert', oldText: string, newText: string}> {
  const origWords = original.split(/(\s+)/);
  const replWords = replacement.split(/(\s+)/);
  const diffs: Array<{type: 'keep'|'replace'|'delete'|'insert', oldText: string, newText: string}> = [];
  let i = 0, j = 0;
  while (i < origWords.length && j < replWords.length) {
    if (origWords[i] === replWords[j]) {
      diffs.push({type: 'keep', oldText: origWords[i], newText: replWords[j]});
      i++; j++;
    } else {
      // Find next matching word in both sequences (look ahead up to 10 tokens)
      let foundOrig = -1, foundRepl = -1;
      for (let k = i + 1; k < Math.min(i + 10, origWords.length); k++) {
        if (origWords[k] === replWords[j]) { foundOrig = k; break; }
      }
      for (let k = j + 1; k < Math.min(j + 10, replWords.length); k++) {
        if (replWords[k] === origWords[i]) { foundRepl = k; break; }
      }
      if (foundOrig >= 0 && (foundRepl < 0 || foundOrig - i <= foundRepl - j)) {
        // Delete words from original until match
        for (let k = i; k < foundOrig; k++) diffs.push({type: 'delete', oldText: origWords[k], newText: ''});
        i = foundOrig;
      } else if (foundRepl >= 0) {
        // Insert words from replacement until match
        for (let k = j; k < foundRepl; k++) diffs.push({type: 'insert', oldText: '', newText: replWords[k]});
        j = foundRepl;
      } else {
        diffs.push({type: 'replace', oldText: origWords[i], newText: replWords[j]});
        i++; j++;
      }
    }
  }
  while (i < origWords.length) { diffs.push({type: 'delete', oldText: origWords[i++], newText: ''}); }
  while (j < replWords.length) { diffs.push({type: 'insert', oldText: '', newText: replWords[j++]}); }
  return diffs;
}

/**
 * Apply an AI-suggested fix using Track Changes.
 * Primary approach: surgical word-level search+replace (avoids OOXML paragraph destruction).
 * Fallback: OOXML insertOoxml if surgical approach fails.
 */
async function applyAIRedline(redline: RedlineItem, cardElement: HTMLElement, fixText?: string): Promise<void> {
  // Fix #10: Don't fall back to recommendation as literal replacement text
  const textToApply = fixText;
  if (!textToApply) {
    showNotification('No replacement text available. Please generate a fix first.', 'warning');
    return;
  }

  // Fix #2: Read-only document check
  const readOnly = await isDocumentReadOnly();
  if (readOnly) {
    showNotification('This document is read-only or protected. Cannot apply changes.', 'error');
    return;
  }

  // Office webview doesn't support window.confirm() — proceed directly

  // P1 #27: Loading indicator — disable all apply buttons on this card
  const cardApplyBtns = cardElement.querySelectorAll('.btn-primary') as NodeListOf<HTMLButtonElement>;
  cardApplyBtns.forEach(btn => { btn.disabled = true; });
  cardElement.classList.add('applying');
  // Add a visual applying indicator
  let applyingIndicator: HTMLElement | null = null;
  try {
    applyingIndicator = document.createElement('div');
    applyingIndicator.className = 'applying-indicator';
    applyingIndicator.style.cssText = 'padding:6px 8px;background:#DBEAFE;border-radius:6px;margin:4px 0;font-size:11px;color:#1E40AF;text-align:center;';
    applyingIndicator.textContent = 'Applying fix to document...';
    cardElement.appendChild(applyingIndicator);
  } catch { /* indicator is non-critical */ }

  try {
    let surgicalSuccess = false;

    // PRIMARY APPROACH: Surgical word-level search+replace (P0 #1 + #5)
    // This avoids OOXML paragraph destruction and double-tracked revisions
    if (redline.redline_type !== 'missing') {
      try {
        await Word.run(async (context) => {
          // Enable tracked changes before applying edits (requires WordApi 1.4+)
          try {
            context.document.changeTrackingMode = Word.ChangeTrackingMode.trackAll;
            await context.sync();
          } catch (trackErr) {
            log.warn('Could not enable ChangeTrackingMode:', trackErr);
          }

          const result = await findTextInDocument(redline.clause_text, context);

          if (!result.range) {
            // Will fall through to OOXML fallback
            throw new Error('SURGICAL_NO_RANGE');
          }

          // Compute word-level diffs between original and replacement
          const diffs = computeWordDiffs(redline.clause_text, textToApply);

          // Check if there are actual changes to apply
          const hasChanges = diffs.some(d => d.type !== 'keep');
          if (!hasChanges) {
            log.warn('No differences found between original and fix text');
            throw new Error('SURGICAL_NO_DIFFS');
          }

          // Collect non-whitespace-only change operations for surgical replacement
          const changeOps = diffs.filter(d => d.type !== 'keep' && d.oldText.trim() !== '' || (d.type === 'insert' && d.newText.trim() !== ''));

          // For each replacement/deletion, search within the found range and apply
          // Process in REVERSE order to avoid position shifting
          const reversedOps = [...changeOps].reverse();

          for (const op of reversedOps) {
            if (op.type === 'replace' && op.oldText.trim()) {
              // Search for the old word within the clause range
              const searchResults = result.range.search(op.oldText, { matchCase: true, matchWholeWord: false });
              searchResults.load('items');
              await context.sync();

              if (searchResults.items.length > 0) {
                // Replace with new text — Word natively tracks this change
                searchResults.items[searchResults.items.length - 1].insertText(op.newText, Word.InsertLocation.replace);
                await context.sync();
              }
            } else if (op.type === 'delete' && op.oldText.trim()) {
              // Search for the word to delete within the clause range
              const searchResults = result.range.search(op.oldText, { matchCase: true, matchWholeWord: false });
              searchResults.load('items');
              await context.sync();

              if (searchResults.items.length > 0) {
                searchResults.items[searchResults.items.length - 1].delete();
                await context.sync();
              }
            } else if (op.type === 'insert' && op.newText.trim()) {
              // For insertions, find preceding context and insert after it
              // Look backwards in diffs for the nearest 'keep' or 'replace' to use as anchor
              const opIdx = diffs.indexOf(op);
              let anchorText = '';
              for (let ai = opIdx - 1; ai >= 0; ai--) {
                const prev = diffs[ai];
                if ((prev.type === 'keep' || prev.type === 'replace') && prev.oldText.trim()) {
                  anchorText = prev.type === 'keep' ? prev.oldText : prev.newText;
                  break;
                }
              }
              if (anchorText.trim()) {
                const anchorResults = result.range.search(anchorText, { matchCase: true, matchWholeWord: false });
                anchorResults.load('items');
                await context.sync();
                if (anchorResults.items.length > 0) {
                  anchorResults.items[anchorResults.items.length - 1].insertText(op.newText, Word.InsertLocation.after);
                  await context.sync();
                }
              }
            }
          }

          // Add a comment explaining the redline
          try {
            result.range.insertComment(`ContraRed: ${redline.explanation || redline.rule_name || 'AI-suggested revision'}`);
            await context.sync();
          } catch (commentErr) {
            log.warn('Could not insert comment:', commentErr);
          }

          surgicalSuccess = true;
          log.info(`Surgical replace succeeded for: ${redline.rule_name}`);
        });
      } catch (surgicalErr) {
        const errMsg = surgicalErr instanceof Error ? surgicalErr.message : String(surgicalErr);
        if (!errMsg.includes('SURGICAL_')) {
          log.warn('Surgical replace failed, falling back to OOXML:', surgicalErr);
        } else {
          log.info('Surgical approach not applicable, using OOXML fallback');
        }
        surgicalSuccess = false;
      }
    }

    // FALLBACK: OOXML approach (for 'missing' type or when surgical fails)
    if (!surgicalSuccess) {
      // Fetch OOXML BEFORE entering Word.run to avoid context timeout
      const redlineResponse = await api.generateRedlineZDR(
        currentAIAnalysis?.document_id || 'ai-doc',
        redline.id,
        redline.clause_text,
        textToApply,
        undefined,
        redline.redline_type || 'violation'
      );

      await Word.run(async (context) => {
        // Enable tracked changes before applying edits (requires WordApi 1.4+)
        try {
          context.document.changeTrackingMode = Word.ChangeTrackingMode.trackAll;
          await context.sync();
        } catch (trackErr) {
          log.warn('Could not enable ChangeTrackingMode:', trackErr);
        }

        const result = await findTextInDocument(redline.clause_text, context);

        if (!result.range) {
          showToastOnCard(cardElement, 'Could not locate this clause — text may have been modified');
          return;
        }

        // Apply the Track Changes OOXML (fallback path)
        if (redline.redline_type === 'missing') {
          result.range.insertOoxml(redlineResponse.ooxml, Word.InsertLocation.after);
        } else {
          result.range.insertOoxml(redlineResponse.ooxml, Word.InsertLocation.replace);
        }
        await context.sync();

        // After applying the fix, add a comment explaining the redline
        try {
          result.range.insertComment(`ContraRed: ${redline.explanation || redline.rule_name || 'AI-suggested revision'}`);
          await context.sync();
        } catch (commentErr) {
          log.warn('Could not insert comment:', commentErr);
        }

        log.info(`OOXML fallback applied for: ${redline.rule_name}`);
      });
    }

    // Store precise location info for undo targeting (runs after either path)
    await Word.run(async (context) => {
      let paragraphIndex = -1;
      try {
        const body = context.document.body;
        const allParas = body.paragraphs;
        allParas.load('items/text');
        await context.sync();
        for (let pi = 0; pi < allParas.items.length; pi++) {
          if (allParas.items[pi].text.includes(textToApply.substring(0, 50))) {
            paragraphIndex = pi;
            break;
          }
        }
        const contextHash = paragraphIndex >= 0 ? allParas.items[paragraphIndex].text.substring(0, 100) : '';
        appliedFixesMap.set(redline.id, {
          originalText: redline.clause_text,
          fixText: textToApply,
          paragraphIndex,
          contextHash,
        });
      } catch (locErr) {
        log.warn('Could not store fix location for undo:', locErr);
      }
    });

    // Mark as fixed and store the applied text for undo
    fixedRisks.add(redline.id);
    cardElement.classList.add('fixed');
    cardElement.dataset.appliedFix = textToApply;
    saveScanState();

    // Show re-scan button so user can verify the fix
    const reScanBtn = cardElement.querySelector('.rescan-btn') as HTMLElement;
    if (reScanBtn) reScanBtn.style.display = 'inline-flex';

    // P1 #27: Show success state
    if (applyingIndicator) {
      applyingIndicator.style.background = '#D1FAE5';
      applyingIndicator.style.color = '#065F46';
      applyingIndicator.textContent = 'Fix applied successfully';
      setTimeout(() => applyingIndicator?.remove(), 3000);
    }
  } catch (error) {
    showToastOnCard(cardElement, 'Fix failed: ' + (error instanceof Error ? error.message : String(error) || 'Unknown error'));
    // P1 #27: Show failure state
    if (applyingIndicator) {
      applyingIndicator.style.background = '#FEE2E2';
      applyingIndicator.style.color = '#991B1B';
      applyingIndicator.textContent = 'Fix failed — see error above';
      setTimeout(() => applyingIndicator?.remove(), 5000);
    }
  } finally {
    // P1 #27: Re-enable buttons
    cardApplyBtns.forEach(btn => { btn.disabled = false; });
    cardElement.classList.remove('applying');
  }
}


/**
 * Apply all unfixed redlines sequentially.
 * Respects the current filter — only applies visible redlines.
 */
let applyAllCancelled = false;

async function applyAllRedlines(): Promise<void> {
  if (!currentAIAnalysis) return;

  const unfixed = getFilteredRedlines().filter(r => !fixedRisks.has(r.id));
  if (unfixed.length === 0) return;

  applyAllCancelled = false;

  const applyBtn = document.getElementById('applyAllBtn') as HTMLButtonElement;
  const progressDiv = document.getElementById('applyProgress');
  const progressFill = document.getElementById('progressFill');
  const progressText = document.getElementById('progressText');

  if (applyBtn) { applyBtn.disabled = false; applyBtn.textContent = 'Cancel'; applyBtn.onclick = () => { applyAllCancelled = true; }; }
  if (progressDiv) progressDiv.style.display = 'block';

  // Check if we have generated fixes ready to apply
  const withGeneratedFix = unfixed.filter(r => document.getElementById(`risk-${r.id}`)?.dataset.generatedFix);

  if (withGeneratedFix.length > 0) {
    // Phase 2: Apply all generated fixes
    let applied = 0;
    let failed = 0;

    for (const redline of withGeneratedFix) {
      if (applyAllCancelled) { if (progressText) progressText.textContent = `Cancelled. ${applied} applied, ${failed} failed.`; break; }

      const pct = ((applied + failed) / withGeneratedFix.length) * 100;
      if (progressFill) progressFill.style.width = `${pct}%`;
      if (progressText) progressText.textContent = `Applying ${applied + failed + 1} / ${withGeneratedFix.length}`;

      const card = document.getElementById(`risk-${redline.id}`);
      const fixText = card?.dataset.generatedFix;
      if (!card || !fixText) { failed++; continue; }

      try {
        await applyAIRedline(redline, card, fixText);
        applied++;
      } catch {
        failed++;
      }
    }

    if (!applyAllCancelled) {
      if (progressFill) progressFill.style.width = '100%';
      if (progressText) progressText.textContent = `Done: ${applied} applied${failed > 0 ? `, ${failed} failed` : ''}`;
    }
  } else {
    // Phase 1: Generate all fixes first
    let generated = 0;
    let failed = 0;

    for (const redline of unfixed) {
      if (applyAllCancelled) { if (progressText) progressText.textContent = `Cancelled. ${generated} generated, ${failed} failed.`; break; }

      const pct = ((generated + failed) / unfixed.length) * 100;
      if (progressFill) progressFill.style.width = `${pct}%`;
      if (progressText) progressText.textContent = `Generating fix ${generated + failed + 1} / ${unfixed.length}`;

      const card = document.getElementById(`risk-${redline.id}`);
      if (!card) { failed++; continue; }

      try {
        const surroundingContext = await getSurroundingContext(redline.clause_text);
        const currentPlaybookId = playbookSelect()?.value || undefined;

        const result = await api.generateFix({
          originalText: redline.clause_text,
          recommendation: redline.recommendation,
          ruleName: redline.rule_name,
          redlineType: redline.redline_type || 'violation',
          surroundingContext,
          playbookId: currentPlaybookId,
        });

        // Store on card and show in generate panel
        card.dataset.generatedFix = result.fix_text;
        const genPanel = card.querySelector('.generate-panel') as HTMLElement;
        if (genPanel) {
          genPanel.style.display = 'block';
          genPanel.innerHTML = '';
          const wrapper = document.createElement('div');
          wrapper.className = 'generate-result';
          const label = document.createElement('div');
          label.className = 'generate-label';
          label.textContent = 'Generated Fix:';
          wrapper.appendChild(label);
          const diffView = document.createElement('div');
          diffView.className = 'diff-view';
          diffView.style.cssText = 'font-family:Georgia,serif;font-size:13px;line-height:1.6;padding:8px;border:1px solid var(--border,#E8E5E0);border-radius:6px;margin-bottom:8px;';
          diffView.innerHTML = wordDiff(redline.clause_text, result.fix_text);
          wrapper.appendChild(diffView);
          const reasoning = document.createElement('div');
          reasoning.className = 'generate-reasoning';
          reasoning.textContent = result.reasoning;
          wrapper.appendChild(reasoning);
          genPanel.appendChild(wrapper);
        }
        generated++;
      } catch {
        failed++;
      }
    }

    if (progressFill) progressFill.style.width = '100%';
    if (progressText) progressText.textContent = `Generated ${generated}/${unfixed.length} fixes${failed > 0 ? ` (${failed} failed)` : ''}. Review, then click to apply.`;
  }

  // Restore button to normal state
  if (applyBtn) {
    applyBtn.disabled = false;
    applyBtn.onclick = () => applyAllRedlines();
  }
  updateApplyAllCount();
}

/**
 * Export risk report as DOCX download.
 */
async function exportReport(): Promise<void> {
  if (!currentAIAnalysis) return;

  const btn = document.getElementById('exportReportBtn') as HTMLButtonElement;
  if (btn) { btn.disabled = true; btn.textContent = 'Generating...'; }

  try {
    const blob = await api.exportReport(currentAIAnalysis);
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = (currentAIAnalysis.filename || 'contract').replace('.docx', '') + '-risk-report.docx';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  } catch (error) {
    log.error('Export failed:', error instanceof Error ? error.message : String(error));
    showNotification('Export failed. Please try again.', 'error');
  } finally {
    if (btn) { btn.disabled = false; btn.textContent = 'Export Report'; }
  }
}

async function getDocumentText(): Promise<string> {
  return Word.run(async (context) => {
    const body = context.document.body;
    body.load('text');
    await context.sync();
    return body.text;
  });
}

// Skeleton loader state
let statusInterval: ReturnType<typeof setInterval> | null = null;
let elapsedInterval: ReturnType<typeof setInterval> | null = null;

function setScanLoading(loading: boolean): void {
  const btn = scanBtn() as HTMLButtonElement | null;
  const btnText = scanBtnText();
  const spinner = scanSpinner();

  if (btn) btn.disabled = loading;
  if (btnText) btnText.style.display = loading ? 'none' : 'inline';
  if (spinner) spinner.style.display = loading ? 'block' : 'none';

  if (loading) {
    startSkeletonLoader();
  } else {
    stopSkeletonLoader();
  }
}

const statusMessages = [
  'Analysing contract\u2026',
  'Reviewing clause language\u2026',
  'Checking against playbook\u2026',
  'Assessing risk exposure\u2026',
  'Deep analysis in progress\u2026',
  'Reviewing all clauses\u2026',
  'Cross-referencing playbook rules\u2026',
  'Preparing risk summary\u2026',
];

function startSkeletonLoader(): void {
  const loader = document.getElementById('reasoningLoader');
  if (!loader) return;

  loader.classList.add('active');

  // Rotate status text
  let msgIndex = 0;
  const statusText = document.getElementById('analysisStatusText');
  if (statusText) statusText.textContent = statusMessages[0];

  statusInterval = setInterval(() => {
    msgIndex = (msgIndex + 1) % statusMessages.length;
    if (statusText) statusText.textContent = statusMessages[msgIndex];
  }, 5000);

  // Elapsed time counter
  let elapsed = 0;
  const elapsedEl = document.getElementById('analysisElapsed');
  if (elapsedEl) elapsedEl.textContent = '0s';

  elapsedInterval = setInterval(() => {
    elapsed++;
    if (elapsedEl) {
      if (elapsed < 60) {
        elapsedEl.textContent = `${elapsed}s`;
      } else {
        const mins = Math.floor(elapsed / 60);
        const secs = elapsed % 60;
        elapsedEl.textContent = `${mins}m ${secs}s`;
      }
    }
    // Informational message after 5 minutes (no timeout)
    if (elapsed === 300 && statusText) {
      statusText.textContent = 'Still analysing\u2026 large documents take longer';
    }
  }, 1000);
}

function stopSkeletonLoader(): void {
  if (statusInterval) {
    clearInterval(statusInterval);
    statusInterval = null;
  }
  if (elapsedInterval) {
    clearInterval(elapsedInterval);
    elapsedInterval = null;
  }

  const loader = document.getElementById('reasoningLoader');
  if (loader) {
    loader.classList.remove('active');
  }
}

// ============================================================================
// Exports (for testing)
// ============================================================================

export { scanDocument, highlightAIText, applyAIRedline, applyAllRedlines, exportReport };
