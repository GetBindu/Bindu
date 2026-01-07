import { renderMessage, renderThinkingIndicator } from './message-renderer.js';
import { querySelector, clearChildren } from '../../utils/dom.js';

export class MessageList {
  constructor(containerId) {
    this.container = querySelector(`#${containerId}`);
    if (!this.container) {
      throw new Error(`Message list container #${containerId} not found`);
    }
  }

  addMessage(content, sender, taskId = null, state = null) {
    const messageEl = renderMessage(content, sender, taskId, state);
    
    if (sender === 'agent' && taskId) {
      messageEl.onclick = () => {
        const event = new CustomEvent('reply-requested', { detail: { taskId } });
        document.dispatchEvent(event);
      };
    }
    
    this.container.appendChild(messageEl);
    this.scrollToBottom();
  }

  addThinkingIndicator(taskId = null) {
    this.removeThinkingIndicator();
    const indicator = renderThinkingIndicator(taskId);
    this.container.appendChild(indicator);
    this.scrollToBottom();
  }

  removeThinkingIndicator() {
    const existing = querySelector('#thinking-indicator', this.container);
    if (existing) {
      existing.remove();
    }
  }

  clear() {
    clearChildren(this.container);
  }

  scrollToBottom() {
    this.container.scrollTop = this.container.scrollHeight;
  }

  getMessages() {
    return Array.from(this.container.querySelectorAll('.message:not(.thinking)'));
  }
}
