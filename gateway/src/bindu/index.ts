// Barrel for the Bindu module — single import point for callers.
//
// Import order matters: identity/ sets the ed25519 sha512 hook on first
// import. Barrel imports it before client/ so downstream code can't
// accidentally call verify() without the hook.

import "./identity"

export * as Protocol from "./protocol"
export * as Identity from "./identity"
export * as Auth from "./auth/resolver"
export * as Client from "./client"

// Convenience re-exports — the shapes callers reach for most often.
export { BinduError, ErrorCode } from "./protocol/jsonrpc"
export { isTerminal, needsCallerAction } from "./protocol/types"
export type { Task, Message, Part, Artifact } from "./protocol/types"
export type { AgentCard, SkillSummary, SkillDetail } from "./protocol/agent-card"
export type { CallPeerInput, CallPeerOutcome, PeerDescriptor } from "./client"
