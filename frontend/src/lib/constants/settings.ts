import { defaultModel } from "$lib/server/models";
import type { SettingsEditable } from "$lib/types/Settings";

export const DEFAULT_SETTINGS = {
	shareConversationsWithModelAuthors: true,
	activeModel: defaultModel.id,
	customPrompts: {},
	multimodalOverrides: {},
	toolsOverrides: {},
	hidePromptExamples: {},
	providerOverrides: {},
	disableStream: false,
	directPaste: false,
} satisfies SettingsEditable;