import { querySelector } from '../../utils/dom.js';

function copyToClipboard(text, button) {
  navigator.clipboard.writeText(text).then(() => {
    const originalText = button.textContent;
    button.textContent = '✓';
    setTimeout(() => {
      button.textContent = originalText;
    }, 1500);
  }).catch(err => {
    console.error('Failed to copy:', err);
  });
}

export class DIDIdentity {
  constructor(containerId) {
    this.container = querySelector(`#${containerId}`);
    if (!this.container) {
      throw new Error(`DID identity container #${containerId} not found`);
    }
  }

  render(didDocument) {
    if (!didDocument) {
      this.container.innerHTML = '<div style="color: #9ca3af; text-align: center; padding: 12px;">DID information not available</div>';
      return;
    }

    const authKey = didDocument.authentication?.[0];

    const html = `
      <table class="did-table">
        <tr>
          <td>DID</td>
          <td>
            <div class="did-value-with-copy">
              <div class="did-value">${didDocument.id || 'N/A'}</div>
              <button class="copy-inline-btn" data-copy="${didDocument.id}" title="Copy DID">📋</button>
            </div>
          </td>
        </tr>
        ${authKey ? `
          <tr>
            <td>Public Key</td>
            <td>
              <div class="did-value-with-copy">
                <div class="did-value">${authKey.publicKeyBase58 || 'N/A'}</div>
                <button class="copy-inline-btn" data-copy="${authKey.publicKeyBase58}" title="Copy Public Key">📋</button>
              </div>
            </td>
          </tr>
        ` : ''}
      </table>
    `;

    this.container.innerHTML = html;

    this.container.querySelectorAll('[data-copy]').forEach(btn => {
      btn.addEventListener('click', () => {
        copyToClipboard(btn.dataset.copy, btn);
      });
    });
  }
}
