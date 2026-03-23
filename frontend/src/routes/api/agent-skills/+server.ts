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
		const skillsUrl = `${binduBaseUrl.replace(/\/$/, "")}/agent/skills`;
		const response = await fetch(skillsUrl, {
			headers: {
				Accept: "application/json",
			},
		});

		if (!response.ok) {
			throw new Error(`Failed to fetch skills: ${response.status}`);
		}

		const skillsData = await response.json();

		return json(skillsData);
	} catch (e) {
		console.error("Failed to fetch agent skills:", e);
		return error(503, {
			message: "Failed to fetch agent skills from backend"
		});
	}
}
