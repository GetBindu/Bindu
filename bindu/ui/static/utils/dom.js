// utils/dom.js

export const $ = (selector, root = document) => root.querySelector(selector);
export const $$ = (selector, root = document) =>
  Array.from(root.querySelectorAll(selector));

export const byId = (id) => document.getElementById(id);

export function setText(el, text) {
  if (!el) return;
  el.textContent = text ?? "";
}

export function setHTML(el, html) {
  if (!el) return;
  el.innerHTML = html ?? "";
}

export function show(el, display = "block") {
  if (!el) return;
  el.style.display = display;
}

export function hide(el) {
  if (!el) return;
  el.style.display = "none";
}

export function createEl(tag, { className, text, html, attrs } = {}) {
  const el = document.createElement(tag);
  if (className) el.className = className;
  if (text != null) el.textContent = text;
  if (html != null) el.innerHTML = html;

  if (attrs && typeof attrs === "object") {
    for (const [k, v] of Object.entries(attrs)) {
      if (v != null) el.setAttribute(k, v);
    }
  }
  return el;
}