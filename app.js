import { getTransactions, getUploads, getGoals, getApiKey, setApiKey, addTransactions, addUpload, saveGoals } from './services/storageService.js';
import { parseFile, normalizeTransactions } from './services/fileParserService.js';
import { getCategoryIcon } from './services/categorizationService.js';
import { buildOverview, computeHealthScore, detectAnomalies, detectSubscriptions, predictGoals, buildForecast, buildReportSummary } from './services/analysisService.js';
import { askGroq } from './services/aiService.js';
import { renderCashflowChart, renderCategoryChart, renderSavingsChart } from './charts/chartService.js';
import { renderKpis, renderTopCategories, renderSpendingBreakdown, renderTransactions, renderBudget, renderUploadHistory, renderGoals, renderAnomalyCards, renderSubscriptionCards, renderForecastCards, updateHeader, updateAiStatus, appendChatMessage, clearAiInput, bindTabActions, bindFilterActions, bindGoalActions, alertUser } from './components/ui.js';
import { formatCurrency } from './utils/format.js';

const BUDGET_TARGETS = {
  Food: 12000,
  Travel: 10000,
  Shopping: 9000,
  Bills: 11000,
  Entertainment: 7000,
  Investments: 12000,
  Health: 7000,
  Miscellaneous: 6000,
};

const state = {
  transactions: [],
  uploads: [],
  goals: [],
  apiKey: '',
  selectedFilter: 'All',
};

const dom = {
  fileInput: document.getElementById('file-input'),
  dropZone: document.getElementById('drop-zone'),
  apiKeyInput: document.getElementById('api-key-input'),
  apiKeyStatus: document.getElementById('api-key-status'),
  exportReportBtn: document.getElementById('export-report-btn'),
  exportSummaryBtn: document.getElementById('export-summary-btn'),
  aiSendBtn: document.getElementById('ai-send-btn'),
  aiInput: document.getElementById('ai-input'),
  goalForm: document.getElementById('goal-form'),
};

async function init() {
  state.transactions = getTransactions();
  state.uploads = getUploads();
  state.goals = getGoals();
  state.apiKey = getApiKey();
  seedDemoData();
  bindEvents();
  updateApiStatus();
  refreshUi();
}

function seedDemoData() {
  if (state.transactions.length || state.uploads.length) return;
  const sampleTransactions = [
    { date: '2025-06-01', vendor: 'Salary Transfer', description: 'Salary credit', amount: 72000, sourceFile: 'seed' },
    { date: '2025-06-02', vendor: 'Metro Card', description: 'Commute recharge', amount: -450, sourceFile: 'seed' },
    { date: '2025-06-03', vendor: 'BSES Electricity', description: 'Electricity bill', amount: -2150, sourceFile: 'seed' },
    { date: '2025-06-04', vendor: 'Swiggy', description: 'Food order', amount: -620, sourceFile: 'seed' },
    { date: '2025-06-05', vendor: 'Netflix', description: 'Subscription', amount: -649, sourceFile: 'seed' },
    { date: '2025-06-06', vendor: 'Amazon', description: 'Shopping', amount: -3120, sourceFile: 'seed' },
    { date: '2025-06-07', vendor: 'Apollo Pharmacy', description: 'Health purchase', amount: -890, sourceFile: 'seed' },
    { date: '2025-06-08', vendor: 'Groww', description: 'Investment SIP', amount: -2400, sourceFile: 'seed' },
  ];
  state.transactions = addTransactions(sampleTransactions);
  state.uploads = addUpload({ fileName: 'demo-data', transactionCount: sampleTransactions.length, sourceType: 'seed' });
  state.goals = saveGoals([{ name: 'Emergency fund', target: 120000, current: 32000, months: 12 }]);
}

