/**
 * Payment Handler for X402 Protocol
 * Handles payment sessions and token management for agents requiring payment
 */

const AGENT_BASE_URL = 'http://localhost:3773';

// Payment state
let paymentToken: string | null = null;

/**
 * Handle 402 Payment Required response
 * Opens payment window, polls for completion, returns payment token
 */
export async function handlePaymentRequired(
	onStatusUpdate?: (message: string) => void
): Promise<boolean> {
	try {
		onStatusUpdate?.('💳 Payment required - starting payment session...');

		// Start payment session (no auth required - public endpoint)
		const sessionResponse = await fetch(`${AGENT_BASE_URL}/api/start-payment-session`, {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json'
			}
		});

		if (!sessionResponse.ok) {
			throw new Error('Failed to start payment session');
		}

		const sessionData = await sessionResponse.json();
		const { session_id, browser_url } = sessionData;

		onStatusUpdate?.('🌐 Opening payment page...');

		// Open payment page in new window
		const paymentWindow = window.open(browser_url, '_blank', 'width=600,height=800');

		if (!paymentWindow) {
			onStatusUpdate?.('❌ Please allow popups to complete payment');
			return false;
		}

		onStatusUpdate?.('⏳ Waiting for payment confirmation...');

		// Poll for payment completion
		const maxAttempts = 60; // 5 minutes (5 second intervals)
		let attempts = 0;

		while (attempts < maxAttempts) {
			await new Promise((resolve) => setTimeout(resolve, 5000)); // Wait 5 seconds
			attempts++;

			const statusResponse = await fetch(`${AGENT_BASE_URL}/api/payment-status/${session_id}`);

			if (!statusResponse.ok) continue;

			const statusData = await statusResponse.json();

			if (statusData.status === 'completed' && statusData.payment_token) {
				paymentToken = statusData.payment_token;
				onStatusUpdate?.('💰 Payment approved! Continuing with your request...');

				// Close payment window if still open
				if (paymentWindow && !paymentWindow.closed) {
					paymentWindow.close();
				}

				return true;
			}

			if (statusData.status === 'failed') {
				onStatusUpdate?.(
					'❌ Payment failed: ' + (statusData.error || 'Unknown error')
				);
				return false;
			}
		}

		onStatusUpdate?.('⏱️ Payment timeout. Please try again.');
		return false;
	} catch (error) {
		console.error('Payment error:', error);
		onStatusUpdate?.(
			'❌ Payment error: ' + (error instanceof Error ? error.message : 'Unknown error')
		);
		return false;
	}
}

/**
 * Get payment headers to include in requests
 */
export function getPaymentHeaders(): Record<string, string> {
	if (!paymentToken) return {};

	// Ensure payment token is properly encoded
	const cleanToken = paymentToken.trim();

	// Check for non-ASCII characters
	// eslint-disable-next-line no-control-regex
	if (!/^[\x00-\x7F]*$/.test(cleanToken)) {
		console.error('Payment token contains non-ASCII characters');
		paymentToken = null;
		return {};
	}

	return { 'X-PAYMENT': cleanToken };
}

/**
 * Clear payment token (call when task reaches terminal state)
 */
export function clearPaymentToken(): void {
	paymentToken = null;
}

/**
 * Check if we have a valid payment token
 */
export function hasPaymentToken(): boolean {
	return paymentToken !== null && paymentToken.length > 0;
}
