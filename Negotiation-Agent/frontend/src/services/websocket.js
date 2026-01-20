// WebSocket Service for real-time communication
import useNegotiationStore from '../hooks/useNegotiationStore'
import toast from 'react-hot-toast'

class WebSocketService {
  constructor() {
    this.ws = null
    this.sessionId = null
    this.reconnectAttempts = 0
    this.maxReconnectAttempts = 5
    this.reconnectDelay = 1000
  }

  connect(sessionId) {
    if (this.ws) {
      this.disconnect()
    }

    this.sessionId = sessionId
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = `${protocol}//${window.location.host}/ws/user/${sessionId}`

    try {
      useNegotiationStore.getState().setConnectionStatus('connecting')
      
      this.ws = new WebSocket(wsUrl)
      
      this.ws.onopen = () => {
        console.log('WebSocket connected')
        useNegotiationStore.getState().setConnectionStatus('connected')
        useNegotiationStore.getState().setIsConnected(true)
        this.reconnectAttempts = 0
        toast.success('Connected to negotiation session')
      }

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          this.handleMessage(data)
        } catch (error) {
          console.error('Error parsing WebSocket message:', error)
        }
      }

      this.ws.onclose = (event) => {
        console.log('WebSocket disconnected', event.code, event.reason)
        useNegotiationStore.getState().setConnectionStatus('disconnected')
        useNegotiationStore.getState().setIsConnected(false)
        
        if (!event.wasClean && this.reconnectAttempts < this.maxReconnectAttempts) {
          this.attemptReconnect()
        }
      }

      this.ws.onerror = (error) => {
        console.error('WebSocket error:', error)
        useNegotiationStore.getState().setConnectionStatus('error')
        toast.error('Connection error occurred')
      }

    } catch (error) {
      console.error('Failed to create WebSocket connection:', error)
      useNegotiationStore.getState().setConnectionStatus('error')
      toast.error('Failed to connect')
    }
  }

  handleMessage(data) {
    const store = useNegotiationStore.getState()

    switch (data.type) {
      case 'negotiation_update':
        store.addMessage({
          type: 'ai',
          content: data.message,
          timestamp: new Date(),
          phase: data.phase,
          strategy: data.strategy
        })
        break

      case 'seller_message':
        store.addMessage({
          type: 'seller',
          content: data.message,
          timestamp: new Date()
        })
        break

      case 'negotiation_complete':
        store.setIsNegotiating(false)
        store.addMessage({
          type: 'system',
          content: data.message,
          timestamp: new Date(),
          success: data.success,
          finalPrice: data.final_price
        })
        
        if (data.success) {
          toast.success(`Negotiation successful! Final price: ₹${data.final_price}`)
        } else {
          toast.error('Negotiation was not successful')
        }
        break

      case 'price_update':
        store.addMessage({
          type: 'price_update',
          content: `Price updated to ₹${data.price}`,
          timestamp: new Date(),
          price: data.price
        })
        break

      case 'status_update':
        if (data.status === 'connected') {
          store.setIsNegotiating(true)
        }
        break

      case 'error':
        console.error('WebSocket error:', data.message)
        toast.error(data.message || 'An error occurred')
        break

      default:
        console.log('Unknown message type:', data.type)
    }
  }

  sendMessage(message) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message))
    } else {
      console.error('WebSocket is not connected')
      toast.error('Connection lost. Please try again.')
    }
  }

  attemptReconnect() {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      toast.error('Failed to reconnect. Please refresh the page.')
      return
    }

    this.reconnectAttempts++
    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1)
    
    toast.loading(`Reconnecting... (${this.reconnectAttempts}/${this.maxReconnectAttempts})`)
    
    setTimeout(() => {
      if (this.sessionId) {
        this.connect(this.sessionId)
      }
    }, delay)
  }

  disconnect() {
    if (this.ws) {
      this.ws.close(1000, 'User disconnected')
      this.ws = null
    }
    this.sessionId = null
    this.reconnectAttempts = 0
    useNegotiationStore.getState().setIsConnected(false)
    useNegotiationStore.getState().setConnectionStatus('disconnected')
  }
}

export default new WebSocketService()