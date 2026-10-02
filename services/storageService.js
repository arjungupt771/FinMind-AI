const STORAGE_KEYS = {
  transactions: 'finmind_transactions',
  uploads: 'finmind_uploads',
  goals: 'finmind_goals',
  settings: 'finmind_settings',
};

function loadJson(key, fallback) {
  try {
    const raw = localStorage.getItem(key);
    return raw ? JSON.parse(raw) : fallback;
  } catch (error) {
    console.warn('Storage read failed', key, error);
    return fallback;
  }
}

function saveJson(key, value) {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch (error) {
    console.warn('Storage write failed', key, error);
  }
}

function generateId(prefix = 'id') {
  return `${prefix}_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
}

export function getTransactions() {
  return loadJson(STORAGE_KEYS.transactions, []);
}

export function setTransactions(transactions) {
  saveJson(STORAGE_KEYS.transactions, transactions);
}

export function addTransactions(newTransactions) {
  const existing = getTransactions();
  const combined = [...existing, ...newTransactions].map(tx => ({
    ...tx,
    id: tx.id || generateId('tx'),
    createdAt: tx.createdAt || new Date().toISOString(),
  }));

  const uniqueMap = new Map();
  combined.forEach((tx) => {
    const key = `${tx.date}|${tx.vendor || tx.description}|${tx.amount}|${tx.category}`;
    if (!uniqueMap.has(key)) {
      uniqueMap.set(key, tx);
    }
  });

  const unique = Array.from(uniqueMap.values());
  saveJson(STORAGE_KEYS.transactions, unique);
  return unique;
}

export function getUploads() {
  return loadJson(STORAGE_KEYS.uploads, []);
}

export function addUpload(upload) {
  const uploads = getUploads();
  const entry = {
    id: generateId('upload'),
    uploadedAt: new Date().toISOString(),
    status: 'Parsed',
    ...upload,
  };
  uploads.unshift(entry);
  saveJson(STORAGE_KEYS.uploads, uploads);
  return uploads;
}

export function getGoals() {
  return loadJson(STORAGE_KEYS.goals, []);
}

export function saveGoals(goals) {
  saveJson(STORAGE_KEYS.goals, goals);
  return goals;
}

export function getSettings() {
  return loadJson(STORAGE_KEYS.settings, {});
}

export function setSetting(key, value) {
  const settings = getSettings();
  settings[key] = value;
  saveJson(STORAGE_KEYS.settings, settings);
  return settings;
}

export function getApiKey() {
  return getSettings().groqApiKey || '';
}

export function setApiKey(value) {
  return setSetting('groqApiKey', value);
}

export function resetStorage() {
  localStorage.removeItem(STORAGE_KEYS.transactions);
  localStorage.removeItem(STORAGE_KEYS.uploads);
  localStorage.removeItem(STORAGE_KEYS.goals);
  localStorage.removeItem(STORAGE_KEYS.settings);
}
