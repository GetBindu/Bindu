import { randomUUID } from "crypto"
import type { PeerAuth } from "../auth/resolver"
import type { LocalIdentity } from "../identity/local"
import type { TokenProvider } from "../identity/hydra-token"
import { Task, isTerminal, needsCallerAction, type Message } from "../protocol/types"
import { Normalize } from "../protocol"
import { BinduError, ErrorCode, SCHEMA_MISMATCH_CODES } from "../protocol/jsonrpc"
import { rpc, type RpcInput } from "./fetch"

/**
 * message/send + tasks/get polling client.
 *
 * Primary flow (per Phase 0 + Bindu docs):
 *   1. POST / method=message/send — get a Task (usually in "submitted")
 *   2. POST / method=tasks/get — poll until terminal state
 *   3. If the task hits `input-required` / `auth-required` /
 *      `payment-required` / `trust-verification-required`, return the
 *      partial Task with a typed state so the planner can decide what to
 *      do (ask user, refresh creds, etc.).
 *
 * Casing resilience: sends `taskId` (camelCase) by default — Phase 0
 * confirmed this is what Bindu accepts. If the first poll returns
 * -32700 or -32602 (both observed as "schema mismatch" codes), we flip to
 * `task_id` once and retry.
 */

const DEFAULT_BACKOFF_MS = [500, 1000, 1000, 2000, 2000, 5000, 5000, 10000] as const
const DEFAULT_MAX_POLLS = 60

export interface SendAndPollInput {
  peerUrl: string
  /** Peer auth descriptor — rpc builds headers per-call. */
  auth?: PeerAuth
  /** Gateway identity — required iff ``auth.type === "did_signed"``. */
  identity?: LocalIdentity
  /** Gateway token provider — used by did_signed peers that omit
   *  ``tokenEnvVar``. */
  tokenProvider?: TokenProvider
  /** Extra static headers (tracing, etc.) merged on top of auth. */
  extraHeaders?: Record<string, string>
  message: Message
  /** Output MIME types to include in `configuration.acceptedOutputModes`. */
  acceptedOutputModes?: string[]
  /** Optional preferences (passthrough). */
  preferences?: Record<string, unknown>
  /** Caller-owned abort signal. Aborting it wakes the poll loop
   *  immediately (not at the next backoff boundary), issues a
   *  best-effort ``tasks/cancel`` to the peer, and throws
   *  ``BinduError.aborted("signal", …)``. */
  signal?: AbortSignal
  /** Per-HTTP-round-trip timeout forwarded to ``rpc()``. Unrelated to
   *  ``deadlineMs``, which bounds the whole poll lifecycle. */
  timeoutMs?: number
  fetch?: typeof fetch
  /** Tuning for polling cadence + bound. */
  backoffMs?: readonly number[]
  maxPolls?: number
  /** Wall-clock ceiling for the entire send + poll lifecycle. On
   *  expiry, same behavior as an aborted ``signal`` but throws
   *  ``BinduError.aborted("deadline", …)``. The planner uses this to
   *  enforce the plan-level ``preferences.timeout_ms``. */
  deadlineMs?: number
}

export interface SendAndPollOutcome {
  task: Task
  /** True if the task reached a terminal state inside this call. */
  terminal: boolean
  /** True if the task is waiting for caller action (input/auth/payment). */
  needsAction: boolean
  /** Number of tasks/get polls executed. */
  polls: number
}

