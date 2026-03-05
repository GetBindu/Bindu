/**
 * Direct Agent API Message Handler
 * Simplified implementation that directly calls agent API without backend complexity
 * Based on working patterns from bindu/ui/static/app.js
 */

import type { MessageUpdate } from '$lib/types/MessageUpdate';
import type { MessageFile } from '$lib/types/Message';
import { MessageUpdateType, MessageUpdateStatus } from '$lib/types/MessageUpdate';
import { handlePaymentRequired, getPaymentHeaders, clearPaymentToken } from './paymentHandler';

const AGENT_BASE_URL = 'http://localhost:3773';

/**
 * Submit feedback for a task
 */
export async function submitTaskFeedback(
	taskId: string,
	feedback: string,
	rating: number
): Promise<{ message: string; task_id: string }> {
	const token = getAuthToken();
	const headers: Record<string, string> = {
		'Content-Type': 'application/json',
		...getPaymentHeaders()
	};

	if (token) {
		headers['Authorization'] = `Bearer ${token}`;
	}

	const response = await fetch(`${AGENT_BASE_URL}/`, {
		method: 'POST',
		headers,
		body: JSON.stringify({
			jsonrpc: '2.0',
			method: 'tasks/feedback',
			params: {
				taskId,
				feedback: feedback || `Rating: ${rating}/5`,
				rating,
				metadata: {
					source: 'web-ui',
					timestamp: new Date().toISOString()
				}
			},
			id: generateId()
		})
	});

	if (!response.ok) {
		const errorText = await response.text().catch(() => 'Unknown error');
		throw new Error(`Feedback submission failed: ${response.status} - ${errorText}`);
	}

	const result = await response.json();

	if (result.error) {
		throw new Error(result.error.message || 'Feedback submission error');
	}

	return result.result;
}

interface TextPart {
	kind: 'text';
	text: string;
}

export interface FilePart {
	kind: 'file';
	text: string;
	file: {
		name?: string;
		mimeType?: string;
		bytes?: string; // base64 encoded
		uri?: string;
	};
}

export interface DataPart {
	kind: 'data';
	text: string;
	data: Record<string, unknown>;
}

type Part = TextPart | FilePart | DataPart;

interface AgentMessage {
	role: 'user' | 'agent';
	parts: Part[];
	kind: 'message';
	messageId: string;
	contextId: string;
	taskId: string;
	referenceTaskIds?: string[];
}

interface AgentTask {
	id: string;
	context_id: string;
	kind: 'task';
	status: {
		state: 'submitted' | 'working' | 'input-required' | 'completed' | 'failed' | 'canceled';
		timestamp: string;
	};
	history: Array<{
		kind: 'message';
		role: 'user' | 'assistant' | 'agent';
		parts: Array<{ kind: 'text'; text: string }>;
	}>;
	artifacts: Array<{
		kind: string;
		parts?: Array<{ kind: 'text'; text: string }>;
		text?: string;
	}>;
	metadata?: Record<string, unknown>;
}

/**
 * Generate a UUID v4
 */
function generateId(): string {
	return crypto.randomUUID();
}

/**
 * Get auth token from localStorage
 */
function getAuthToken(): string | null {
	if (typeof window === 'undefined') return null;
	return localStorage.getItem('bindu_oauth_token');
}

/**
 * Extract text from task (artifacts or history)
 */
function extractTextFromTask(task: AgentTask): string {
	// Try artifacts first (completed tasks)
	if (task.artifacts && task.artifacts.length > 0) {
		const textParts: string[] = [];
		for (const artifact of task.artifacts) {
			if (artifact.parts) {
				for (const part of artifact.parts) {
					if (part.kind === 'text' && part.text) {
						textParts.push(part.text);
					}
				}
			} else if (artifact.text) {
				textParts.push(artifact.text);
			}
		}
		if (textParts.length > 0) return textParts.join('\n');
	}

	// Fallback to history (input-required, etc.)
	if (task.history && task.history.length > 0) {
		for (let i = task.history.length - 1; i >= 0; i--) {
			const msg = task.history[i];
			if (msg.role === 'assistant' || msg.role === 'agent') {
				if (msg.parts) {
					for (const part of msg.parts) {
						if (part.kind === 'text' && part.text) {
							return part.text;
						}
					}
				}
			}
		}
	}

	return '';
}

