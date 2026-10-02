import { categorizeTransaction } from './categorizationService.js';

const AMOUNT_PATTERN = /(-?\d{1,3}(?:[\,\d]{2,})?(?:\.\d+)?)/g;
const DATE_PATTERNS = [
  /(\d{2}[\/\-]\d{2}[\/\-]\d{2,4})/, // 01/06/2025 or 01-06-2025
  /(\d{4}[\/\-]\d{2}[\/\-]\d{2})/, // 2025-06-01
  /(\d{1,2}\s+[A-Za-z]{3}\s+\d{4})/, // 1 Jun 2025
];

function toNumber(value) {
  if (value === undefined || value === null) return 0;
  const normalized = String(value).replace(/[^0-9\-\.]/g, '').replace(/(\..*)\./g, '$1');
  return Number(normalized) || 0;
}

function parseDate(value) {
  if (!value) return null;
  const text = String(value).trim();
  const iso = new Date(text);
  if (!Number.isNaN(iso.getTime())) {
    return iso.toISOString();
  }

  for (const pattern of DATE_PATTERNS) {
    const match = text.match(pattern);
    if (match) {
      const candidate = new Date(match[1]);
      if (!Number.isNaN(candidate.getTime())) {
        return candidate.toISOString();
      }
    }
  }
  return null;
}

function safeString(value) {
  return value == null ? '' : String(value).trim();
}

function extractDateFromText(text) {
  for (const pattern of DATE_PATTERNS) {
    const match = text.match(pattern);
    if (match) {
      return parseDate(match[1]);
    }
  }
  return new Date().toISOString();
}

function normalizeRow(row, sourceLabel) {
  const lowered = Object.keys(row).reduce((acc, key) => {
    acc[key.toLowerCase().trim()] = row[key];
    return acc;
  }, {});

  const description = safeString(lowered.description || lowered.narration || lowered.particulars || lowered.remark || lowered.remarks || lowered.vendor || lowered.merchant || lowered.name);
  const debit = toNumber(lowered.debit || lowered.amount || lowered.withdrawal || lowered.outflow);
  const credit = toNumber(lowered.credit || lowered.inflow || lowered.deposit);
  const amount = credit || -debit || toNumber(lowered.amount || lowered.value);
  const date = parseDate(lowered.date || lowered.transactiondate || lowered.txndate || lowered.postingdate) || extractDateFromText(description + ' ' + sourceLabel);

  return {
    date,
    vendor: description,
    description,
    amount,
    sourceFile: sourceLabel,
  };
}

function parseCsvText(text) {
  const lines = text.split(/\r?\n/).filter(Boolean);
  if (!lines.length) return [];
  const header = lines[0].split(/,|\t|\|/).map((h) => h.trim());
  const rows = lines.slice(1).map((line) => {
    const cells = line.split(/,|\t|\|/);
    if (cells.length !== header.length) {
      return null;
    }
    return header.reduce((row, key, index) => {
      row[key] = cells[index].trim();
      return row;
    }, {});
  }).filter(Boolean);
  return rows.map((row) => normalizeRow(row, 'CSV'));
}

function parseXlsxWorkbook(workbook) {
  const sheetName = workbook.SheetNames[0];
  const sheet = workbook.Sheets[sheetName];
  const rows = XLSX.utils.sheet_to_json(sheet, { defval: '' });
  return rows.map((row) => normalizeRow(row, 'XLSX'));
}

async function parsePdfBuffer(arrayBuffer) {
  if (!window.pdfjsLib) {
    throw new Error('PDF parser library not loaded');
  }
  const pdf = await window.pdfjsLib.getDocument({ data: arrayBuffer }).promise;
  const pages = [];
  for (let i = 1; i <= pdf.numPages; i += 1) {
    const page = await pdf.getPage(i);
    const content = await page.getTextContent();
    pages.push(content.items.map((item) => item.str).join(' '));
  }

  const text = pages.join('\n');
  const lines = text.split(/\r?\n/).filter((line) => line.trim().length > 10);
  const candidates = [];
  lines.forEach((line) => {
    const amountMatches = line.match(AMOUNT_PATTERN);
    const date = extractDateFromText(line);
    if (amountMatches && amountMatches.length) {
      const rawAmount = amountMatches[amountMatches.length - 1];
      const amount = toNumber(rawAmount);
      if (Math.abs(amount) > 0) {
        candidates.push({
          date,
          vendor: line,
          description: line,
          amount: amount > 0 ? amount * -1 : amount,
          sourceFile: 'PDF',
        });
      }
    }
  });
  return candidates;
}

export async function parseFile(file) {
  const extension = file.name.toLowerCase().split('.').pop();
  if (extension === 'csv') {
    const text = await file.text();
    return {
      transactions: parseCsvText(text),
      sourceFile: file.name,
      mimeType: file.type,
    };
  }

  if (extension === 'xlsx' || extension === 'xls') {
    const data = await file.arrayBuffer();
    const workbook = XLSX.read(data, { type: 'array' });
    return {
      transactions: parseXlsxWorkbook(workbook),
      sourceFile: file.name,
      mimeType: file.type,
    };
  }

  if (extension === 'pdf') {
    const data = await file.arrayBuffer();
    const transactions = await parsePdfBuffer(data);
    return {
      transactions,
      sourceFile: file.name,
      mimeType: file.type,
    };
  }

  throw new Error('Unsupported file format. Upload PDF, CSV, or XLSX.');
}

export function normalizeTransactions(parsed) {
  return parsed.transactions
    .map((tx) => categorizeTransaction(normalizeRow(tx, parsed.sourceFile)))
    .filter((tx) => tx.date && Number.isFinite(tx.amount));
}
