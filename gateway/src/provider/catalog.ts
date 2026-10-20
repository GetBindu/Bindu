export type MiniMaxRegion = "global_en" | "cn_zh"
export type MiniMaxProtocol = "openai" | "anthropic"

export const MINIMAX_ENDPOINTS = {
  global_en: {
    openaiBaseURL: "https://api.minimax.io/v1",
    anthropicBaseURL: "https://api.minimax.io/anthropic",
    docsRoot: "https://platform.minimax.io/docs",
  },
  cn_zh: {
    openaiBaseURL: "https://api.minimaxi.com/v1",
    anthropicBaseURL: "https://api.minimaxi.com/anthropic",
    docsRoot: "https://platform.minimaxi.com/docs",
  },
} as const satisfies Record<
  MiniMaxRegion,
  Record<`${MiniMaxProtocol}BaseURL`, string> & { docsRoot: string }
>

/** Current ordinary choices; explicit saved and custom IDs remain usable. */
export const MINIMAX_MODELS = [
  {
    id: "MiniMax-M3.1-Flash",
    aliases: ["minimax-m3.1-flash"],
    contextWindow: 1_000_000,
    maxOutputTokens: 524_288,
    pricingUsdPerMillionTokens: {
      input: 0.15,
      output: 0.6,
      cacheRead: 0.015,
      cacheWrite: null,
    },
    inputModalities: ["text", "image", "video"],
    thinking: ["adaptive"],
    reasoningEfforts: ["low", "medium", "high", "xhigh", "max"],
  },
  {
    id: "MiniMax-M3",
    aliases: ["minimax-m3"],
    contextWindow: 1_000_000,
    pricingUsdPerMillionTokens: {
      input: 0.3,
      output: 1.2,
      cacheRead: 0.06,
      cacheWrite: null,
    },
    // Standard tier for prompts above the published 512k threshold.
    longContextPricingUsdPerMillionTokens: {
      input: 0.6,
      output: 2.4,
      cacheRead: 0.12,
      cacheWrite: null,
    },
    inputModalities: ["text", "image", "video"],
    thinking: ["adaptive", "disabled"],
  },
] as const

export const DEFAULT_MINIMAX_MODEL = "MiniMax-M3.1-Flash"

/** Normalize known aliases without replacing an explicitly configured model. */
export function normalizeMiniMaxModelId(modelId: string): string {
  if (!modelId) return DEFAULT_MINIMAX_MODEL
  const model = MINIMAX_MODELS.find(
    (candidate) => candidate.id === modelId || candidate.aliases.some((alias) => alias === modelId),
  )
  if (model) return model.id
  // Compatibility with the aliases offered before the current catalog.
  if (modelId === "minimax-m2.7") return "MiniMax-M2.7"
  return modelId
}
