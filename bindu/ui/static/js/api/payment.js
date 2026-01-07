import { apiClient } from './client.js';
import { CONFIG } from '../config.js';
import { store } from '../state/store.js';

export async function startPaymentSession() {
  return await apiClient.request(CONFIG.ENDPOINTS.PAYMENT_SESSION, {
    method: 'POST'
  });
}

export async function getPaymentStatus(sessionId) {
  return await apiClient.request(`${CONFIG.ENDPOINTS.PAYMENT_STATUS}/${sessionId}`);
}

export async function handlePaymentFlow() {
  try {
    const sessionData = await startPaymentSession();
    const { session_id, browser_url } = sessionData;
    
    if (!browser_url) {
      throw new Error('No payment URL received');
    }
    
    const paymentWindow = window.open(browser_url, '_blank', 'width=600,height=800');
    
    if (!paymentWindow) {
      throw new Error('Popup blocked - please allow popups to complete payment');
    }
    
    const maxAttempts = 60;
    const pollInterval = 5000;
    let attempts = 0;
    
    while (attempts < maxAttempts) {
      await new Promise(resolve => setTimeout(resolve, pollInterval));
      attempts++;
      
      try {
        const statusData = await getPaymentStatus(session_id);
        
        if (statusData.status === 'completed' && statusData.payment_token) {
          if (paymentWindow && !paymentWindow.closed) {
            paymentWindow.close();
          }
          
          const cleanToken = statusData.payment_token.trim();
          if (!/^[\x00-\x7F]*$/.test(cleanToken)) {
            throw new Error('Payment token contains non-ASCII characters');
          }
          
          store.setState({ paymentToken: cleanToken });
          
          return {
            success: true,
            token: cleanToken
          };
        }
        
        if (statusData.status === 'failed') {
          throw new Error(statusData.error || 'Payment failed');
        }
      } catch (error) {
        if (attempts >= maxAttempts) {
          throw error;
        }
      }
    }
    
    throw new Error('Payment timeout - please try again');
    
  } catch (error) {
    console.error('Payment error:', error);
    throw error;
  }
}

export function clearPaymentToken() {
  store.setState({ paymentToken: null });
}

export function getPaymentToken() {
  const state = store.getState();
  return state.paymentToken;
}
