import * as XLSX from 'xlsx';
import { GlobalWorkerOptions, getDocument } from 'pdfjs-dist/build/pdf';
import pdfWorkerUrl from 'pdfjs-dist/build/pdf.worker.min.mjs?url';

GlobalWorkerOptions.workerSrc = pdfWorkerUrl;

const DATE_PATTERNS = [
  /\d{4}[\/\-]\d{2}[\/\-]\d{2}/,
  /\d{2}[\/\-]\d{2}[\/\-]\d{2,4}/,
  /\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4}/,
];

function toNumber(value) {
  if (value == null) return 0;
  const cleaned = String(value).replace(/[^0-9\-\.]/g, '');
  return Number(cleaned) || 0;
}

function parseDate(value) {
  if (!value) return null;
  const text = String(value).trim();
  const date = new Date(text);
  if (!Number.isNaN(date.getTime())) {
    return date.toISOString();
  }
  for (const pattern of DATE_PATTERNS) {
    const match = text.match(pattern);
    if (match) {
      const candidate = new Date(match[0]);
      if (!Number.isNaN(candidate.getTime())) {
        return candidate.toISOString();
      }
    }
  }
  return null;
}

function normalizeRow(row, sourceLabel) {
  const safe = (value) => (value == null ? '' : String(value).trim());
  const entry = Object.keys(row).reduce((acc, key) => {
    acc[key.toLowerCase().trim()] = safe(row[key]);
    return acc;
  }, {});

  const description = entry.description || entry.narration || entry.particulars || entry.remark || entry.merchant || entry.vendor || entry.name || '';
  const debit = toNumber(entry.debit || entry.withdrawal || entry.outflow || entry.amount || '');
  const credit = toNumber(entry.credit || entry.deposit || entry.inflow || '');
  const amount = credit || -debit || toNumber(entry.amount || '');
  const date = parseDate(entry.date || entry.transactiondate || entry.txndate || entry.postingdate) || new Date().toISOString();

  return {
    date,
    vendor: description,
    description,
    amount,
    sourceFile: sourceLabel,
  };
}

function parseCsvText(text) {
  const lines = text.split(/\r?\n/).filter((line) => line.trim());
  const header = lines[0]?.split(/,|\t|\|/).map((column) => column.trim()) || [];
  const data = lines.slice(1).map((line) => {
    const values = line.split(/,|\t|\|/).map((value) => value.trim());
    if (values.length !== header.length) return null;
    return header.reduce((row, key, index) => {
      row[key] = values[index];
      return row;
    }, {});
  }).filter(Boolean);
  return data.map((row) => normalizeRow(row, 'CSV'));
}

function parseXlsxWorkbook(workbook) {
  const sheet = workbook.Sheets[workbook.SheetNames[0]];
  const rows = XLSX.utils.sheet_to_json(sheet, { defval: '' });
  return rows.map((row) => normalizeRow(row, 'XLSX'));
}

async function parsePdfBuffer(arrayBuffer) {
  const pdf = await getDocument({ data: arrayBuffer }).promise;
  const lines = [];
  for (let i = 1; i <= pdf.numPages; i += 1) {
    const page = await pdf.getPage(i);
    const content = await page.getTextContent();
    lines.push(content.items.map((item) => item.str).join(' '));
  }
  const text = lines.join('\n');
  const rows = text.split(/\r?\n/).filter((line) => line.trim().length > 10);
  return rows.map((line) => {
    const amountMatch = line.match(/(-?\d{1,3}(?:[\,\d]{2,})?(?:\.\d+)?)/g);
    return {
      date: parseDate(line) || new Date().toISOString(),
      vendor: line,
      description: line,
      amount: amountMatch ? toNumber(amountMatch[amountMatch.length - 1]) * -1 : 0,
      sourceFile: 'PDF',
    };
  }).filter((row) => row.amount !== 0);
}

export async function parseFile(file) {
  const extension = file.name.toLowerCase().split('.').pop();
  if (extension === 'csv') {
    const text = await file.text();
    return { transactions: parseCsvText(text), sourceFile: file.name, mimeType: file.type };
  }
  if (extension === 'xlsx' || extension === 'xls') {
    const data = await file.arrayBuffer();
    const workbook = XLSX.read(data, { type: 'array' });
    return { transactions: parseXlsxWorkbook(workbook), sourceFile: file.name, mimeType: file.type };
  }
  if (extension === 'pdf') {
    const buffer = await file.arrayBuffer();
    const transactions = await parsePdfBuffer(buffer);
    return { transactions, sourceFile: file.name, mimeType: file.type };
  }
  throw new Error('Unsupported file format. Upload a CSV, XLSX, or PDF statement.');
}

export function normalizeTransactions(parsed) {
  return parsed.transactions.filter((tx) => tx.date && Number.isFinite(tx.amount));
}
