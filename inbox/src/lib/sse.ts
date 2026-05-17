/** POST-SSE parser. Browser `EventSource` only does GET, but the
 * gateway's `/plan` is a POST with a JSON body — so we have to drive
 * the stream by hand. Reads frames from a fetch `Response.body`, splits
 * on the blank-line frame separator, and calls `onEvent` for each
 * `event: <type>\ndata: <json>\n\n` pair.
 *
 * The handler receives `{type, data}` where `data` is JSON-parsed if
 * the upstream sent JSON, or the raw string otherwise. Resolves when
 * the upstream closes the stream (typically after the `done` frame),
 * rejects if the read errors. Cancel by aborting the fetch — the
 * AbortSignal propagation closes the ReadableStream which short-
 * circuits the read loop. */
export async function postSse(
	url: string,
	init: RequestInit,
	onEvent: (ev: { type: string; data: unknown }) => void,
): Promise<Response> {
	const res = await fetch(url, init);
	if (!res.ok || !res.body) return res;
	const reader = res.body.getReader();
	const decoder = new TextDecoder();
	let buffer = "";
	try {
		while (true) {
			const { done, value } = await reader.read();
			if (done) break;
			buffer += decoder.decode(value, { stream: true });
			let idx: number;
			while ((idx = buffer.indexOf("\n\n")) !== -1) {
				const frame = buffer.slice(0, idx);
				buffer = buffer.slice(idx + 2);
				dispatch(frame, onEvent);
			}
		}
		// Flush any trailing frame that didn't end in \n\n.
		if (buffer.trim()) dispatch(buffer, onEvent);
	} finally {
		reader.releaseLock();
	}
	return res;
}

function dispatch(
	frame: string,
	onEvent: (ev: { type: string; data: unknown }) => void,
) {
	const lines = frame.split("\n");
	let type = "message";
	const dataLines: string[] = [];
	for (const line of lines) {
		if (line.startsWith("event:")) type = line.slice("event:".length).trim();
		else if (line.startsWith("data:"))
			dataLines.push(line.slice("data:".length).trim());
	}
	if (dataLines.length === 0) return;
	const raw = dataLines.join("\n");
	let data: unknown = raw;
	try {
		data = JSON.parse(raw);
	} catch {
		/* leave as string */
	}
	onEvent({ type, data });
}
