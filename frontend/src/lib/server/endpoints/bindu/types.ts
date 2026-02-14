/**
 * Bindu A2A Protocol Types
 * Defines TypeScript interfaces for the Agent-to-Agent (A2A) JSON-RPC protocol
 */

// ============================================================================
// Core A2A Message Types
// ============================================================================

export type PartKind = "text" | "file" | "data";

export interface TextPart {
	kind: "text";
	text: string;
}

export interface FilePart {
	kind: "file";
	file: {
		name?: string;
		mimeType?: string;
		bytes?: string; // base64 encoded
		uri?: string;
	};
}

export interface DataPart {
	kind: "data";
	data: Record<string, unknown>;
}

export type Part = TextPart | FilePart | DataPart;

export interface BinduMessage {
	role: "user" | "agent";
	parts: Part[];
	kind: "message";
	messageId: string;
	contextId: string;
	taskId: string;
	referenceTaskIds?: string[]; // For task continuity (A2A protocol)
}

// ============================================================================
// Task Status Types
// ============================================================================

export type TaskState =
	| "submitted"
	| "working"
	| "input-required"
	| "auth-required"
	| "completed"
	| "canceled"
	| "failed"
	| "unknown";

export interface TaskStatus {
	state: TaskState;
	timestamp: string;
	message?: BinduMessage;
}

export interface Artifact {
	kind: string;
	text?: string;
	name?: string;
	description?: string;
	index?: number;
	append?: boolean;
	lastChunk?: boolean;
	metadata?: Record<string, unknown>;
}

export interface Task {
	id: string; // Primary task ID field
	taskId?: string; // Alias for compatibility
	context_id?: string; // Server uses snake_case
	contextId?: string; // Alias for compatibility
	status: TaskStatus;
	artifacts?: Artifact[];
	history?: BinduMessage[];
	metadata?: Record<string, unknown>;
}

// ============================================================================
// JSON-RPC Types
// ============================================================================

export interface BinduJsonRpcRequest {
	jsonrpc: "2.0";
	method: string;
	params: Record<string, unknown>;
	id: string;
}

export interface BinduJsonRpcResponse {
	jsonrpc: "2.0";
	result?: {
		task?: Task;
		[key: string]: unknown;
	};
	error?: {
		code: number;
		message: string;
		data?: unknown;
	};
	id: string;
}

export interface MessageSendParams {
	message: BinduMessage;
	configuration?: {
		acceptedOutputModes?: string[];
		blocking?: boolean;
		historyLength?: number;
		systemPrompt?: string;
		pushNotificationConfig?: {
			url: string;
			token?: string;
		};
	};
}

// ============================================================================
// Streaming Types
// ============================================================================

export interface BinduStreamEvent {
	jsonrpc: "2.0";
	method?: string;
	params?: {
		taskId?: string;
		contextId?: string;
		status?: TaskStatus;
		artifact?: Artifact;
		final?: boolean;
	};
	result?: {
		task?: Task;
	};
	id?: string;
}

// ============================================================================
// Agent Card Types (Discovery)
// ============================================================================

export interface AgentSkill {
	id: string;
	name: string;
	description?: string;
	tags?: string[];
	examples?: string[];
	inputModes?: string[];
	outputModes?: string[];
}

export interface AgentCapabilities {
	streaming?: boolean;
	taskManagement?: boolean;
	pushNotifications?: boolean;
	stateTransitions?: string[];
}

export interface AgentEndpoints {
	jsonrpc: string;
	webhook?: string;
}

export interface AgentCard {
	name: string;
	description?: string;
	version?: string;
	did?: string;
	url?: string;
	provider?: {
		organization?: string;
		url?: string;
	};
	capabilities?: AgentCapabilities;
	skills?: AgentSkill[];
	endpoints?: AgentEndpoints;
	defaultInputModes?: string[];
	defaultOutputModes?: string[];
	authentication?: {
		schemes?: string[];
		credentials?: string;
	};
}

// ============================================================================
// Helper Types
// ============================================================================

export interface BinduEndpointConfig {
	type: "bindu";
	baseURL: string;
	apiKey?: string;
	paymentToken?: string;
}

// ============================================================================
// Payment & Auth Types
// ============================================================================

export interface PaymentSessionResponse {
	session_id: string;
	browser_url: string;
}

export interface PaymentStatusResponse {
	status: "pending" | "completed" | "failed";
	payment_token?: string;
	error?: string;
}

// Terminal states: task is IMMUTABLE, next message creates NEW task
export const TERMINAL_STATES: TaskState[] = ["completed", "failed", "canceled"];

// Non-terminal states: task is MUTABLE, can continue with SAME task ID
export const NON_TERMINAL_STATES: TaskState[] = ["input-required", "auth-required"];

// Working states: task is in progress
export const WORKING_STATES: TaskState[] = ["submitted", "working"];
