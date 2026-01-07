import { querySelectorAll } from '../../utils/dom.js';

export class Tabs {
  constructor() {
    this.tabButtons = querySelectorAll('.tab');
    this.tabContents = querySelectorAll('.tab-content');
    
    this.setupEventListeners();
  }

  setupEventListeners() {
    this.tabButtons.forEach(button => {
      button.addEventListener('click', (e) => {
        const tabName = this.getTabName(button);
        if (tabName) {
          this.switchTab(tabName, button);
        }
      });
    });
  }

  getTabName(button) {
    const onclick = button.getAttribute('onclick');
    if (onclick) {
      const match = onclick.match(/switchTab\('([^']+)'\)/);
      return match ? match[1] : null;
    }
    return button.dataset.tab;
  }

  switchTab(tabName, clickedButton) {
    this.tabButtons.forEach(tab => tab.classList.remove('active'));
    clickedButton.classList.add('active');

    this.tabContents.forEach(content => content.classList.remove('active'));
    const targetContent = document.getElementById(tabName);
    if (targetContent) {
      targetContent.classList.add('active');
    }

    const event = new CustomEvent('tab-switched', { detail: { tabName } });
    document.dispatchEvent(event);
  }
}
