import { querySelector } from '../../utils/dom.js';
import { sanitizeInput } from '../../utils/validators.js';
import { CONFIG } from '../../config.js';

export class MessageInput {
  constructor(inputId, buttonId) {
    this.input = querySelector(`#${inputId}`);
    this.button = querySelector(`#${buttonId}`);
    
    if (!this.input || !this.button) {
      throw new Error('Message input or button not found');
    }

    this.setupEventListeners();
  }

  setupEventListeners() {
    this.input.addEventListener('keypress', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        this.handleSend();
      }
    });

    this.button.addEventListener('click', () => {
      this.handleSend();
    });
  }

  handleSend() {
    const text = this.getValue();
    if (!text) return;

    this.clear();
    this.setDisabled(true);

    const event = new CustomEvent('message-send', { 
      detail: { text } 
    });
    document.dispatchEvent(event);
  }

  getValue() {
    return sanitizeInput(this.input.value, CONFIG.UI.MAX_MESSAGE_LENGTH);
  }

  setValue(value) {
    this.input.value = value;
  }

  clear() {
    this.input.value = '';
  }

  focus() {
    this.input.focus();
  }

  setDisabled(disabled) {
    this.button.disabled = disabled;
    this.input.disabled = disabled;
  }
}
