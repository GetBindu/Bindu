import { config } from "$lib/server/config";
import { json, error } from "@sveltejs/kit";

export async function GET() {
	const binduBaseUrl = config.BINDU_BASE_URL;

	if (!binduBaseUrl) {
		return error(503, {
			message: "Bindu agent not configured"
		});
	}

	try {
		const healthUrl = `${binduBaseUrl.replace(/\/$/, "")}/health`;
		const response = await fetch(healthUrl, {
			headers: {
				Accept: "application/json",
			},
		});

		if (!response.ok) {
			throw new Error(`Failed to fetch health status: ${response.status}`);
		}

		const healthData = await response.json();

		return json(healthData);
	} catch (e) {
		console.error("Failed to fetch agent health:", e);
		return error(503, {
			message: "Failed to fetch agent health from backend"
		});
	}
}