/**
 * Send message to agent and poll for completion
 * Returns an async generator that yields MessageUpdate objects
 *
 * @param message - The message text to send
 * @param contextId - The context ID for the conversation
 * @param abortSignal - Signal to abort the request
 * @param existingTaskId - If provided and task is in non-terminal state, reuse this taskId
 * @param taskState - Current state of the task (input-required, completed, etc.)
 * @param replyToTaskId - Explicit reply to a specific task (always creates new task)
 */
export async function* sendAgentMessage(
	message: string,
	contextId?: string,
	abortSignal?: AbortSignal,
	currentTaskId?: string,
	taskState?: string,
	replyToTaskId?: string,
	files?: MessageFile[]
): AsyncGenerator<MessageUpdate, void, unknown> {
	const token = typeof window !== 'undefined' ? localStorage.getItem('bindu_oauth_token') : null;
	const headers: Record<string, string> = {
		'Content-Type': 'application/json',
		...getPaymentHeaders()
	};

	if (token) {
		headers['Authorization'] = `Bearer ${token}`;
	}

	// Generate IDs
	const messageId = generateId();

	// Task ID logic based on A2A protocol:
	// - Explicit reply: ALWAYS create new task with referenceTaskIds
	// - Non-terminal states (input-required, auth-required): REUSE task ID
	// - Terminal states (completed, failed, canceled): CREATE new task
	// - No current task: CREATE new task
	let taskId: string;
	const referenceTaskIds: string[] = [];

	if (replyToTaskId) {
		// Explicit reply to a specific task - always create new task
		taskId = generateId();
		referenceTaskIds.push(replyToTaskId);
	} else {
		const isNonTerminalState = taskState &&
			(taskState === 'input-required' || taskState === 'auth-required');

		if (isNonTerminalState && currentTaskId) {
			// Continue same task for non-terminal states
			taskId = currentTaskId;
		} else {
			// Create new task
			taskId = generateId();
			// Reference previous task if it exists
			if (currentTaskId) {
				referenceTaskIds.push(currentTaskId);
			}
		}
	}

	// Pad contextId to 32 chars if it's a MongoDB ObjectId (24 chars)
	const newContextId = contextId
		? (contextId.length === 24 ? contextId.padEnd(32, '0') : contextId)
		: generateId();

	// Build message parts
	const parts: Part[] = [{ kind: 'text', text: message }];

	// Add file parts if present
	if (files && files.length > 0) {
		for (const file of files) {
			parts.push({
				kind: 'file',
				text: '',
				file: {
					name: file.name,
					mimeType: file.mime,
					bytes: file.value // base64 data
				}
			});
		}
	}

	// Build message with optional referenceTaskIds
	const agentMessage: AgentMessage = {
		role: 'user',
		parts,
		kind: 'message',
		messageId,
		contextId: newContextId,
		taskId,
		...(referenceTaskIds.length > 0 && { referenceTaskIds })
	};

	// Step 1: Send message
	yield { type: MessageUpdateType.Status, status: MessageUpdateStatus.Started };

	const requestBody = {
		jsonrpc: '2.0',
		method: 'message/send',
		params: {
			message: agentMessage,
			configuration: {
				acceptedOutputModes: ['application/json']
			}
		},
		id: generateId()
	};

	try {
		let response = await fetch(`${AGENT_BASE_URL}/`, {
			method: 'POST',
			headers,
			body: JSON.stringify(requestBody),
			signal: abortSignal
		});

		// Handle 402 Payment Required
		if (response.status === 402) {
			console.log('Payment required, starting payment flow...');

			const paymentSuccess = await handlePaymentRequired((message) => {
				// Emit status updates during payment
				console.log('Payment status:', message);
			});

			if (paymentSuccess) {
				console.log('Payment completed, retrying request with payment token...');

				// Retry with payment token
				const retryHeaders: Record<string, string> = {
					'Content-Type': 'application/json',
					...getPaymentHeaders()
				};

				if (token) {
					retryHeaders['Authorization'] = `Bearer ${token}`;
				}

				response = await fetch(`${AGENT_BASE_URL}/`, {
					method: 'POST',
					headers: retryHeaders,
					body: JSON.stringify(requestBody),
					signal: abortSignal
				});

				console.log('Retry response status:', response.status);

				if (!response.ok) {
					const errorText = await response.text().catch(() => 'Unknown error');
					console.error('Retry failed:', response.status, errorText);
					throw new Error(`Agent request failed after payment: ${response.status} - ${errorText}`);
				}

				console.log('Retry successful, continuing with normal flow...');

				// Update headers to include payment token for subsequent polling requests
				headers['X-PAYMENT'] = getPaymentHeaders()['X-PAYMENT'] || '';
			} else {
				throw new Error('Payment required but not completed');
			}
		} else if (!response.ok) {
			const errorText = await response.text().catch(() => 'Unknown error');
			throw new Error(`Agent request failed: ${response.status} - ${errorText}`);
		}

		let result;
		try {
			result = await response.json();
		} catch (parseError) {
			console.error('Failed to parse response JSON:', parseError);
			const text = await response.text();
			console.error('Response text:', text);
			throw new Error('Failed to parse response');
		}

		if (result.error) {
			console.error('Response contains error:', result.error);
			throw new Error(result.error.message || 'Agent error');
		}

		if (!result.result) {
			console.error('Response missing result field:', result);
			throw new Error('Invalid response: missing result');
		}

		const task = result.result as AgentTask;
		const submittedTaskId = task.id;

		// Emit initial task metadata
		yield {
			type: MessageUpdateType.TaskMetadata,
			taskId: submittedTaskId,
			contextId: newContextId,
			status: task.status.state,
			...(agentMessage.referenceTaskIds && { referenceTaskIds: agentMessage.referenceTaskIds })
		};

		// Step 2: Poll for completion
		const pollInterval = 1000; // 1 second
		const maxAttempts = 300; // 5 minutes

		for (let attempt = 0; attempt < maxAttempts; attempt++) {
			if (abortSignal?.aborted) {
				throw new Error('Request aborted');
			}

			// Wait before polling (except first attempt)
			if (attempt > 0) {
				await new Promise(resolve => setTimeout(resolve, pollInterval));
			}

			// Poll task status
			const statusResponse = await fetch(`${AGENT_BASE_URL}/`, {
				method: 'POST',
				headers,
				body: JSON.stringify({
					jsonrpc: '2.0',
					method: 'tasks/get',
					params: { taskId: submittedTaskId },
					id: generateId()
				}),
				signal: abortSignal
			});

			if (!statusResponse.ok) {
				continue; // Retry on error
			}

			const statusResult = await statusResponse.json();

			if (statusResult.error) {
				throw new Error(statusResult.error.message || 'Task status error');
			}

			const currentTask = statusResult.result as AgentTask;
			const taskState = currentTask.status.state;

			// Emit task status update
			yield {
				type: MessageUpdateType.TaskMetadata,
				taskId: submittedTaskId,
				contextId: newContextId,
				status: taskState,
				...(agentMessage.referenceTaskIds && { referenceTaskIds: agentMessage.referenceTaskIds })
			};

			// Check if task is complete or needs input
			if (taskState === 'completed' || taskState === 'input-required') {
				const text = extractTextFromTask(currentTask);

				// Yield final answer directly (no stream tokens needed)
				// The FinalAnswer will set message.content which the UI will render
				yield {
					type: MessageUpdateType.FinalAnswer,
					text: text || '',
					interrupted: false
				};

				// Yield finished status to signal completion
				yield {
					type: MessageUpdateType.Status,
					status: MessageUpdateStatus.Finished
				};

				// Clear payment token only when task completes (not for input-required)
				// This ensures new tasks require new payment, but continuing same task reuses token
				if (taskState === 'completed') {
					clearPaymentToken();
				}

				// Exit immediately - stop polling
				return;
			} else if (taskState === 'failed') {
				clearPaymentToken();
				throw new Error(`Task failed: ${currentTask.metadata?.error || 'Unknown error'}`);
			} else if (taskState === 'canceled') {
				clearPaymentToken();
				throw new Error('Task was canceled');
			}
			// Otherwise continue polling (working, submitted)
		}

		throw new Error('Task polling timeout');

	} catch (error) {
		yield {
			type: MessageUpdateType.Status,
			status: MessageUpdateStatus.Error,
			message: error instanceof Error ? error.message : 'Unknown error'
		};
		throw error;
	}
}
