import { create } from 'zustand'

const useNegotiationStore = create((set, get) => ({
  // Connection state
  isConnected: false,
  connectionStatus: 'disconnected', // disconnected, connecting, connected, error
  
  // Session state
  sessionId: null,
  isNegotiating: false,
  
  // Product data
  product: null,
  marketAnalysis: null,
  
  // Messages
  messages: [],
  
  // Form data
  formData: {
    productUrl: '',
    targetPrice: '',
    maxBudget: '',
    approach: 'diplomatic',
    timeline: 'flexible',
    specialRequirements: ''
  },
  
  // Actions
  setConnectionStatus: (status) => set({ connectionStatus: status }),
  setIsConnected: (connected) => set({ isConnected: connected }),
  
  setSession: (sessionId) => set({ sessionId }),
  setIsNegotiating: (negotiating) => set({ isNegotiating: negotiating }),
  
  setProduct: (product) => set({ product }),
  setMarketAnalysis: (analysis) => set({ marketAnalysis: analysis }),
  
  addMessage: (message) => set((state) => ({ 
    messages: [...state.messages, { ...message, id: Date.now() }] 
  })),
  clearMessages: () => set({ messages: [] }),
  
  updateFormData: (updates) => set((state) => ({
    formData: { ...state.formData, ...updates }
  })),
  resetFormData: () => set({
    formData: {
      productUrl: '',
      targetPrice: '',
      maxBudget: '',
      approach: 'diplomatic',
      timeline: 'flexible',
      specialRequirements: ''
    }
  }),
  
  // Reset all state
  reset: () => set({
    isConnected: false,
    connectionStatus: 'disconnected',
    sessionId: null,
    isNegotiating: false,
    product: null,
    marketAnalysis: null,
    messages: [],
  }),
}))

export default useNegotiationStore