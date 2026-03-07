/**
 * ContraRed - Word Add-in Main Logic
 * 
 * Implements: Login, Document Scan, Risk Highlighting, Redline Application
 * Now with AI-First analysis using Gemini for holistic contract review.
 */

import { api, AIRedlineItem, AIAnalysisResult, DocumentListItem } from './api';
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

/**
 * Read surrounding context (paragraph text) around a given text in the Word document.
 * Gives the AI model the full clause context for better fix generation.
 */
async function getSurroundingContext(originalText: string): Promise<string> {
  try {
    return await Word.run(async (context) => {
      const result = await findTextInDocument(originalText, context);
      if (!result.range) return '';

      // Get the paragraph containing the text
      const para = result.range.paragraphs;
      para.load('items/text');
      await context.sync();

      if (para.items.length === 0) return '';

      // Get the first paragraph's parent body to find adjacent paragraphs
      const firstPara = para.items[0];
      const body = context.document.body;
      const allParas = body.paragraphs;
      allParas.load('items/text');
      await context.sync();

      // Find index of our paragraph and get one before + one after
      const texts: string[] = [];
      let foundIdx = -1;
      for (let i = 0; i < allParas.items.length; i++) {
        if (allParas.items[i].text === firstPara.text && foundIdx === -1) {
          foundIdx = i;
        }
      }

      if (foundIdx > 0) texts.push(allParas.items[foundIdx - 1].text);
      if (foundIdx >= 0) texts.push(allParas.items[foundIdx].text);
      if (foundIdx >= 0 && foundIdx + 1 < allParas.items.length) texts.push(allParas.items[foundIdx + 1].text);

      const combined = texts.join('\n');
      // Cap at ~5000 chars to keep API payload reasonable
      return combined.length > 5000 ? combined.slice(0, 5000) : combined;
    });
  } catch (error) {
    log.warn('Failed to get surrounding context:', error);
    return '';
  }
}

// ============================================================================
// State
// ============================================================================

let currentAIAnalysis: AIAnalysisResult | null = null;
const fixedRisks: Set<string> = new Set();
let isScanning = false;  // Guard against double-click race condition

