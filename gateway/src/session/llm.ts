import { Effect, Stream } from "effect"
import { streamText, type LanguageModel, type ModelMessage, type Tool as AITool, type StopCondition } from "ai"

/**
 * Thin wrapper around AI SDK's `streamText` that returns an Effect Stream
 * of the LLM events.
 *
 * Design note: OpenCode's `session/llm.ts` is 453 lines because it handles
 * multi-provider retries, structured output, Anthropic cache-control
 * injection, GPT reasoning, Gemini safety, usage normalization, etc. The
 * gateway defers those concerns — Phase 1 supports Anthropic + OpenAI with
 * their defaults. Phase 2 can add provider-specific knobs.
 */

export type StreamEvent =
  | { type: "start" }
  | { type: "text-delta"; id: string; delta: string }
  | { type: "text-end"; id: string }
  | {
      type: "tool-call"
      toolCallId: string
      toolName: string
      input: unknown
    }
  | {
      type: "tool-result"
      toolCallId: string
      toolName: string
      output: unknown
    }
  | {
      type: "finish"
      finishReason: "stop" | "length" | "tool-calls" | "content-filter" | "error" | "other" | "unknown"
      usage: {
        inputTokens?: number
        outputTokens?: number
        totalTokens?: number
        cachedInputTokens?: number
      }
    }
  | { type: "error"; error: Error }

export interface StreamInput {
  /** The LanguageModel handle (obtain via ProviderService.model). */
  model: LanguageModel
  systemPrompt: string
  messages: ModelMessage[]
  tools: Record<string, AITool>
  temperature?: number
  topP?: number
  maxSteps?: number
  abortSignal?: AbortSignal
}

/**
 * Returns an Effect Stream of LLM events. Caller must have already resolved
 * the LanguageModel (via ProviderService.model). Keeps this module free of
 * service dependencies so callers can compose it without adding R.
 */
export function stream(input: StreamInput): Stream.Stream<StreamEvent, Error> {
  return streamTextToEffect(input.model, input)
}

function streamTextToEffect(model: LanguageModel, input: StreamInput): Stream.Stream<StreamEvent, Error> {
  const result = streamText({
    model,
    system: input.systemPrompt,
    messages: input.messages,
    tools: input.tools,
    temperature: input.temperature,
    topP: input.topP,
    stopWhen: input.maxSteps ? (stepCountIs(input.maxSteps) as StopCondition<any>) : undefined,
    abortSignal: input.abortSignal,
  })

  // Pull from AI SDK's AsyncIterable<fullStream event>, map each event to
  // our narrower StreamEvent union (or null), then drop nulls. Prepend a
  // synthetic `start` frame so downstream has a known first signal.
  const raw: Stream.Stream<unknown, Error> = Stream.fromAsyncIterable(result.fullStream, (cause): Error =>
    cause instanceof Error ? cause : new Error(String(cause)),
  )

  const mapped = raw.pipe(
    Stream.map((evt: any): StreamEvent | null => mapEvent(evt)),
    Stream.filter((e): e is StreamEvent => e !== null),
  )

  const start: Stream.Stream<StreamEvent, Error> = Stream.fromArray<StreamEvent>([{ type: "start" }])
  return Stream.concat(start, mapped)
}

function mapEvent(evt: any): StreamEvent | null {
  switch (evt.type) {
    case "text-delta":
      return { type: "text-delta", id: evt.id, delta: evt.text }
    case "text-end":
      return { type: "text-end", id: evt.id }
    case "tool-call":
      return {
        type: "tool-call",
        toolCallId: evt.toolCallId,
        toolName: evt.toolName,
        input: evt.input,
      }
    case "tool-result":
      return {
        type: "tool-result",
        toolCallId: evt.toolCallId,
        toolName: evt.toolName,
        output: evt.output,
      }
    case "finish":
      return {
        type: "finish",
        finishReason: (evt.finishReason ?? "unknown") as StreamEvent["type"] extends "finish" ? any : any,
        usage: {
          inputTokens: evt.totalUsage?.inputTokens,
          outputTokens: evt.totalUsage?.outputTokens,
          totalTokens: evt.totalUsage?.totalTokens,
          cachedInputTokens: evt.totalUsage?.cachedInputTokens,
        },
      }
    case "error":
      return { type: "error", error: evt.error instanceof Error ? evt.error : new Error(String(evt.error)) }
    default:
      return null
  }
}

/** AI SDK v5 `stepCountIs` helper shim — it's exported from "ai" but only on some versions. */
function stepCountIs(n: number) {
  return ({ steps }: { steps: { text?: string }[] }) => steps.length >= n
}