function bindEvents() {
  bindTabActions();
  bindFilterActions((category) => {
    state.selectedFilter = category;
    renderTransactions(state.transactions, category);
  });
  bindGoalActions(handleGoalComplete);

  dom.fileInput.addEventListener('change', async (event) => {
    const file = event.target.files[0];
    if (file) await handleUploadFile(file);
    dom.fileInput.value = '';
  });

  dom.dropZone.addEventListener('click', () => dom.fileInput.click());
  dom.dropZone.addEventListener('dragover', (event) => {
    event.preventDefault();
    dom.dropZone.classList.add('drop-active');
  });
  dom.dropZone.addEventListener('dragleave', () => dom.dropZone.classList.remove('drop-active'));
  dom.dropZone.addEventListener('drop', async (event) => {
    event.preventDefault();
    dom.dropZone.classList.remove('drop-active');
    const file = event.dataTransfer.files[0];
    if (file) await handleUploadFile(file);
  });

  document.getElementById('save-key-btn').addEventListener('click', handleSaveApiKey);
  dom.exportReportBtn.addEventListener('click', generateFinancialReportPdf);
  dom.exportSummaryBtn.addEventListener('click', exportAiMonthlySummary);
  dom.aiSendBtn.addEventListener('click', handleAiQuestion);
  dom.aiInput.addEventListener('keydown', (event) => {
    if (event.key === 'Enter') {
      event.preventDefault();
      handleAiQuestion();
    }
  });

  document.getElementById('goal-form').addEventListener('submit', (event) => {
    event.preventDefault();
    handleGoalCreate();
  });
}

function updateApiStatus() {
  const enabled = Boolean(state.apiKey);
  updateAiStatus(enabled);
  dom.apiKeyStatus.textContent = enabled ? 'Groq API key saved and ready' : 'No Groq API key saved yet';
  dom.apiKeyStatus.className = enabled ? 'status-label active' : 'status-label';
  dom.apiKeyInput.value = state.apiKey;
}

function refreshUi() {
  const analysis = buildOverview(state.transactions);
  const health = computeHealthScore(state.transactions);
  const anomalies = detectAnomalies(state.transactions);
  const subscriptions = detectSubscriptions(state.transactions);
  const goals = predictGoals(state.goals, state.transactions);
  const forecast = buildForecast(state.transactions, 12);

  renderKpis(analysis);
  updateHeader(health);
  renderTopCategories(analysis.topCategories);
  renderSpendingBreakdown(analysis.spendingBreakdown.map((item) => ({ ...item, icon: getCategoryIcon(item.category) })));
  renderTransactions(state.transactions, state.selectedFilter);
  renderBudget(analysis.spendingBreakdown.map((item) => ({ ...item, budget: BUDGET_TARGETS[item.category] || Math.max(8000, item.amount * 1.2) })));
  renderUploadHistory(state.uploads);
  renderGoals(goals);
  renderAnomalyCards(anomalies);
  renderSubscriptionCards(subscriptions);
  renderForecastCards(forecast);

  const cashflowCanvas = document.getElementById('cashflow-chart');
  const categoryCanvas = document.getElementById('category-chart');
  const savingsCanvas = document.getElementById('savings-chart');
  renderCashflowChart(cashflowCanvas, analysis.monthlyCashflow);
  renderCategoryChart(categoryCanvas, analysis.spendingBreakdown.map((item) => ({ ...item, color: '#7C6AF7' })));
  renderSavingsChart(savingsCanvas, analysis.savingsGrowth);
}

async function handleUploadFile(file) {
  try {
    dom.dropZone.classList.add('parsing');
    dom.dropZone.innerHTML = `<div class="upload-icon">⏳</div><div class="upload-text">Parsing ${file.name}...</div>`;
    const parsed = await parseFile(file);
    const transactions = normalizeTransactions(parsed);
    if (!transactions.length) {
      throw new Error('No transactions were detected in the uploaded file.');
    }

    state.transactions = addTransactions(transactions);
    state.uploads = addUpload({ fileName: file.name, transactionCount: transactions.length, sourceType: parsed.mimeType });
    refreshUi();
    alertUser(`Imported ${transactions.length} transactions from ${file.name}`, 'success');
  } catch (error) {
    console.error(error);
    alertUser(error.message || 'Upload failed. Please try a different statement.', 'error');
  } finally {
    dom.dropZone.classList.remove('parsing');
    dom.dropZone.innerHTML = `<div class="upload-icon">📄</div><div class="upload-text">Drop PDF / CSV / XLSX statement here</div><div class="upload-sub">Supports bank statements, credit card and UPI exports</div>`;
  }
}

