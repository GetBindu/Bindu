import { config } from "$lib/server/config";
import { error } from "@sveltejs/kit";
import type { RequestHandler } from "./$types";

export const POST: RequestHandler = async ({ request }) => {
	const binduBaseUrl = config.BINDU_BASE_URL;

	if (!binduBaseUrl) {
		return error(503, "Bindu agent not configured. Set BINDU_BASE_URL environment variable.");
	}

	try {
		// Get request body
		const body = await request.json();

		// Validate DID is provided
		if (!body.did) {
			return error(400, "DID is required");
		}

		// Get authorization header from request
		const authHeader = request.headers.get("authorization");

		// Forward request to Bindu agent
		const response = await fetch(`${binduBaseUrl}/did/resolve`, {
			method: "POST",
			headers: {
				"Content-Type": "application/json",
				...(authHeader ? { Authorization: authHeader } : {}),
			},
			body: JSON.stringify(body),
		});

		if (!response.ok) {
			return error(response.status, `DID resolution failed: ${response.statusText}`);
		}

		const data = await response.json();
		return new Response(JSON.stringify(data), {
			status: 200,
			headers: {
				"Content-Type": "application/json",
			},
		});
	} catch (err) {
		console.error("DID resolution proxy error:", err);
		return error(500, "Failed to communicate with Bindu agent");
	}
};
