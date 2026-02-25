import { collections } from "$lib/server/database";
import { z } from "zod";
import { authCondition } from "$lib/server/auth";
import  type { SettingsEditable } from "$lib/types/Settings";
import { DEFAULT_SETTINGS } from "$lib/constants/settings";

export async function POST({ request, locals }) {
	const body = await request.json();

	const { welcomeModalSeen, ...settings } = z
		.object({
			shareConversationsWithModelAuthors: z
				.boolean()
				.default(DEFAULT_SETTINGS.shareConversationsWithModelAuthors),
			welcomeModalSeen: z.boolean().optional(),
			activeModel: z.string().default(DEFAULT_SETTINGS.activeModel),
			customPrompts: z.record(z.string()).default({}),
			multimodalOverrides: z.record(z.boolean()).default({}),
			toolsOverrides: z.record(z.boolean()).default({}),
			providerOverrides: z.record(z.string()).default({}),
			disableStream: z.boolean().default(false),
			directPaste: z.boolean().default(false),
			hidePromptExamples: z.record(z.boolean()).default({}),
			billingOrganization: z.string().optional(),
		})
		.parse(body) satisfies SettingsEditable;

	await collections.settings.updateOne(
		authCondition(locals),
		{
			$set: {
				...settings,
				...(welcomeModalSeen && { welcomeModalSeenAt: new Date() }),
				updatedAt: new Date(),
			},
			$setOnInsert: {
				createdAt: new Date(),
			},
		},
		{
			upsert: true,
		}
	);
	// return ok response
	return new Response();
}
