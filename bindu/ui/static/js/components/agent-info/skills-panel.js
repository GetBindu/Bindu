import { querySelector } from '../../utils/dom.js';
import { truncateText } from '../../utils/formatters.js';

const SKILL_ICONS = {
  'question-answering': '💬',
  'pdf-processing': '📄',
  'text-generation': '✍️',
  'image-generation': '🎨',
  'code-generation': '💻',
  'data-analysis': '📊',
  'translation': '🌐',
  'summarization': '📝'
};

export class SkillsPanel {
  constructor(containerId) {
    this.container = querySelector(`#${containerId}`);
    if (!this.container) {
      throw new Error(`Skills panel container #${containerId} not found`);
    }
  }

  render(skills) {
    if (!skills || skills.length === 0) {
      this.container.innerHTML = '<div style="color: #9ca3af; font-size: 11px;">No skills available</div>';
      return;
    }

    const html = skills.map(skill => {
      const skillName = skill.name || skill.id || 'Unknown Skill';
      const icon = SKILL_ICONS[skillName] || SKILL_ICONS[skill.id] || '⚡';
      const description = skill.description || '';
      const truncatedDesc = truncateText(description, 60);

      return `
        <div class="skill-item" data-skill-id="${skill.id}">
          <div class="skill-header">
            <span class="skill-icon">${icon}</span>
            <span class="skill-name">${skillName}</span>
          </div>
          ${truncatedDesc ? `<div class="skill-description">${truncatedDesc}</div>` : ''}
        </div>
      `;
    }).join('');

    this.container.innerHTML = html;

    this.container.querySelectorAll('.skill-item').forEach(item => {
      item.addEventListener('click', () => {
        const skillId = item.dataset.skillId;
        const event = new CustomEvent('skill-details-requested', { detail: { skillId } });
        document.dispatchEvent(event);
      });
    });
  }
}
