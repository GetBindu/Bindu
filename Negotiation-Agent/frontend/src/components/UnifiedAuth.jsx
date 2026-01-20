import React, { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { 
  User, 
  Mail, 
  Lock, 
  UserPlus, 
  LogIn, 
  Eye, 
  EyeOff,
  Shield,
  Zap,
  Users,
  ShoppingBag
} from 'lucide-react'
import toast from 'react-hot-toast'

const UnifiedAuth = ({ onAuthSuccess, userType = 'buyer' }) => {
  const [isLogin, setIsLogin] = useState(true)
  const [showPassword, setShowPassword] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    password: '',
    confirmPassword: '',
    userType: userType // 'buyer' or 'seller'
  })

  const handleInputChange = (e) => {
    setFormData(prev => ({
      ...prev,
      [e.target.name]: e.target.value
    }))
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setIsLoading(true)

    try {
      // Validation
      if (!isLogin && formData.password !== formData.confirmPassword) {
        toast.error('Passwords do not match')
        return
      }

      const endpoint = isLogin ? '/api/auth/login' : '/api/auth/register'
      const payload = isLogin 
        ? { email: formData.email, password: formData.password, user_type: formData.userType }
        : { 
            name: formData.name, 
            email: formData.email, 
            password: formData.password,
            user_type: formData.userType
          }

      const response = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      })

      const data = await response.json()

      if (data.success) {
        toast.success(isLogin ? 'Login successful!' : 'Account created successfully!')
        onAuthSuccess(data.user, data.token)
      } else {
        toast.error(data.message || 'Authentication failed')
      }
    } catch (error) {
      console.error('Auth error:', error)
      toast.error('Network error. Please try again.')
    } finally {
      setIsLoading(false)
    }
  }

  const userTypeConfig = {
    buyer: {
      title: 'Buyer Portal',
      subtitle: 'Smart AI-powered negotiation for better deals',
      icon: ShoppingBag,
      gradient: 'from-primary-600 to-accent-600',
      features: [
        'AI-powered negotiation assistant',
        'Market price analysis',
        'Automated deal hunting',
        'Real-time chat with sellers'
      ]
    },
    seller: {
      title: 'Seller Portal',
      subtitle: 'Manage negotiations and connect with buyers',
      icon: Users,
      gradient: 'from-accent-600 to-primary-600',
      features: [
        'Session-based buyer chat',
        'Negotiation analytics',
        'Deal management tools',
        'Customer insights'
      ]
    }
  }

  const config = userTypeConfig[userType]
  const IconComponent = config.icon

  return (
    <div className="min-h-screen bg-gradient-to-br from-dark-950 via-dark-900 to-primary-950 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Header */}
        <motion.div 
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center mb-8"
        >
          <div className={`w-20 h-20 bg-gradient-to-br ${config.gradient} rounded-2xl flex items-center justify-center mx-auto mb-4 shadow-2xl`}>
            <IconComponent className="w-10 h-10 text-white" />
          </div>
          <h1 className="text-3xl font-bold bg-gradient-to-r from-primary-300 to-accent-300 bg-clip-text text-transparent mb-2">
            {config.title}
          </h1>
          <p className="text-gray-400 text-sm">
            {config.subtitle}
          </p>
        </motion.div>

        {/* Auth Form */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-white/5 backdrop-blur-xl rounded-2xl border border-white/10 shadow-2xl overflow-hidden"
        >
          {/* Tab Switcher */}
          <div className="flex border-b border-white/10">
            <button
              onClick={() => setIsLogin(true)}
              className={`flex-1 px-6 py-4 text-sm font-semibold transition-all duration-300 relative ${
                isLogin ? 'text-white' : 'text-gray-400 hover:text-white'
              }`}
            >
              {isLogin && (
                <motion.div
                  layoutId="authTab"
                  className={`absolute inset-0 bg-gradient-to-r ${config.gradient}`}
                  initial={false}
                  transition={{ type: "spring", stiffness: 500, damping: 30 }}
                />
              )}
              <div className="relative flex items-center justify-center gap-2">
                <LogIn className="w-4 h-4" />
                Sign In
              </div>
            </button>
            <button
              onClick={() => setIsLogin(false)}
              className={`flex-1 px-6 py-4 text-sm font-semibold transition-all duration-300 relative ${
                !isLogin ? 'text-white' : 'text-gray-400 hover:text-white'
              }`}
            >
              {!isLogin && (
                <motion.div
                  layoutId="authTab"
                  className={`absolute inset-0 bg-gradient-to-r ${config.gradient}`}
                  initial={false}
                  transition={{ type: "spring", stiffness: 500, damping: 30 }}
                />
              )}
              <div className="relative flex items-center justify-center gap-2">
                <UserPlus className="w-4 h-4" />
                Sign Up
              </div>
            </button>
          </div>

          {/* Form Content */}
          <div className="p-8">
            <form onSubmit={handleSubmit} className="space-y-6">
              <AnimatePresence mode="wait">
                {!isLogin && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: 'auto' }}
                    exit={{ opacity: 0, height: 0 }}
                    transition={{ duration: 0.3 }}
                  >
                    <div className="relative">
                      <User className="absolute left-4 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
                      <input
                        type="text"
                        name="name"
                        value={formData.name}
                        onChange={handleInputChange}
                        placeholder="Full Name"
                        required={!isLogin}
                        className="w-full pl-12 pr-4 py-4 bg-dark-800/50 border border-primary-600/30 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-primary-500 text-white placeholder-gray-400 backdrop-blur-sm transition-all duration-300"
                      />
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>

              <div className="relative">
                <Mail className="absolute left-4 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
                <input
                  type="email"
                  name="email"
                  value={formData.email}
                  onChange={handleInputChange}
                  placeholder="Email Address"
                  required
                  className="w-full pl-12 pr-4 py-4 bg-dark-800/50 border border-primary-600/30 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-primary-500 text-white placeholder-gray-400 backdrop-blur-sm transition-all duration-300"
                />
              </div>

              <div className="relative">
                <Lock className="absolute left-4 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
                <input
                  type={showPassword ? 'text' : 'password'}
                  name="password"
                  value={formData.password}
                  onChange={handleInputChange}
                  placeholder="Password"
                  required
                  className="w-full pl-12 pr-12 py-4 bg-dark-800/50 border border-primary-600/30 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-primary-500 text-white placeholder-gray-400 backdrop-blur-sm transition-all duration-300"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-4 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-white transition-colors"
                >
                  {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                </button>
              </div>

              <AnimatePresence mode="wait">
                {!isLogin && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: 'auto' }}
                    exit={{ opacity: 0, height: 0 }}
                    transition={{ duration: 0.3 }}
                  >
                    <div className="relative">
                      <Shield className="absolute left-4 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
                      <input
                        type="password"
                        name="confirmPassword"
                        value={formData.confirmPassword}
                        onChange={handleInputChange}
                        placeholder="Confirm Password"
                        required={!isLogin}
                        className="w-full pl-12 pr-4 py-4 bg-dark-800/50 border border-primary-600/30 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-primary-500 text-white placeholder-gray-400 backdrop-blur-sm transition-all duration-300"
                      />
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>

              <motion.button
                type="submit"
                disabled={isLoading}
                className={`w-full px-6 py-4 bg-gradient-to-r ${config.gradient} text-white font-semibold rounded-xl shadow-lg hover:shadow-xl transition-all duration-300 flex items-center justify-center gap-3 ${
                  isLoading ? 'opacity-50 cursor-not-allowed' : 'hover:scale-[1.02]'
                }`}
                whileTap={{ scale: 0.98 }}
              >
                {isLoading ? (
                  <>
                    <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    Processing...
                  </>
                ) : (
                  <>
                    {isLogin ? <LogIn className="w-5 h-5" /> : <UserPlus className="w-5 h-5" />}
                    {isLogin ? 'Sign In' : 'Create Account'}
                    <Zap className="w-5 h-5" />
                  </>
                )}
              </motion.button>
            </form>
          </div>

          {/* Features List */}
          <div className="border-t border-white/10 p-6 bg-white/5">
            <h4 className="font-semibold text-primary-300 mb-3 text-sm">What you get:</h4>
            <ul className="space-y-2">
              {config.features.map((feature, index) => (
                <motion.li
                  key={index}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: index * 0.1 }}
                  className="flex items-center gap-2 text-xs text-gray-300"
                >
                  <div className="w-1.5 h-1.5 bg-gradient-to-r from-primary-400 to-accent-400 rounded-full" />
                  {feature}
                </motion.li>
              ))}
            </ul>
          </div>
        </motion.div>

        {/* Footer */}
        <motion.p 
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.5 }}
          className="text-center text-gray-500 text-xs mt-6"
        >
          Secure authentication powered by NegotiBot AI
        </motion.p>
      </div>
    </div>
  )
}

export default UnifiedAuth