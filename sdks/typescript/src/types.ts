/**
 * Bindu SDK Type Definitions
 *
 * These types define the developer-facing API for the TypeScript SDK.
 * Developers interact with these types — they never see gRPC or proto types.
 */

/** A single message in conversation history. */
export interface ChatMessage {
  role: string;
  content: string;
}

/** Response from the handler — either plain text or a state transition. */
export interface HandlerResponse {
  content?: string;
  state?: "input-required" | "auth-required";
  prompt?: string;
  metadata?: Record<string, string>;
}

/** Handler function type — what the developer implements. */
export type MessageHandler = (
  messages: ChatMessage[]
) => Promise<string | HandlerResponse>;

/** Deployment configuration. */
export interface DeploymentConfig {
  url: string;
  expose?: boolean;
  protocol_version?: string;
  cors_origins?: string[];
}

/** Execution cost configuration for x402 payments. */
export interface ExecutionCost {
  amount: string;
  token?: string;
  network?: string;
  pay_to_address?: string;
}

/** Agent capabilities. */
export interface Capabilities {
  streaming?: boolean;
  push_notifications?: boolean;
  state_transition_history?: boolean;
}

/** Skill configuration — either a path to a skill file or inline definition. */
export type SkillConfig = string | InlineSkill;

/** Inline skill definition (when not loading from file). */
export interface InlineSkill {
  name: string;
  description: string;
  tags?: string[];
  input_modes?: string[];
  output_modes?: string[];
  version?: string;
  author?: string;
}

/** Full configuration for bindufy(). */
export interface BinduConfig {
  /** Agent author email (required). */
  author: string;

  /** Human-readable agent name (required). */
  name: string;

  /** Agent description. */
  description?: string;

  /** Agent version (default: "1.0.0"). */
  version?: string;

  /** Deployment configuration (required). */
  deployment: DeploymentConfig;

  /** List of skills — file paths or inline definitions. */
  skills?: SkillConfig[];

  /** Agent capabilities. */
  capabilities?: Capabilities;

  /** Agent type (default: "agent"). */
  kind?: "agent" | "team" | "workflow";

  /** Execution cost for x402 payments. */
  execution_cost?: ExecutionCost | ExecutionCost[];

  /** Bindu core gRPC address (default: "localhost:3774"). */
  coreAddress?: string;

  /** Port for this SDK's AgentHandler server (default: auto-assigned). */
  callbackPort?: number;

  /** Additional metadata. */
  extra_metadata?: Record<string, string>;

  /** Enable debug mode. */
  debug_mode?: boolean;

  /** Enable telemetry. */
  telemetry?: boolean;

  /** Number of history sessions to maintain. */
  num_history_sessions?: number;
}

/** Response from RegisterAgent — returned after successful registration. */
export interface RegistrationResult {
  agentId: string;
  did: string;
  agentUrl: string;
}
