import { existsSync, readFileSync, statSync } from "node:fs";
import net from "node:net";
import { homedir } from "node:os";
import path from "node:path";
import { Agent } from "undici";

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
			ca: readFileSync(CA_PATH),
			// Peer cert SANs are DIDs (did:bindu:...), not hostnames. We
			// rely on (a) chain verification against our private CA and
			// (b) app-layer DID signature verification via a2aHeaders.
			checkServerIdentity: () => undefined,
		},
	});
	cachedPeerDispatcher = { agent, mtimeMs };
	return agent;
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
			const r = await fetch(`${url}/health`, {
				signal,
				// Spawned children may be on HTTPS with a DID-named cert;
				// see insecureLoopbackDispatcher above. Peers on the public
				// internet are unaffected (their certs verify normally
				// regardless of this dispatcher).
				dispatcher: insecureLoopbackDispatcher,
			} as RequestInit & { dispatcher: Agent });
			if (r.ok) return true;
		} catch {
			/* ECONNREFUSED while the child is still booting — keep trying */
		}
		await new Promise((res) => setTimeout(res, 400));
	}
	return false;
}
