import { config } from "$lib/server/config";
import type { ChatTemplateInput } from "$lib/types/Template";
import { z } from "zod";
import endpoints, { type Endpoint } from "./endpoints/endpoints";

import { logger } from "$lib/server/logger";
import type { AgentCard } from "./endpoints/bindu/types";

type Optional<T, K extends keyof T> = Pick<Partial<T>, K> & Omit<T, K>;

interface ModelConfig {
	id?: string;
	name: string;
	displayName?: string;
	description?: string;
	preprompt: string;
	multimodal: boolean;
	multimodalAcceptedMimetypes?: string[];
	supportsTools: boolean;
	unlisted: boolean;
	systemRoleSupported: boolean;
	isRouter?: boolean;
	endpoints?: Array<{
		type: "bindu";
		baseURL: string;
		apiKey?: string;
		streamingSupported?: boolean;
	}>;
}

function getChatPromptRender(_m: ModelConfig): (inputs: ChatTemplateInput) => string {
	return ({ messages, preprompt }) => {
		const parts: string[] = [];
		if (preprompt) parts.push(`[SYSTEM]\n${preprompt}`);
		for (const msg of messages) {
			const role = msg.from === "assistant" ? "ASSISTANT" : msg.from.toUpperCase();
			parts.push(`[${role}]\n${msg.content}`);
		}
		parts.push(`[ASSISTANT]`);
		return parts.join("\n\n");
	};
}

const processModel = async (m: ModelConfig) => ({
	...m,
	chatPromptRender: getChatPromptRender(m),
	id: m.id || m.name,
	displayName: m.displayName || m.name,
	preprompt: m.preprompt,
	parameters: { stop_sequences: [] as string[] },
	unlisted: m.unlisted ?? false,
});

const addEndpoint = (m: Awaited<ReturnType<typeof processModel>>) => ({
	...m,
	getEndpoint: async (): Promise<Endpoint> => {
		if (!m.endpoints || m.endpoints.length === 0) {
			throw new Error("No endpoints configured.");
		}
		const endpoint = m.endpoints[0];

		if (endpoint.type === "bindu") {
			return await endpoints.bindu({ ...endpoint });
		}

		throw new Error(`Unsupported endpoint type: ${endpoint.type}`);
	},
});

type InternalProcessedModel = Awaited<ReturnType<typeof addEndpoint>> & {
	isRouter: boolean;
	hasInferenceAPI: boolean;
};

export type ModelsRefreshSummary = {
	refreshedAt: Date;
	durationMs: number;
	added: string[];
	removed: string[];
	changed: string[];
	total: number;
};

export type ProcessedModel = InternalProcessedModel;

export let models: ProcessedModel[] = [];
export let defaultModel!: ProcessedModel;
export let taskModel!: ProcessedModel;
export let validModelIdSchema: z.ZodType<string> = z.string();
export let lastModelRefresh = new Date(0);
export let lastModelRefreshDurationMs = 0;
export let lastModelRefreshSummary: ModelsRefreshSummary = {
	refreshedAt: new Date(0),
	durationMs: 0,
	added: [],
	removed: [],
	changed: [],
	total: 0,
};

const createValidModelIdSchema = (modelList: ProcessedModel[]): z.ZodType<string> => {
	if (modelList.length === 0) {
		throw new Error("No models available to build validation schema");
	}
	const ids = new Set(modelList.map((m) => m.id));
	return z.string().refine((value) => ids.has(value), "Invalid model id");
};

const applyModelState = (newModels: ProcessedModel[], startedAt: number): ModelsRefreshSummary => {
	if (newModels.length === 0) {
		throw new Error("Failed to load any models");
	}

	const refreshedAt = new Date();
	const durationMs = Date.now() - startedAt;

	models = newModels;
	defaultModel = models[0];
	taskModel = models[0];
	validModelIdSchema = createValidModelIdSchema(models);
	lastModelRefresh = refreshedAt;
	lastModelRefreshDurationMs = durationMs;

	const summary: ModelsRefreshSummary = {
		refreshedAt,
		durationMs,
		added: [],
		removed: [],
		changed: [],
		total: models.length,
	};

	lastModelRefreshSummary = summary;

	logger.info({ total: summary.total, durationMs: summary.durationMs }, "[models] Model loaded");

	return summary;
};

