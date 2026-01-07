import { querySelector } from '../../utils/dom.js';
import { getSkillDetails } from '../../api/agent.js';

export class SkillModal {
  constructor(modalId) {
    this.modal = querySelector(`#${modalId}`);
    this.modalTitle = querySelector('#skill-modal-title');
    this.modalBody = querySelector('#skill-modal-body');
    this.closeBtn = querySelector('.skill-modal-close', this.modal);
    
    if (!this.modal) {
      throw new Error(`Skill modal #${modalId} not found`);
    }

    this.setupEventListeners();
  }

  setupEventListeners() {
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

    document.addEventListener('skill-details-requested', (e) => {
      this.open(e.detail.skillId);
    });
  }

  async open(skillId) {
    this.modal.style.display = 'flex';
    this.modalBody.innerHTML = '<div class="loading">Loading skill details...</div>';
    this.modalTitle.textContent = 'Skill Details';

    try {
      const skillData = await getSkillDetails(skillId);
      this.renderSkillDetails(skillData);
    } catch (error) {
      console.error('Error loading skill details:', error);
      this.modalBody.innerHTML = '<div class="error" style="display:block;">Failed to load skill details</div>';
    }
  }

  renderSkillDetails(skill) {
    this.modalTitle.textContent = skill.name || skill.id;

    const html = `
      <div class="skill-detail-section">
        <h3>Description</h3>
        <p>${skill.description || 'No description available'}</p>
      </div>

      ${skill.tags && skill.tags.length > 0 ? `
        <div class="skill-detail-section">
          <h3>Tags</h3>
          <div class="skill-tags">
            ${skill.tags.map(tag => `<span class="skill-tag">${tag}</span>`).join('')}
          </div>
        </div>
      ` : ''}

      ${skill.examples && skill.examples.length > 0 ? `
        <div class="skill-detail-section">
          <h3>Example Queries</h3>
          <ul class="skill-examples">
            ${skill.examples.map(ex => `<li>"${ex}"</li>`).join('')}
          </ul>
        </div>
      ` : ''}

      ${skill.input_modes && skill.input_modes.length > 0 ? `
        <div class="skill-detail-section">
          <h3>Input Modes</h3>
          <p>${skill.input_modes.join(', ')}</p>
        </div>
      ` : ''}

      ${skill.output_modes && skill.output_modes.length > 0 ? `
        <div class="skill-detail-section">
          <h3>Output Modes</h3>
          <p>${skill.output_modes.join(', ')}</p>
        </div>
      ` : ''}

      ${skill.version ? `
        <div class="skill-detail-section">
          <h3>Version</h3>
          <p>${skill.version}</p>
        </div>
      ` : ''}

      ${skill.performance ? `
        <div class="skill-detail-section">
          <h3>Performance</h3>
          <p>Avg Processing Time: ${skill.performance.avg_processing_time_ms}ms</p>
          <p>Max Concurrent Requests: ${skill.performance.max_concurrent_requests}</p>
        </div>
      ` : ''}
    `;

    this.modalBody.innerHTML = html;
  }

  close() {
    this.modal.style.display = 'none';
  }

  isOpen() {
    return this.modal.style.display === 'flex';
  }
}
