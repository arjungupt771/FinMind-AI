export function buildOverview(transactions) {
  const totals = transactions.reduce(
    (acc, tx) => {
      if (tx.amount >= 0) acc.income += tx.amount;
      else acc.expense += Math.abs(tx.amount);
      if (tx.category === 'Investments') acc.investments += Math.abs(tx.amount);
      return acc;
    },
    { income: 0, expense: 0, investments: 0 }
  );

  const savings = totals.income - totals.expense;
  const savingsRate = totals.income ? (savings / totals.income) * 100 : 0;
  const expenseRatio = totals.income ? (totals.expense / totals.income) * 100 : 0;
  const investmentRatio = totals.income ? (totals.investments / totals.income) * 100 : 0;

  return {
    income: totals.income,
    expense: totals.expense,
    savings,
    savingsRate,
    expenseRatio,
    investmentRatio,
    balance: savings,
    monthlyCashflow: buildMonthlyCashflow(transactions),
    spendingBreakdown: buildSpendingBreakdown(transactions),
  };
}

function monthKey(dateString) {
  const date = new Date(dateString);
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`;
}

function formatMonthLabel(key) {
  const [year, month] = key.split('-').map(Number);
  return new Date(year, month - 1).toLocaleString('default', { month: 'short', year: 'numeric' });
}

function groupByMonth(transactions) {
  return transactions.reduce((groups, tx) => {
    const key = monthKey(tx.date);
    if (!groups[key]) groups[key] = { income: 0, expense: 0, savings: 0, month: formatMonthLabel(key) };
    if (tx.amount >= 0) groups[key].income += tx.amount;
    else groups[key].expense += Math.abs(tx.amount);
    groups[key].savings = groups[key].income - groups[key].expense;
    return groups;
  }, {});
}

function buildMonthlyCashflow(transactions) {
  return Object.values(groupByMonth(transactions)).sort((a, b) => new Date(a.month) - new Date(b.month));
}

function buildSpendingBreakdown(transactions) {
  const categories = {};
  transactions.forEach((tx) => {
    if (tx.amount < 0) {
      categories[tx.category] = (categories[tx.category] || 0) + Math.abs(tx.amount);
    }
  });
  return Object.entries(categories)
    .map(([category, amount]) => ({ category, amount }))
    .sort((a, b) => b.amount - a.amount);
}

export function computeHealthScore(transactions) {
  const income = transactions.filter((tx) => tx.amount >= 0).reduce((sum, tx) => sum + tx.amount, 0);
  const expense = transactions.filter((tx) => tx.amount < 0).reduce((sum, tx) => sum + Math.abs(tx.amount), 0);
  const investments = transactions.filter((tx) => tx.category === 'Investments').reduce((sum, tx) => sum + Math.abs(tx.amount), 0);
  const debt = transactions.filter((tx) => tx.description?.toLowerCase().includes('loan') || tx.category === 'Bills').reduce((sum, tx) => sum + Math.abs(tx.amount), 0);
  const avgMonthlyExpense = expense / Math.max(1, Object.keys(groupByMonth(transactions)).length);
  const emergencyCoverage = avgMonthlyExpense > 0 ? Math.min(12, Math.max(0, (income - expense) / avgMonthlyExpense)) : 0;

  const savingsRate = income ? ((income - expense) / income) * 100 : 0;
  const expenseRatio = income ? (expense / income) * 100 : 0;
  const investmentRatio = income ? (investments / income) * 100 : 0;
  const debtRatio = income ? (debt / income) * 100 : 0;

  const score = Math.round(
    Math.min(
      100,
      Math.max(0, savingsRate * 0.3 + (100 - expenseRatio) * 0.25 + emergencyCoverage * 4 + investmentRatio * 1.5 + (20 - debtRatio) * 1.5)
    )
  );

  const recommendations = [];
  if (savingsRate < 20) recommendations.push('Aim to save at least 20% of income each month.');
  if (expenseRatio > 70) recommendations.push('Reduce discretionary spending to improve your expense ratio.');
  if (emergencyCoverage < 3) recommendations.push('Increase emergency savings to cover 3–6 months of expenses.');
  if (investmentRatio < 10) recommendations.push('Consider allocating more to investments for long-term growth.');

  return {
    score,
    savingsRate,
    expenseRatio,
    investmentRatio,
    debtRatio,
    emergencyCoverage,
    explanations: [
      `Savings rate: ${savingsRate.toFixed(1)}%`,
      `Expense ratio: ${expenseRatio.toFixed(1)}%`,
      `Investment allocation: ${investmentRatio.toFixed(1)}%`,
      `Emergency coverage: ${emergencyCoverage.toFixed(1)} months`,
      `Debt ratio estimate: ${debtRatio.toFixed(1)}%`,
    ],
    recommendations,
  };
}

export function detectAnomalies(transactions) {
  const expenseTx = transactions.filter((tx) => tx.amount < 0);
  const categoryMap = expenseTx.reduce((map, tx) => {
    if (!map[tx.category]) map[tx.category] = [];
    map[tx.category].push(Math.abs(tx.amount));
    return map;
  }, {});

  const oddTransactions = expenseTx.filter((tx) => {
    const values = categoryMap[tx.category] || [];
    const mean = values.reduce((sum, v) => sum + v, 0) / Math.max(1, values.length);
    const variance = values.reduce((sum, v) => sum + Math.pow(v - mean, 2), 0) / Math.max(1, values.length);
    const stdDev = Math.sqrt(variance);
    return Math.abs(Math.abs(tx.amount) - mean) > Math.max(2000, stdDev * 2);
  });

  const recurring = Object.values(
    transactions.reduce((rec, tx) => {
      const key = normalizeKey(tx.merchant || tx.description);
      if (tx.amount < 0) {
        rec[key] = rec[key] || { merchant: tx.merchant || tx.description, count: 0, total: 0, category: tx.category };
        rec[key].count += 1;
        rec[key].total += Math.abs(tx.amount);
      }
      return rec;
    }, {})
  ).filter((item) => item.count >= 3);

  return {
    oddTransactions,
    spendingSpikes: [],
    recurring,
  };
}

function normalizeKey(value = '') {
  return String(value).toLowerCase().trim();
}

export function detectSubscriptions(transactions) {
  const candidates = transactions.reduce((map, tx) => {
    if (tx.amount < 0) {
      const key = normalizeKey(tx.merchant || tx.description);
      map[key] = map[key] || { merchant: tx.merchant || tx.description, count: 0, total: 0, categories: new Set() };
      map[key].count += 1;
      map[key].total += Math.abs(tx.amount);
      map[key].categories.add(tx.category);
    }
    return map;
  }, {});

  return Object.values(candidates)
    .filter((item) => item.count >= 3)
    .map((item) => ({
      merchant: item.merchant,
      monthlyAmount: Math.round(item.total / item.count),
      annualEstimate: Math.round((item.total / item.count) * 12),
      category: Array.from(item.categories)[0] || 'Miscellaneous',
      occurrences: item.count,
    }))
    .sort((a, b) => b.annualEstimate - a.annualEstimate);
}

export function predictGoals(goals, transactions) {
  const monthly = buildMonthlyCashflow(transactions);
  const avgSavings = monthly.length ? monthly.reduce((sum, item) => sum + item.savings, 0) / monthly.length : 0;
  return goals.map((goal) => {
    const remaining = Math.max(0, goal.target - goal.current);
    const pace = Math.max(goal.monthlyContribution || 0, Math.round(avgSavings * 0.6), 1000);
    const monthsUntil = remaining > 0 ? Math.ceil(remaining / pace) : 0;
    const finish = new Date();
    finish.setMonth(finish.getMonth() + monthsUntil);
    return {
      ...goal,
      remaining,
      progress: goal.target ? Math.min(100, Math.round((goal.current / goal.target) * 100)) : 0,
      monthlyRequirement: pace,
      predictedCompletion: remaining === 0 ? 'Completed' : finish.toLocaleString('default', { month: 'short', year: 'numeric' }),
    };
  });
}

export function buildForecast(transactions, horizon = 12) {
  const monthly = buildMonthlyCashflow(transactions);
  const recent = monthly.slice(-6);
  const avgExpense = recent.reduce((sum, item) => sum + item.expense, 0) / Math.max(1, recent.length);
  const avgIncome = recent.reduce((sum, item) => sum + item.income, 0) / Math.max(1, recent.length);
  const forecast = [];
  for (let i = 1; i <= horizon; i += 1) {
    const date = new Date();
    date.setMonth(date.getMonth() + i);
    forecast.push({
      month: date.toLocaleString('default', { month: 'short', year: 'numeric' }),
      income: Math.round(avgIncome * (1 + 0.01 * i)),
      expense: Math.round(avgExpense * (1 + 0.015 * i)),
      savings: Math.round(avgIncome * (1 + 0.01 * i) - avgExpense * (1 + 0.015 * i)),
    });
  }
  return forecast;
}
