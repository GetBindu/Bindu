import React, { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useForm } from 'react-hook-form'
import { 
  ExternalLink, 
  DollarSign, 
  Target, 
  Clock, 
  MessageSquare,
  Play,
  Sparkles,
  ArrowRight,
  AlertCircle,
  Settings,
  Zap,
  Palette,
  Globe
} from 'lucide-react'
import useNegotiationStore from '../hooks/useNegotiationStore'
import apiService from '../services/api'
import websocketService from '../services/websocket'
import toast from 'react-hot-toast'

const Sidebar = () => {
  const [activeTab, setActiveTab] = useState('negotiate')
  const { 
    isNegotiating, 
    connectionStatus,
    formData,
    updateFormData,
    reset,
    setProduct,
    setMarketAnalysis,
    setSession,
    clearMessages
  } = useNegotiationStore()
  
  const { register, handleSubmit, formState: { errors, isSubmitting }, reset: resetForm } = useForm({
    defaultValues: formData
  })

  const onSubmit = async (data) => {
    try {
      updateFormData(data)
      clearMessages()
      
      const response = await apiService.startNegotiation({
        product_url: data.productUrl,
        target_price: parseInt(data.targetPrice),
        max_budget: parseInt(data.maxBudget),
        approach: data.approach,
        timeline: data.timeline,
        special_requirements: data.specialRequirements || undefined
      })

      if (response.success) {
        setSession(response.session.session_id)
        setProduct(response.product_info)
        setMarketAnalysis(response.market_analysis)
        websocketService.connect(response.session.session_id)
        toast.success('Negotiation started successfully!')
      } else {
        toast.error(response.message || 'Failed to start negotiation')
      }
    } catch (error) {
      console.error('Error starting negotiation:', error)
      toast.error(error.message || 'Failed to start negotiation')
    }
  }

  const startDemo = async () => {
    try {
      clearMessages()
      
      const demoData = {
        product_url: "https://demo.olx.in/laptop-macbook-pro",
        target_price: 75000,
        max_budget: 85000,
        approach: "diplomatic",
        timeline: "flexible",
        special_requirements: "Demo negotiation session"
      }

      const response = await apiService.startDemoNegotiation(demoData)

      if (response.success) {
        setSession(response.session.session_id)
        setProduct(response.product_info)
        setMarketAnalysis(response.market_analysis)
        websocketService.connect(response.session.session_id)
        toast.success('Demo negotiation started!')
      } else {
        toast.error('Failed to start demo')
      }
    } catch (error) {
      console.error('Error starting demo:', error)
      toast.error('Failed to start demo negotiation')
    }
  }

  const handleReset = () => {
    if (window.confirm('Are you sure you want to reset the current session?')) {
      websocketService.disconnect()
      reset()
      resetForm()
      toast.success('Session reset successfully')
    }
  }

  const tabs = [
    { id: 'negotiate', label: 'Negotiate', icon: Zap, color: 'from-primary-500 to-primary-700' },
    { id: 'demo', label: 'Demo', icon: Sparkles, color: 'from-accent-500 to-accent-700' },
  ]

  const getStatusColor = () => {
    switch (connectionStatus) {
      case 'connected': return 'bg-emerald-500'
      case 'connecting': return 'bg-amber-500 animate-pulse'
      case 'error': return 'bg-red-500'
      default: return 'bg-gray-500'
    }
  }

  return (
    <div className="w-96 bg-gradient-to-br from-dark-900 via-dark-800 to-primary-900 text-white flex flex-col border-r border-primary-800/30 shadow-2xl">
      {/* Header with gradient */}
      <div className="relative p-6 border-b border-primary-700/30">
        <div className="absolute inset-0 bg-gradient-to-r from-primary-600/10 to-accent-600/10" />
        
        <div className="relative flex items-center gap-4 mb-4">
          <div className="w-12 h-12 bg-gradient-to-br from-primary-500 to-accent-500 rounded-xl flex items-center justify-center shadow-lg">
            <Settings className="w-6 h-6 text-white" />
          </div>
          <div>
            <h2 className="font-bold text-xl bg-gradient-to-r from-primary-300 to-accent-300 bg-clip-text text-transparent">
              Control Center
            </h2>
            <p className="text-gray-300 text-sm">Configure your AI negotiation</p>
          </div>
        </div>

        {/* Enhanced Status Indicator */}
        <div className="relative flex items-center gap-3 p-3 bg-white/5 rounded-lg border border-white/10 backdrop-blur-sm">
          <div className={`w-3 h-3 rounded-full ${getStatusColor()}`} />
          <span className="capitalize font-medium text-sm">{connectionStatus}</span>
          {connectionStatus === 'connected' && (
            <div className="ml-auto">
              <Globe className="w-4 h-4 text-emerald-400" />
            </div>
          )}
        </div>
      </div>

      {/* Enhanced Tab Navigation */}
      <div className="flex border-b border-primary-700/30 bg-gradient-to-r from-dark-800 to-dark-700">
        {tabs.map(tab => (
          <motion.button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex-1 px-4 py-4 text-sm font-semibold transition-all duration-300 relative overflow-hidden ${
              activeTab === tab.id
                ? 'text-white'
                : 'text-gray-300 hover:text-white'
            }`}
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
          >
            {activeTab === tab.id && (
              <motion.div
                layoutId="activeTab"
                className={`absolute inset-0 bg-gradient-to-r ${tab.color}`}
                initial={false}
                transition={{ type: "spring", stiffness: 500, damping: 30 }}
              />
            )}
            <div className="relative flex items-center justify-center gap-2">
              <tab.icon className="w-4 h-4" />
              {tab.label}
            </div>
          </motion.button>
        ))}
      </div>

      {/* Enhanced Content */}
      <div className="flex-1 overflow-y-auto scrollbar-hide">
        <AnimatePresence mode="wait">
          {activeTab === 'negotiate' && (
            <motion.div
              key="negotiate"
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 20 }}
              transition={{ duration: 0.3 }}
              className="p-6"
            >
              <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
                {/* Product URL */}
                <div className="space-y-2">
                  <label className="flex items-center gap-2 text-sm font-semibold text-primary-200">
                    <ExternalLink className="w-4 h-4" />
                    Product URL
                  </label>
                  <div className="relative">
                    <input
                      type="url"
                      {...register('productUrl', { 
                        required: 'Product URL is required',
                        pattern: {
                          value: /^https?:\/\/.+/,
                          message: 'Please enter a valid URL'
                        }
                      })}
                      className="w-full px-4 py-3 bg-dark-800/50 border border-primary-600/30 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-primary-500 text-white placeholder-gray-400 backdrop-blur-sm transition-all duration-300"
                      placeholder="https://www.olx.in/item/..."
                      disabled={isNegotiating}
                    />
                    {errors.productUrl && (
                      <motion.p 
                        initial={{ opacity: 0, y: -10 }}
                        animate={{ opacity: 1, y: 0 }}
                        className="text-red-400 text-xs mt-2 flex items-center gap-1 bg-red-500/10 px-2 py-1 rounded-lg"
                      >
                        <AlertCircle className="w-3 h-3" />
                        {errors.productUrl.message}
                      </motion.p>
                    )}
                  </div>
                </div>

                {/* Price Inputs */}
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <label className="flex items-center gap-2 text-sm font-semibold text-primary-200">
                      <Target className="w-4 h-4" />
                      Target Price
                    </label>
                    <input
                      type="number"
                      {...register('targetPrice', { 
                        required: 'Target price is required',
                        min: { value: 1, message: 'Price must be greater than 0' }
                      })}
                      className="w-full px-4 py-3 bg-dark-800/50 border border-primary-600/30 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-primary-500 text-white placeholder-gray-400 backdrop-blur-sm transition-all duration-300"
                      placeholder="₹15,000"
                      disabled={isNegotiating}
                    />
                    {errors.targetPrice && (
                      <p className="text-red-400 text-xs">{errors.targetPrice.message}</p>
                    )}
                  </div>

                  <div className="space-y-2">
                    <label className="flex items-center gap-2 text-sm font-semibold text-primary-200">
                      <DollarSign className="w-4 h-4" />
                      Max Budget
                    </label>
                    <input
                      type="number"
                      {...register('maxBudget', { 
                        required: 'Max budget is required',
                        min: { value: 1, message: 'Budget must be greater than 0' }
                      })}
                      className="w-full px-4 py-3 bg-dark-800/50 border border-primary-600/30 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-primary-500 text-white placeholder-gray-400 backdrop-blur-sm transition-all duration-300"
                      placeholder="₹20,000"
                      disabled={isNegotiating}
                    />
                    {errors.maxBudget && (
                      <p className="text-red-400 text-xs">{errors.maxBudget.message}</p>
                    )}
                  </div>
                </div>

                {/* Approach */}
                <div className="space-y-2">
                  <label className="flex items-center gap-2 text-sm font-semibold text-primary-200">
                    <MessageSquare className="w-4 h-4" />
                    Negotiation Style
                  </label>
                  <select
                    {...register('approach')}
                    className="w-full px-4 py-3 bg-dark-800/50 border border-primary-600/30 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-primary-500 text-white backdrop-blur-sm transition-all duration-300"
                    disabled={isNegotiating}
                  >
                    <option value="diplomatic">🤝 Diplomatic - Polite and professional</option>
                    <option value="assertive">💪 Assertive - Direct and confident</option>
                    <option value="considerate">🤗 Considerate - Patient and understanding</option>
                  </select>
                </div>

                {/* Timeline */}
                <div className="space-y-2">
                  <label className="flex items-center gap-2 text-sm font-semibold text-primary-200">
                    <Clock className="w-4 h-4" />
                    Purchase Timeline
                  </label>
                  <select
                    {...register('timeline')}
                    className="w-full px-4 py-3 bg-dark-800/50 border border-primary-600/30 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-primary-500 text-white backdrop-blur-sm transition-all duration-300"
                    disabled={isNegotiating}
                  >
                    <option value="flexible">⏰ Flexible - No rush</option>
                    <option value="week">📅 Within a week</option>
                    <option value="urgent">🚀 Urgent - ASAP</option>
                  </select>
                </div>

                {/* Special Requirements */}
                <div className="space-y-2">
                  <label className="text-sm font-semibold text-primary-200">
                    Special Requirements (Optional)
                  </label>
                  <textarea
                    {...register('specialRequirements')}
                    className="w-full px-4 py-3 bg-dark-800/50 border border-primary-600/30 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-primary-500 text-white placeholder-gray-400 resize-none backdrop-blur-sm transition-all duration-300"
                    rows={3}
                    placeholder="Any specific requirements or preferences..."
                    disabled={isNegotiating}
                  />
                </div>

                {/* Action Buttons */}
                <div className="space-y-3">
                  <motion.button
                    type="submit"
                    disabled={isSubmitting || isNegotiating}
                    className={`w-full px-6 py-4 bg-gradient-to-r from-primary-600 to-accent-600 text-white font-semibold rounded-xl shadow-lg hover:shadow-xl transition-all duration-300 flex items-center justify-center gap-3 ${
                      (isSubmitting || isNegotiating) ? 'opacity-50 cursor-not-allowed' : 'hover:from-primary-500 hover:to-accent-500'
                    }`}
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                  >
                    {isSubmitting ? (
                      <>
                        <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                        Initializing...
                      </>
                    ) : (
                      <>
                        <Play className="w-5 h-5" />
                        Start AI Negotiation
                        <ArrowRight className="w-5 h-5" />
                      </>
                    )}
                  </motion.button>

                  {isNegotiating && (
                    <motion.button
                      type="button"
                      onClick={handleReset}
                      className="w-full px-6 py-3 bg-red-600/20 border border-red-500/30 text-red-400 font-medium rounded-xl hover:bg-red-600/30 transition-all duration-300"
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                    >
                      Reset Session
                    </motion.button>
                  )}
                </div>
              </form>
            </motion.div>
          )}

          {activeTab === 'demo' && (
            <motion.div
              key="demo"
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 20 }}
              transition={{ duration: 0.3 }}
              className="p-6"
            >
              <div className="text-center space-y-6">
                <motion.div 
                  className="w-24 h-24 bg-gradient-to-br from-accent-400 to-primary-600 rounded-2xl flex items-center justify-center mx-auto shadow-2xl"
                  whileHover={{ rotate: 5, scale: 1.05 }}
                  transition={{ type: "spring", stiffness: 300 }}
                >
                  <Sparkles className="w-12 h-12 text-white" />
                </motion.div>
                
                <div>
                  <h3 className="text-2xl font-bold mb-3 bg-gradient-to-r from-accent-300 to-primary-300 bg-clip-text text-transparent">
                    Try Demo Mode
                  </h3>
                  <p className="text-gray-300 text-sm leading-relaxed">
                    Experience NegotiBot AI with a simulated negotiation session. 
                    Perfect for understanding how our AI works without using real product URLs.
                  </p>
                </div>

                <div className="bg-gradient-to-br from-dark-800/50 to-primary-900/50 rounded-xl p-6 text-left border border-primary-700/30 backdrop-blur-sm">
                  <h4 className="font-semibold text-primary-300 mb-4 flex items-center gap-2">
                    <Palette className="w-4 h-4" />
                    Demo Features:
                  </h4>
                  <ul className="text-sm text-gray-300 space-y-3">
                    {[
                      'Realistic AI negotiation simulation',
                      'Advanced response generation',
                      'Market analysis insights',
                      'Real-time chat interface',
                      'Performance analytics'
                    ].map((feature, index) => (
                      <motion.li 
                        key={index}
                        initial={{ opacity: 0, x: -10 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: index * 0.1 }}
                        className="flex items-center gap-3"
                      >
                        <div className="w-2 h-2 bg-gradient-to-r from-primary-400 to-accent-400 rounded-full" />
                        {feature}
                      </motion.li>
                    ))}
                  </ul>
                </div>

                <motion.button
                  onClick={startDemo}
                  disabled={isNegotiating || isSubmitting}
                  className={`w-full px-6 py-4 bg-gradient-to-r from-accent-600 to-primary-600 text-white font-semibold rounded-xl shadow-lg hover:shadow-xl transition-all duration-300 flex items-center justify-center gap-3 ${
                    (isNegotiating || isSubmitting) ? 'opacity-50 cursor-not-allowed' : 'hover:from-accent-500 hover:to-primary-500'
                  }`}
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                >
                  <Sparkles className="w-5 h-5" />
                  Launch Demo Experience
                  <ArrowRight className="w-5 h-5" />
                </motion.button>

                {isNegotiating && (
                  <motion.button
                    onClick={handleReset}
                    className="w-full px-6 py-3 bg-red-600/20 border border-red-500/30 text-red-400 font-medium rounded-xl hover:bg-red-600/30 transition-all duration-300"
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                  >
                    Stop Demo
                  </motion.button>
                )}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  )
}

export default Sidebar