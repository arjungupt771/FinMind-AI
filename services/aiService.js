import { formatCurrency } from '../utils/format.js';

const FALLBACK_MESSAGES = [
  'Your spending is concentrated in Food and Shopping. Cut one dining-out meal per week to improve savings.',
  'Your emergency coverage is under 4 months. Boost liquid savings before increasing investment risk.',
  'Recurring OTT subscriptions appear high. Review and keep only services you use every month.',
  'A healthy goal is to save at least 20% of your income. Your current pace is within reach with one small budget adjustment.',
];

function buildTransactionSummary(transactions) {
  const recent = transactions
    .sort((a, b) => new Date(b.date) - new Date(a.date))
    .slice(0, 10);
  return recent.map((tx) => `${tx.date.slice(0, 10)}: ${tx.merchant} ${tx.amount < 0 ? 'spent' : 'received'} ${formatCurrency(tx.amount)} in ${tx.category}`).join('\n');
}

export function buildAiPrompt(question, state) {
  const { transactions = [], analysis = {}, health = {}, goals = [] } = state;
  return `You are FinMind AI, a personal finance copilot for a user in India.
- Monthly income approx ₹${Math.round(analysis.income || 72000)}.
- Current savings rate: ${health.savingsRate?.toFixed(1) || 0}%.
- Expense ratio: ${health.expenseRatio?.toFixed(1) || 0}%.
- Top categories: ${analysis.topCategories?.map((item) => item.category).join(', ') || 'N/A'}.
- Latest goals: ${goals.map((goal) => `${goal.name} target ₹${goal.target}`).join(', ') || 'No active goals'}.

Latest transaction summary:
${buildTransactionSummary(transactions)}

Question: ${question}
Provide concise, actionable recommendations for this specific user. Use ₹ amounts where possible. Suggest overspending flags, savings actions, and investment allocation. Do not mention that this is a demo.`;
}

export async function askGroq(question, state, apiKey) {
  if (!apiKey) {
    const fallback = FALLBACK_MESSAGES[Math.floor(Math.random() * FALLBACK_MESSAGES.length)];
    return `Demo AI response: ${fallback}`;
  }

  const prompt = buildAiPrompt(question, state);
  const payload = {
    model: 'groq-1.1',
    input: prompt,
    max_output_tokens: 300,
    temperature: 0.25,
  };

  const response = await fetch('https://api.groq.com/v1/complete', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${apiKey}`,
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error(`Groq API error ${response.status}`);
  }

  const payloadResponse = await response.json();
  if (payloadResponse?.output?.length) {
    return payloadResponse.output.join('\n').trim();
  }
  if (payloadResponse?.text) {
    return payloadResponse.text;
  }
  return 'Groq AI did not return a response. Please try again later.';
}
