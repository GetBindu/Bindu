export function formatDate(date, options = {}) {
  const d = date instanceof Date ? date : new Date(date);
  const defaults = {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  };
  return d.toLocaleDateString('en-US', { ...defaults, ...options });
}

export function formatRelativeTime(date) {
  const d = date instanceof Date ? date : new Date(date);
  const now = new Date();
  const diffMs = now - d;
  const diffSec = Math.floor(diffMs / 1000);
  const diffMin = Math.floor(diffSec / 60);
  const diffHour = Math.floor(diffMin / 60);
  const diffDay = Math.floor(diffHour / 24);

  if (diffSec < 60) return 'just now';
  if (diffMin < 60) return `${diffMin}m ago`;
  if (diffHour < 24) return `${diffHour}h ago`;
  if (diffDay < 7) return `${diffDay}d ago`;
  return formatDate(d, { year: 'numeric', month: 'short', day: 'numeric' });
}

export function formatNumber(num, decimals = 0) {
  return Number(num).toFixed(decimals);
}

export function formatCurrency(amount, currency = 'USD') {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency
  }).format(amount);
}

export function truncateText(text, maxLength = 50, suffix = '...') {
  if (!text || text.length <= maxLength) return text;
  return text.slice(0, maxLength - suffix.length) + suffix;
}

export function formatBytes(bytes, decimals = 2) {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(decimals)) + ' ' + sizes[i];
}

export function capitalizeFirst(str) {
  if (!str) return '';
  return str.charAt(0).toUpperCase() + str.slice(1);
}

export function formatTaskStatus(status) {
  const statusMap = {
    'completed': '✅ Completed',
    'failed': '❌ Failed',
    'canceled': '🚫 Canceled',
    'input-required': '⏳ Waiting for input',
    'running': '🔄 Running'
  };
  return statusMap[status] || status;
}

export function formatMessagePreview(message, maxLength = 50) {
  if (!message) return '';
  const cleaned = message.replace(/\n/g, ' ').trim();
  return truncateText(cleaned, maxLength);
}
