import { Context, Effect, Layer, Stream } from "effect"
import { BusEvent, Service as BusService } from "../bus"
import { Service as AgentService, type Info as AgentInfo } from "../agent"
import { Service as ConfigService } from "../config"
import { Service as ToolRegistryService } from "../tool/registry"
import type { Def as ToolDef, Context as ToolContext } from "../tool/tool"
import { Service as SessionService } from "./index"
import { Service as ProviderService } from "../provider"
import { stream as llmStream, type StreamEvent } from "./llm"
import type { ModelMessage } from "ai"
import { z } from "zod"
import {
  AssistantMessageInfo,
  Part,
  ToolPart,
  TextPart,
  toModelMessages,
  type MessageWithParts,
} from "./message"
import { CallID, MessageID, SessionID, newMessageID, newPartID } from "./schema"
import { tool as aiTool, jsonSchema } from "ai"
// PermissionService imported elsewhere; included via layer graph.

/**
 * Session prompt loop — the gateway's planner brain.
 *
 * What this does (one complete call):
 *   1. Load session history + supplemental tool set
 *   2. Build system prompt (agent.prompt + config.instructions)
 *   3. Convert our Part[] message history into AI SDK ModelMessage[]
 *   4. Hand each registered Tool to AI SDK as an `ai.tool()` with its
 *      `execute` wired back through our ToolRegistry
 *   5. Call `streamText`; AI SDK handles the agentic loop (tool call →
 *      execute → feed result → call again) up to `steps`
 *   6. Accumulate Parts from the fullStream, publish Bus events, persist
 *      the finalized assistant Message
 *
 * What's deliberately out of scope (Phase 2+):
 *   - Compaction when we overflow context
 *   - Subagent/Task tool (we dispatch via `agent_call` instead)
 *   - Structured output mode
 *   - Mid-stream cancel / revert
 *   - Plugin hooks (beforeTool / afterTool)
 */

export const PromptEvent = {
  Started: BusEvent.define(
    "session.prompt.started",
    z.object({ sessionID: z.string(), messageID: z.string() }),
  ),
  TextDelta: BusEvent.define(
    "session.prompt.text",
    z.object({ sessionID: z.string(), messageID: z.string(), partID: z.string(), delta: z.string() }),
  ),
  ToolCallStart: BusEvent.define(
    "session.prompt.tool.start",
    z.object({
      sessionID: z.string(),
      messageID: z.string(),
      partID: z.string(),
      callID: z.string(),
      tool: z.string(),
      input: z.unknown(),
    }),
  ),
  ToolCallEnd: BusEvent.define(
    "session.prompt.tool.end",
    z.object({
      sessionID: z.string(),
      messageID: z.string(),
      partID: z.string(),
      callID: z.string(),
      tool: z.string(),
      output: z.unknown().optional(),
      error: z.string().optional(),
      title: z.string().optional(),
    }),
  ),
  Finished: BusEvent.define(
    "session.prompt.finished",
    z.object({
      sessionID: z.string(),
      messageID: z.string(),
      stopReason: z.string(),
      usage: z
        .object({
          inputTokens: z.number().optional(),
          outputTokens: z.number().optional(),
          totalTokens: z.number().optional(),
          cachedInputTokens: z.number().optional(),
        })
        .optional(),
    }),
  ),
}

export interface PromptInput {
  sessionID: SessionID
  agent: string
  /** New user message parts to append before running (empty = resume existing state). */
  parts: Part[]
  /** Optional tool set to register for this call. Tools are scoped per-call. */
  tools?: ToolDef[]
  /** Override for model selection, bypassing agent.model. */
  modelOverride?: string
  /** Override for max agentic steps, bypassing agent.steps. */
  stepsOverride?: number
  abort?: AbortSignal
}

export interface Interface {
  readonly prompt: (input: PromptInput) => Effect.Effect<MessageWithParts, Error>
}

export class Service extends Context.Service<Service, Interface>()("@bindu/SessionPrompt") {}

