import { querySelector, createElementWithHTML } from '../../utils/dom.js';

export class AgentOverview {
  constructor(containerId) {
    this.container = querySelector(`#${containerId}`);
    if (!this.container) {
      throw new Error(`Agent overview container #${containerId} not found`);
    }
  }

  render(manifest) {
    if (!manifest) {
      this.container.innerHTML = '<div class="error" style="display:block;">Failed to load agent information</div>';
      return;
    }

    const didExtension = manifest.capabilities?.extensions?.find(ext => ext.uri?.startsWith('did:'));
    const author = didExtension?.params?.author || 'Unknown';

    const html = `
      <table class="info-table">
        <tr>
          <td>Author</td>
          <td>${author}</td>
        </tr>
        <tr>
          <td>Version</td>
          <td>${manifest.version || 'N/A'}</td>
        </tr>
        ${manifest.url ? `
          <tr>
            <td>URL</td>
            <td>${manifest.url}</td>
          </tr>
        ` : ''}
        ${manifest.protocolVersion ? `
          <tr>
            <td>Protocol</td>
            <td>${manifest.protocolVersion}</td>
          </tr>
        ` : ''}
        ${manifest.capabilities?.streaming ? `
          <tr>
            <td>Streaming</td>
            <td>✓ Supported</td>
          </tr>
        ` : ''}
      </table>
    `;

    this.container.innerHTML = html;
  }
}
