// utils/markdown.js

export function renderMarkdown(markdownText = "") {
    if (typeof markdownText !== "string") return "";
  
    // marked is expected to be available globally (via CDN script)
    if (typeof marked === "undefined" || !marked?.parse) {
      // Fallback: escape and render as plain text
      return escapeHtml(markdownText);
    }
  
    return marked.parse(markdownText);
  }
  
  export function escapeHtml(text = "") {
    const map = {
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#039;",
    };
    return String(text).replace(/[&<>"']/g, (m) => map[m]);
  }  