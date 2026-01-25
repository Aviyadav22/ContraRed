/**
 * ContraRed - Word Add-in Main Logic
 * 
 * Implements: Login, Document Scan, Risk Highlighting, Redline Application
 * Now with AI-First analysis using Gemini for holistic contract review.
 */

import { api, RiskItem, AnalysisResult, AIRedlineItem, AIAnalysisResult } from './api';
import Fuse from 'fuse.js';

// ============================================================================
// State
// ============================================================================

let currentAnalysis: AnalysisResult | null = null;
let currentAIAnalysis: AIAnalysisResult | null = null;  // AI-first analysis result
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
  }

  // Load available playbooks
  loadPlaybooks();
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
    console.warn('Could not load playbooks:', error);
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
  currentAnalysis = null;
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
    console.log('Starting AI analysis with playbook:', selectedPlaybookId || 'Default');
    console.log('Document text length:', documentText.length);

    const aiResult = await api.analyzeWithAI(documentText, 'document.docx', selectedPlaybookId);
    console.log('AI analysis complete:', aiResult);
    console.log('Executive summary:', aiResult.executive_summary);
    console.log('Redlines count:', aiResult.redlines?.length);

    currentAIAnalysis = aiResult;
    fixedRisks.clear();

    // Step 3: Display AI results (executive summary + redlines)
    console.log('Calling displayAIResults...');
    displayAIResults(aiResult);

    // Step 4: Highlight risks in document using three-tier search
    console.log('Calling highlightAIRedlines...');
    await highlightAIRedlines(aiResult.redlines);
    console.log('Scan complete!');

  } catch (error) {
    console.error('AI Scan failed:', error);
    alert(`AI Scan failed: ${(error as Error).message}`);
  } finally {
    setScanLoading(false);
  }
}

/**
 * Display AI analysis results in the UI.
 */
function displayAIResults(result: AIAnalysisResult): void {
  console.log('=== displayAIResults START ===');
  console.log('Result object:', JSON.stringify(result, null, 2));

  // Show results section (uses inline style, not class)
  const results = document.getElementById('resultsSection') as HTMLElement | null;
  console.log('resultsSection element:', results);

  if (results) {
    results.style.display = 'block';
    console.log('✓ Results section style set to block');
  } else {
    console.error('✗ resultsSection element not found in DOM!');
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

    // Display executive summary points
    if (keyConcernsDiv && result.executive_summary.length > 0) {
      keyConcernsDiv.innerHTML = result.executive_summary
        .map(point => `<div class="concern-item">• ${point}</div>`)
        .join('');
    }

    if (recommendationDiv) {
      recommendationDiv.textContent = `${result.total_risks} clauses require attention.`;
    }
  }

  // Display redlines as risk cards
  const list = riskList();
  if (!list) return;
  list.innerHTML = '';

  if (result.redlines.length === 0) {
    const empty = emptyState();
    if (empty) empty.style.display = 'block';
    console.log('No redlines - showing empty state');
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
function createAIRedlineCard(redline: AIRedlineItem, documentId: string): HTMLElement {
  const card = document.createElement('div');
  card.className = 'risk-card';
  card.id = `risk-${redline.id}`;

  const levelClass = redline.risk_level.toLowerCase();
  const truncatedClause = redline.original_text.length > 100
    ? redline.original_text.slice(0, 100) + '...'
    : redline.original_text;

  card.innerHTML = `
    <div class="risk-card-header">
      <div class="risk-indicator ${levelClass}"></div>
      <div class="risk-title">${redline.rule_name}</div>
    </div>
    <div class="risk-clause">"${truncatedClause}"</div>
    <div class="risk-explanation">${redline.explanation}</div>
    ${redline.suggested_fix ? `
      <div class="suggested-fix">
        <strong>Suggested Fix:</strong> ${redline.suggested_fix.slice(0, 150)}${redline.suggested_fix.length > 150 ? '...' : ''}
      </div>
    ` : ''}
    <div class="risk-actions">
      <button class="btn btn-secondary btn-sm highlight-btn" data-text="${encodeURIComponent(redline.original_text)}">
        <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" width="14" height="14">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/>
        </svg>
        Highlight
      </button>
      ${redline.suggested_fix ? `
        <button class="btn btn-primary btn-sm fix-btn" data-docid="${documentId}" data-redlineid="${redline.id}">
          <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" width="14" height="14">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>
          </svg>
          Fix
        </button>
      ` : ''}
    </div>
    <div class="fixed-badge">✓ Fixed</div>
  `;

  // Bind button handlers
  const highlightBtn = card.querySelector('.highlight-btn');
  const fixBtn = card.querySelector('.fix-btn');

  highlightBtn?.addEventListener('click', async () => {
    const text = decodeURIComponent((highlightBtn as HTMLElement).dataset.text || '');
    await highlightAIText(text, redline.risk_level);
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

        console.log(`Highlighted using ${result.method} match (confidence: ${result.confidence.toFixed(2)})`);
      } else {
        console.warn('Could not find text in document:', searchText.slice(0, 50) + '...');
        alert('Could not locate this clause in the document. The text may have been modified.');
      }
    });
  } catch (error) {
    console.error('Highlight error:', error);
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
      console.log(`Highlighted ${redlines.length} AI redlines`);
    });
  } catch (error) {
    console.error('Bulk highlight error:', error);
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

      console.log('Applied AI fix for:', redline.rule_name);
    });
  } catch (error) {
    console.error('Apply redline error:', error);
    alert(`Failed to apply fix: ${(error as Error).message}`);
  }
}

