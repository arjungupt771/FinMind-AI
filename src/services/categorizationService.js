const CATEGORY_DEFINITION = {
  Food: ['food', 'restaurant', 'cafe', 'coffee', 'swiggy', 'zomato', 'dining', 'pizza', 'mcd', 'kfc', 'canteen'],
  Travel: ['uber', 'ola', 'taxi', 'metro', 'train', 'railway', 'flight', 'airline', 'bus', 'travel'],
  Shopping: ['amazon', 'flipkart', 'myntra', 'shopping', 'mall', 'store', 'zara', 'ajio', 'bigbasket', 'nykaa'],
  Bills: ['electricity', 'phone', 'mobile', 'reliance', 'jio', 'water', 'subscription', 'utility', 'bill', 'rent', 'emi'],
  Entertainment: ['netflix', 'prime', 'hotstar', 'spotify', 'bookmyshow', 'cinema', 'movies', 'gaming', 'ott'],
  Investments: ['mutual fund', 'sip', 'investment', 'stock', 'nse', 'bse', 'groww', 'zerodha', 'fund', 'etf', 'insurance'],
  Health: ['pharmacy', 'clinic', 'hospital', 'doctor', 'health', 'gym', 'fitness', 'medic', 'dental'],
};

const DEFAULT_CATEGORIES = ['Food', 'Travel', 'Shopping', 'Bills', 'Entertainment', 'Investments', 'Health', 'Miscellaneous', 'Income'];

function normalizeText(value = '') {
  return String(value).trim().toLowerCase();
}

function matchCategory(vendor, description, amount) {
  const text = normalizeText(`${vendor} ${description}`);
  for (const [category, tokens] of Object.entries(CATEGORY_DEFINITION)) {
    if (tokens.some((token) => text.includes(token))) {
      return category;
    }
  }
  return amount >= 0 ? 'Income' : 'Miscellaneous';
}

export function categorizeTransaction(tx) {
  const description = tx.description || tx.vendor || '';
  const merchant = normalizeText(tx.vendor || description).replace(/\s*[|\/\-]\s*/g, ' ').trim() || 'Unknown Merchant';
  const category = matchCategory(tx.vendor, description, tx.amount);
  const type = tx.amount >= 0 ? 'income' : 'expense';
  return {
    ...tx,
    category,
    type,
    merchant,
  };
}

export function getSupportedCategories() {
  return DEFAULT_CATEGORIES;
}

export function getCategoryIcon(category) {
  const icons = {
    Food: '🍜',
    Travel: '✈️',
    Shopping: '🛍️',
    Bills: '📄',
    Entertainment: '🎬',
    Investments: '📈',
    Health: '🩺',
    Miscellaneous: '🧾',
    Income: '💰',
  };
  return icons[category] || '💡';
}