export const layer = Layer.effect(
  Service,
  Effect.gen(function* () {
    const sessions = yield* SessionService
    const agents = yield* AgentService
    const config = yield* ConfigService
    const registry = yield* ToolRegistryService
    const bus = yield* BusService
    // Pull ProviderService into outer scope so llm.stream's requirement is
    // satisfied by the Layer graph rather than propagated through prompt's R.
    const provider = yield* ProviderService
    // PermissionService is consumed by tools' own ctx.ask() — the Layer
    // graph provides it implicitly when tools run.

    const prompt: Interface["prompt"] = (input) =>
      Effect.gen(function* () {
        const agentInfo = (yield* agents.get(input.agent)) as AgentInfo | undefined
        if (!agentInfo) return yield* Effect.fail(new Error(`prompt: unknown agent "${input.agent}"`))

        const cfg = yield* config.get()
        const model = input.modelOverride ?? agentInfo.model
        if (!model) return yield* Effect.fail(new Error(`prompt: agent "${input.agent}" has no model configured`))
        const [providerID, ...modelParts] = model.split("/")
        const modelID = modelParts.join("/")

        const messageID = newMessageID()

        // 1. Append user message (if any) to the session
        if (input.parts.length > 0) {
          yield* sessions.appendUser({ sessionID: input.sessionID, parts: input.parts })
        }

        // 2. Load full message history
        const history = yield* sessions.history(input.sessionID)
        const modelMessages: ModelMessage[] = toModelMessages(history)

        // 3. Build system prompt
        const systemPrompt = buildSystemPrompt(agentInfo, cfg.instructions)

        // 4. Build AI SDK tools from the registered tools
        const aiTools = yield* Effect.all(
          (input.tools ?? []).map((t) => wrapTool(t, input.sessionID, messageID)),
        )
        const toolMap: Record<string, ReturnType<typeof aiTool>> = {}
        for (const [id, ai] of aiTools) toolMap[id] = ai

        // 5. Register the tool set for the duration of this call so any
        //    nested lookups (rare) see the scoped set.
        yield* bus.publish(PromptEvent.Started, {
          sessionID: input.sessionID,
          messageID,
        })

        const assistantInfo: AssistantMessageInfo = {
          id: messageID as unknown as MessageID,
          sessionID: input.sessionID,
          role: "assistant",
          modelID,
          providerID,
          agent: input.agent,
          tokens: { input: 0, output: 0, total: 0, cache: { read: 0, write: 0 } },
          time: { created: Date.now() },
        }

        const body = Effect.gen(function* () {
          const llm = yield* provider.model(model)
          const events = llmStream({
            model: llm,
            systemPrompt,
            messages: modelMessages,
            tools: toolMap,
            temperature: agentInfo.temperature,
            topP: agentInfo.topP,
            maxSteps: input.stepsOverride ?? agentInfo.steps,
            abortSignal: input.abort,
          })

          const partsByText = new Map<string, TextPart>()
          const partsByCall = new Map<string, ToolPart>()
          let stopReason: AssistantMessageInfo["stopReason"] = "stop"
          let usage: AssistantMessageInfo["tokens"] = assistantInfo.tokens
          let caught: Error | null = null

          yield* Stream.runForEach(events, (evt) => handleEvent(evt))
          if (caught) return yield* Effect.fail(caught)

          function handleEvent(evt: StreamEvent): Effect.Effect<void> {
            return Effect.gen(function* () {
              switch (evt.type) {
                case "start":
                  return
                case "text-delta": {
                  const existing = partsByText.get(evt.id)
                  if (existing) {
                    existing.text += evt.delta
                  } else {
                    const part: TextPart = {
                      id: newPartID(),
                      type: "text",
                      text: evt.delta,
                      time: { start: Date.now() },
                    }
                    partsByText.set(evt.id, part)
                  }
                  yield* bus.publish(PromptEvent.TextDelta, {
                    sessionID: input.sessionID,
                    messageID,
                    partID: partsByText.get(evt.id)!.id,
                    delta: evt.delta,
                  })
                  return
                }
                case "text-end": {
                  const existing = partsByText.get(evt.id)
                  if (existing?.time) existing.time.end = Date.now()
                  return
                }
                case "tool-call": {
                  const partID = newPartID()
                  const part: ToolPart = {
                    id: partID,
                    type: "tool",
                    callID: evt.toolCallId as unknown as CallID,
                    tool: evt.toolName,
                    state: {
                      status: "pending",
                      input: evt.input,
                      time: { start: Date.now() },
                    },
                  }
                  partsByCall.set(evt.toolCallId, part)
                  yield* bus.publish(PromptEvent.ToolCallStart, {
                    sessionID: input.sessionID,
                    messageID,
                    partID,
                    callID: evt.toolCallId,
                    tool: evt.toolName,
                    input: evt.input,
                  })
                  return
                }
                case "tool-result": {
                  const existing = partsByCall.get(evt.toolCallId)
                  if (!existing) return
                  existing.state = {
                    status: "completed",
                    input:
                      existing.state.status === "pending" || existing.state.status === "running"
                        ? existing.state.input
                        : undefined,
                    output: typeof evt.output === "string" ? evt.output : JSON.stringify(evt.output),
                    time: {
                      start: existing.state.time?.start ?? Date.now(),
                      end: Date.now(),
                    },
                  }
                  yield* bus.publish(PromptEvent.ToolCallEnd, {
                    sessionID: input.sessionID,
                    messageID,
                    partID: existing.id,
                    callID: evt.toolCallId,
                    tool: evt.toolName,
                    output: evt.output,
                  })
                  return
                }
                case "finish": {
                  stopReason = mapFinishReason(evt.finishReason)
                  usage = {
                    input: evt.usage.inputTokens ?? 0,
                    output: evt.usage.outputTokens ?? 0,
                    total: evt.usage.totalTokens ?? 0,
                    cache: {
                      read: evt.usage.cachedInputTokens ?? 0,
                      write: 0,
                    },
                  }
                  return
                }
                case "error": {
                  stopReason = "error"
                  caught = evt.error
                  return
                }
              }
            })
          }

          // Assemble final parts in the order they arrived: text first, then tool calls.
          const finalParts: Part[] = [
            ...Array.from(partsByText.values()),
            ...Array.from(partsByCall.values()),
          ]

          const finalInfo: AssistantMessageInfo = {
            ...assistantInfo,
            tokens: usage,
            time: { created: assistantInfo.time.created, completed: Date.now() },
            stopReason,
          }

          const saved = yield* sessions.appendAssistant({
            sessionID: input.sessionID,
            info: finalInfo,
            parts: finalParts,
          })

          yield* bus.publish(PromptEvent.Finished, {
            sessionID: input.sessionID,
            messageID,
            stopReason: stopReason ?? "stop",
            usage: evtUsage(usage),
          })

          return saved
        })

        return yield* body
      })

    return Service.of({ prompt })
  }),
)

