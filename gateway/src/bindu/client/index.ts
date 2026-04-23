import { Context, Effect, Layer } from "effect"
import { randomUUID } from "crypto"
import type { Message, Part, Task } from "../protocol/types"
import { sendAndPoll, type SendAndPollOutcome } from "./poll"
import { type PeerAuth } from "../auth/resolver"
import type { LocalIdentity } from "../identity/local"
import type { TokenProvider } from "../identity/hydra-token"
import { BinduError, ErrorCode } from "../protocol/jsonrpc"
import { verifyArtifact } from "../identity/verify"
import { createResolver, primaryPublicKeyBase58 } from "../identity/resolve"
import { getPeerDID } from "../protocol/identity"
import type { AgentCard } from "../protocol/agent-card"
import { fetchAgentCard } from "./agent-card"

/**
 * Public Bindu client — the thing the planner's tools invoke.
 *
 * `callPeer` turns a typed (peer, skill, input) triple into:
 *   1. A `message/send` with proper UUIDs + camelCase params
 *   2. A polling loop until terminal/needs-action
 *   3. Optional signature verification on returned artifacts (when the
 *      peer config enables `trust.verifyDID`)
 *
 * Returns the Task + metadata about verification. The planner (Day 9)
 * unpacks artifacts and feeds them back into the loop.
 */

export interface PeerDescriptor {
  /** Friendly name from the agent catalog (e.g. "research"). */
  name: string
  /** Peer root URL (e.g. "https://research.acme.com"). Comes from the
   *  External caller's agent catalog, never from AgentCard.url (Phase 0
   *  finding — that field is sometimes incomplete). */
  url: string
  auth?: PeerAuth
  /** Cached AgentCard if we've fetched it for this session; enables
   *  DID-based signature verification. */
  card?: AgentCard
  trust?: {
    verifyDID?: boolean
    pinnedDID?: string
  }
}

export interface CallPeerInput {
  peer: PeerDescriptor
  /** Skill id on the peer (informational; tools surface this). */
  skill?: string
  /** Input payload — plain string (wrapped as TextPart) or structured Parts. */
  input: string | Part[]
  /** Context id (one per gateway session). */
  contextId: string
  /** Task lineage for dependent tool calls. */
  referenceTaskIds?: string[]
  signal?: AbortSignal
  timeoutMs?: number
  acceptedOutputModes?: string[]
}

export interface CallPeerOutcome {
  task: Task
  terminal: boolean
  needsAction: boolean
  polls: number
  /** Signature verification result, or `null` if verification not enabled. */
  signatures: {
    ok: boolean
    signed: number
    verified: number
    unsigned: number
  } | null
}

export interface Interface {
  readonly callPeer: (input: CallPeerInput) => Effect.Effect<CallPeerOutcome, BinduError>
  readonly cancel: (input: { peer: PeerDescriptor; taskId: string }) => Effect.Effect<void, BinduError>
}

export class Service extends Context.Service<Service, Interface>()("@bindu/Client") {}

/**
 * Build the Client layer with the gateway's DID identity and an
 * optional Hydra token provider.
 *
 * ``identity`` lets the gateway talk to ``did_signed`` peers —
 * every outbound call to such a peer is signed with this identity's
 * private key. For ``bearer`` / ``bearer_env`` / ``none`` peers,
 * identity is ignored.
 *
 * ``tokenProvider`` is the auto path for the OAuth bearer: when a
 * ``did_signed`` peer omits ``tokenEnvVar``, the gateway calls
 * ``tokenProvider.getToken()`` to get a fresh-or-cached Hydra
 * access_token. Safe to omit if all ``did_signed`` peers explicitly
 * set ``tokenEnvVar`` (the federated pattern), or if the gateway
 * doesn't talk to any ``did_signed`` peers.
 *
 * Exported as a factory so ``index.ts`` can wire the identity and
 * token provider at boot. The default ``layer`` export below is a
 * zero-argument variant for backward compat with existing tests and
 * deployments that don't enable DID signing.
 */
