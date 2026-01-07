import { renderMarkdown } from '../../utils/markdown.js';
import { createElement, createElementWithHTML } from '../../utils/dom.js';

export function renderMessage(content, sender, taskId = null, state = null) {
  const messageDiv = createElement('div', `message ${sender}`);
  const contentDiv = createElement('div', 'message-content');

  if (sender === 'agent' && taskId) {
    messageDiv.style.cursor = 'pointer';
    messageDiv.dataset.taskId = taskId;
  }

  if (sender === 'agent') {
    contentDiv.innerHTML = renderMarkdown(content);
  } else {
    contentDiv.textContent = content;
  }

  if (state && state.toLowerCase() === 'completed' && sender === 'agent' && taskId) {
    const feedbackBtn = createElement('button', 'feedback-btn-corner', '👍 Feedback');
    feedbackBtn.onclick = (e) => {
      e.stopPropagation();
      const event = new CustomEvent('feedback-requested', { detail: { taskId } });
      document.dispatchEvent(event);
    };
    contentDiv.appendChild(feedbackBtn);
  }

  messageDiv.appendChild(contentDiv);

  if (taskId && state) {
    const metaDiv = createElement('div', 'message-meta');
    metaDiv.innerHTML = `Task: ${taskId} <span class="task-badge ${state}">${state}</span>`;
    messageDiv.appendChild(metaDiv);
  }

  return messageDiv;
}

export function renderThinkingIndicator(taskId = null) {
  const thinkingDiv = createElement('div', 'message agent thinking');
  thinkingDiv.id = 'thinking-indicator';

  const contentDiv = createElement('div', 'message-content');

  const dotsDiv = createElementWithHTML('div', 'thinking-dots', '<span>.</span><span>.</span><span>.</span>');
  contentDiv.appendChild(dotsDiv);

  if (taskId) {
    const cancelBtn = createElement('button', 'cancel-task-btn', '✕ Cancel');
    cancelBtn.onclick = async (e) => {
      e.stopPropagation();
      if (confirm('Are you sure you want to cancel this task?')) {
        const event = new CustomEvent('task-cancel-requested', { detail: { taskId } });
        document.dispatchEvent(event);
      }
    };
    contentDiv.appendChild(cancelBtn);
  }

  thinkingDiv.appendChild(contentDiv);
  return thinkingDiv;
}

export function renderStatusMessage(message) {
  return renderMessage(message, 'status');
}
