const CATEGORY_DEFINITION = {
  Food: ['food', 'restaurant', 'cafe', 'coffee', 'swiggy', 'zomato', 'dining', 'pizza', 'bhukkad', 'mcd', 'kfc', 'canteen', 'canteen'],
  Travel: ['uber', 'ola', 'taxi', 'metro', 'train', 'railway', 'flight', 'airline', 'bus', 'travel', 'rail'],
  Shopping: ['amazon', 'swiggy', 'flipkart', 'myntra', 'shopping', 'mall', 'store', 'zara', 'ajio', 'costco', 'bigbasket', 'nykaa'],
  Bills: ['electricity', 'phone', 'mobile', 'reliance', 'jio', 'bills', 'bill', 'water', 'subscription', 'subscription fee', 'utility', 'umpay'],
  Entertainment: ['netflix', 'prime', 'hotstar', 'spotify', 'bookmyshow', 'cinema', 'movies', 'ticket', 'gaming', 'entertainment', 'ott'],
  Investments: ['mutual fund', 'sip', 'investment', 'stock', 'nse', 'bse', 'groww', 'zerodha', 'fund', 'etf', 'insurance'],
  Health: ['pharmacy', 'clinic', 'hospital', 'doctor', 'health', 'medic', 'dental', 'fitness', 'gym', 'care', 'ayushman'],
};

const DEFAULT_CATEGORIES = [
  'Food',
  'Travel',
  'Shopping',
  'Bills',
  'Entertainment',
  'Investments',
  'Health',
  'Miscellaneous',
  'Income',
];

function normalizeText(text = '') {
  return String(text).trim().toLowerCase();
}

function findCategory(description, vendor, amount) {
  const text = normalizeText(`${vendor} ${description}`);
  for (const [category, terms] of Object.entries(CATEGORY_DEFINITION)) {
    if (terms.some((term) => text.includes(term))) {
      return category;
    }
  }
  if (amount >= 0) {
    return 'Income';
  }
  return 'Miscellaneous';
}

export function categorizeTransaction(tx) {
  const { description = '', vendor = '', amount = 0 } = tx;
  const category = findCategory(description, vendor, amount);
  const type = amount >= 0 ? 'income' : 'expense';
  const merchant = normalizeText(vendor || description).replace(/\s+\|\s+|\s+-\s+|\s+\/\s+/g, ' ').trim();
  return {
    ...tx,
    category,
    type,
    merchant: merchant || 'Unknown Merchant',
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
