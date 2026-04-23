import { Context, Effect, Layer } from "effect"
import { Service as DBService, type MessageRow, type SessionRow } from "../db"
import { AssistantMessageInfo, UserMessageInfo, type MessageInfo, type MessageWithParts, type Part } from "./message"
import { MessageID, SessionID, newMessageID, newSessionID } from "./schema"
import { z } from "zod"

/**
 * Session service — thin wrapper over DB.Service with canonical message
 * conversions.
 *
 * The DB stores one message row per Message with all its parts inlined as a
 * JSONB array on the `parts` column. Much simpler than OpenCode's separate
 * Message + Part tables because our Part set is smaller and we don't need
 * per-part streaming mutation — parts are written atomically once the
 * assistant message completes a step.
 */

export interface CreateInput {
  externalSessionID?: string
  userPrefs?: Record<string, unknown>
  agentCatalog?: unknown[]
}

export interface AppendUserInput {
  sessionID: SessionID
  parts: Part[]
}

export interface AppendAssistantInput {
  sessionID: SessionID
  info: AssistantMessageInfo
  parts: Part[]
}

export interface Interface {
  readonly create: (input: CreateInput) => Effect.Effect<SessionRow, Error>
  readonly get: (key: { id?: string; externalID?: string }) => Effect.Effect<SessionRow | undefined, Error>
  readonly touch: (id: SessionID) => Effect.Effect<void, Error>
  readonly updateAgentCatalog: (id: SessionID, catalog: unknown[]) => Effect.Effect<void, Error>
  readonly history: (id: SessionID) => Effect.Effect<MessageWithParts[], Error>
  readonly appendUser: (input: AppendUserInput) => Effect.Effect<MessageWithParts, Error>
  readonly appendAssistant: (input: AppendAssistantInput) => Effect.Effect<MessageWithParts, Error>
  readonly replaceAssistant: (input: AppendAssistantInput) => Effect.Effect<MessageWithParts, Error>
}

export class Service extends Context.Service<Service, Interface>()("@bindu/Session") {}

function toWire(info: MessageInfo, parts: Part[]) {
  return {
    role: info.role,
    parts,
    metadata: { info },
  }
}

function fromWire(row: MessageRow): MessageWithParts {
  const metaInfo = (row.metadata as Record<string, unknown> | undefined)?.info
  if (!metaInfo) throw new Error(`session: message row ${row.id} missing metadata.info`)
  const info = parseInfoWithDefaults(metaInfo, row)
  return {
    info,
    parts: z.array(z.any()).parse(row.parts) as Part[],
  }
}

function parseInfoWithDefaults(raw: unknown, row: MessageRow): MessageInfo {
  // metadata.info is written by our own code, so the shape should always
  // match. But message rows persist across gateway restarts and version
  // bumps — parse permissively to tolerate forward-compat drift.
  const obj = raw as Record<string, unknown>
  if (obj.role === "user") return UserMessageInfo.parse(obj)
  if (obj.role === "assistant") return AssistantMessageInfo.parse(obj)
  throw new Error(`session: unknown role on message row ${row.id}: ${String(obj.role)}`)
}

export const layer = Layer.effect(
  Service,
  Effect.gen(function* () {
    const db = yield* DBService

    const create: Interface["create"] = ({ externalSessionID, userPrefs, agentCatalog }) =>
      db.createSession({
        externalId: externalSessionID,
        prefs: userPrefs,
        agentCatalog,
      })

    const get: Interface["get"] = (key) =>
      db.getSession({ id: key.id, externalId: key.externalID })

    const touch: Interface["touch"] = (id) => db.touchSession(id)

    const updateAgentCatalog: Interface["updateAgentCatalog"] = (id, catalog) =>
      db.updateSessionCatalog(id, catalog)

    const history: Interface["history"] = (sessionID) =>
      Effect.gen(function* () {
        const rows = yield* db.listMessages(sessionID)
        const active = rows.map(fromWire)

        // Inject compaction summary at the head as a synthetic user
        // message. Using "user" role (not "system") because most providers
        // treat a single system block as the agent prompt; we don't want
        // to clobber that. Tagging `synthetic: true` so audit/debug can
        // distinguish it from real turns.
        const sess = yield* db.getSession({ id: sessionID })
        const summary = (sess as unknown as { compaction_summary?: string })?.compaction_summary
        if (!summary) return active

        const synthetic: MessageWithParts = {
          info: {
            id: newMessageID(),
            sessionID,
            role: "user",
            time: { created: Date.now() },
          },
          parts: [
            {
              id: newMessageID() as unknown as import("./schema").PartID,
              type: "text",
              text: `[Prior session context, compacted]\n\n${summary}`,
              synthetic: true,
              time: { start: Date.now() },
            },
          ],
        }
        return [synthetic, ...active]
      })

    const appendUser: Interface["appendUser"] = ({ sessionID, parts }) =>
      Effect.gen(function* () {
        const info: UserMessageInfo = {
          id: newMessageID(),
          sessionID,
          role: "user",
          time: { created: Date.now() },
        }
        const wire = toWire(info, parts)
        const row = yield* db.appendMessage({
          sessionId: sessionID,
          role: wire.role,
          parts: wire.parts,
          metadata: wire.metadata,
        })
        yield* db.touchSession(sessionID)
        return { info: parseInfoWithDefaults(wire.metadata.info, row), parts }
      })

    const appendAssistant: Interface["appendAssistant"] = ({ sessionID, info, parts }) =>
      Effect.gen(function* () {
        const wire = toWire(info, parts)
        yield* db.appendMessage({
          sessionId: sessionID,
          role: wire.role,
          parts: wire.parts,
          metadata: wire.metadata,
        })
        yield* db.touchSession(sessionID)
        return { info, parts }
      })

    /**
     * Replace is best-effort: DB stores each assistant step as its own row
     * for now. A Phase 2 enhancement could add an `upsert_by(messageID)`
     * query. For MVP, we just append; history is flat and streaming-safe.
     */
    const replaceAssistant: Interface["replaceAssistant"] = appendAssistant

    return Service.of({
      create,
      get,
      touch,
      updateAgentCatalog,
      history,
      appendUser,
      appendAssistant,
      replaceAssistant,
    })
  }),
)

export { SessionID, newSessionID, MessageID, newMessageID } from "./schema"
export type { MessageWithParts } from "./message"
export * as Message from "./message"
export * as Compaction from "./compaction"
export * as Revert from "./revert"
export * as Overflow from "./overflow"
export * as Summary from "./summary"
