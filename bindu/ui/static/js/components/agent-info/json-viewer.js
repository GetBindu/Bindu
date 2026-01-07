import { querySelector } from '../../utils/dom.js';

export class JSONViewer {
  constructor(containerId, copyButtonId) {
    this.container = querySelector(`#${containerId}`);
    this.copyButton = querySelector(`#${copyButtonId}` || `.${copyButtonId}`);
    
    if (!this.container) {
      throw new Error(`JSON viewer container #${containerId} not found`);
    }

    if (this.copyButton) {
      this.setupCopyButton();
    }

    this.data = null;
  }

  setupCopyButton() {
    this.copyButton.addEventListener('click', () => {
      this.copyJSON();
    });
  }

  render(data) {
    this.data = data;
    
    if (!data) {
      this.container.textContent = 'No data available';
      return;
    }

    const jsonString = JSON.stringify(data, null, 2);
    this.container.textContent = jsonString;
  }

  copyJSON() {
    if (!this.data) return;

    const jsonString = JSON.stringify(this.data, null, 2);
    navigator.clipboard.writeText(jsonString).then(() => {
      if (this.copyButton) {
        const originalText = this.copyButton.textContent;
        this.copyButton.textContent = '✓ Copied!';
        setTimeout(() => {
          this.copyButton.textContent = originalText;
        }, 2000);
      }
    }).catch(err => {
      console.error('Failed to copy:', err);
    });
  }
}