async function fetchAndDisplaySummary(documentId: string, contractText: string, playbookId?: string): Promise<void> {
  const summarySection = document.getElementById('aiSummarySection');
  const riskLevelBadge = document.getElementById('riskLevelBadge');
  const keyConcernsDiv = document.getElementById('keyConcerns');
  const recommendationDiv = document.getElementById('recommendation');

  if (!summarySection) return;

  try {
    // Show section with loading state
    summarySection.style.display = 'block';
    if (riskLevelBadge) riskLevelBadge.textContent = 'Analyzing...';
    if (keyConcernsDiv) keyConcernsDiv.innerHTML = '<div style="color: var(--text-muted);">Generating AI summary...</div>';
    if (recommendationDiv) recommendationDiv.textContent = '';

    // Fetch AI summary
    const summary = await api.getSummary(documentId, contractText, playbookId);

    // Update risk level badge with appropriate color
    if (riskLevelBadge) {
      riskLevelBadge.textContent = summary.risk_level;
      const levelColors: Record<string, string> = {
        'Critical': 'var(--danger)',
        'High': 'var(--warning)',
        'Medium': 'var(--warning)',
        'Low': 'var(--success)'
      };
      riskLevelBadge.style.color = levelColors[summary.risk_level] || 'var(--text-muted)';
    }

    // Display key concerns as bullet points
    if (keyConcernsDiv && summary.key_concerns.length > 0) {
      keyConcernsDiv.innerHTML = summary.key_concerns
        .map(c => `<div style="font-size: 12px; color: var(--text-primary); margin-bottom: 4px;">• ${c}</div>`)
        .join('');
    }

    // Display recommendation
    if (recommendationDiv && summary.recommendation) {
      recommendationDiv.textContent = `💡 ${summary.recommendation}`;
    }

  } catch (error) {
    console.error('Summary fetch failed:', error);
    if (keyConcernsDiv) {
      keyConcernsDiv.innerHTML = '<div style="color: var(--warning);">Could not generate AI summary</div>';
    }
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
// Results Display
// ============================================================================

function displayResults(result: AnalysisResult): void {
  // Show results section
  if (resultsSection()) resultsSection()!.style.display = 'block';

  // Update summary counts
  if (redCount()) redCount()!.textContent = String(result.risk_summary.red);
  if (yellowCount()) yellowCount()!.textContent = String(result.risk_summary.yellow);
  if (greenCount()) greenCount()!.textContent = String(result.risk_summary.green);
  if (riskCount()) riskCount()!.textContent = `${result.total_risks} items`;

  // Render risk cards
  const list = riskList();
  const empty = emptyState();

  if (!list) return;
  list.innerHTML = '';

  if (result.risks.length === 0) {
    if (empty) empty.style.display = 'block';
    return;
  }

  if (empty) empty.style.display = 'none';

  // Sort: RED first, then YELLOW, then GREEN
  const sortedRisks = [...result.risks].sort((a, b) => {
    const order = { RED: 0, YELLOW: 1, GREEN: 2 };
    return order[a.risk_level] - order[b.risk_level];
  });

  sortedRisks.forEach((risk) => {
    const card = createRiskCard(risk, result.document_id);
    list.appendChild(card);
  });
}

function createRiskCard(risk: RiskItem, documentId: string): HTMLElement {
  const card = document.createElement('div');
  card.className = 'risk-card';
  card.id = `risk-${risk.id}`;

  const levelClass = risk.risk_level.toLowerCase();
  const truncatedClause = risk.clause_text.length > 100
    ? risk.clause_text.slice(0, 100) + '...'
    : risk.clause_text;

  card.innerHTML = `
        <div class="risk-card-header">
            <div class="risk-indicator ${levelClass}"></div>
            <div class="risk-title">${risk.rule_name}</div>
            ${risk.is_deal_breaker ? '<span class="risk-deal-breaker">DEAL BREAKER</span>' : ''}
        </div>
        <div class="risk-clause">"${truncatedClause}"</div>
        ${risk.ai_explanation ? `<div class="risk-explanation">${risk.ai_explanation}</div>` : ''}
        <div class="risk-actions">
            <button class="btn btn-secondary btn-sm highlight-btn" data-clause="${encodeURIComponent(risk.clause_text)}">
                <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" width="14" height="14">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/>
                </svg>
                Highlight
            </button>
            ${risk.risk_level !== 'GREEN' && risk.suggested_fix ? `
                <button class="btn btn-primary btn-sm fix-btn" data-docid="${documentId}" data-riskid="${risk.id}">
                    <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" width="14" height="14">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>
                    </svg>
                    Fix
                </button>
            ` : ''}
        </div>
        <div class="fixed-badge">✓ Fixed</div>
    `;

  // Bind button handlers
  const highlightBtn = card.querySelector('.highlight-btn');
  const fixBtn = card.querySelector('.fix-btn');

  highlightBtn?.addEventListener('click', () => {
    const clause = decodeURIComponent((highlightBtn as HTMLElement).dataset.clause || '');
    highlightRisk(clause, risk.risk_level);
  });

  fixBtn?.addEventListener('click', async () => {
    const docId = (fixBtn as HTMLElement).dataset.docid!;
    const riskId = (fixBtn as HTMLElement).dataset.riskid!;
    await applyRedline(docId, riskId, risk, card);
  });

  return card;
}

// ============================================================================
// Risk Highlighting
// ============================================================================

async function highlightRisk(clauseText: string, riskLevel: string): Promise<void> {
  // Validate search string - Word API has a 255 character limit
  if (!clauseText || clauseText.trim().length === 0) {
    alert('No text to highlight.');
    return;
  }

  // Truncate if too long (Word API limit is 255 chars)
  let searchText = clauseText.trim();
  if (searchText.length > 250) {
    // Use first 250 chars to leave buffer for edge cases
    searchText = searchText.substring(0, 250);
  }

  // Remove special characters that can break search
  searchText = searchText.replace(/[\r\n\t]+/g, ' ').trim();

  if (searchText.length < 3) {
    alert('Search text too short to highlight reliably.');
    return;
  }

  const colorMap: Record<string, string> = {
    RED: 'Red',
    YELLOW: 'Yellow',
    GREEN: 'BrightGreen'
  };
  const highlightColor = colorMap[riskLevel] || 'Yellow';

  try {
    await Word.run(async (context) => {
      // Search for ALL occurrences (handles duplicate text)
      const searchResults = context.document.body.search(searchText, {
        matchCase: false,
        matchWholeWord: false
      });
      searchResults.load('font');
      await context.sync();

      if (searchResults.items.length === 0) {
        alert('Could not find this text in the document. It may have been modified.');
        return;
      }

      // Highlight ALL matches
      searchResults.items.forEach((item) => {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        item.font.highlightColor = highlightColor as any;
      });

      // Scroll to the first match
      searchResults.items[0].select();

      await context.sync();
    });
  } catch (error) {
    console.error('Highlight error:', error);
    const errMsg = (error as Error).message || String(error);
    if (errMsg.includes('SearchStringInvalidOrTooLong')) {
      alert('Text is too long or contains special characters that cannot be searched.');
    } else {
      alert(`Highlight failed: ${errMsg}`);
    }
  }
}

// ============================================================================
// Redline Application
// ============================================================================

async function applyRedline(
  documentId: string,
  riskId: string,
  risk: RiskItem,
  cardElement: HTMLElement
): Promise<void> {
  // Prevent double-clicks
  if (fixedRisks.has(riskId)) return;

  const fixBtn = cardElement.querySelector('.fix-btn') as HTMLButtonElement;
  if (fixBtn) fixBtn.disabled = true;

  // Validate and sanitize search text (same as highlightRisk)
  let searchText = (risk.clause_text || '').trim();
  if (searchText.length > 250) {
    searchText = searchText.substring(0, 250);
  }
  searchText = searchText.replace(/[\r\n\t]+/g, ' ').trim();

  if (searchText.length < 3) {
    alert('Text too short to find in document.');
    if (fixBtn) fixBtn.disabled = false;
    return;
  }

  try {
    // Use ZDR mode redline generation with paragraph_hash for better matching
    const redline = await api.generateRedlineZDR(
      documentId,
      riskId,
      risk.clause_text,
      risk.suggested_fix || risk.clause_text,
      risk.paragraph_hash
    );

    // Log match confidence for debugging
    if (redline.match_confidence && redline.match_confidence < 1.0) {
      console.log(`Redline matched with ${(redline.match_confidence * 100).toFixed(0)}% confidence (${redline.match_method})`);
    }

    // Apply in Word
    await Word.run(async (context) => {
      // Find the clause
      const searchResults = context.document.body.search(searchText, {
        matchCase: false
      });
      searchResults.load('items');
      await context.sync();

      if (searchResults.items.length === 0) {
        throw new Error('Could not find this text in the document');
      }

      // Replace the FIRST match with the redline OOXML
      const range = searchResults.items[0];
      range.insertOoxml(redline.ooxml, Word.InsertLocation.replace);
      await context.sync();
    });

    // Mark as fixed in UI
    fixedRisks.add(riskId);
    cardElement.classList.add('fixed');

  } catch (error) {
    console.error('Redline failed:', error);
    const errMsg = (error as Error).message || String(error);
    if (errMsg.includes('SearchStringInvalidOrTooLong')) {
      alert('Text is too long or contains special characters that cannot be fixed automatically.');
    } else {
      alert(`Failed to apply fix: ${errMsg}`);
    }
    if (fixBtn) fixBtn.disabled = false;
  }
}

// ============================================================================
// Exports (for testing)
// ============================================================================

export { scanDocument, highlightRisk, applyRedline };
