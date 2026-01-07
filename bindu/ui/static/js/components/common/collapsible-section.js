import { querySelectorAll } from '../../utils/dom.js';

export class CollapsibleSection {
  constructor() {
    this.setupSections();
  }

  setupSections() {
    const headers = querySelectorAll('.section-header');
    
    headers.forEach(header => {
      header.addEventListener('click', () => {
        this.toggleSection(header);
      });
    });
  }

  toggleSection(header) {
    const content = header.nextElementSibling;
    const icon = header.querySelector('.toggle-icon');
    
    if (!content || !icon) return;

    if (content.classList.contains('expanded')) {
      content.classList.remove('expanded');
      content.classList.add('collapsed');
      icon.style.transform = 'rotate(-90deg)';
    } else {
      content.classList.remove('collapsed');
      content.classList.add('expanded');
      icon.style.transform = 'rotate(0deg)';
    }
  }
}