function handleSaveApiKey() {
  const key = dom.apiKeyInput.value.trim();
  if (!key) {
    alertUser('Enter a valid Groq API key to enable AI.', 'error');
    return;
  }
  state.apiKey = key;
  setApiKey(key);
  updateApiStatus();
  alertUser('Groq API key saved successfully.', 'success');
}

async function handleAiQuestion() {
  const question = dom.aiInput.value.trim();
  if (!question) return;
  appendChatMessage(question, false);
  clearAiInput();
  appendChatMessage('Analyzing your data…', true);
  try {
    const response = await askGroq(question, { transactions: state.transactions, analysis: buildOverview(state.transactions), health: computeHealthScore(state.transactions), goals: state.goals }, state.apiKey);
    appendChatMessage(response, true);
  } catch (error) {
    appendChatMessage(`AI error: ${error.message}`, true);
    alertUser('Could not connect to Groq AI. Check your key and network.', 'error');
  }
}

async function generateFinancialReportPdf() {
  const report = buildReportSummary(state.transactions, buildOverview(state.transactions), computeHealthScore(state.transactions), predictGoals(state.goals, state.transactions), detectSubscriptions(state.transactions));
  const { jsPDF } = window.jspdf;
  const doc = new jsPDF({ unit: 'pt', format: 'a4' });
  const lines = [
    'FinMind AI — Financial Report',
    `Generated: ${new Date().toLocaleString()}`,
    '',
    report.summary,
    '',
    `Health score: ${report.health.score}/100`,
    ...report.health.explanations,
    '',
    'Top categories:',
    ...report.analysis.topCategories.map((item) => `${item.category}: ${formatCurrency(item.amount)}`),
    '',
    'Subscriptions:',
    ...report.subscriptions.map((sub) => `${sub.merchant}: ${formatCurrency(sub.monthlyAmount)} / mo`),
  ];
  doc.setFontSize(12);
  lines.forEach((line, index) => doc.text(line, 40, 60 + index * 18));
  doc.save(`finmind-report-${new Date().toISOString().slice(0, 10)}.pdf`);
}

async function exportAiMonthlySummary() {
  try {
    const question = 'Generate a concise monthly financial summary based on my uploaded transactions, current goals, and spending categories.';
    const summary = await askGroq(question, { transactions: state.transactions, analysis: buildOverview(state.transactions), health: computeHealthScore(state.transactions), goals: state.goals }, state.apiKey);
    const { jsPDF } = window.jspdf;
    const doc = new jsPDF({ unit: 'pt', format: 'a4' });
    const lines = ['FinMind AI — AI-generated Monthly Summary', `Generated: ${new Date().toLocaleString()}`, '', ...summary.split('\n')];
    doc.setFontSize(12);
    lines.forEach((line, index) => doc.text(line, 40, 60 + index * 18));
    doc.save(`finmind-ai-summary-${new Date().toISOString().slice(0, 10)}.pdf`);
    alertUser('AI summary exported successfully.', 'success');
  } catch (error) {
    alertUser('AI summary export failed. Please try again.', 'error');
  }
}

function handleGoalCreate() {
  const name = document.getElementById('goal-name').value.trim();
  const target = Number(document.getElementById('goal-target').value);
  const current = Number(document.getElementById('goal-current').value);
  const months = Number(document.getElementById('goal-months').value);
  if (!name || target <= 0) {
    alertUser('Please enter a valid goal name and target amount.', 'error');
    return;
  }
  const newGoal = { name, target, current: Math.max(0, current), months: Math.max(1, months) };
  state.goals = saveGoals([...state.goals, newGoal]);
  document.getElementById('goal-form').reset();
  refreshUi();
  alertUser('Savings goal created.', 'success');
}

function handleGoalComplete(index) {
  const goals = [...state.goals];
  goals.splice(index, 1);
  state.goals = saveGoals(goals);
  refreshUi();
  alertUser('Goal cleared from your plan.', 'success');
}

init();
