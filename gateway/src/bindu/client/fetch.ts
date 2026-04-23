import { buildAuthHeaders, type PeerAuth } from "../auth/resolver"
import type { LocalIdentity } from "../identity/local"
import type { TokenProvider } from "../identity/hydra-token"
import { BinduError, JsonRpcResponse, type JsonRpcRequest } from "../protocol/jsonrpc"

/**
 * HTTP transport for Bindu JSON-RPC calls.
 *
 * Thin wrapper over fetch() that:
 *   - serializes the JSON-RPC request body ONCE
 *   - builds auth headers per-call (async — the ``did_signed`` variant
 *     signs the serialized body)
 *   - parses the response into a typed ``{ result }`` | ``{ error }``
 *   - normalizes transport-level failures into BinduError
 *   - honors abort signal + timeout
 *
 * The "serialize once" invariant is load-bearing: the body signed by
 * the ``did_signed`` path MUST be byte-for-byte identical to the body
 * sent on the wire, or the peer's DID middleware will return
 * ``crypto_mismatch``. Never re-stringify the request between signing
 * and sending.
 *
 * Does NOT retry — retry policy lives in ``poll.ts`` where it can make
 * informed decisions (schema-mismatch flip, auth refresh, etc.).
 */

export interface RpcInput {
  /** Peer root URL (e.g. "https://research.acme.com"). Trailing slash optional. */
  peerUrl: string
  /** The JSON-RPC request body. ``id`` is caller-assigned. */
  request: JsonRpcRequest
  /** Peer auth descriptor. When present, rpc() builds the
   *  Authorization header (and X-DID-* headers for ``did_signed``)
   *  based on this. */
  auth?: PeerAuth
  /** Gateway's DID identity. Required when ``auth.type === "did_signed"``
   *  — the signer needs it to sign the body. Safe to omit for other
   *  auth types. */
  identity?: LocalIdentity
  /** Gateway's Hydra token provider. Used by ``auth.type === "did_signed"``
   *  peers that omit ``tokenEnvVar`` — they fall back to this
   *  provider (auto-acquired at boot). Safe to omit; only relevant
   *  when the gateway has a configured Hydra. */
  tokenProvider?: TokenProvider
  /** Extra headers that don't depend on the body (e.g. tracing
   *  propagation). Merged after auth headers so auth can't be
   *  overridden accidentally. */
  extraHeaders?: Record<string, string>
  signal?: AbortSignal
  /** Timeout in ms (default 60s). */
  timeoutMs?: number
  /** Optional fetch injection for tests. */
  fetch?: typeof fetch
}

export interface RpcSuccess<T = unknown> {
  ok: true
  result: T
  id: JsonRpcRequest["id"]
}
export interface RpcFailure {
  ok: false
  error: BinduError
  id: JsonRpcRequest["id"]
}
export type RpcOutcome<T = unknown> = RpcSuccess<T> | RpcFailure

export async function rpc<T = unknown>(input: RpcInput): Promise<RpcOutcome<T>> {
  const fetcher = input.fetch ?? fetch
  const url = stripTrailingSlash(input.peerUrl) + "/"
  const timeoutMs = input.timeoutMs ?? 60_000

  const ac = new AbortController()
  const forwardAbort = () => ac.abort()
  input.signal?.addEventListener("abort", forwardAbort, { once: true })
  const timer = setTimeout(() => ac.abort(), timeoutMs)

  // Serialize once. The same exact bytes are passed both to the signer
  // (when auth.type === "did_signed") and to the HTTP body — any
  // second serialization would produce different bytes and break the
  // signature.
  const bodyStr = JSON.stringify(input.request)

  try {
    const authHdrs = await buildAuthHeaders(
      input.auth,
      bodyStr,
      input.identity,
      input.tokenProvider,
    )
    const resp = await fetcher(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
        ...(input.extraHeaders ?? {}),
        ...authHdrs,
      },
      body: bodyStr,
      signal: ac.signal,
    })

    if (!resp.ok) {
      // Non-2xx. Try to extract a JSON-RPC error body.
      const text = await resp.text().catch(() => "")
      let payload: unknown
      try {
        payload = JSON.parse(text)
      } catch {
        return {
          ok: false,
          error: BinduError.transport(
            `HTTP ${resp.status} ${resp.statusText} — body not JSON (${text.slice(0, 120)})`,
            input.peerUrl,
          ),
          id: input.request.id,
        }
      }
      const parsed = JsonRpcResponse.safeParse(payload)
      if (parsed.success && parsed.data.error) {
        return {
          ok: false,
          error: BinduError.fromRpc(parsed.data.error, input.peerUrl),
          id: input.request.id,
        }
      }
      return {
        ok: false,
        error: BinduError.transport(
          `HTTP ${resp.status} ${resp.statusText}`,
          input.peerUrl,
        ),
        id: input.request.id,
      }
    }

    const raw = (await resp.json()) as unknown
    const parsed = JsonRpcResponse.safeParse(raw)
    if (!parsed.success) {
      return {
        ok: false,
        error: BinduError.transport(
          `invalid JSON-RPC envelope from peer: ${parsed.error.message}`,
          input.peerUrl,
        ),
        id: input.request.id,
      }
    }
    if (parsed.data.error) {
      return {
        ok: false,
        error: BinduError.fromRpc(parsed.data.error, input.peerUrl),
        id: parsed.data.id,
      }
    }
    return {
      ok: true,
      result: parsed.data.result as T,
      id: parsed.data.id,
    }
  } catch (e: unknown) {
    const cause = e instanceof Error ? e : new Error(String(e))
    if (cause.name === "AbortError") {
      return {
        ok: false,
        error: BinduError.transport("aborted", input.peerUrl, cause),
        id: input.request.id,
      }
    }
    return {
      ok: false,
      error: BinduError.transport(cause.message, input.peerUrl, cause),
      id: input.request.id,
    }
  } finally {
    clearTimeout(timer)
    input.signal?.removeEventListener("abort", forwardAbort)
  }
}

function stripTrailingSlash(u: string): string {
  return u.endsWith("/") ? u.slice(0, -1) : u
}
