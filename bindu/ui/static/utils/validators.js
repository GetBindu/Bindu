// utils/validators.js

export function isNonEmptyString(v) {
  return typeof v === "string" && v.trim().length > 0;
}

export function isAsciiOnly(str) {
  if (typeof str !== "string") return false;
  return /^[\x00-\x7F]*$/.test(str);
}

export function cleanToken(token) {
  if (!isNonEmptyString(token)) return null;
  const t = token.trim();
  return isAsciiOnly(t) ? t : null;
}

export function isValidUrl(url) {
  try {
    new URL(url);
    return true;
  } catch {
    return false;
  }
}