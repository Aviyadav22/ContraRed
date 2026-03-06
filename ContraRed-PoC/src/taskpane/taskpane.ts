/**
 * ContraRed - Word Add-in Main Logic
 * 
 * Implements: Login, Document Scan, Risk Highlighting, Redline Application
 * Now with AI-First analysis using Gemini for holistic contract review.
 */

import { api, AIRedlineItem, AIAnalysisResult } from './api';
import Fuse from 'fuse.js';

// ============================================================================
// State
// ============================================================================

let currentAIAnalysis: AIAnalysisResult | null = null;
const fixedRisks: Set<string> = new Set();

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

    // Allow Enter key to submit login
    passwordInput()?.addEventListener('keypress', (e) => {
      if (e.key === 'Enter') handleLogin();
    });

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
}

// Admin feature handlers
function bindAdminActions(): void {
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
    console.warn('[ContraRed] Could not load playbooks:', error);
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

  // Tier 1: Exact search
  const exactResults = body.search(searchText, { matchCase: false, matchWholeWord: false });
  exactResults.load('items');
  await context.sync();

  if (exactResults.items.length > 0) {
    return { range: exactResults.items[0], method: 'exact', confidence: 1.0 };
  }

  // Tier 2: Normalized search (try first 50 chars, stripped of punctuation)
  const normalizedSearch = searchText.replace(/[^\w\s]/g, '').trim().slice(0, 50);
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
  setScanLoading(true);

  try {
    // Step 1: Get document text from Word
    const documentText = await getDocumentText();

    if (!documentText || documentText.trim().length < 50) {
      alert('Document appears to be empty or too short. Please add some contract text.');
      return;
    }

    // Step 2: Call AI-First analysis API (with selected playbook)
    const selectedPlaybookId = playbookSelect()?.value || undefined;
    console.log('[ContraRed] Starting analysis...');

    const aiResult = await api.analyzeWithAI(documentText, 'document.docx', selectedPlaybookId);

    currentAIAnalysis = aiResult;
    fixedRisks.clear();

    // Step 3: Display AI results (executive summary + redlines)
    displayAIResults(aiResult);

    // Step 4: Highlight risks in document using three-tier search
    await highlightAIRedlines(aiResult.redlines);
    console.log('[ContraRed] Analysis complete:', { risks: aiResult.redlines?.length, tokens: aiResult.tokens_used });

  } catch (error) {
    console.error('[ContraRed] Scan failed:', error);
    alert(`AI Scan failed: ${(error as Error).message}`);
  } finally {
    setScanLoading(false);
  }
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
    console.error('[ContraRed] resultsSection element not found in DOM');
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

  // Display redlines as risk cards — clean up old event listeners by replacing container
  let list = riskList();
  if (!list) return;
  const parent = list.parentNode;
  if (parent) {
    const newList = list.cloneNode(false) as HTMLElement;
    parent.replaceChild(newList, list);
    list = newList;
  }
  list.innerHTML = '';

  if (result.redlines.length === 0) {
    const empty = emptyState();
    if (empty) empty.style.display = 'block';
    return;
  }

  const empty = emptyState();
  if (empty) empty.style.display = 'none';

  // Sort by risk level (RED first)
  const sortedRedlines = [...result.redlines].sort((a, b) => {
    const order = { RED: 0, YELLOW: 1 };
    return (order[a.risk_level] || 2) - (order[b.risk_level] || 2);
  });

  sortedRedlines.forEach((redline) => {
    const card = createAIRedlineCard(redline, result.document_id);
    list.appendChild(card);
  });
}

/**
 * Create a risk card for an AI redline item.
 */
