import { ContextList } from './context-list.js';
import { querySelector } from '../../utils/dom.js';

export class ContextSidebar {
  constructor() {
    this.contextList = new ContextList('context-list');
    this.newChatBtn = querySelector('.new-chat-btn');
    
    this.setupEventListeners();
  }

  setupEventListeners() {
    if (this.newChatBtn) {
      this.newChatBtn.addEventListener('click', () => {
        this.handleNewChat();
      });
    }
  }

  handleNewChat() {
    const event = new CustomEvent('context-new');
    document.dispatchEvent(event);
  }

  update(contexts, activeContextId = null) {
    this.contextList.update(contexts, activeContextId);
  }
}
