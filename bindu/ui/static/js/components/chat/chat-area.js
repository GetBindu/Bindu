import { MessageList } from './message-list.js';
import { MessageInput } from './message-input.js';
import { querySelector } from '../../utils/dom.js';

export class ChatArea {
  constructor() {
    this.messageList = new MessageList('chat-messages');
    this.messageInput = new MessageInput('message-input', 'send-button');
    this.replyIndicator = querySelector('#reply-indicator');
    this.replyText = querySelector('#reply-text');
    this.contextIndicator = querySelector('#context-indicator-text');
    this.errorDisplay = querySelector('#chat-error');
    
    this.currentReplyTo = null;
    
    this.setupEventListeners();
  }

  setupEventListeners() {
    document.addEventListener('message-send', (e) => {
      this.handleMessageSend(e.detail.text);
    });

    document.addEventListener('reply-requested', (e) => {
      this.setReplyTo(e.detail.taskId);
    });

    const closeReplyBtn = querySelector('.reply-close');
    if (closeReplyBtn) {
      closeReplyBtn.addEventListener('click', () => this.clearReply());
    }
  }

  handleMessageSend(text) {
    const event = new CustomEvent('chat-message-send', {
      detail: { 
        text,
        replyToTaskId: this.currentReplyTo
      }
    });
    document.dispatchEvent(event);
  }

  addMessage(content, sender, taskId = null, state = null) {
    this.messageList.addMessage(content, sender, taskId, state);
  }

  addThinkingIndicator(taskId = null) {
    this.messageList.addThinkingIndicator(taskId);
  }

  removeThinkingIndicator() {
    this.messageList.removeThinkingIndicator();
  }

  clearMessages() {
    this.messageList.clear();
  }

  setReplyTo(taskId) {
    this.currentReplyTo = taskId;
    if (this.replyText) {
      this.replyText.textContent = `💬 Replying to task: ${taskId.substring(0, 8)}...`;
    }
    if (this.replyIndicator) {
      this.replyIndicator.classList.add('visible');
    }
    this.messageInput.focus();
  }

  clearReply() {
    this.currentReplyTo = null;
    if (this.replyIndicator) {
      this.replyIndicator.classList.remove('visible');
    }
  }

  updateContextIndicator(contextId) {
    if (!this.contextIndicator) return;
    
    if (contextId) {
      const shortId = contextId.substring(0, 8);
      this.contextIndicator.textContent = `Active Context: ${shortId}`;
    } else {
      this.contextIndicator.textContent = 'No active context - Start a new conversation';
    }
  }

  showError(message) {
    if (!this.errorDisplay) return;
    
    this.errorDisplay.textContent = message;
    this.errorDisplay.style.display = 'block';
    
    setTimeout(() => {
      this.errorDisplay.style.display = 'none';
    }, 5000);
  }

  enableInput() {
    this.messageInput.setDisabled(false);
  }

  disableInput() {
    this.messageInput.setDisabled(true);
  }
}
