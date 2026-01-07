export function createElement(tag, className = '', content = '') {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (content) element.textContent = content;
  return element;
}

export function createElementWithHTML(tag, className = '', html = '') {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (html) element.innerHTML = html;
  return element;
}

export function querySelector(selector, parent = document) {
  return parent.querySelector(selector);
}

export function querySelectorAll(selector, parent = document) {
  return Array.from(parent.querySelectorAll(selector));
}

export function addClass(element, ...classes) {
  if (element) element.classList.add(...classes);
}

export function removeClass(element, ...classes) {
  if (element) element.classList.remove(...classes);
}

export function toggleClass(element, className) {
  if (element) element.classList.toggle(className);
}

export function hasClass(element, className) {
  return element ? element.classList.contains(className) : false;
}

export function setAttributes(element, attributes) {
  if (!element) return;
  Object.entries(attributes).forEach(([key, value]) => {
    element.setAttribute(key, value);
  });
}

export function removeElement(element) {
  if (element && element.parentNode) {
    element.parentNode.removeChild(element);
  }
}

export function clearChildren(element) {
  if (element) {
    while (element.firstChild) {
      element.removeChild(element.firstChild);
    }
  }
}

export function appendChildren(parent, ...children) {
  if (!parent) return;
  children.forEach(child => {
    if (child) parent.appendChild(child);
  });
}

export function on(element, event, handler, options = {}) {
  if (element) {
    element.addEventListener(event, handler, options);
    return () => element.removeEventListener(event, handler, options);
  }
  return () => {};
}

export function delegate(parent, selector, event, handler) {
  return on(parent, event, (e) => {
    const target = e.target.closest(selector);
    if (target) {
      handler.call(target, e);
    }
  });
}