/**
 * Fetch Bindu agent from /.well-known/agent.json or use default config
 */
const fetchBinduAgent = async (): Promise<ModelConfig> => {
	const binduBaseUrl = (config.BINDU_BASE_URL || "").trim();
	const binduApiKey = (config.BINDU_API_KEY || "").trim();
	const defaultAgentName = (config.BINDU_AGENT_NAME || "").trim() || "Bindu";

	// Default fallback config
	const defaultConfig: ModelConfig = {
		id: "bindu",
		name: "bindu",
		displayName: defaultAgentName,
		description: "Chat with your Bindu backend",
		preprompt: "",
		multimodal: false,
		supportsTools: true,
		unlisted: false,
		systemRoleSupported: true,
		isRouter: false,
		endpoints: binduBaseUrl
			? [
					{
						type: "bindu" as const,
						baseURL: binduBaseUrl,
						apiKey: binduApiKey,
						streamingSupported: true,
					},
			  ]
			: undefined,
	};

	if (!binduBaseUrl) {
		logger.info("[models] No BINDU_BASE_URL set, using default agent config");
		return defaultConfig;
	}

	try {
		const agentCardUrl = `${binduBaseUrl.replace(/\/$/, "")}/.well-known/agent.json`;
		logger.info({ url: agentCardUrl }, "[models] Fetching Bindu agent card");

		const response = await fetch(agentCardUrl, {
			headers: binduApiKey ? { Authorization: `Bearer ${binduApiKey}` } : undefined,
			signal: AbortSignal.timeout(parseInt(config.BINDU_TIMEOUT_MS || "10000", 10)),
		});

		if (!response.ok) {
			logger.warn(
				{ status: response.status, url: agentCardUrl },
				"[models] Failed to fetch Bindu agent card, using default"
			);
			return defaultConfig;
		}

		const agentCard: AgentCard = await response.json();
		logger.info({ name: agentCard.name }, "[models] Loaded Bindu agent");

		const displayName = defaultAgentName || agentCard.name || "Bindu";

		return {
			id: "bindu",
			name: "bindu",
			displayName,
			description: agentCard.description || "Chat with your Bindu backend",
			preprompt: "",
			multimodal: false,
			supportsTools: agentCard.capabilities?.taskManagement ?? true,
			unlisted: false,
			systemRoleSupported: true,
			isRouter: false,
			endpoints: [
				{
					type: "bindu" as const,
					baseURL: agentCard.endpoints?.jsonrpc || binduBaseUrl,
					apiKey: binduApiKey,
					streamingSupported: agentCard.capabilities?.streaming ?? true,
				},
			],
		};
	} catch (error) {
		logger.warn({ error }, "[models] Error fetching Bindu agent, using default config");
		return defaultConfig;
	}
};

const buildModels = async (): Promise<ProcessedModel[]> => {
	const binduAgent = await fetchBinduAgent();

	const processed = await processModel(binduAgent)
		.then(addEndpoint)
		.then(async (m) => ({
			...m,
			hasInferenceAPI: false,
			isRouter: false as boolean,
		}));

	return [processed as ProcessedModel];
};

const rebuildModels = async (): Promise<ModelsRefreshSummary> => {
	const startedAt = Date.now();
	const newModels = await buildModels();
	return applyModelState(newModels, startedAt);
};

await rebuildModels();

export const refreshModels = async (): Promise<ModelsRefreshSummary> => {
	return rebuildModels();
};

export const validateModel = (_models: BackendModel[]) => {
	return z.enum([_models[0].id, ..._models.slice(1).map((m) => m.id)]);
};

export type BackendModel = Optional<
	typeof defaultModel,
	"preprompt" | "parameters" | "multimodal" | "unlisted" | "hasInferenceAPI"
>;
