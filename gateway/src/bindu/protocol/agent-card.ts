import { z } from "zod"

/**
 * AgentCard + Skill Zod schemas.
 *
 * Parse permissively — deployed Bindu agents add Bindu-specific fields
 * (`agentTrust` as object, `extraData`, `debugLevel`, etc.) that aren't in
 * the A2A base spec. We keep them in via `.passthrough()` and ignore the
 * ones the gateway doesn't act on.
 */

// --------------------------------------------------------------------
// Security schemes — union matching Bindu's TypedDict
// --------------------------------------------------------------------

export const HTTPAuthScheme = z
  .object({
    type: z.literal("http"),
    scheme: z.string(),
    bearerFormat: z.string().optional(),
    description: z.string().optional(),
  })
  .passthrough()

export const APIKeyAuthScheme = z
  .object({
    type: z.literal("apiKey"),
    name: z.string(),
    in: z.enum(["query", "header", "cookie"]),
    description: z.string().optional(),
  })
  .passthrough()

export const OAuth2AuthScheme = z
  .object({
    type: z.literal("oauth2"),
    flows: z.record(z.string(), z.any()),
    description: z.string().optional(),
  })
  .passthrough()

export const OpenIdConnectAuthScheme = z
  .object({
    type: z.literal("openIdConnect"),
    openIdConnectUrl: z.string(),
    description: z.string().optional(),
  })
  .passthrough()

export const MutualTLSAuthScheme = z
  .object({
    type: z.literal("mutualTLS"),
    description: z.string().optional(),
  })
  .passthrough()

export const SecurityScheme = z.union([
  HTTPAuthScheme,
  APIKeyAuthScheme,
  OAuth2AuthScheme,
  OpenIdConnectAuthScheme,
  MutualTLSAuthScheme,
])
export type SecurityScheme = z.infer<typeof SecurityScheme>

// --------------------------------------------------------------------
// AgentCard.skills[] — inline SkillSummary
// --------------------------------------------------------------------

export const SkillSummary = z
  .object({
    id: z.string(),
    name: z.string().optional(),
    description: z.string().optional(),
    version: z.string().optional(),
    tags: z.array(z.string()).optional(),
    examples: z.array(z.string()).optional(),
    // Bindu agents expose these via /agent/skills — they appear inline too
    inputModes: z.array(z.string()).optional(),
    outputModes: z.array(z.string()).optional(),
    input_modes: z.array(z.string()).optional(), // snake variant (normalize.ts)
    output_modes: z.array(z.string()).optional(),
    documentationPath: z.string().optional(),
    documentation_path: z.string().optional(),
  })
  .passthrough()
export type SkillSummary = z.infer<typeof SkillSummary>

// --------------------------------------------------------------------
// /agent/skills/{id} — SkillDetail (snake_case on the wire)
// --------------------------------------------------------------------

export const SkillDetail = SkillSummary.extend({
  author: z.string().optional(),
  // Both casings accepted; normalize.ts canonicalizes to camelCase internally.
  capabilities_detail: z.record(z.string(), z.any()).optional(),
  capabilitiesDetail: z.record(z.string(), z.any()).optional(),

  requirements: z
    .object({
      packages: z.array(z.string()).optional(),
      system: z.array(z.string()).optional(),
      min_memory_mb: z.number().optional(),
      minMemoryMb: z.number().optional(),
      external_services: z.array(z.string()).optional(),
      externalServices: z.array(z.string()).optional(),
    })
    .passthrough()
    .optional(),

  performance: z
    .object({
      avg_processing_time_ms: z.number().optional(),
      avgProcessingTimeMs: z.number().optional(),
      max_concurrent_requests: z.number().optional(),
      maxConcurrentRequests: z.number().optional(),
      memory_per_request_mb: z.number().optional(),
      memoryPerRequestMb: z.number().optional(),
      scalability: z.string().optional(),
    })
    .passthrough()
    .optional(),

  allowed_tools: z.array(z.string()).optional(),
  allowedTools: z.array(z.string()).optional(),

  documentation: z.record(z.string(), z.any()).optional(),

  assessment: z
    .object({
      keywords: z.array(z.string()).optional(),
      specializations: z.any().optional(), // sometimes objects, sometimes arrays across deployed agents
      anti_patterns: z.any().optional(),
      antiPatterns: z.any().optional(),
      complexity_indicators: z.any().optional(),
      complexityIndicators: z.any().optional(),
    })
    .passthrough()
    .optional(),

  has_documentation: z.boolean().optional(),
  hasDocumentation: z.boolean().optional(),
}).passthrough()
export type SkillDetail = z.infer<typeof SkillDetail>

