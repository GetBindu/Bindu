import { Hono } from "hono";
import { serve } from "@hono/node-server";

interface LiveEvent {
	id: string;
	agentId: string;
	receivedAt: string;
	payload: Record<string, unknown>;
}

interface AgentRecord {
	id: string;
	url?: string;
	did?: unknown;
	agentCard?: unknown;
	resolvedAt?: string;
}

// agentId → base URL for callbacks. Hardcoded for the dev fleet; real
// production deployments would learn this from a signed payload field.
const AGENT_URLS: Record<string, string> = {
	"agno-simple": "http://127.0.0.1:3773",
	"agno-paywall": "http://127.0.0.1:3775",
	gateway: "http://127.0.0.1:3774",
};

const events: LiveEvent[] = [];
const agents: Map<string, AgentRecord> = new Map();
const subscribers = new Set<(e: LiveEvent) => void>();

// Optional dev-time bearer token gate. When BINDU_COMMS_TOKEN is set, /api/*
// requires Authorization: Bearer <token>. Webhooks stay open (agents
// authenticate via DID/HMAC headers in the future).
const REQUIRED_TOKEN = process.env.BINDU_COMMS_TOKEN ?? "";

// Accept the token from either the Authorization header (preferred — used
// by direct API consumers / curl) OR a ?token= query param (the only way
// browser EventSource can authenticate, since it can't set headers).
//
// Query-string tokens get logged by intermediaries, so this is a
// dev-surface compromise. A real auth track would use cookies or move
// off EventSource to fetch-stream.
function authMiddleware(c: {
	req: { header: (name: string) => string | undefined; query: (name: string) => string | undefined };
}) {
	if (!REQUIRED_TOKEN) return null;
	const header = c.req.header("authorization") ?? "";
	if (header === `Bearer ${REQUIRED_TOKEN}`) return null;
	const query = c.req.query("token") ?? "";
	if (query === REQUIRED_TOKEN) return null;
	return { error: "unauthorized" } as const;
}

async function resolveAgent(agentId: string): Promise<AgentRecord> {
	const cached = agents.get(agentId);
	if (cached?.did && cached?.agentCard) return cached;
	const base = AGENT_URLS[agentId];
	const rec: AgentRecord = cached ?? { id: agentId, url: base };
	if (!base) {
		agents.set(agentId, rec);
		return rec;
	}
	try {
		const [didR, cardR] = await Promise.all([
			fetch(`${base}/.well-known/did.json`).then((r) => (r.ok ? r.json() : null)),
			fetch(`${base}/.well-known/agent.json`).then((r) => (r.ok ? r.json() : null)),
		]);
		rec.did = didR;
		rec.agentCard = cardR;
		rec.url = base;
		rec.resolvedAt = new Date().toISOString();
	} catch (err) {
		console.warn(`[resolve] ${agentId} failed:`, (err as Error).message);
	}
	agents.set(agentId, rec);
	return rec;
}

const app = new Hono();

app.post("/webhooks/bindu/:agentId", async (c) => {
	const agentId = c.req.param("agentId");
	const payload = (await c.req.json()) as Record<string, unknown>;
	const ev: LiveEvent = {
		id: String(payload.event_id ?? crypto.randomUUID()),
		agentId,
		receivedAt: new Date().toISOString(),
		payload,
	};
	events.push(ev);
	if (events.length > 1000) events.shift();
	for (const cb of subscribers) cb(ev);
	console.log(`[webhook] ${agentId} ${payload.kind ?? "?"} ${payload.task_id ?? ""}`);
	if (!agents.has(agentId)) {
		resolveAgent(agentId).catch(() => {});
	}
	return c.json({ ok: true });
});

app.get("/api/events/stream", (c) => {
	const blocked = authMiddleware(c);
	if (blocked) return c.json(blocked, 401);
	const agentFilter = c.req.query("agentId");
	const stream = new ReadableStream({
		start(controller) {
			const enc = new TextEncoder();
			const send = (e: LiveEvent) => {
				if (agentFilter && e.agentId !== agentFilter) return;
				controller.enqueue(enc.encode(`data: ${JSON.stringify(e)}\n\n`));
			};
			for (const e of events.slice(-50)) send(e);
			subscribers.add(send);
			c.req.raw.signal.addEventListener("abort", () => {
				subscribers.delete(send);
				controller.close();
			});
		},
	});
	return new Response(stream, {
		headers: {
			"content-type": "text/event-stream",
			"cache-control": "no-cache",
			connection: "keep-alive",
		},
	});
});

app.get("/api/agents", (c) => {
	const blocked = authMiddleware(c);
	if (blocked) return c.json(blocked, 401);
	return c.json(Array.from(new Set(events.map((e) => e.agentId))));
});

app.get("/api/agents/:agentId", async (c) => {
	const blocked = authMiddleware(c);
	if (blocked) return c.json(blocked, 401);
	const rec = await resolveAgent(c.req.param("agentId"));
	return c.json(rec);
});

// Phase 5: action callbacks. Looks up the source agent, sends a follow-up
// JSON-RPC message on the same context/task. Only `input` is meaningful end-
// to-end today; `approve`/`pay`/`decline` are recorded but not yet wired to
// the underlying protocol moves.
app.post("/api/events/:id/action", async (c) => {
	const blocked = authMiddleware(c);
	if (blocked) return c.json(blocked, 401);
	const evId = c.req.param("id");
	const ev = events.find((e) => e.id === evId);
	if (!ev) return c.json({ error: "event-not-found" }, 404);
	const body = (await c.req.json().catch(() => ({}))) as {
		kind?: "approve" | "decline" | "input" | "pay";
		text?: string;
	};
	const kind = body.kind ?? "approve";
	const base = AGENT_URLS[ev.agentId];
	const taskId = ev.payload.task_id as string | undefined;
	const contextId = ev.payload.context_id as string | undefined;
	console.log(`[action] ${kind} on ${evId} (agent=${ev.agentId} task=${taskId})`);

	if (kind === "input" && base && taskId && contextId) {
		const msg = {
			jsonrpc: "2.0",
			id: crypto.randomUUID(),
			method: "message/send",
			params: {
				message: {
					role: "user",
					kind: "message",
					parts: [{ kind: "text", text: body.text ?? "(continue)" }],
					messageId: crypto.randomUUID(),
					contextId,
					taskId,
				},
				configuration: { acceptedOutputModes: ["application/json"] },
			},
		};
		try {
			const r = await fetch(base, {
				method: "POST",
				headers: { "content-type": "application/json" },
				body: JSON.stringify(msg),
			});
			return c.json({ ok: r.ok, status: r.status, delivered: r.ok });
		} catch (err) {
			return c.json({ ok: false, error: (err as Error).message }, 502);
		}
	}
	// approve / decline / pay don't have protocol callbacks wired yet —
	// don't pretend they do.
	return c.json({
		ok: true,
		kind,
		recorded: true,
		protocolMovePending: true,
	});
});

serve({ fetch: app.fetch, port: 3787 }, (info) => {
	console.log(`[bindu-communication] api on http://127.0.0.1:${info.port}`);
	if (REQUIRED_TOKEN) {
		console.log(`[bindu-communication] /api/* requires Bearer token`);
	}
});
