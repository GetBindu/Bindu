/** Tiny POST-JSON helper used by every form/action site in the UI.
 *
 * Why: four components (compose modal, add-agent modal, reply box,
 * action panel) all did the same fetch + json-with-fallback + error
 * extraction dance — same shape, slightly different copy. This
 * centralises:
 *   - the headers + JSON.stringify
 *   - the `.json().catch(() => null)` so a non-JSON body doesn't throw
 *   - the convention that the server signals failure via either an
 *     HTTP status or `{ ok: false, error/detail }`
 *
 * Callers get a single `result.errMsg` string that's safe to render. */

interface ErrorShape {
	ok?: boolean;
	error?: string;
	detail?: string;
}

export interface PostJsonResult<T> {
	ok: boolean;
	status: number;
	data: T | null;
	errMsg: string | null;
}

export async function postJson<T = unknown>(
	path: string,
	body: unknown,
): Promise<PostJsonResult<T>> {
	try {
		const r = await fetch(path, {
			method: "POST",
			headers: { "content-type": "application/json" },
			body: JSON.stringify(body),
		});
		const parsed = (await r.json().catch(() => null)) as
			| (T & ErrorShape)
			| null;
		const err = parsed as ErrorShape | null;
		if (!r.ok || err?.ok === false) {
			return {
				ok: false,
				status: r.status,
				data: (parsed as T) ?? null,
				errMsg: err?.detail ?? err?.error ?? `HTTP ${r.status}`,
			};
		}
		return {
			ok: true,
			status: r.status,
			data: parsed as T,
			errMsg: null,
		};
	} catch (err) {
		return {
			ok: false,
			status: 0,
			data: null,
			errMsg: (err as Error).message,
		};
	}
}
