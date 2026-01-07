export function isValidEmail(email) {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return emailRegex.test(email);
}

export function isValidURL(url) {
  try {
    new URL(url);
    return true;
  } catch {
    return false;
  }
}

export function isValidJSON(str) {
  try {
    JSON.parse(str);
    return true;
  } catch {
    return false;
  }
}

export function isNonEmptyString(value) {
  return typeof value === 'string' && value.trim().length > 0;
}

export function isValidTaskId(taskId) {
  return isNonEmptyString(taskId);
}

export function isValidContextId(contextId) {
  return isNonEmptyString(contextId);
}

export function isValidRating(rating) {
  const num = parseInt(rating, 10);
  return !isNaN(num) && num >= 1 && num <= 5;
}

export function isASCII(str) {
  return /^[\x00-\x7F]*$/.test(str);
}

export function sanitizeInput(input, maxLength = 5000) {
  if (typeof input !== 'string') return '';
  return input.trim().slice(0, maxLength);
}

export function validateToken(token) {
  if (!token || typeof token !== 'string') return false;
  const cleaned = token.trim();
  return cleaned.length > 0 && isASCII(cleaned);
}