// --------------------------------------------------------------------
// Capabilities + Extensions
// --------------------------------------------------------------------

export const AgentExtension = z
  .object({
    uri: z.string(),
    description: z.string().optional(),
    required: z.boolean().optional(),
    params: z.record(z.string(), z.any()).optional(),
  })
  .passthrough()
export type AgentExtension = z.infer<typeof AgentExtension>

export const AgentCapabilities = z
  .object({
    extensions: z.array(AgentExtension).optional(),
    pushNotifications: z.boolean().optional(),
    stateTransitionHistory: z.boolean().optional(),
    streaming: z.boolean().optional(),
  })
  .passthrough()
export type AgentCapabilities = z.infer<typeof AgentCapabilities>

// --------------------------------------------------------------------
// AgentTrust — Bindu extension, agents return an object, OpenAPI docs say string
// --------------------------------------------------------------------

export const AgentTrust = z.union([
  z.string(),
  z
    .object({
      identityProvider: z.string().optional(),
      inheritedRoles: z.array(z.string()).optional(),
      creatorId: z.string().optional(),
      creationTimestamp: z.number().optional(),
      trustVerificationRequired: z.boolean().optional(),
      allowedOperations: z.record(z.string(), z.any()).optional(),
    })
    .passthrough(),
])
export type AgentTrust = z.infer<typeof AgentTrust>

// --------------------------------------------------------------------
// AgentCard
// --------------------------------------------------------------------

export const AgentCard = z
  .object({
    id: z.string(),
    name: z.string(),
    description: z.string().optional(),
    url: z.string().optional(),
    version: z.string().optional(),
    protocolVersion: z.string().optional(),
    documentationUrl: z.string().optional(),
    iconUrl: z.string().optional(),

    capabilities: AgentCapabilities.optional(),
    skills: z.array(SkillSummary).default([]),
    kind: z.enum(["agent", "team", "workflow"]).optional(),

    agentTrust: AgentTrust.optional(),
    executionCost: z.record(z.string(), z.any()).optional(),
    numHistorySessions: z.number().optional(),
    preferredTransport: z.string().optional(),

    defaultInputModes: z.array(z.string()).default([]),
    defaultOutputModes: z.array(z.string()).default([]),

    security: z.array(z.record(z.string(), z.array(z.string()))).optional(),
    securitySchemes: z.record(z.string(), SecurityScheme).optional(),

    extraData: z.record(z.string(), z.any()).optional(),
    debugMode: z.boolean().optional(),
    debugLevel: z.number().optional(),
    monitoring: z.boolean().optional(),
    telemetry: z.boolean().optional(),

    additionalInterfaces: z.array(z.any()).optional(),
  })
  .passthrough()
export type AgentCard = z.infer<typeof AgentCard>

// --------------------------------------------------------------------
// DID Document
// --------------------------------------------------------------------

export const DIDVerificationMethod = z
  .object({
    id: z.string(),
    type: z.string(),
    controller: z.string(),
    publicKeyBase58: z.string().optional(),
    publicKeyMultibase: z.string().optional(),
    publicKeyJwk: z.record(z.string(), z.any()).optional(),
  })
  .passthrough()
export type DIDVerificationMethod = z.infer<typeof DIDVerificationMethod>

export const DIDDocument = z
  .object({
    "@context": z.union([z.string(), z.array(z.string())]).optional(),
    id: z.string(),
    created: z.string().optional(),
    authentication: z.array(z.union([z.string(), DIDVerificationMethod])).optional(),
    verificationMethod: z.array(DIDVerificationMethod).optional(),
    assertionMethod: z.array(z.union([z.string(), DIDVerificationMethod])).optional(),
  })
  .passthrough()
export type DIDDocument = z.infer<typeof DIDDocument>
