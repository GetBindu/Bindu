import { querySelector } from '../../utils/dom.js';

export class FeedbackModal {
  constructor(modalId) {
    this.modal = querySelector(`#${modalId}`);
    this.taskIdDisplay = querySelector('#feedback-task-id');
    this.ratingSelect = querySelector('#feedback-rating');
    this.feedbackText = querySelector('#feedback-text');
    this.submitBtn = querySelector('.btn-primary', this.modal);
    this.cancelBtn = querySelector('.btn-secondary', this.modal);
    this.closeBtn = querySelector('.modal-close', this.modal);
    
    if (!this.modal) {
      throw new Error(`Feedback modal #${modalId} not found`);
    }

    this.currentTaskId = null;
    this.setupEventListeners();
  }

  setupEventListeners() {
    if (this.submitBtn) {
      this.submitBtn.addEventListener('click', () => this.handleSubmit());
    }

    if (this.cancelBtn) {
      this.cancelBtn.addEventListener('click', () => this.close());
    }

    if (this.closeBtn) {
      this.closeBtn.addEventListener('click', () => this.close());
    }

    this.modal.addEventListener('click', (e) => {
      if (e.target === this.modal) {
        this.close();
      }
    });

    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && this.isOpen()) {
        this.close();
      }
    });

    document.addEventListener('feedback-requested', (e) => {
      this.open(e.detail.taskId);
    });
  }

  open(taskId) {
    this.currentTaskId = taskId;
    
    if (this.taskIdDisplay) {
      this.taskIdDisplay.textContent = taskId;
    }
    
    this.modal.style.display = 'flex';
  }

  close() {
    this.modal.style.display = 'none';
    this.reset();
  }

  reset() {
    this.currentTaskId = null;
    
    if (this.feedbackText) {
      this.feedbackText.value = '';
    }
    
    if (this.ratingSelect) {
      this.ratingSelect.value = '5';
    }
  }

  handleSubmit() {
    if (!this.currentTaskId) return;

    const rating = parseInt(this.ratingSelect?.value || '5', 10);
    const feedback = this.feedbackText?.value.trim() || '';

    const event = new CustomEvent('feedback-submit', {
      detail: {
        taskId: this.currentTaskId,
        rating,
        feedback
      }
    });
    document.dispatchEvent(event);

    this.close();
  }

  isOpen() {
    return this.modal.style.display === 'flex';
  }
}
