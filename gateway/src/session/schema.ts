import { z } from "zod"
import { randomUUID } from "crypto"

/**
 * Identifier types for session, message, and tool-call parts.
 *
 * UUID v4 throughout — simpler than OpenCode's ULID-prefixed identifiers and
 * matches the rest of the Bindu ecosystem (agent IDs, task IDs, context IDs
 * on the wire are all UUIDs).
 */

export const SessionID = z.string().uuid().brand<"SessionID">()
export type SessionID = z.infer<typeof SessionID>
export const newSessionID = (): SessionID => SessionID.parse(randomUUID())

export const MessageID = z.string().uuid().brand<"MessageID">()
export type MessageID = z.infer<typeof MessageID>
export const newMessageID = (): MessageID => MessageID.parse(randomUUID())

export const PartID = z.string().uuid().brand<"PartID">()
export type PartID = z.infer<typeof PartID>
export const newPartID = (): PartID => PartID.parse(randomUUID())

export const CallID = z.string().min(1).brand<"CallID">()
export type CallID = z.infer<typeof CallID>
