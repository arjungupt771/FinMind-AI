import { getCategoryIcon } from './categorizationService.js';

const MS_PER_DAY = 24 * 60 * 60 * 1000;

function monthKey(dateString) {
  const date = new Date(dateString);
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`;
}

function formatMonthLabel(key) {
  const [year, month] = key.split('-').map(Number);
  return new Date(year, month - 1).toLocaleString('default', { month: 'short', year: 'numeric' });
}

function groupByMonth(transactions) {
  return transactions.reduce((memo, tx) => {
    const key = monthKey(tx.date);
    memo[key] = memo[key] || { income: 0, expense: 0, savings: 0, transactions: [] };
    memo[key].transactions.push(tx);
    if (tx.amount >= 0) memo[key].income += tx.amount;
    else memo[key].expense += Math.abs(tx.amount);
    memo[key].savings = memo[key].income - memo[key].expense;
    return memo;
  }, {});
}

export function buildOverview(transactions) {
  const totals = transactions.reduce(
    (acc, tx) => {
      if (tx.amount >= 0) acc.income += tx.amount;
      else acc.expense += Math.abs(tx.amount);
      if (tx.category === 'Investments') acc.investments += Math.abs(tx.amount);
      if (tx.category === 'Bills') acc.bills += Math.abs(tx.amount);
      if (tx.category === 'Food') acc.food += Math.abs(tx.amount);
      return acc;
    },
    { income: 0, expense: 0, investments: 0, bills: 0, food: 0 }
  );

  const savings = totals.income - totals.expense;
  const savingsRate = totals.income > 0 ? (savings / totals.income) * 100 : 0;
  const expenseRatio = totals.income > 0 ? (totals.expense / totals.income) * 100 : 0;
  return {
    income: totals.income,
    expense: totals.expense,
    savings,
    savingsRate,
    expenseRatio,
    topCategories: getTopCategories(transactions),
    monthlyCashflow: buildMonthlyCashflow(transactions),
    spendingBreakdown: buildSpendingBreakdown(transactions),
    savingsGrowth: buildSavingsGrowth(transactions),
    categoryTrends: buildCategoryTrends(transactions),
  };
}

function getTopCategories(transactions) {
  const totals = {};
  transactions.forEach((tx) => {
    if (tx.amount < 0) {
      totals[tx.category] = (totals[tx.category] || 0) + Math.abs(tx.amount);
    }
  });
  return Object.entries(totals)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 5)
    .map(([category, amount]) => ({ category, amount, icon: getCategoryIcon(category) }));
}

function buildMonthlyCashflow(transactions) {
  const grouped = groupByMonth(transactions);
  return Object.keys(grouped)
    .sort()
    .map((month) => ({ month: formatMonthLabel(month), ...grouped[month] }));
}

function buildSpendingBreakdown(transactions) {
  const categories = {};
  transactions.forEach((tx) => {
    if (tx.amount < 0) {
      categories[tx.category] = (categories[tx.category] || 0) + Math.abs(tx.amount);
    }
  });
  return Object.entries(categories).map(([category, amount]) => ({ category, amount, icon: getCategoryIcon(category) }));
}

function buildCategoryTrends(transactions) {
  const monthly = groupByMonth(transactions);
  const categoryTrend = {};
  transactions.forEach((tx) => {
    if (tx.amount < 0) {
      const month = monthKey(tx.date);
      categoryTrend[tx.category] = categoryTrend[tx.category] || {};
      categoryTrend[tx.category][month] = (categoryTrend[tx.category][month] || 0) + Math.abs(tx.amount);
    }
  });
  return Object.entries(categoryTrend).map(([category, data]) => ({ category, data }));
}

function buildSavingsGrowth(transactions) {
  const monthly = buildMonthlyCashflow(transactions);
  return monthly.map((entry) => ({ month: entry.month, savings: entry.savings }));
}

export function computeHealthScore(transactions) {
  const income = transactions.filter((tx) => tx.amount >= 0).reduce((sum, tx) => sum + tx.amount, 0);
  const expense = transactions.filter((tx) => tx.amount < 0).reduce((sum, tx) => sum + Math.abs(tx.amount), 0);
  const investments = transactions.filter((tx) => tx.category === 'Investments').reduce((sum, tx) => sum + Math.abs(tx.amount), 0);
  const debt = transactions.filter((tx) => tx.category === 'Bills' && tx.description.toLowerCase().includes('loan')).reduce((sum, tx) => sum + Math.abs(tx.amount), 0);
  const avgMonthlyExpense = expense / Math.max(1, Object.keys(groupByMonth(transactions)).length);
  const emergencyCoverage = avgMonthlyExpense > 0 ? Math.max(0, (income - expense) / avgMonthlyExpense) : 0;

  const savingsRate = income > 0 ? ((income - expense) / income) * 100 : 0;
  const expenseRatio = income > 0 ? (expense / income) * 100 : 0;
  const investmentRatio = income > 0 ? (investments / income) * 100 : 0;
  const debtRatio = income > 0 ? (debt / income) * 100 : 0;

  const score = Math.round(
    Math.max(
      0,
      Math.min(
        100,
        savingsRate * 0.3 + (100 - expenseRatio) * 0.2 + Math.min(emergencyCoverage, 6) * 5 + investmentRatio * 1.5 + (20 - debtRatio) * 1.5
      )
    )
  );

  const explanations = [
    `Savings rate is ${savingsRate.toFixed(1)}%`,
    `Expense to income ratio is ${expenseRatio.toFixed(1)}%`,
    `Emergency coverage is ${emergencyCoverage.toFixed(1)} months`,
    `Investment ratio is ${investmentRatio.toFixed(1)}%`,
    `Debt ratio is ${debtRatio.toFixed(1)}%`,
  ];

  return { score, savingsRate, expenseRatio, emergencyCoverage, investmentRatio, debtRatio, explanations };
}

export function detectAnomalies(transactions) {
  const expenseTransactions = transactions.filter((tx) => tx.amount < 0);
  const categories = {};
  expenseTransactions.forEach((tx) => {
    categories[tx.category] = categories[tx.category] || [];
    categories[tx.category].push(Math.abs(tx.amount));
  });

  const oddTransactions = expenseTransactions.filter((tx) => {
    const amounts = categories[tx.category] || [];
    const mean = amounts.reduce((sum, value) => sum + value, 0) / Math.max(1, amounts.length);
    const variance = amounts.reduce((sum, value) => sum + Math.pow(value - mean, 2), 0) / Math.max(1, amounts.length);
    const std = Math.sqrt(variance);
    return Math.abs(Math.abs(tx.amount) - mean) > Math.max(3000, std * 2);
  });

  const monthly = buildMonthlyCashflow(transactions);
  const recent = monthly.slice(-4);
  const spendingSpikes = [];
  if (recent.length >= 2) {
    const last = recent[recent.length - 1];
    const priorAverage = recent.slice(0, -1).reduce((sum, item) => sum + item.expense, 0) / Math.max(1, recent.length - 1);
    if (last.expense > priorAverage * 1.25) {
      spendingSpikes.push({ month: last.month, amount: last.expense, previous: priorAverage });
    }
  }

  const merchantCounts = transactions.reduce((map, tx) => {
    const key = tx.merchant || tx.description;
    if (tx.amount < 0) {
      map[key] = map[key] || { count: 0, total: 0, examples: [] };
      map[key].count += 1;
      map[key].total += Math.abs(tx.amount);
      if (map[key].examples.length < 2) map[key].examples.push(tx);
    }
    return map;
  }, {});

  const recurring = Object.entries(merchantCounts)
    .filter(([, value]) => value.count >= 3)
    .map(([merchant, value]) => ({ merchant, occurrences: value.count, annualCost: Math.round((value.total / value.count) * 12), average: Math.round(value.total / value.count) }));

  return { oddTransactions, spendingSpikes, recurringExpenses: recurring };
}

export function detectSubscriptions(transactions) {
  const subscriptions = {};
  transactions.forEach((tx) => {
    if (tx.amount < 0) {
      const key = tx.merchant || tx.description;
      subscriptions[key] = subscriptions[key] || { merchant: key, count: 0, total: 0, sampleCategory: tx.category };
      subscriptions[key].count += 1;
      subscriptions[key].total += Math.abs(tx.amount);
    }
  });
  return Object.values(subscriptions)
    .filter((item) => item.count >= 3)
    .map((item) => ({
      merchant: item.merchant,
      monthlyAmount: Math.round(item.total / item.count),
      annualEstimate: Math.round((item.total / item.count) * 12),
      category: item.sampleCategory,
      occurrences: item.count,
    }))
    .sort((a, b) => b.annualEstimate - a.annualEstimate);
}

export function predictGoals(goals, transactions) {
  const monthlyData = buildMonthlyCashflow(transactions);
  const avgSavings = monthlyData.length
    ? monthlyData.reduce((sum, item) => sum + item.savings, 0) / monthlyData.length
    : 0;

  return goals.map((goal) => {
    const savedSoFar = goal.current || 0;
    const remaining = Math.max(0, goal.target - savedSoFar);
    const recommendedMonthly = remaining > 0 ? Math.max(0, remaining / Math.max(1, goal.months || 6)) : 0;
    const pace = Math.max(recommendedMonthly, avgSavings * 0.6, 1000);
    const monthsToFinish = remaining > 0 ? Math.ceil(remaining / pace) : 0;
    const predictedCompletion = new Date();
    predictedCompletion.setMonth(predictedCompletion.getMonth() + monthsToFinish);
    return {
      ...goal,
      savedSoFar,
      remaining,
      recommendedMonthly: Math.round(Math.max(recommendedMonthly, pace)),
      predictedCompletion: remaining === 0 ? 'Completed' : predictedCompletion.toLocaleDateString('default', { month: 'short', year: 'numeric' }),
    };
  });
}

export function buildForecast(transactions, horizon = 12) {
  const monthly = buildMonthlyCashflow(transactions);
  const lastSix = monthly.slice(-6);
  const avgExpense = lastSix.reduce((sum, entry) => sum + entry.expense, 0) / Math.max(1, lastSix.length);
  const avgIncome = lastSix.reduce((sum, entry) => sum + entry.income, 0) / Math.max(1, lastSix.length);
  const growthRate = lastSix.length > 1 ? (monthly.slice(-1)[0].expense - monthly[0].expense) / Math.max(1, monthly[0].expense) : 0;
  const forecast = [];
  let nextIncome = avgIncome;
  let nextExpense = avgExpense;
  for (let i = 1; i <= horizon; i += 1) {
    nextIncome *= 1 + growthRate * 0.02;
    nextExpense *= 1 + growthRate * 0.02;
    const date = new Date();
    date.setMonth(date.getMonth() + i);
    forecast.push({ month: date.toLocaleString('default', { month: 'short', year: 'numeric' }), income: Math.round(nextIncome), expense: Math.round(nextExpense), savings: Math.round(nextIncome - nextExpense) });
  }
  return forecast;
}

export function buildReportSummary(transactions, analysis, health, goals, subscriptions) {
  return {
    analysis,
    health,
    goals,
    subscriptions,
    summary: `This report summarizes ${transactions.length} uploaded transactions, highlights your spending categories, and provides a ${health.score}/100 financial health score. Your top categories are ${analysis.topCategories.map((item) => item.category).join(', ')}.`,
  };
}

export function renderCategoryCards(spendingBreakdown) {
  return spendingBreakdown.map((item) => ({
    title: item.category,
    amount: item.amount,
    icon: getCategoryIcon(item.category),
  }));
}