export const makeLayer = (
  identity?: LocalIdentity,
  tokenProvider?: TokenProvider,
) =>
  Layer.effect(
    Service,
    Effect.sync(() => {
      const didResolver = createResolver()

      const callPeer: Interface["callPeer"] = (input) =>
        Effect.tryPromise({
          try: () => runCall(input, didResolver, identity, tokenProvider),
          catch: (e) =>
            e instanceof BinduError
              ? e
              : BinduError.transport(
                  e instanceof Error ? e.message : String(e),
                  input.peer.url,
                  e,
                ),
        })

      const cancel: Interface["cancel"] = ({ peer, taskId }) =>
        Effect.tryPromise({
          try: () => runCancel(peer, taskId, identity, tokenProvider),
          catch: (e) =>
            e instanceof BinduError
              ? e
              : BinduError.transport(
                  e instanceof Error ? e.message : String(e),
                  peer.url,
                  e,
                ),
        })

      return Service.of({ callPeer, cancel })
    }),
  )

/** Default layer — no identity, no token provider. ``did_signed``
 *  peers will fail at call time with a clear error pointing at
 *  ``makeLayer(identity, tokenProvider)``. */
export const layer = makeLayer(undefined, undefined)

async function runCall(
  input: CallPeerInput,
  didResolver: ReturnType<typeof createResolver>,
  identity: LocalIdentity | undefined,
  tokenProvider: TokenProvider | undefined,
): Promise<CallPeerOutcome> {
  // Populate peer.card from /.well-known/agent.json on first contact.
  // Cached per process — subsequent calls to the same peer are free.
  // This activates the AgentCard-based DID fallback in
  // maybeVerifySignatures: when the caller enabled `trust.verifyDID`
  // without pinning a DID, the gateway recovers the peer's published
  // DID here and verifies against its public key.
  //
  // Runs concurrently-safe (cache handles races via last-write-wins,
  // AgentCards are stable), non-blocking on failure (returns null,
  // peer.card stays undefined, verification falls through to the
  // pinnedDID-only path).
  if (!input.peer.card && input.peer.trust?.verifyDID) {
    const card = await fetchAgentCard(input.peer.url, { signal: input.signal })
    if (card) input.peer.card = card
  }

  const parts: Part[] =
    typeof input.input === "string" ? [{ kind: "text", text: input.input }] : input.input

  const message: Message = {
    messageId: randomUUID(),
    contextId: input.contextId,
    taskId: randomUUID(),
    kind: "message",
    role: "user",
    parts,
    ...(input.referenceTaskIds && input.referenceTaskIds.length > 0
      ? { referenceTaskIds: input.referenceTaskIds }
      : {}),
  }

  const outcome: SendAndPollOutcome = await sendAndPoll({
    peerUrl: input.peer.url,
    auth: input.peer.auth,
    identity,
    tokenProvider,
    message,
    signal: input.signal,
    timeoutMs: input.timeoutMs,
    acceptedOutputModes: input.acceptedOutputModes,
  })

  const signatures = await maybeVerifySignatures(input.peer, outcome.task, didResolver)

  return {
    task: outcome.task,
    terminal: outcome.terminal,
    needsAction: outcome.needsAction,
    polls: outcome.polls,
    signatures,
  }
}

async function maybeVerifySignatures(
  peer: PeerDescriptor,
  task: Task,
  didResolver: ReturnType<typeof createResolver>,
): Promise<CallPeerOutcome["signatures"]> {
  if (!peer.trust?.verifyDID) return null
  if (!task.artifacts || task.artifacts.length === 0) return null

  const did = peer.trust.pinnedDID ?? (peer.card ? getPeerDID(peer.card) : null)
  if (!did) return null

  // Fetch (or hit cache) for the DID Document, extract the primary key.
  const doc = await didResolver.resolve(peer.url, did).catch(() => null)
  if (!doc) return null
  const pubkey = primaryPublicKeyBase58(doc)
  if (!pubkey) return null

  let signed = 0
  let verified = 0
  let unsigned = 0
  for (const art of task.artifacts) {
    const outcome = await verifyArtifact({
      parts: art.parts ?? [],
      publicKeyBase58: pubkey,
    })
    signed += outcome.signed
    verified += outcome.verified
    unsigned += outcome.unsigned
  }
  return {
    ok: signed === 0 ? true : signed === verified,
    signed,
    verified,
    unsigned,
  }
}

async function runCancel(
  peer: PeerDescriptor,
  taskId: string,
  identity: LocalIdentity | undefined,
  tokenProvider: TokenProvider | undefined,
): Promise<void> {
  const { cancel } = await import("./poll")
  await cancel(
    { peerUrl: peer.url, auth: peer.auth, identity, tokenProvider },
    taskId,
  )
}
