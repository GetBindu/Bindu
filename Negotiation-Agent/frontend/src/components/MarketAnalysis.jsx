import React from 'react'
import { motion } from 'framer-motion'
import { 
  BarChart3, 
  TrendingUp, 
  TrendingDown, 
  Minus,
  DollarSign,
  Target,
  Activity
} from 'lucide-react'

const MarketAnalysis = ({ analysis }) => {
  if (!analysis) return null

  const getTrendIcon = (trend) => {
    switch (trend?.toLowerCase()) {
      case 'increasing':
      case 'up':
        return <TrendingUp className="w-4 h-4 text-green-500" />
      case 'decreasing':
      case 'down':
        return <TrendingDown className="w-4 h-4 text-red-500" />
      case 'stable':
      default:
        return <Minus className="w-4 h-4 text-gray-500" />
    }
  }

  const getTrendColor = (trend) => {
    switch (trend?.toLowerCase()) {
      case 'increasing':
      case 'up':
        return 'text-green-600 bg-green-50 border-green-200'
      case 'decreasing':
      case 'down':
        return 'text-red-600 bg-red-50 border-red-200'
      case 'stable':
      default:
        return 'text-gray-600 bg-gray-50 border-gray-200'
    }
  }

  return (
    <motion.div
      className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay: 0.1 }}
    >
      <div className="p-6">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-12 h-12 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-xl flex items-center justify-center">
            <BarChart3 className="w-6 h-6 text-white" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-gray-900">Market Analysis</h3>
            <p className="text-sm text-gray-600">Real-time marketplace intelligence</p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Average Price */}
          {analysis.average_price && (
            <div className="bg-blue-50 rounded-lg p-4 border border-blue-200">
              <div className="flex items-center gap-2 mb-2">
                <DollarSign className="w-5 h-5 text-blue-600" />
                <h4 className="font-medium text-blue-900">Average Price</h4>
              </div>
              <div className="text-2xl font-bold text-blue-900">
                ₹{analysis.average_price.toLocaleString()}
              </div>
              <p className="text-sm text-blue-700 mt-1">
                Market standard pricing
              </p>
            </div>
          )}

          {/* Price Range */}
          {analysis.price_range && (
            <div className="bg-purple-50 rounded-lg p-4 border border-purple-200">
              <div className="flex items-center gap-2 mb-2">
                <Target className="w-5 h-5 text-purple-600" />
                <h4 className="font-medium text-purple-900">Price Range</h4>
              </div>
              <div className="space-y-1">
                <div className="text-lg font-bold text-purple-900">
                  ₹{analysis.price_range.min?.toLocaleString()} - ₹{analysis.price_range.max?.toLocaleString()}
                </div>
                <div className="text-sm text-purple-700">
                  Min to max market prices
                </div>
              </div>
            </div>
          )}

          {/* Market Trend */}
          <div className={`rounded-lg p-4 border ${getTrendColor(analysis.market_trend)}`}>
            <div className="flex items-center gap-2 mb-2">
              {getTrendIcon(analysis.market_trend)}
              <h4 className="font-medium">Market Trend</h4>
            </div>
            <div className="text-lg font-bold capitalize">
              {analysis.market_trend || 'Stable'}
            </div>
            <p className="text-sm mt-1 opacity-80">
              Current market direction
            </p>
          </div>
        </div>

        {/* Additional Insights */}
        {(analysis.demand_level || analysis.competition_level || analysis.seasonal_factor) && (
          <div className="mt-6 pt-4 border-t border-gray-200">
            <h4 className="font-medium text-gray-900 mb-3 flex items-center gap-2">
              <Activity className="w-5 h-5 text-gray-600" />
              Market Insights
            </h4>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {analysis.demand_level && (
                <div className="text-center p-3 bg-gray-50 rounded-lg">
                  <div className="text-sm font-medium text-gray-900">Demand Level</div>
                  <div className="text-lg font-bold text-gray-700 capitalize mt-1">
                    {analysis.demand_level}
                  </div>
                </div>
              )}
              
              {analysis.competition_level && (
                <div className="text-center p-3 bg-gray-50 rounded-lg">
                  <div className="text-sm font-medium text-gray-900">Competition</div>
                  <div className="text-lg font-bold text-gray-700 capitalize mt-1">
                    {analysis.competition_level}
                  </div>
                </div>
              )}
              
              {analysis.seasonal_factor && (
                <div className="text-center p-3 bg-gray-50 rounded-lg">
                  <div className="text-sm font-medium text-gray-900">Seasonal Factor</div>
                  <div className="text-lg font-bold text-gray-700 capitalize mt-1">
                    {analysis.seasonal_factor}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Recommendations */}
        {analysis.recommendations && analysis.recommendations.length > 0 && (
          <div className="mt-6 pt-4 border-t border-gray-200">
            <h4 className="font-medium text-gray-900 mb-3">AI Recommendations</h4>
            <div className="space-y-2">
              {analysis.recommendations.map((recommendation, index) => (
                <div
                  key={index}
                  className="flex items-start gap-2 p-3 bg-green-50 rounded-lg border border-green-200"
                >
                  <div className="w-1.5 h-1.5 bg-green-500 rounded-full mt-2 flex-shrink-0" />
                  <span className="text-sm text-green-800">{recommendation}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Analysis Timestamp */}
        <div className="mt-4 pt-4 border-t border-gray-200">
          <div className="text-xs text-gray-500 flex items-center justify-between">
            <span>Analysis updated: {new Date().toLocaleString()}</span>
            <span className="flex items-center gap-1">
              <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
              Live data
            </span>
          </div>
        </div>
      </div>
    </motion.div>
  )
}

export default MarketAnalysis