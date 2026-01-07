export function renderMarkdown(text) {
  if (typeof marked === 'undefined') {
    console.warn('marked.js not loaded, returning plain text');
    return escapeHTML(text);
  }
  
  try {
    marked.setOptions({
      breaks: true,
      gfm: true,
      headerIds: false,
      mangle: false
    });
    
    return marked.parse(text);
  } catch (error) {
    console.error('Markdown rendering error:', error);
    return escapeHTML(text);
  }
}

export function escapeHTML(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

export function stripMarkdown(text) {
  return text
    .replace(/#{1,6}\s+/g, '')
    .replace(/\*\*(.+?)\*\*/g, '$1')
    .replace(/\*(.+?)\*/g, '$1')
    .replace(/_(.+?)_/g, '$1')
    .replace(/`(.+?)`/g, '$1')
    .replace(/\[(.+?)\]\(.+?\)/g, '$1')
    .replace(/!\[.*?\]\(.+?\)/g, '')
    .replace(/>\s+/g, '')
    .replace(/\n{2,}/g, '\n')
    .trim();
}

export function extractCodeBlocks(text) {
  const codeBlockRegex = /```(\w+)?\n([\s\S]+?)```/g;
  const blocks = [];
  let match;
  
  while ((match = codeBlockRegex.exec(text)) !== null) {
    blocks.push({
      language: match[1] || 'text',
      code: match[2].trim()
    });
  }
  
  return blocks;
}

export function highlightCode(code, language = 'text') {
  if (typeof hljs !== 'undefined') {
    try {
      if (language && hljs.getLanguage(language)) {
        return hljs.highlight(code, { language }).value;
      }
      return hljs.highlightAuto(code).value;
    } catch (error) {
      console.error('Code highlighting error:', error);
    }
  }
  
  return escapeHTML(code);
}