function buildSystemPrompt(agent: AgentInfo, instructions: string[]): string {
  const parts: string[] = []
  if (agent.prompt) parts.push(agent.prompt)
  for (const inst of instructions) parts.push(inst)
  return parts.join("\n\n").trim()
}

function mapFinishReason(r: StreamEvent["type"] extends "finish" ? any : any): AssistantMessageInfo["stopReason"] {
  switch (r) {
    case "stop":
      return "stop"
    case "length":
      return "length"
    case "tool-calls":
      return "tool-calls"
    case "content-filter":
      return "content-filter"
    case "error":
      return "error"
    default:
      return "stop"
  }
}

function evtUsage(u: AssistantMessageInfo["tokens"]) {
  return {
    inputTokens: u.input,
    outputTokens: u.output,
    totalTokens: u.total,
    cachedInputTokens: u.cache.read,
  }
}

function wrapTool(tool: ToolDef, sessionID: SessionID, messageID: MessageID): Effect.Effect<[string, any]> {
  return Effect.sync(() => {
    const wrapped = aiTool({
      description: tool.description,
      inputSchema: tool.parameters as any,
      execute: async (args: any, opts: { toolCallId: string; abortSignal?: AbortSignal }) => {
        const ctx: ToolContext = {
          sessionId: sessionID,
          messageId: messageID,
          agent: "planner",
          callId: opts.toolCallId,
          abort: opts.abortSignal ?? new AbortController().signal,
          metadata: () => Effect.void,
        }
        const result = await Effect.runPromise(tool.execute(args, ctx))
        return result.output
      },
    } as any)
    return [tool.id, wrapped] as [string, any]
  })
}
