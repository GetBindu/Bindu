/**
 * Bindu A2A Protocol Endpoint Adapter
 * Translates between chat-ui's internal format and Bindu's JSON-RPC A2A protocol
 */

import { z } from "zod";
import { collections, ObjectId } from "$lib/server/database";
import { config } from "$lib/server/config";
import type { Endpoint, EndpointMessage } from "../endpoints";
import { binduResponseToStream } from "./binduToTextGenerationStream";
import type {
	BinduMessage,
	MessageSendParams,
	BinduJsonRpcRequest,
	Task,
	Part,
	TaskState
} from "./types";
import { writable } from "svelte/store"; // This might not be needed, but stream needs Writable from stream module if specialized

import { TERMINAL_STATES, NON_TERMINAL_STATES } from "./types";

export const endpointBinduParametersSchema = z.object({
	type: z.literal("bindu"),
	baseURL: z.string().url(),
	apiKey: z.string().optional().default(""),
	paymentToken: z.string().optional().default(""),
	streamingSupported: z.boolean().default(true),
});

/**
 * Helper to build headers with auth and payment tokens
 * Matches legacy app.js pattern for getAuthHeaders() and getPaymentHeaders()
 */
function buildHeaders(apiKey: string, paymentToken?: string): Record<string, string> {
	const headers: Record<string, string> = {
		"Content-Type": "application/json",
	};

	if (apiKey) {
		headers["Authorization"] = `Bearer ${apiKey}`;
	}

	if (paymentToken) {
		// Ensure payment token is properly encoded (ASCII only)
		const cleanToken = paymentToken.trim();
		// eslint-disable-next-line no-control-regex
		if (/^[\x00-\x7F]*$/.test(cleanToken)) {
			headers["X-PAYMENT"] = cleanToken;
		}
	}

	return headers;
}

/**
 * Determine task ID based on A2A protocol state machine:
 * - Non-terminal states (input-required, auth-required): REUSE same task ID
 * - Terminal states (completed, failed, canceled): CREATE new task with referenceTaskIds
 * - No current task: CREATE new task
 * Matches legacy app.js task ID logic in sendMessage()
 */
function determineTaskIdAndReferences(
	lastTaskId?: string,
	lastTaskState?: TaskState
): { taskId: string; referenceTaskIds?: string[] } {
	const isNonTerminalState = lastTaskState && NON_TERMINAL_STATES.includes(lastTaskState);

	if (isNonTerminalState && lastTaskId) {
		// Continue same task for non-terminal states
		return { taskId: lastTaskId };
	} else if (lastTaskId) {
		// Terminal state or no state - create new task, reference previous
		return { taskId: crypto.randomUUID(), referenceTaskIds: [lastTaskId] };
	} else {
		// First message in conversation
		return { taskId: crypto.randomUUID() };
	}
}

/**
 * Convert chat-ui message format to Bindu message parts
 */
async function messageContentToParts(message: EndpointMessage): Promise<Part[]> {
	const parts: Part[] = [];

	// Handle string content
	if (typeof message.content === "string") {
		parts.push({ kind: "text", text: message.content });
	}

	// Handle file attachments if present
	if (message.files?.length) {
		for (const file of message.files) {
			if (file.type === "base64") {
				parts.push({
					kind: "file",
					text: "",
					file: {
						name: file.name,
						mimeType: file.mime,
						bytes: file.value,
					},
				});
			} else if (file.type === "hash") {
				try {
					const stream = collections.bucket.openDownloadStream(new ObjectId(file.value));
					const chunks: Buffer[] = [];
					const writableStream = {
						write: (chunk: Buffer) => chunks.push(chunk),
						end: () => { },
					};
					// @ts-ignore - The mock stream implementation is simple
					stream.pipe(writableStream);

					const buffer = Buffer.concat(chunks);
					parts.push({
						kind: "file",
						text: "",
						file: {
							name: file.name,
							mimeType: file.mime,
							bytes: buffer.toString("base64"),
						},
					});
				} catch (e) {
					console.error(`Failed to read file ${file.value}`, e);
				}
			}
		}
	}

	return parts;
}

