import { Effect } from "effect"
import { tool as aiTool } from "ai"
import type { Def as ToolDef, Context as ToolContext } from "../tool/tool"
import type { AssistantMessageInfo } from "./message"
import type { SessionID, MessageID } from "./schema"
import type { Info as AgentInfo } from "../agent"
import {
	type ToolCallRecord,
	doomLoopBailMessage,
	hashToolInput,
	isDoomLoop,
} from "./doom-loop"

/**
 * Helpers extracted from `./prompt.ts` — pure/near-pure logic that has no
 * reason to live inside the layer factory. Keeping them here lets the main
 * prompt loop stay focused on orchestration.
 */

export function buildSystemPrompt(
  agent: AgentInfo,
  instructions: string[],
  recipeSummary?: string,
): string {
  const parts: string[] = []
  if (agent.prompt) parts.push(agent.prompt)
  if (recipeSummary) parts.push(recipeSummary)
  for (const inst of instructions) parts.push(inst)
  return parts.join("\n\n").trim()
}

export function mapFinishReason(r: unknown): AssistantMessageInfo["stopReason"] {
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

export function evtUsage(u: AssistantMessageInfo["tokens"]) {
  return {
    inputTokens: u.input,
    outputTokens: u.output,
    totalTokens: u.total,
    cachedInputTokens: u.cache.read,
  }
}

/**
 * Adapt a gateway `ToolDef` into an AI SDK `tool()` — bridging Effect-based
 * execution into the AI SDK's Promise-based `execute`. Metadata returned by
 * the tool is stashed in `metadataByCall` keyed on toolCallId, because the
 * AI SDK's tool result can only carry a string.
 *
 * `recentCalls` is a session-scoped sliding log used by the doom-loop
 * detector. Each invocation pushes its `(tool, inputHash)`; before pushing,
 * the helper checks whether the previous (THRESHOLD - 1) entries already
 * match — if so, the actual `execute` is skipped and a synthetic "stop
 * retrying" message is returned to the LLM. The model receives it as a
 * tool result and can recover within the same agentic turn.
 */
export function wrapTool(
  tool: ToolDef,
  sessionID: SessionID,
  messageID: MessageID,
  metadataByCall: Map<string, Record<string, unknown>>,
  recentCalls: ToolCallRecord[],
): Effect.Effect<[string, any]> {
  return Effect.sync(() => {
    const wrapped = aiTool({
      description: tool.description,
      inputSchema: tool.parameters as any,
      execute: async (args: any, opts: { toolCallId: string; abortSignal?: AbortSignal }) => {
        const incoming: ToolCallRecord = {
          tool: tool.id,
          inputHash: hashToolInput(args),
        }
        if (isDoomLoop(recentCalls, incoming)) {
          // Record the bailed call too so the next identical one still
          // sees a saturated tail and bails as well. The model has to do
          // something different to break out.
          recentCalls.push(incoming)
          return doomLoopBailMessage(tool.id)
        }
        recentCalls.push(incoming)
        const ctx: ToolContext = {
          sessionId: sessionID,
          messageId: messageID,
          agent: "planner",
          callId: opts.toolCallId,
          abort: opts.abortSignal ?? new AbortController().signal,
          metadata: () => Effect.void,
        }
        const result = await Effect.runPromise(tool.execute(args, ctx))
        if (result.metadata) {
          metadataByCall.set(opts.toolCallId, result.metadata as Record<string, unknown>)
        }
        return result.output
      },
    } as any)
    return [tool.id, wrapped] as [string, any]
  })
}
