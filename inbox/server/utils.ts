import { existsSync, readFileSync, statSync } from "node:fs";
import net from "node:net";
import { homedir } from "node:os";
import path from "node:path";
import tls from "node:tls";
import {
	Agent,
	fetch as undiciFetch,
	type Dispatcher,
	type RequestInit as UndiciRequestInit,
} from "undici";

/** Like `fetch`, but accepts an undici `dispatcher` and routes through
 * undici's own fetch implementation so the dispatcher contract matches.
 *
 * Why this exists: Node 22 ships a bundled undici (6.x) used by global
 * `fetch`. Our `package.json` pins undici@8 because we need the v8
 * dispatcher API (Agent options around TLS, ALPN, etc.). Cross-version
 * passing — a global-fetch call with an undici-8 Agent as `dispatcher` —
 * fails at runtime with `"invalid onRequestStart method"` because the
 * dispatcher protocol drifted between v6 and v8.
 *
 * Calling sites that need a dispatcher MUST go through this helper.
 * Sites that don't pass a dispatcher can keep using the global `fetch`
 * — those paths don't trip the version mismatch. Cast on return is a
 * type-only fix: at runtime, undici's Response is a Web-spec Response,
 * but the .d.ts types disagree on field nullability for `body` and
 * `headers`, which would otherwise infect every caller. */
export async function dispatcherFetch(
	url: string,
	init: UndiciRequestInit & { dispatcher: Dispatcher },
): Promise<Response> {
	const res = await undiciFetch(url, init);
	return res as unknown as Response;
}

/** Trust bundle = our private step-ca + Node's default Mozilla roots.
 *
 *  Setting `ca` on undici.Agent.connect REPLACES Node's default CA store
 *  rather than augmenting it (Node TLS docs). If we passed just our
 *  step-ca bundle, every HTTPS call through this dispatcher to a peer
 *  with a public CA (Let's Encrypt, DigiCert, etc.) would fail with
 *  UNABLE_TO_VERIFY_LEAF_SIGNATURE. Concatenating the system roots
 *  preserves the dispatcher's ability to reach public-CA peers while
 *  still trusting our private CA.
 *
 *  `tls.rootCertificates` is the Mozilla bundle Node ships. Free to call;
 *  the array is computed once and frozen at process start. */
function withSystemRoots(caBundle: Buffer): string[] {
	return [...tls.rootCertificates, caBundle.toString("utf8")];
}

/** Loopback-only HTTPS dispatcher.
 *
 * Inbox subprocesses (the personal agent today, the gateway tomorrow) now
 * default to mTLS. Their cert is real — signed by the production Bindu
 * Intermediate CA — but its CN/SAN is the agent's DID, not "127.0.0.1",
 * so Node's stock hostname verification rejects it. We're calling our own
 * spawned-child on the loopback interface, so we deliberately skip the
 * verify here. Outbound-to-peers (Phase B) gets a properly verifying
 * dispatcher with a CA bundle + client cert.
 */
export const insecureLoopbackDispatcher = new Agent({
	connect: { rejectUnauthorized: false },
});

/* -------------------------------------------------------------------------- */
/*  Peer-A2A dispatcher (Phase B)                                             */
/* -------------------------------------------------------------------------- */

/** Resolve the personal agent's PKI dir. The personal-agent spawner writes
 *  cert/key/CA-bundle here once the agent has bootstrapped (Phase A wired
 *  the env that triggers the bootstrap). */
const PERSONAL_PKI_DIR =
	process.env.BINDU_PERSONAL_PKI_DIR ??
	path.join(homedir(), ".bindu", "personal", ".bindu");
const CERT_PATH = path.join(PERSONAL_PKI_DIR, "tls_cert.pem");
const KEY_PATH = path.join(PERSONAL_PKI_DIR, "tls_key.pem");
const CA_PATH = path.join(PERSONAL_PKI_DIR, "ca_bundle.pem");

let cachedPeerDispatcher: { agent: Agent; mtimeMs: number } | null = null;

