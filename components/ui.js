import { formatCurrency, formatPercent, createPopupMessage } from '../utils/format.js';

export function updateHeader(health) {
  document.getElementById('score-value').textContent = health.score;
  document.getElementById('score-label').textContent = health.score >= 80 ? 'Excellent' : health.score >= 60 ? 'Good' : 'Needs improvement';
  document.getElementById('health-details').innerHTML = health.explanations.map((line) => `<div>${line}</div>`).join('');
}

export function renderKpis(summary) {
  document.getElementById('kpi-income').textContent = formatCurrency(summary.income);
  document.getElementById('kpi-expense').textContent = formatCurrency(summary.expense);
  document.getElementById('kpi-savings').textContent = formatCurrency(summary.savings);
  document.getElementById('kpi-rate').textContent = formatPercent(summary.savingsRate);
}

export function renderTopCategories(categories) {
  const container = document.getElementById('top-categories');
  container.innerHTML = categories.length
    ? categories.map((cat) => `
      <div class="cat-item">
        <div class="cat-icon">${cat.icon}</div>
        <div class="cat-name">${cat.category}</div>
        <div class="cat-amt">${formatCurrency(cat.amount)}</div>
      </div>
    `).join('')
    : '<div class="empty-state">Upload your first statement to see top spending categories.</div>';
}

export function renderSpendingBreakdown(breakdown) {
  const container = document.getElementById('breakdown-list');
  if (!container) return;
  container.innerHTML = breakdown.length
    ? breakdown.map((item) => `
      <div class="cat-item">
        <div class="cat-icon">${item.icon}</div>
        <div class="cat-name">${item.category}</div>
        <div class="cat-amt">${formatCurrency(item.amount)}</div>
      </div>
    `).join('')
    : '<div class="empty-state">Waiting for transaction data.</div>';
}

export function renderTransactions(transactions, filter = 'All') {
  const filterContainer = document.getElementById('transaction-filters');
  const categories = ['All', 'Food', 'Travel', 'Shopping', 'Bills', 'Entertainment', 'Investments', 'Health', 'Miscellaneous', 'Income'];
  filterContainer.innerHTML = categories.map((category) => `
    <button class="filter-pill ${category === filter ? 'active' : ''}" data-category="${category}">${category}</button>
  `).join('');

  const list = document.getElementById('transaction-list');
  const filtered = filter === 'All' ? transactions : transactions.filter((tx) => tx.category === filter);

  if (!filtered.length) {
    list.innerHTML = '<div class="empty-state">No transactions match this filter.</div>';
    return;
  }

  list.innerHTML = filtered.map((tx) => `
    <div class="tx-item">
      <div class="tx-icon">${tx.merchant?.slice(0, 2).toUpperCase()}</div>
      <div class="tx-info">
        <div class="tx-name">${tx.description}</div>
        <div class="tx-date">${new Date(tx.date).toLocaleDateString()} · ${tx.category}</div>
      </div>
      <div class="tx-amt ${tx.amount >= 0 ? 'positive' : 'negative'}">${formatCurrency(tx.amount)}</div>
    </div>
  `).join('');
}

export function renderBudget(breakdown) {
  const container = document.getElementById('budget-list');
  if (!container) return;
  container.innerHTML = breakdown.map((item) => {
    const used = item.amount;
    const limit = item.budget || Math.max(item.amount * 1.2, 5000);
    const percent = Math.min(100, Math.round((used / limit) * 100));
    return `
      <div class="budget-card">
        <div class="budget-row">
          <div>${item.icon} ${item.category}</div>
          <div>${formatCurrency(used)} / ${formatCurrency(limit)}</div>
        </div>
        <div class="progress-bar"><div class="progress-fill" style="width:${percent}%"></div></div>
        <div class="budget-footer">${percent}% used</div>
      </div>
    `;
  }).join('');
}

