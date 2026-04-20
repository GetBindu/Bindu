import type { ModelMessage, LanguageModel } from "ai"
import { generateText } from "ai"
import type { MessageWithParts } from "./message"
import { toModelMessages } from "./message"

/**
 * Summarize a run of older messages into a compact paragraph so they can be
 * replaced by a single synthetic system turn during compaction.
 *
 * The summary captures: what the user has asked, which agents have been
 * called, what artifacts came back (key facts only — not full payloads),
 * and the current state of the plan.
 *
 * Second-pass semantics: when an earlier compaction already ran for this
 * session, the caller passes `priorSummary`. We feed it to the model with
 * an explicit "facts-preservation" instruction so the new summary is a
 * SUPERSET (not a replacement) of the old one. Without this, the second
 * pass would quietly drop every fact captured by the first — see
 * gateway/src/session/compaction.ts for the lifecycle.
 *
 * We intentionally keep this single-pass and cheap. OpenCode's equivalent
 * (`session/summary.ts` + `session/compaction.ts`) does a more sophisticated
 * multi-step reduction; for Phase 1, a one-shot summary is sufficient.
 */

const SUMMARY_SYSTEM = `You are a session compaction summarizer for the Bindu Gateway.
You receive a list of messages representing recent multi-agent work: user
questions, planner reasoning, agent tool calls, and agent responses. You may
also receive a PRIOR SUMMARY produced by an earlier compaction pass.

Your job: produce ONE concise paragraph (≤ 400 words) that captures ALL of:
1. What the user has asked (the running goal)
2. Which remote agents have been called and for what sub-task
3. The KEY FACTS returned by each agent — not full quotes, just the load-bearing details the planner will need to answer remaining questions
4. The current state of the plan: what's done, what remains

If a PRIOR SUMMARY is provided:
- Treat its facts as authoritative and CARRY THEM FORWARD into your output.
- You may rephrase for concision, but MUST preserve every named entity,
  quoted result, decision, and translation present in the prior summary.
- Add new facts from the new messages; do not drop old ones to make room.
- The new summary must be a SUPERSET of the prior summary, not a replacement.

DO NOT:
- Invent facts that aren't in the messages or the prior summary
- Include agent DIDs, URLs, tokens, or any auth material
- Format as bullets; use flowing prose so it reads as context

Output the paragraph directly, no preamble.`

export interface SummarizeInput {
  model: LanguageModel
  /** Messages that will be collapsed into the summary. */
  messagesToCompact: MessageWithParts[]
  /**
   * Summary produced by a previous compaction pass for this session, if any.
   * When present, the summarizer is instructed to carry its facts forward
   * into the new summary so long sessions don't progressively forget.
   */
  priorSummary?: string | null
  abortSignal?: AbortSignal
}

export async function summarize(input: SummarizeInput): Promise<string> {
  const history: ModelMessage[] = toModelMessages(input.messagesToCompact)
  const messages: ModelMessage[] = []
  // Single truthiness check, shared by both the marker block and the
  // closing instruction — otherwise an all-whitespace priorSummary would
  // drop the marker but still reference "the PRIOR SUMMARY above",
  // confusing the model.
  const prior = input.priorSummary?.trim() ?? ""
  const hasPrior = prior.length > 0

  if (hasPrior) {
    messages.push({
      role: "user",
      content: `[PRIOR SUMMARY — preserve every fact below in your output]\n\n${prior}`,
    })
  }
  messages.push(...history)
  messages.push({
    role: "user",
    content: hasPrior
      ? "Produce ONE compact paragraph that unions the PRIOR SUMMARY above with the new messages. Follow the rules in your system message — the new summary must be a superset of the prior summary."
      : "Summarize the above session history into one compact paragraph per the rules in your system message.",
  })
  const result = await generateText({
    model: input.model,
    system: SUMMARY_SYSTEM,
    messages,
    abortSignal: input.abortSignal,
  })
  return result.text.trim()
}
