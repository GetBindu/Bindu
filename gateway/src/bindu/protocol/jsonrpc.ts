import { z } from "zod"

/**
 * JSON-RPC 2.0 envelope + Bindu-specific error codes.
 *
 * Phase 0 finding: Bindu returns `-32700 JSONParseError` for schema
 * validation failures (e.g., snake_case where camelCase is expected). The
 * error mapper treats `-32700` and `-32602 InvalidParams` as interchangeable
 * for retry-on-casing-mismatch logic.
 */

// --------------------------------------------------------------------
// Request / Response envelopes
// --------------------------------------------------------------------

export const JsonRpcRequest = z.object({
  jsonrpc: z.literal("2.0"),
  method: z.string(),
  id: z.union([z.string(), z.number(), z.null()]),
  params: z.unknown().optional(),
})
export type JsonRpcRequest = z.infer<typeof JsonRpcRequest>

export const JsonRpcErrorPayload = z
  .object({
    code: z.number(),
    message: z.string(),
    data: z.unknown().optional(),
  })
  .passthrough()
export type JsonRpcErrorPayload = z.infer<typeof JsonRpcErrorPayload>

export const JsonRpcResponse = z
  .object({
    jsonrpc: z.literal("2.0"),
    id: z.union([z.string(), z.number(), z.null()]),
    result: z.unknown().optional(),
    error: JsonRpcErrorPayload.optional(),
  })
  .refine((r) => r.result !== undefined || r.error !== undefined, {
    message: "JSON-RPC response must have either result or error",
  })
export type JsonRpcResponse = z.infer<typeof JsonRpcResponse>

// --------------------------------------------------------------------
// Error codes
// --------------------------------------------------------------------

export const ErrorCode = {
  // Standard JSON-RPC 2.0
  JsonParse: -32700,
  InvalidRequest: -32600,
  MethodNotFound: -32601,
  InvalidParams: -32602,
  InternalError: -32603,

  // A2A spec
  TaskNotFound: -32001,
  TaskNotCancelable: -32002,
  PushNotificationNotSupported: -32003,
  UnsupportedOperation: -32004,
  ContentTypeNotSupported: -32005,
  InvalidAgentResponse: -32006,
  AuthenticatedExtendedCardNotConfigured: -32007,

  // Bindu extensions
  TaskImmutable: -32008,
  AuthenticationRequired: -32009,
  InvalidToken: -32010,
  TokenExpired: -32011,
  InvalidTokenSignature: -32012,
  InsufficientPermissions: -32013,
  ContextNotFound: -32020,
  ContextNotCancelable: -32021,
  SkillNotFound: -32030,
} as const

export type ErrorCodeValue = (typeof ErrorCode)[keyof typeof ErrorCode]

/**
 * Schema-mismatch codes — Phase 0 showed Bindu uses `-32700` where the spec
 * would use `-32602`. Treat both as "retry with different casing".
 */
export const SCHEMA_MISMATCH_CODES: readonly number[] = [
  ErrorCode.JsonParse,
  ErrorCode.InvalidParams,
]

export const RETRYABLE_CODES: readonly number[] = [
  ErrorCode.InternalError,
  ErrorCode.JsonParse,
]

export const AUTH_CODES: readonly number[] = [
  ErrorCode.AuthenticationRequired,
  ErrorCode.InvalidToken,
  ErrorCode.TokenExpired,
  ErrorCode.InvalidTokenSignature,
]

// --------------------------------------------------------------------
// BinduError — typed error class
// --------------------------------------------------------------------

export class BinduError extends Error {
  readonly code: number
  readonly data?: unknown
  readonly peer?: string

  constructor(code: number, message: string, opts?: { data?: unknown; peer?: string; cause?: unknown }) {
    super(message, opts?.cause ? { cause: opts.cause } : undefined)
    this.name = "BinduError"
    this.code = code
    this.data = opts?.data
    this.peer = opts?.peer
  }

  static fromRpc(payload: JsonRpcErrorPayload, peer?: string): BinduError {
    return new BinduError(payload.code, payload.message, { data: payload.data, peer })
  }

  static transport(message: string, peer?: string, cause?: unknown): BinduError {
    return new BinduError(ErrorCode.InternalError, `transport: ${message}`, { peer, cause })
  }

  isSchemaMismatch(): boolean {
    return SCHEMA_MISMATCH_CODES.includes(this.code)
  }

  isAuth(): boolean {
    return AUTH_CODES.includes(this.code)
  }

  isRetryable(): boolean {
    return RETRYABLE_CODES.includes(this.code)
  }

  isTerminal(): boolean {
    return (
      this.code === ErrorCode.InsufficientPermissions ||
      this.code === ErrorCode.InvalidRequest ||
      this.code === ErrorCode.TaskNotFound ||
      this.code === ErrorCode.TaskImmutable ||
      this.code === ErrorCode.SkillNotFound
    )
  }
}
