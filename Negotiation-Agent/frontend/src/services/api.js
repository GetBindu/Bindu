// API Service for NegotiBot
class APIService {
  constructor() {
    this.baseURL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
  }

  async request(endpoint, options = {}) {
    const url = `${this.baseURL}${endpoint}`
    const config = {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    }

    try {
      const response = await fetch(url, config)
      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.message || `HTTP error! status: ${response.status}`)
      }

      return data
    } catch (error) {
      console.error('API request failed:', error)
      throw error
    }
  }

  // Negotiation endpoints
  async startNegotiation(negotiationData) {
    return this.request('/api/negotiate-url', {
      method: 'POST',
      body: JSON.stringify(negotiationData),
    })
  }

  async startDemoNegotiation(demoData) {
    return this.request('/api/demo-negotiate', {
      method: 'POST',
      body: JSON.stringify(demoData),
    })
  }

  async sendSellerResponse(sessionId, message) {
    return this.request('/api/seller-response', {
      method: 'POST',
      body: JSON.stringify({
        session_id: sessionId,
        message: message,
      }),
    })
  }

  async getMarketAnalysis(productData) {
    return this.request('/api/market-analysis', {
      method: 'POST',
      body: JSON.stringify(productData),
    })
  }

  // Session endpoints
  async getSession(sessionId) {
    return this.request(`/api/sessions/${sessionId}`)
  }

  async getAnalytics() {
    return this.request('/api/analytics/performance')
  }

  // Health check
  async healthCheck() {
    return this.request('/api/health')
  }
}

export default new APIService()