function createAIRedlineCard(redline: AIRedlineItem, _documentId: string): HTMLElement {
  const card = document.createElement('div');
  card.className = 'risk-card';
  card.id = `risk-${redline.id}`;

  const levelClass = redline.risk_level.toLowerCase();
  const truncatedClause = redline.original_text.length > 100
    ? redline.original_text.slice(0, 100) + '...'
    : redline.original_text;
  const truncatedFix = redline.suggested_fix
    ? (redline.suggested_fix.length > 150 ? redline.suggested_fix.slice(0, 150) + '...' : redline.suggested_fix)
    : '';

  // Use innerHTML for static structure only; dynamic text set via textContent below
  card.innerHTML = `
    <div class="risk-card-header">
      <div class="risk-indicator ${levelClass}"></div>
      <div class="risk-title"></div>
    </div>
    <div class="risk-clause"></div>
    <div class="risk-explanation"></div>
    ${redline.suggested_fix ? `
      <div class="suggested-fix">
        <strong>Suggested Fix:</strong> <span class="suggested-fix-text"></span>
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
      ${redline.suggested_fix ? `
        <button class="btn btn-primary btn-sm fix-btn">
          <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" width="14" height="14">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>
          </svg>
          Fix
        </button>
      ` : ''}
    </div>
    <div class="fixed-badge">\u2713 Fixed</div>
  `;

  // Set dynamic text content safely to prevent XSS
  const ruleNameEl = card.querySelector('.risk-title');
  if (ruleNameEl) ruleNameEl.textContent = redline.rule_name;
  const clauseEl = card.querySelector('.risk-clause');
  if (clauseEl) clauseEl.textContent = '"' + truncatedClause + '"';
  const explanationEl = card.querySelector('.risk-explanation');
  if (explanationEl) explanationEl.textContent = redline.explanation;
  const suggestedFixEl = card.querySelector('.suggested-fix-text');
  if (suggestedFixEl) suggestedFixEl.textContent = truncatedFix;

  // Bind button handlers
  const highlightBtn = card.querySelector('.highlight-btn');
  const fixBtn = card.querySelector('.fix-btn');

  highlightBtn?.addEventListener('click', async () => {
    await highlightAIText(redline.original_text, redline.risk_level);
  });

  fixBtn?.addEventListener('click', async () => {
    await applyAIRedline(redline, card);
  });

  return card;
}

/**
 * Highlight text found by AI using three-tier search.
 */
async function highlightAIText(searchText: string, riskLevel: 'RED' | 'YELLOW'): Promise<void> {
  try {
    await Word.run(async (context) => {
      const result = await findTextInDocument(searchText, context);

      if (result.range) {
        // Use a visible red for critical risks, light yellow for warnings
        const color = riskLevel === 'RED' ? '#F87171' : '#FEF08A';
        result.range.font.highlightColor = color;
        result.range.select();
        await context.sync();

        console.log(`[ContraRed] Highlighted via ${result.method} match (confidence: ${result.confidence.toFixed(2)})`);
      } else {
        console.warn('[ContraRed] Could not find text in document:', searchText.slice(0, 50) + '...');
        alert('Could not locate this clause in the document. The text may have been modified.');
      }
    });
  } catch (error) {
    console.error('[ContraRed] Highlight error:', error);
  }
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
          // Use a visible red for critical risks, light yellow for warnings
          const color = redline.risk_level === 'RED' ? '#F87171' : '#FEF08A';
          result.range.font.highlightColor = color;
        }
      }
      await context.sync();
      console.log(`[ContraRed] Highlighted ${redlines.length} redlines in document`);
    });
  } catch (error) {
    console.error('[ContraRed] Bulk highlight error:', error);
  }
}

/**
 * Apply an AI-suggested fix using Track Changes.
 */
async function applyAIRedline(redline: AIRedlineItem, cardElement: HTMLElement): Promise<void> {
  if (!redline.suggested_fix) {
    alert('No suggested fix available for this clause.');
    return;
  }

  try {
    await Word.run(async (context) => {
      const result = await findTextInDocument(redline.original_text, context);

      if (!result.range) {
        alert('Could not locate this clause in the document.');
        return;
      }

      // Generate redline OOXML via backend
      const redlineResponse = await api.generateRedlineZDR(
        currentAIAnalysis?.document_id || 'ai-doc',
        redline.id,
        redline.original_text,
        redline.suggested_fix
      );

      // Apply the Track Changes OOXML
      result.range.insertOoxml(redlineResponse.ooxml, Word.InsertLocation.replace);
      await context.sync();

      // Mark as fixed
      fixedRisks.add(redline.id);
      cardElement.classList.add('fixed');

      console.log('[ContraRed] Applied fix for:', redline.rule_name);
    });
  } catch (error) {
    console.error('[ContraRed] Apply redline error:', error);
    alert(`Failed to apply fix: ${(error as Error).message}`);
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

// Reasoning loader state
let reasoningInterval: ReturnType<typeof setInterval> | null = null;
let reasoningStartTime = 0;

function setScanLoading(loading: boolean): void {
  const btn = scanBtn() as HTMLButtonElement | null;
  const btnText = scanBtnText();
  const spinner = scanSpinner();

  if (btn) btn.disabled = loading;
  if (btnText) btnText.style.display = loading ? 'none' : 'inline';
  if (spinner) spinner.style.display = loading ? 'block' : 'none';

  if (loading) {
    startReasoningLoader();
  } else {
    stopReasoningLoader();
  }
}

function startReasoningLoader(): void {
  const loader = document.getElementById('reasoningLoader');
  if (!loader) return;

  // Show loader
  loader.classList.add('active');

  // Reset all steps
  const steps = loader.querySelectorAll('.reasoning-step');
  steps.forEach(step => {
    step.classList.remove('active', 'complete');
    const indicator = step.querySelector('.step-indicator');
    if (indicator) {
      indicator.classList.remove('active', 'complete');
      indicator.classList.add('pending');
      indicator.textContent = '';
    }
    const time = step.querySelector('.step-time');
    if (time) time.textContent = '';
  });

  reasoningStartTime = Date.now();
  let currentStep = 0;

  // Immediately show first step
  activateStep(0);

  // Progress through steps
  const stepTimes = [0, 4000, 8000, 15000, 22000, 30000]; // When each step starts

  reasoningInterval = setInterval(() => {
    const elapsed = Date.now() - reasoningStartTime;

    // Check if we should advance to a new step
    for (let i = currentStep + 1; i < stepTimes.length; i++) {
      if (elapsed >= stepTimes[i]) {
        completeStep(currentStep);
        activateStep(i);
        currentStep = i;
      }
    }

    // Update time on current active step
    const activeStep = loader.querySelector(`.reasoning-step[data-step="${currentStep}"]`);
    if (activeStep) {
      const timeEl = activeStep.querySelector('.step-time');
      if (timeEl) timeEl.textContent = `${Math.floor(elapsed / 1000)}s`;
    }
  }, 500);
}

function activateStep(stepIndex: number): void {
  const loader = document.getElementById('reasoningLoader');
  if (!loader) return;

  const step = loader.querySelector(`.reasoning-step[data-step="${stepIndex}"]`);
  if (step) {
    step.classList.add('active');
    step.classList.remove('complete');
    const indicator = step.querySelector('.step-indicator');
    if (indicator) {
      indicator.classList.remove('pending', 'complete');
      indicator.classList.add('active');
    }
  }
}

function completeStep(stepIndex: number): void {
  const loader = document.getElementById('reasoningLoader');
  if (!loader) return;

  const step = loader.querySelector(`.reasoning-step[data-step="${stepIndex}"]`);
  if (step) {
    step.classList.remove('active');
    step.classList.add('complete');
    const indicator = step.querySelector('.step-indicator');
    if (indicator) {
      indicator.classList.remove('pending', 'active');
      indicator.classList.add('complete');
      indicator.textContent = '✓';
    }
  }
}

function stopReasoningLoader(): void {
  if (reasoningInterval) {
    clearInterval(reasoningInterval);
    reasoningInterval = null;
  }

  const loader = document.getElementById('reasoningLoader');
  if (loader) {
    // Mark all steps as complete
    const steps = loader.querySelectorAll('.reasoning-step');
    steps.forEach((step, i) => {
      step.classList.add('active', 'complete');
      const indicator = step.querySelector('.step-indicator');
      if (indicator) {
        indicator.classList.remove('pending', 'active');
        indicator.classList.add('complete');
        indicator.textContent = '✓';
      }
    });

    // Hide loader after a brief delay
    setTimeout(() => {
      loader.classList.remove('active');
    }, 800);
  }
}

// ============================================================================
// Exports (for testing)
// ============================================================================

export { scanDocument, highlightAIText, applyAIRedline };