export function renderUploadHistory(uploads) {
  const container = document.getElementById('upload-history');
  container.innerHTML = uploads.length
    ? uploads.map((upload) => `
      <div class="upload-card">
        <div>
          <div class="upload-title">${upload.fileName}</div>
          <div class="upload-meta">${new Date(upload.uploadedAt).toLocaleString()} · ${upload.transactionCount} tx</div>
        </div>
        <div class="upload-status">${upload.status}</div>
      </div>
    `).join('')
    : '<div class="empty-state">No statements uploaded yet.</div>';
}

export function renderGoals(goals) {
  const container = document.getElementById('goal-list');
  container.innerHTML = goals.length
    ? goals.map((goal, index) => `
      <div class="goal-card">
        <div class="goal-title">${goal.name}</div>
        <div>${formatCurrency(goal.current)} saved of ${formatCurrency(goal.target)}</div>
        <div class="goal-meta">Monthly target: ${formatCurrency(goal.recommendedMonthly)} · Complete by ${goal.predictedCompletion}</div>
        <button class="ghost-btn" data-goal-index="${index}">Mark complete</button>
      </div>
    `).join('')
    : '<div class="empty-state">Create your first savings goal.</div>';
}

export function renderAnomalyCards(anomalies) {
  const container = document.getElementById('anomaly-list');
  if (!container) return;
  container.innerHTML = anomalies.oddTransactions.length
    ? anomalies.oddTransactions.slice(0, 4).map((tx) => `
      <div class="anomaly-card">
        <div>${tx.merchant || tx.description}</div>
        <div>${formatCurrency(tx.amount)}</div>
      </div>
    `).join('')
    : '<div class="empty-state">No unusual transactions detected.</div>';
}

export function renderSubscriptionCards(subscriptions) {
  const container = document.getElementById('subscription-list');
  if (!container) return;
  container.innerHTML = subscriptions.length
    ? subscriptions.map((sub) => `
      <div class="sub-card">
        <div class="sub-name">${sub.merchant}</div>
        <div>${formatCurrency(sub.monthlyAmount)} / mo · est. ${formatCurrency(sub.annualEstimate)} / yr</div>
      </div>
    `).join('')
    : '<div class="empty-state">No recurring subscriptions found yet.</div>';
}

export function renderForecastCards(forecast) {
  const container = document.getElementById('forecast-list');
  container.innerHTML = forecast.slice(0, 6).map((item) => `
    <div class="forecast-row">
      <div>${item.month}</div>
      <div>${formatCurrency(item.expense)}</div>
      <div>${formatCurrency(item.savings)}</div>
    </div>
  `).join('');
}

export function updateAiStatus(enabled) {
  const badge = document.getElementById('ai-status');
  badge.textContent = enabled ? '● Live AI' : '● Demo AI';
  badge.classList.toggle('live', enabled);
}

export function appendChatMessage(message, fromBot = true) {
  const container = document.getElementById('ai-chat');
  const className = fromBot ? 'ai-msg bot' : 'ai-msg user';
  container.innerHTML += `<div class="${className}">${message}</div>`;
  container.scrollTop = container.scrollHeight;
}

export function clearAiInput() {
  document.getElementById('ai-input').value = '';
}

export function bindTabActions() {
  document.querySelectorAll('[data-tab]').forEach((button) => {
    button.addEventListener('click', () => {
      document.querySelectorAll('[data-pane]').forEach((pane) => pane.classList.remove('active'));
      document.querySelectorAll('[data-tab]').forEach((tab) => tab.classList.remove('active'));
      const target = button.dataset.tab;
      button.classList.add('active');
      document.querySelector(`[data-pane="${target}"]`).classList.add('active');
    });
  });
}

export function bindFilterActions(onFilterChange) {
  document.getElementById('transaction-filters').addEventListener('click', (event) => {
    const category = event.target.dataset.category;
    if (category) {
      onFilterChange(category);
    }
  });
}

export function bindGoalActions(onComplete) {
  document.getElementById('goal-list').addEventListener('click', (event) => {
    const index = event.target.dataset.goalIndex;
    if (index != null && typeof onComplete === 'function') {
      onComplete(Number(index));
    }
  });
}

export function alertUser(message, type = 'info') {
  createPopupMessage(message, type);
}
