import type { BackendModel } from "$lib/server/models";

export type Model = Pick<
	BackendModel,
	| "id"
	| "name"
	| "displayName"
	| "isRouter"
	| "parameters"
	| "multimodal"
	| "unlisted"
	| "hasInferenceAPI"
> & Partial<Pick<
	BackendModel,
	| "description"
	| "preprompt"
	| "multimodalAcceptedMimetypes"
>>;