export async function sendAndPoll(input: SendAndPollInput): Promise<SendAndPollOutcome> {
  // Merge the caller's signal with an internal deadline timer into one
  // controller. ``rpc()`` receives the merged signal so in-flight HTTP
  // aborts immediately on either trigger; the poll loop's abortable
  // sleep watches the same signal.
  const merged = mergeAbort(input.signal, input.deadlineMs)

  const baseRpc: Omit<RpcInput, "request"> = {
    peerUrl: input.peerUrl,
    auth: input.auth,
    identity: input.identity,
    tokenProvider: input.tokenProvider,
    extraHeaders: input.extraHeaders,
    signal: merged.signal,
    timeoutMs: input.timeoutMs,
    fetch: input.fetch,
  }

  try {
    // 1. message/send
    if (merged.signal.aborted) throw abortError(merged, input.peerUrl)

    const sendResp = await rpc<unknown>({
      ...baseRpc,
      request: {
        jsonrpc: "2.0",
        method: "message/send",
        id: randomUUID(),
        params: {
          message: input.message,
          configuration: {
            acceptedOutputModes: input.acceptedOutputModes ?? ["text/plain", "application/json"],
          },
          ...(input.preferences ? { preferences: input.preferences } : {}),
        },
      },
    })

    if (!sendResp.ok) {
      if (merged.signal.aborted) throw abortError(merged, input.peerUrl)
      throw sendResp.error
    }

    const initial = parseTask(sendResp.result, input.peerUrl)
    const submittedId = initial.id

    // First response may already be terminal (rare but possible for sync-ish agents)
    if (isTerminal(initial.status.state)) {
      return { task: initial, terminal: true, needsAction: false, polls: 0 }
    }
    if (needsCallerAction(initial.status.state)) {
      return { task: initial, terminal: false, needsAction: true, polls: 0 }
    }

    // 2. poll loop
    const backoff = input.backoffMs ?? DEFAULT_BACKOFF_MS
    const maxPolls = input.maxPolls ?? DEFAULT_MAX_POLLS
    let paramCasing: "camel" | "snake" = "camel"
    let lastTask = initial
    let polls = 0

    for (let i = 0; i < maxPolls; i++) {
      try {
        await abortableSleep(backoff[Math.min(i, backoff.length - 1)], merged.signal)
      } catch {
        // Abort fired mid-sleep — issue best-effort cancel, then throw.
        await cancel(baseRpcNoSignal(baseRpc), submittedId).catch(() => {})
        throw abortError(merged, input.peerUrl, { lastState: lastTask.status.state })
      }
      polls += 1

      const pollResp = await rpc<unknown>({
        ...baseRpc,
        request: {
          jsonrpc: "2.0",
          method: "tasks/get",
          id: randomUUID(),
          params: paramCasing === "camel" ? { taskId: submittedId } : { task_id: submittedId },
        },
      })

      if (!pollResp.ok) {
        if (merged.signal.aborted) {
          await cancel(baseRpcNoSignal(baseRpc), submittedId).catch(() => {})
          throw abortError(merged, input.peerUrl, { lastState: lastTask.status.state })
        }
        // Schema-mismatch: flip casing ONCE and retry without counting this against the poll budget.
        if (SCHEMA_MISMATCH_CODES.includes(pollResp.error.code) && paramCasing === "camel") {
          paramCasing = "snake"
          i -= 1
          continue
        }
        if (SCHEMA_MISMATCH_CODES.includes(pollResp.error.code) && paramCasing === "snake") {
          // Already flipped once; give up.
          throw pollResp.error
        }
        // Other errors propagate
        throw pollResp.error
      }

      lastTask = parseTask(pollResp.result, input.peerUrl)

      if (isTerminal(lastTask.status.state)) {
        return { task: lastTask, terminal: true, needsAction: false, polls }
      }
      if (needsCallerAction(lastTask.status.state)) {
        return { task: lastTask, terminal: false, needsAction: true, polls }
      }
    }

    // Exhausted without terminal state. Best-effort cancel, then fail.
    await cancel(baseRpcNoSignal(baseRpc), submittedId).catch(() => {
      /* best-effort; ignore */
    })
    throw new BinduError(ErrorCode.InternalError, `poll exhausted after ${polls} attempts`, {
      peer: input.peerUrl,
      data: { lastState: lastTask.status.state },
    })
  } finally {
    merged.cleanup()
  }
}

/**
 * Strip the merged signal from the rpc base when issuing a best-effort
 * ``tasks/cancel`` after abort. The merged signal is already aborted at
 * that point, which would cause the cancel RPC to fail instantly — defeating
 * the "tell the peer to stop" intent. The per-HTTP timeoutMs still bounds
 * the cancel attempt.
 */
function baseRpcNoSignal(base: Omit<RpcInput, "request">): Omit<RpcInput, "request"> {
  return { ...base, signal: undefined }
}

interface MergedAbort {
  signal: AbortSignal
  /** ``"deadline"`` once the deadline timer has fired. */
  reason: "signal" | "deadline" | null
  cleanup: () => void
}

function mergeAbort(caller: AbortSignal | undefined, deadlineMs: number | undefined): MergedAbort {
  const ac = new AbortController()
  const state: MergedAbort = {
    signal: ac.signal,
    reason: null,
    cleanup: () => {},
  }

  const onCallerAbort = () => {
    if (state.reason === null) state.reason = "signal"
    ac.abort()
  }

  if (caller) {
    if (caller.aborted) {
      state.reason = "signal"
      ac.abort()
    } else {
      caller.addEventListener("abort", onCallerAbort, { once: true })
    }
  }

  let timer: ReturnType<typeof setTimeout> | null = null
  if (typeof deadlineMs === "number" && deadlineMs > 0 && !ac.signal.aborted) {
    timer = setTimeout(() => {
      if (state.reason === null) state.reason = "deadline"
      ac.abort()
    }, deadlineMs)
  }

  state.cleanup = () => {
    if (timer) clearTimeout(timer)
    if (caller) caller.removeEventListener("abort", onCallerAbort)
  }

  return state
}

function abortError(merged: MergedAbort, peer: string, extra?: Record<string, unknown>): BinduError {
  const reason = merged.reason ?? "signal"
  return BinduError.aborted(reason, peer, extra)
}

export async function cancel(base: Omit<RpcInput, "request">, taskId: string): Promise<void> {
  const resp = await rpc<unknown>({
    ...base,
    request: {
      jsonrpc: "2.0",
      method: "tasks/cancel",
      id: randomUUID(),
      params: { taskId },
    },
  })
  if (!resp.ok && resp.error.code !== ErrorCode.TaskNotCancelable) {
    throw resp.error
  }
}

function parseTask(raw: unknown, peerUrl: string): Task {
  const normalized = Normalize.fromWire("task", raw)
  const parsed = Task.safeParse(normalized)
  if (!parsed.success) {
    throw new BinduError(
      ErrorCode.InvalidAgentResponse,
      `peer returned invalid Task shape: ${parsed.error.message}`,
      { peer: peerUrl, data: raw },
    )
  }
  return parsed.data
}

function abortableSleep(ms: number, signal: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
    if (signal.aborted) {
      reject(new Error("aborted"))
      return
    }
    const timer = setTimeout(() => {
      signal.removeEventListener("abort", onAbort)
      resolve()
    }, ms)
    const onAbort = () => {
      clearTimeout(timer)
      reject(new Error("aborted"))
    }
    signal.addEventListener("abort", onAbort, { once: true })
  })
}
