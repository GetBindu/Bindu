import net from "node:net";

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
			const r = await fetch(`${url}/health`, { signal });
			if (r.ok) return true;
		} catch {
			/* ECONNREFUSED while the child is still booting — keep trying */
		}
		await new Promise((res) => setTimeout(res, 400));
	}
	return false;
}
