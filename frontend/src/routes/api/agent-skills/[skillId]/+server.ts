import { config } from "$lib/server/config";
import { json, error } from "@sveltejs/kit";
import type { RequestHandler } from "./$types";

export const GET: RequestHandler = async ({ params }) => {
	const binduBaseUrl = config.BINDU_BASE_URL;
	const { skillId } = params;

	if (!binduBaseUrl) {
		return error(503, {
			message: "Bindu agent not configured"
		});
	}

	try {
		const skillUrl = `${binduBaseUrl.replace(/\/$/, "")}/agent/skills/${skillId}`;
		const response = await fetch(skillUrl, {
			headers: {
				Accept: "application/json",
			},
		});

		if (!response.ok) {
			throw new Error(`Failed to fetch skill details: ${response.status}`);
		}

		const skillData = await response.json();

		return json(skillData);
	} catch (e) {
		console.error(`Failed to fetch skill ${skillId}:`, e);
		return error(503, {
			message: `Failed to fetch skill ${skillId} from backend`
		});
	}
};