/**
 * Build the complete message history for context
 * Tracks task IDs and states for proper task continuity
 */
async function buildMessageHistory(
	messages: EndpointMessage[],
	contextId: string
): Promise<{ lastMessage: BinduMessage; history: BinduMessage[]; lastTaskId?: string; lastTaskState?: string }> {
	const history: BinduMessage[] = [];
	let lastTaskId: string | undefined;
	let lastTaskState: string | undefined;

	for (let i = 0; i < messages.length; i++) {
		const msg = messages[i];
		const taskId = crypto.randomUUID();
		const binduMsg: BinduMessage = {
			role: msg.from === "assistant" ? "agent" : "user",
			parts: await messageContentToParts(msg),
			kind: "message",
			messageId: crypto.randomUUID(),
			contextId,
			taskId,
		};
		history.push(binduMsg);

		// Track last user message's task ID for continuity
		if (msg.from === "user") {
			lastTaskId = taskId;
		}
	}

	const lastMessage = history[history.length - 1];
	return { lastMessage, history: history.slice(0, -1), lastTaskId, lastTaskState };
}

/**
 * Create the Bindu endpoint handler
 */
export async function endpointBindu(
	input: z.input<typeof endpointBinduParametersSchema>
): Promise<Endpoint> {
	const { baseURL, apiKey, paymentToken } = endpointBinduParametersSchema.parse(input);

	// Use configured API key or fall back to environment variable
	const effectiveApiKey = apiKey || config.BINDU_API_KEY || "";
	let currentPaymentToken = paymentToken || "";

	return async ({ messages, conversationId, preprompt, abortSignal }) => {
		// Filter to get actual user/assistant messages
		const conversationMessages = messages.filter(
			(m) => m.from === "user" || m.from === "assistant"
		);

		if (conversationMessages.length === 0) {
			throw new Error("No messages to send to Bindu agent");
		}

		// Use conversation ID as context ID for continuity
		// Convert MongoDB ObjectId (24 chars) to UUID format (32 chars hex)
		const contextId = conversationId
			? conversationId.toString().padEnd(32, '0')  // Pad to 32 chars for UUID format
			: crypto.randomUUID();

		// 4. Build context and task
		const { lastMessage, lastTaskId, lastTaskState } = await buildMessageHistory(
			conversationMessages,
			contextId
		);
		let currentTaskId = lastTaskId;

		// Determine task ID based on A2A protocol state machine
		const { taskId, referenceTaskIds } = determineTaskIdAndReferences(
			lastTaskId,
			lastTaskState as TaskState | undefined
		);

		// Override taskId for the actual request
		lastMessage.taskId = taskId;
		if (referenceTaskIds && referenceTaskIds.length > 0) {
			lastMessage.referenceTaskIds = referenceTaskIds;
		}

		// Prepare system prompt as part of configuration if present
		const systemContext = preprompt?.trim()
			? { systemPrompt: preprompt.trim() }
			: {};

		// Build JSON-RPC request params
		const params: MessageSendParams = {
			message: lastMessage,
			configuration: {
				acceptedOutputModes: ["text/plain", "application/json"],
				blocking: false,  // Use async task pattern
				...systemContext,
			},
		};

		// Step 1: Send message (returns task immediately)
		const messageRequest: BinduJsonRpcRequest = {
			jsonrpc: "2.0",
			method: "message/send",
			params: params as unknown as Record<string, unknown>,
			id: crypto.randomUUID(),
		};

		// Build headers with auth and payment tokens
		let headers = buildHeaders(effectiveApiKey, currentPaymentToken);

		// Step 1: Send message (returns task immediately)
		const messageResponse = await fetch(baseURL, {
			method: "POST",
			headers,
			body: JSON.stringify(messageRequest),
			signal: abortSignal,
		});

		// Handle 401 Unauthorized (Auth Required)
		if (messageResponse.status === 401) {
			throw new Error(
				"Authentication required. Please provide a valid API key or JWT token."
			);
		}

		// Handle 402 Payment Required
		if (messageResponse.status === 402) {
			// In server-side context, we cannot handle payment UI flow
			// This should be handled by the client/frontend
			throw new Error(
				"Payment required. This agent requires payment to process requests. Please configure a payment token."
			);
		}

		if (!messageResponse.ok) {
			const errorText = await messageResponse.text().catch(() => "Unknown error");
			throw new Error(
				`Message send failed: ${messageResponse.status} ${messageResponse.statusText} - ${errorText}`
			);
		}

		const messageResult = await messageResponse.json();
		if (messageResult.error) {
			throw new Error(`Message send error: ${messageResult.error.message}`);
		}

		// Extract task from result - result IS the task directly
		const initialTask = messageResult.result;
		if (!initialTask || !initialTask.id) {
			throw new Error("No task returned from message/send");
		}
		const submittedTaskId = initialTask.id;

		// Step 2: Poll for task completion
		const pollInterval = 1000; // Poll every 1 second (matches legacy UI)
		const maxAttempts = 300; // Max 5 minutes (300 * 1000ms)

		for (let attempt = 0; attempt < maxAttempts; attempt++) {
			if (abortSignal?.aborted) {
				throw new Error("Request aborted");
			}

			// Wait before polling (skip first attempt)
			if (attempt > 0) {
				await new Promise(resolve => setTimeout(resolve, pollInterval));
			}

			// Get task status
			const statusRequest: BinduJsonRpcRequest = {
				jsonrpc: "2.0",
				method: "tasks/get",
				params: { taskId: submittedTaskId },
				id: crypto.randomUUID(),
			};

			// Rebuild headers in case payment token was added
			headers = buildHeaders(effectiveApiKey, currentPaymentToken);

			const statusResponse = await fetch(baseURL, {
				method: "POST",
				headers,
				body: JSON.stringify(statusRequest),
				signal: abortSignal,
			});

			if (!statusResponse.ok) {
				continue; // Retry on error
			}

			const statusResult = await statusResponse.json();

			if (statusResult.error) {
				throw new Error(`Task status error: ${statusResult.error.message}`);
			}

			// Result IS the task directly
			const task: Task = statusResult.result;
			if (!task || !task.status) {
				continue; // Task not ready yet
			}

			const taskState = task.status.state;

			// Terminal states - task is IMMUTABLE
			if (TERMINAL_STATES.includes(taskState)) {
				// Clear payment token when task reaches terminal state
				// Next message will create NEW task and require NEW payment
				currentPaymentToken = "";

				if (taskState === "completed" || taskState === "input-required") {
					// Convert the completed task result to a stream
					const mockResponse = new Response(JSON.stringify(statusResult), {
						status: 200,
						headers: { 'Content-Type': 'application/json' }
					});
					return binduResponseToStream(mockResponse);
				} else if (taskState === "failed") {
					const errorMsg = task.metadata?.error ||
						task.metadata?.error_message ||
						task.status?.message ||
						"Task failed";
					throw new Error(`Task failed: ${errorMsg}`);
				} else if (taskState === "canceled") {
					throw new Error("Task was canceled");
				}
			}
			// Non-terminal states - task still MUTABLE, waiting for input
			else if (NON_TERMINAL_STATES.includes(taskState)) {
				// Return current state (input-required, auth-required)
				// Next message will REUSE same task ID
				const mockResponse = new Response(JSON.stringify(statusResult), {
					status: 200,
					headers: { 'Content-Type': 'application/json' }
				});
				return binduResponseToStream(mockResponse);
			}
			// Working states - continue polling (submitted, working)
			// Continue to next iteration
		}

		throw new Error("Task polling timeout - task did not complete in time");
	};
}