/** Returns an undici Agent that presents the personal agent's mTLS cert
 *  on outbound A2A calls and trusts peers signed by the same private CA.
 *
 *  Behavior:
 *    - If cert files don't exist yet (personal agent not spawned): returns
 *      undefined → caller falls back to the default (no client cert).
 *    - On HTTP destinations the dispatcher options are ignored; works.
 *    - On HTTPS destinations we present the cert and trust ONLY the
 *      bundled CA. Cert SANs are DIDs, not hostnames, so hostname
 *      verification is disabled — identity is enforced at the app layer
 *      via X-DID-Signature (a2aHeaders) and the cert chain still has
 *      to reach our Root CA.
 *    - File mtime is checked on every call; the cert renews every ~16h
 *      and we pick the new one up automatically without restart.
 */
export function buildPeerDispatcher(): Agent | undefined {
	if (!existsSync(CERT_PATH) || !existsSync(KEY_PATH) || !existsSync(CA_PATH)) {
		return undefined;
	}
	const mtimeMs = statSync(CERT_PATH).mtimeMs;
	if (cachedPeerDispatcher && cachedPeerDispatcher.mtimeMs === mtimeMs) {
		return cachedPeerDispatcher.agent;
	}
	const agent = new Agent({
		connect: {
			cert: readFileSync(CERT_PATH),
			key: readFileSync(KEY_PATH),
			ca: withSystemRoots(readFileSync(CA_PATH)),
			// Peer cert SANs are DIDs (did:bindu:...), not hostnames. We
			// rely on (a) chain verification against our private CA and
			// (b) app-layer DID signature verification via a2aHeaders.
			checkServerIdentity: () => undefined,
		},
	});
	cachedPeerDispatcher = { agent, mtimeMs };
	return agent;
}

/* -------------------------------------------------------------------------- */
/*  DID-pinned dispatcher (Option C)                                          */
/* -------------------------------------------------------------------------- */

/** Per-DID cache so we don't re-build a TLS Agent on every inspector hit.
 *  Keyed by `<expectedDid>@<mtimeMs>` so cert rotation invalidates entries
 *  the same way buildPeerDispatcher does. */
const didPinnedCache = new Map<string, Agent>();

/** Parse the comma-separated `subjectaltname` string Node hands to
 *  checkServerIdentity into the list of underlying values. Format is
 *  `URI:did:bindu:..., DNS:foo, IP Address:127.0.0.1` — we strip the
 *  type prefix so a caller can match on the raw URI/DNS/IP string. */
function parseSans(subjectaltname: string | undefined): string[] {
	if (!subjectaltname) return [];
	return subjectaltname
		.split(",")
		.map((s) => s.trim())
		.map((s) => s.replace(/^(URI|DNS|IP Address|email):/i, ""));
}

/** Loopback HTTPS dispatcher that pins BOTH the cert chain (to our private
 *  CA) AND the peer's identity (to a specific DID present in the cert SAN).
 *
 *  This is the secure choice for talking to a known-DID spawned child like
 *  the personal agent. Stronger than buildPeerDispatcher() because it
 *  rejects valid-but-wrong-DID certs from our own CA — i.e. it survives
 *  a hypothetical "someone else got a cert from step-ca" scenario.
 *
 *  Returns undefined when cert files aren't on disk yet (first-spawn
 *  window). Callers fall back to insecureLoopbackDispatcher in that case
 *  — there's no DID to pin against before the agent has bootstrapped.
 */
export function buildLoopbackDispatcherForDid(
	expectedDid: string,
): Agent | undefined {
	if (!existsSync(CERT_PATH) || !existsSync(KEY_PATH) || !existsSync(CA_PATH)) {
		return undefined;
	}
	const mtimeMs = statSync(CERT_PATH).mtimeMs;
	const cacheKey = `${expectedDid}@${mtimeMs}`;
	const cached = didPinnedCache.get(cacheKey);
	if (cached) return cached;

	const agent = new Agent({
		connect: {
			cert: readFileSync(CERT_PATH),
			key: readFileSync(KEY_PATH),
			ca: withSystemRoots(readFileSync(CA_PATH)),
			// Two-layer identity check: chain must reach our private CA
			// (handled by `ca` above + Node's default chain verify), AND
			// the cert SAN must include the DID we expected. Without the
			// SAN check, any cert from our CA would be accepted — defeating
			// the point of pinning. The cert object Node hands us exposes
			// SANs as a comma-separated string in `subjectaltname`.
			checkServerIdentity: (_hostname, cert) => {
				const sans = parseSans(cert.subjectaltname);
				if (sans.includes(expectedDid)) return undefined;
				return new Error(
					`cert SAN [${sans.join(", ")}] does not include expected DID ${expectedDid}`,
				);
			},
		},
	});
	didPinnedCache.set(cacheKey, agent);
	return agent;
}

