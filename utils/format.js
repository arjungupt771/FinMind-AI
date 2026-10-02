export function formatCurrency(value) {
  if (value == null || Number.isNaN(value)) return '₹0';
  return `₹${Math.round(value).toLocaleString('en-IN')}`;
}

export function formatPercent(value) {
  return `${value.toFixed(1)}%`;
}

export function safeText(value) {
  return value == null ? '' : String(value);
}

export function formatMonth(dateString) {
  const date = new Date(dateString);
  return date.toLocaleString('default', { month: 'short', year: 'numeric' });
}

export function createPopupMessage(message, type = 'info') {
  const toast = document.getElementById('toast');
  if (!toast) return;
  toast.textContent = message;
  toast.className = `toast toast-${type} show`;
  setTimeout(() => {
    toast.classList.remove('show');
  }, 3200);
}