// Filter & Sort state
let activeFilter: 'ALL' | 'RED' | 'YELLOW' | 'UNFIXED' = 'ALL';
let activeSort: 'risk_level' | 'rule_name' = 'risk_level';
let searchQuery = '';

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

    // Template picker
    document.getElementById('templateBtn')?.addEventListener('click', toggleTemplatePicker);
    document.getElementById('templatePickerClose')?.addEventListener('click', () => {
      const picker = document.getElementById('templatePicker');
      if (picker) picker.style.display = 'none';
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

    // Export report
    document.getElementById('exportReportBtn')?.addEventListener('click', exportReport);

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

  // Load available playbooks
  loadPlaybooks();

  // Load recent scans
  loadRecentScans();
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
        <div class="recent-scan-item" title="${escapeHtml(doc.filename)} — ${doc.total_risks} risks">
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
    picker.style.display = 'none';
    return;
  }

  picker.style.display = 'block';
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
          <span class="template-badge ${escapeHtml(t.category)}">${escapeHtml(t.category)}</span>
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
    if (modal) modal.style.display = 'block';
  });

  createCancel?.addEventListener('click', () => {
    const modal = document.getElementById('createPlaybookModal');
    if (modal) modal.style.display = 'none';
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

  if (errorDiv) errorDiv.classList.remove('show');
  if (submitBtn) submitBtn.disabled = true;

  try {
    await api.createPlaybook(name, descInput?.value?.trim() || undefined, categorySelect?.value || 'custom');
    // Close modal and refresh playbooks
    const modal = document.getElementById('createPlaybookModal');
    if (modal) modal.style.display = 'none';
    clearPlaybookForm();
    await loadPlaybooks();
  } catch (error) {
    if (errorDiv) {
      errorDiv.textContent = (error as Error).message || 'Failed to create playbook';
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

  setLoginLoading(true);
  hideLoginError();

  try {
    await api.login(email, password);
    showMainPanel();
  } catch (error) {
    showLoginError((error as Error).message || 'Login failed');
  } finally {
    setLoginLoading(false);
  }
}

function handleLogout(): void {
  api.logout();
  currentAIAnalysis = null;
  fixedRisks.clear();

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
  context: Word.RequestContext
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
    threshold: 0.4,  // Allow 40% difference
    includeScore: true,
  });

  const fuzzyResults = fuse.search(searchText);

  if (fuzzyResults.length > 0 && fuzzyResults[0].score !== undefined) {
    const bestMatch = fuzzyResults[0];
    const confidence = 1 - (bestMatch.score || 0);  // Convert score to confidence

    // Get the range of the matched paragraph
    const matchedParagraph = paragraphData[bestMatch.refIndex];
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

    if (!documentText || documentText.trim().length < 50) {
      displayScanError(new Error('Document appears to be empty or too short. Please add some contract text.'));
      return;
    }

    // Step 2: Call AI-First analysis API (with selected playbook)
    const selectedPlaybookId = playbookSelect()?.value || undefined;
    log.info('Starting analysis...');

    const aiResult = await api.analyzeWithAI(documentText, 'document.docx', selectedPlaybookId);

    currentAIAnalysis = aiResult;
    fixedRisks.clear();

    // Step 3: Display AI results (executive summary + redlines)
    displayAIResults(aiResult);

    // Step 4: Highlight risks in document using three-tier search
    await highlightAIRedlines(aiResult.redlines);
    log.info('Analysis complete:', { risks: aiResult.redlines?.length, tokens: aiResult.tokens_used });

  } catch (error) {
    log.error('Scan failed:', error);
    displayScanError(error as Error);
  } finally {
    isScanning = false;
    setScanLoading(false);
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
function displayAIResults(result: AIAnalysisResult): void {
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
  if (greenCount()) greenCount()!.textContent = '0';  // AI doesn't return green
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
  if (bulkBar) bulkBar.style.display = result.redlines.length > 0 ? 'block' : 'none';

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
function getFilteredRedlines(): AIRedlineItem[] {
  if (!currentAIAnalysis) return [];

  let filtered = [...currentAIAnalysis.redlines];

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
      r.original_text.toLowerCase().includes(q) ||
      r.explanation.toLowerCase().includes(q)
    );
  }

  // Apply sort
  if (activeSort === 'risk_level') {
    const order: Record<string, number> = { RED: 0, YELLOW: 1 };
    filtered.sort((a, b) => (order[a.risk_level] ?? 2) - (order[b.risk_level] ?? 2));
  } else if (activeSort === 'rule_name') {
    filtered.sort((a, b) => a.rule_name.localeCompare(b.rule_name));
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
    if (riskCount()) riskCount()!.textContent = '0 items';
    return;
  }

  const empty = emptyState();
  if (empty) empty.style.display = 'none';
  if (riskCount()) riskCount()!.textContent = `${filtered.length} items`;

  const docId = currentAIAnalysis?.document_id || '';
  filtered.forEach((redline) => {
    const card = createAIRedlineCard(redline, docId);
    if (fixedRisks.has(redline.id)) card.classList.add('fixed');
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

  if (unfixed === 0) {
    if (btnText) btnText.textContent = 'All Fixed';
    if (applyBtn) applyBtn.disabled = true;
  } else if (generated > 0) {
    // Some fixes already generated — show "Apply N Generated"
    if (btnText) btnText.textContent = `Apply ${generated} Generated Fix${generated !== 1 ? 'es' : ''}`;
    if (applyBtn) applyBtn.disabled = false;
  } else {
    if (btnText) btnText.textContent = `Generate All Fixes (${unfixed})`;
    if (applyBtn) applyBtn.disabled = false;
  }
}

/**
 * Create a risk card for an AI redline item.
 */
function createAIRedlineCard(redline: AIRedlineItem, _documentId: string): HTMLElement {
  const card = document.createElement('div');
  card.className = 'risk-card';
  card.id = `risk-${redline.id}`;
  card.dataset.risk = redline.risk_level.toLowerCase();

  const isMissing = redline.redline_type === 'missing';
  const truncatedClause = redline.original_text.length > 100
    ? redline.original_text.slice(0, 100) + '...'
    : redline.original_text;
  const truncatedRec = redline.recommendation
    ? (redline.recommendation.length > 150 ? redline.recommendation.slice(0, 150) + '...' : redline.recommendation)
    : '';
  const clauseLabel = isMissing ? 'Insert after: ' : '';
  const typeBadge = isMissing
    ? '<span class="redline-type-badge type-missing">Missing</span>'
    : '<span class="redline-type-badge type-violation">Violation</span>';

  card.innerHTML = `
    <div class="risk-card-header">
      <div class="risk-title"></div>
      ${typeBadge}
    </div>
    <div class="risk-clause"><span class="clause-label">${escapeHtml(clauseLabel)}</span><span class="clause-text"></span></div>
    <div class="risk-explanation"></div>
    ${redline.recommendation ? `
      <div class="suggested-fix">
        <strong>Recommendation:</strong> <span class="suggested-fix-text"></span>
      </div>
    ` : ''}
    <div class="risk-actions">
      <button class="btn btn-secondary btn-sm highlight-btn">
        <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" width="14" height="14">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/>
        </svg>
        Highlight
      </button>
      <button class="btn btn-primary btn-sm generate-fix-btn">
        <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" width="14" height="14">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/>
        </svg>
        Generate Fix
      </button>
      <button class="btn btn-secondary btn-sm research-btn">
        <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" width="14" height="14">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"/>
        </svg>
        Research
      </button>
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

  // Bind button handlers
  const highlightBtn = card.querySelector('.highlight-btn');
  highlightBtn?.addEventListener('click', async () => {
    await highlightAIText(redline.original_text, redline.risk_level, redline.redline_type);
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
      const surroundingContext = await getSurroundingContext(redline.original_text);
      const currentPlaybookId = playbookSelect()?.value || undefined;

      const result = await api.generateFix({
        originalText: redline.original_text,
        recommendation: redline.recommendation,
        ruleName: redline.rule_name,
        redlineType: redline.redline_type || 'violation',
        surroundingContext,
        playbookId: currentPlaybookId,
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

      const fixText = document.createElement('div');
      fixText.className = 'generate-text';
      fixText.textContent = result.fix_text;
      wrapper.appendChild(fixText);

      const reasoning = document.createElement('div');
      reasoning.className = 'generate-reasoning';
      reasoning.textContent = result.reasoning;
      wrapper.appendChild(reasoning);

      const actions = document.createElement('div');
      actions.className = 'generate-actions';

      const applyBtn = document.createElement('button');
      applyBtn.className = 'btn btn-primary btn-sm';
      applyBtn.textContent = 'Apply to Document';
      applyBtn.addEventListener('click', async () => {
        applyBtn.disabled = true;
        applyBtn.textContent = 'Applying...';
        try {
          await applyAIRedline(redline, card, result.fix_text);
          generatePanel.style.display = 'none';
        } catch (err) {
          showToastOnCard(card, 'Apply failed: ' + ((err as Error).message || 'Unknown error'));
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
      const result = await api.researchClause(redline.original_text, redline.rule_name);

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

  return card;
}

/**
 * Highlight text found by AI using three-tier search.
 * Uses blue for missing clause anchors, red/yellow for violations.
 */
async function highlightAIText(searchText: string, riskLevel: 'RED' | 'YELLOW', redlineType?: string): Promise<void> {
  try {
    await Word.run(async (context) => {
      const result = await findTextInDocument(searchText, context);

      if (result.range) {
        let color: string;
        if (redlineType === 'missing') {
          color = '#93C5FD'; // Blue for missing clause insert points
        } else {
          color = riskLevel === 'RED' ? '#F87171' : '#FEF08A';
        }
        result.range.font.highlightColor = color;
        result.range.select();
        await context.sync();

        log.info(`Highlighted via ${result.method} match (confidence: ${result.confidence.toFixed(2)})`);
      } else {
        log.warn('Could not find text in document:', searchText.slice(0, 50) + '...');
      }
    });
  } catch (error) {
    log.error('Highlight error:', error);
  }
}

/**
 * Undo a previously applied redline fix.
 * For violations: finds the applied fix text and replaces it back with original_text.
 * For missing clauses: finds the inserted text and removes it.
 */
async function undoRedlineFix(redline: AIRedlineItem, appliedFix?: string): Promise<void> {
  await Word.run(async (context) => {
    // Search for the applied fix text (stored on card, or fall back to recommendation)
    const searchText = appliedFix || redline.recommendation;
    if (!searchText) return;

    const result = await findTextInDocument(searchText, context);
    if (!result.range) {
      throw new Error('Could not locate the applied fix in the document');
    }

    if (redline.redline_type === 'missing') {
      // Missing clause was inserted — delete it
      result.range.delete();
    } else {
      // Violation was replaced — put back the original text
      result.range.insertText(redline.original_text, Word.InsertLocation.replace);
    }
    await context.sync();
    log.info(`Undid fix for: ${redline.rule_name}`);
  });
}

/**
 * Highlight all AI redlines in the document.
 */
async function highlightAIRedlines(redlines: AIRedlineItem[]): Promise<void> {
  try {
    await Word.run(async (context) => {
      for (const redline of redlines) {
        const result = await findTextInDocument(redline.original_text, context);

        if (result.range) {
          let color: string;
          if (redline.redline_type === 'missing') {
            color = '#93C5FD'; // Blue for insertion points
          } else {
            color = redline.risk_level === 'RED' ? '#F87171' : '#FEF08A';
          }
          result.range.font.highlightColor = color;
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
 * Apply an AI-suggested fix using Track Changes.
 */
async function applyAIRedline(redline: AIRedlineItem, cardElement: HTMLElement, fixText?: string): Promise<void> {
  const textToApply = fixText || redline.recommendation;
  if (!textToApply) {
    return;
  }

  try {
    // Fetch OOXML BEFORE entering Word.run to avoid context timeout
    const redlineResponse = await api.generateRedlineZDR(
      currentAIAnalysis?.document_id || 'ai-doc',
      redline.id,
      redline.original_text,
      textToApply,
      undefined,
      redline.redline_type || 'violation'
    );

    await Word.run(async (context) => {
      const result = await findTextInDocument(redline.original_text, context);

      if (!result.range) {
        showToastOnCard(cardElement, 'Could not locate this clause — text may have been modified');
        return;
      }

      // Apply the Track Changes OOXML
      if (redline.redline_type === 'missing') {
        result.range.insertOoxml(redlineResponse.ooxml, Word.InsertLocation.after);
      } else {
        result.range.insertOoxml(redlineResponse.ooxml, Word.InsertLocation.replace);
      }
      await context.sync();

      // Mark as fixed and store the applied text for undo
      fixedRisks.add(redline.id);
      cardElement.classList.add('fixed');
      cardElement.dataset.appliedFix = textToApply;
    });
  } catch (error) {
    showToastOnCard(cardElement, 'Fix failed: ' + ((error as Error).message || 'Unknown error'));
  }
}


/**
 * Apply all unfixed redlines sequentially.
 * Respects the current filter — only applies visible redlines.
 */
async function applyAllRedlines(): Promise<void> {
  if (!currentAIAnalysis) return;

  const unfixed = getFilteredRedlines().filter(r => !fixedRisks.has(r.id));
  if (unfixed.length === 0) return;

  const applyBtn = document.getElementById('applyAllBtn') as HTMLButtonElement;
  const progressDiv = document.getElementById('applyProgress');
  const progressFill = document.getElementById('progressFill');
  const progressText = document.getElementById('progressText');

  if (applyBtn) applyBtn.disabled = true;
  if (progressDiv) progressDiv.style.display = 'block';

  // Check if we have generated fixes ready to apply
  const withGeneratedFix = unfixed.filter(r => document.getElementById(`risk-${r.id}`)?.dataset.generatedFix);

  if (withGeneratedFix.length > 0) {
    // Phase 2: Apply all generated fixes
    let applied = 0;
    let failed = 0;

    for (const redline of withGeneratedFix) {
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

    if (progressFill) progressFill.style.width = '100%';
    if (progressText) progressText.textContent = `Done: ${applied} applied${failed > 0 ? `, ${failed} failed` : ''}`;
  } else {
    // Phase 1: Generate all fixes first
    let generated = 0;
    let failed = 0;

    for (const redline of unfixed) {
      const pct = ((generated + failed) / unfixed.length) * 100;
      if (progressFill) progressFill.style.width = `${pct}%`;
      if (progressText) progressText.textContent = `Generating fix ${generated + failed + 1} / ${unfixed.length}`;

      const card = document.getElementById(`risk-${redline.id}`);
      if (!card) { failed++; continue; }

      try {
        const surroundingContext = await getSurroundingContext(redline.original_text);
        const currentPlaybookId = playbookSelect()?.value || undefined;

        const result = await api.generateFix({
          originalText: redline.original_text,
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
          const text = document.createElement('div');
          text.className = 'generate-text';
          text.textContent = result.fix_text;
          wrapper.appendChild(text);
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

  if (applyBtn) applyBtn.disabled = false;
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
    log.error('Export failed:', (error as Error).message);
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
