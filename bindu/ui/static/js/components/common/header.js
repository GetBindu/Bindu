import { querySelector } from '../../utils/dom.js';

export class Header {
  constructor() {
    this.nameElement = querySelector('#agent-name-header');
    this.subtitleElement = querySelector('#agent-subtitle');
    this.metadataElement = querySelector('#agent-metadata');
    this.paywallBadge = querySelector('#paywall-badge');
    this.authButton = querySelector('.auth-settings-btn');
    
    this.setupEventListeners();
  }

  setupEventListeners() {
    if (this.authButton) {
      this.authButton.addEventListener('click', () => {
        const event = new CustomEvent('auth-settings-requested');
        document.dispatchEvent(event);
      });
    }
  }

  updateAgentInfo(manifest) {
    if (!manifest) return;

    if (this.nameElement) {
      this.nameElement.textContent = manifest.name || 'Bindu Agent';
    }

    if (this.subtitleElement) {
      this.subtitleElement.textContent = manifest.description || 'A Bindu agent';
    }

    if (this.metadataElement) {
      this.updateMetadata(manifest);
    }
  }

  updateMetadata(manifest) {
    let urlWithPort = manifest.url || manifest.uri || window.location.origin;
    urlWithPort = urlWithPort.replace(/^https?:\/\//, '').split('/')[0];

    const binduVersion = manifest.bindu_version || manifest.metadata?.bindu_version || '0.1.0';

    const hasPaywall = manifest.capabilities?.extensions?.some(ext =>
      ext.uri?.includes('x402') || ext.uri?.includes('payment')
    ) || manifest.execution_cost || manifest.paymentRequired;

    const requiresAuth = manifest.auth?.enabled ||
      manifest.authentication_required ||
      manifest.capabilities?.authentication ||
      manifest.security?.authentication_required;

    this.metadataElement.innerHTML = `
      <span class="metadata-badge">Bindu v${binduVersion}</span>
      <span class="metadata-badge">Protocol v${manifest.protocolVersion || '0.2.5'}</span>
      <span class="metadata-badge">${urlWithPort}</span>
    `;

    if (this.paywallBadge && (hasPaywall || requiresAuth)) {
      let badgeText = '';
      if (hasPaywall && requiresAuth) {
        badgeText = '💰🔐 Paid + Auth';
      } else if (hasPaywall) {
        badgeText = '💰 Behind Paywall';
      } else if (requiresAuth) {
        badgeText = '🔐 Behind Auth';
      }
      this.paywallBadge.textContent = badgeText;
      this.paywallBadge.style.display = 'inline-block';
    }
  }
}