/** Heuristic: is this URL a loopback HTTPS destination we spawned?
 *  Used by callers that want to pick between the DID-pinned dispatcher
 *  (loopback child) and default fetch (external peer with public CA). */
export function isLoopbackHttpsUrl(url: string): boolean {
	try {
		const u = new URL(url);
		if (u.protocol !== "https:") return false;
		return u.hostname === "127.0.0.1" || u.hostname === "localhost" || u.hostname === "::1";
	} catch {
		return false;
	}
}

/** Pick the right undici dispatcher for a server-side fetch to a Bindu
 *  agent endpoint (well-known docs, /agent/skills, /health, etc.). Three
 *  buckets:
 *
 *    1. Loopback HTTPS spawned child (the personal agent today, the
 *       gateway tomorrow). Cert is signed by our private step-ca and
 *       the SAN is a DID, not the hostname. Plain fetch fails both
 *       chain verify and hostname verify. Returns a DID-pinned
 *       dispatcher if `expectedDid` is known, otherwise the insecure
 *       loopback dispatcher (rejectUnauthorized:false) as a cold-start
 *       fallback.
 *
 *    2. External HTTPS peer (public CA). Returns undefined → caller
 *       uses plain fetch, Node verifies against Mozilla roots. The
 *       DID-pinned dispatcher would reject these since their certs
 *       are not from our private CA.
 *
 *    3. HTTP destination. Returns undefined → plain fetch; dispatcher
 *       wouldn't do anything useful here anyway.
 *
 *  Returning undefined is a feature: callers can spread the result as
 *  `...(d ? { dispatcher: d } : {})` and the type system stays clean.
 */
export function pickPeerDispatcher(
	base: string,
	expectedDid: string | null,
): Agent | undefined {
	if (!isLoopbackHttpsUrl(base)) return undefined;
	if (expectedDid) {
		return buildLoopbackDispatcherForDid(expectedDid) ?? insecureLoopbackDispatcher;
	}
	return insecureLoopbackDispatcher;
}

/** Ask the OS for an unused TCP port on 127.0.0.1. Used by both the
 * gateway spawner (index.ts) and the personal-agent spawner so we don't
 * collide with whatever's already running. The OS guarantees the port
 * is free at the moment we close the probe socket; a race with another
 * process binding it before our child does is possible but vanishingly
 * rare on a single-user laptop. */
export function pickFreePort(): Promise<number> {
	return new Promise((resolveOk, rejectErr) => {
		const srv = net.createServer();
		srv.unref();
		srv.on("error", rejectErr);
		srv.listen(0, "127.0.0.1", () => {
			const addr = srv.address();
			srv.close(() => {
				if (typeof addr === "object" && addr && "port" in addr) {
					resolveOk(addr.port);
				} else {
					rejectErr(new Error("server.address() returned unexpected shape"));
				}
			});
		});
	});
}

/** Poll `${url}/health` every 400ms until it 2xxs or `timeoutMs` elapses.
 * Pass an AbortSignal to cancel early when the parent abandons the wait
 * (the personal-agent spawner doesn't currently use this — index.ts does
 * via its in-flight spawn dedupe). */
export async function pollHealth(
	url: string,
	timeoutMs: number,
	signal?: AbortSignal,
): Promise<boolean> {
	const start = Date.now();
	while (Date.now() - start < timeoutMs) {
		if (signal?.aborted) return false;
		try {
			const r = await dispatcherFetch(`${url}/health`, {
				signal: signal ?? undefined,
				// Spawned children may be on HTTPS with a DID-named cert;
				// see insecureLoopbackDispatcher above. Peers on the public
				// internet are unaffected (their certs verify normally
				// regardless of this dispatcher).
				dispatcher: insecureLoopbackDispatcher,
			});
			if (r.ok) return true;
		} catch {
			/* ECONNREFUSED while the child is still booting — keep trying */
		}
		await new Promise((res) => setTimeout(res, 400));
	}
	return false;
}
