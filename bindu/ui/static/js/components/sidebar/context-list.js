import { createElement, createElementWithHTML, clearChildren } from '../../utils/dom.js';
import { formatRelativeTime, formatMessagePreview } from '../../utils/formatters.js';

function getContextColor(index) {
  const colors = ['color-blue', 'color-green', 'color-purple', 'color-orange', 'color-pink', 'color-teal'];
  return colors[index % colors.length];
}

function renderContextItem(ctx, index, activeContextId) {
  const isActive = ctx.id === activeContextId;
  const time = formatRelativeTime(ctx.timestamp || Date.now());
  const preview = formatMessagePreview(ctx.firstMessage || 'New conversation');
  const taskCount = ctx.taskCount || 0;
  const contextShortId = ctx.id.substring(0, 8);
  const colorClass = getContextColor(index);

  const html = `
    <div class="context-item ${isActive ? 'active' : ''}" data-context-id="${ctx.id}">
      <div class="context-header">
        <div class="context-badge ${colorClass}">${contextShortId}</div>
        <div class="context-time">${time}</div>
        <button class="context-clear-btn" data-action="clear" title="Clear context">×</button>
      </div>
      <div class="context-preview">${preview}</div>
      <div class="context-footer">
        <span class="context-tasks">${taskCount} task${taskCount !== 1 ? 's' : ''}</span>
        <span class="context-id-label">Context: ${contextShortId}</span>
      </div>
    </div>
  `;

  return createElementWithHTML('div', '', html).firstChild;
}

export class ContextList {
  constructor(containerId) {
    this.container = document.getElementById(containerId);
    if (!this.container) {
      throw new Error(`Context list container #${containerId} not found`);
    }

    this.setupEventListeners();
  }

  setupEventListeners() {
    this.container.addEventListener('click', (e) => {
      const contextItem = e.target.closest('.context-item');
      if (!contextItem) return;

      const clearBtn = e.target.closest('[data-action="clear"]');
      if (clearBtn) {
        e.stopPropagation();
        const contextId = contextItem.dataset.contextId;
        this.handleClearContext(contextId);
        return;
      }

      const contextId = contextItem.dataset.contextId;
      this.handleSwitchContext(contextId);
    });
  }

  handleSwitchContext(contextId) {
    const event = new CustomEvent('context-switch', { detail: { contextId } });
    document.dispatchEvent(event);
  }

  handleClearContext(contextId) {
    if (confirm('Are you sure you want to clear this context and all its tasks? This action cannot be undone.')) {
      const event = new CustomEvent('context-clear', { detail: { contextId } });
      document.dispatchEvent(event);
    }
  }

  render(contexts, activeContextId = null) {
    clearChildren(this.container);

    if (!contexts || contexts.length === 0) {
      const emptyDiv = createElement('div', 'loading', 'No contexts yet');
      this.container.appendChild(emptyDiv);
      return;
    }

    const sortedContexts = [...contexts].sort((a, b) => 
      (b.timestamp || 0) - (a.timestamp || 0)
    );

    sortedContexts.forEach((ctx, index) => {
      const item = renderContextItem(ctx, index, activeContextId);
      this.container.appendChild(item);
    });
  }

  update(contexts, activeContextId = null) {
    this.render(contexts, activeContextId);
  }
}
