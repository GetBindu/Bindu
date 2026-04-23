/**
 * Wire ↔ canonical casing normalization for Bindu types.
 *
 * Phase 0 found that deployed Bindu agents use a MIXED casing scheme:
 *
 *   | Type                     | Wire casing                                       |
 *   |--------------------------|---------------------------------------------------|
 *   | AgentCard (top-level)    | camelCase: protocolVersion, defaultInputModes…    |
 *   | AgentCard.skills[] inline| camelCase: documentationPath                      |
 *   | SkillDetail              | snake_case: input_modes, output_modes,            |
 *   |                          |             capabilities_detail, allowed_tools…  |
 *   | Task (top-level)         | mixed: context_id (snake); rest flat             |
 *   | Task.history[]           | snake_case: message_id, context_id, task_id,      |
 *   |                          |             reference_task_ids                    |
 *   | Task.artifacts[]         | snake_case: artifact_id                          |
 *   | Message request params   | camelCase: messageId, contextId, taskId           |
 *   | tasks/get params         | camelCase: taskId (snake → -32700)                |
 *
 * This module canonicalizes to camelCase on read and back to the peer's
 * expected casing on write. Phase 2 might add per-peer "preferred casing"
 * profiles once we learn which agents accept what.
 */

type TypeTag =
  | "task"
  | "artifact"
  | "history-message"
  | "skill-detail"
  | "tasks-get-params"
  | "tasks-cancel-params"

// --------------------------------------------------------------------
// Key maps — wire → canonical (identity for camelCase-on-wire fields)
// --------------------------------------------------------------------

const taskMap: Record<string, string> = {
  context_id: "contextId",
  contextId: "contextId",
  id: "id",
  kind: "kind",
  status: "status",
  history: "history",
  artifacts: "artifacts",
  metadata: "metadata",
}

const artifactMap: Record<string, string> = {
  artifact_id: "artifactId",
  artifactId: "artifactId",
  name: "name",
  description: "description",
  parts: "parts",
  append: "append",
  last_chunk: "lastChunk",
  lastChunk: "lastChunk",
  extensions: "extensions",
  metadata: "metadata",
}

const historyMessageMap: Record<string, string> = {
  kind: "kind",
  role: "role",
  parts: "parts",
  message_id: "messageId",
  messageId: "messageId",
  task_id: "taskId",
  taskId: "taskId",
  context_id: "contextId",
  contextId: "contextId",
  reference_task_ids: "referenceTaskIds",
  referenceTaskIds: "referenceTaskIds",
  metadata: "metadata",
}

const skillDetailMap: Record<string, string> = {
  id: "id",
  name: "name",
  description: "description",
  version: "version",
  tags: "tags",
  examples: "examples",
  input_modes: "inputModes",
  inputModes: "inputModes",
  output_modes: "outputModes",
  outputModes: "outputModes",
  documentation_path: "documentationPath",
  documentationPath: "documentationPath",
  author: "author",
  capabilities_detail: "capabilitiesDetail",
  capabilitiesDetail: "capabilitiesDetail",
  requirements: "requirements",
  performance: "performance",
  allowed_tools: "allowedTools",
  allowedTools: "allowedTools",
  documentation: "documentation",
  assessment: "assessment",
  has_documentation: "hasDocumentation",
  hasDocumentation: "hasDocumentation",
}

const tasksGetParamsMap: Record<string, string> = {
  task_id: "taskId",
  taskId: "taskId",
  history_length: "historyLength",
  historyLength: "historyLength",
  metadata: "metadata",
}

const tasksCancelParamsMap: Record<string, string> = {
  task_id: "taskId",
  taskId: "taskId",
  metadata: "metadata",
}

const mapFor = (tag: TypeTag): Record<string, string> => {
  switch (tag) {
    case "task":
      return taskMap
    case "artifact":
      return artifactMap
    case "history-message":
      return historyMessageMap
    case "skill-detail":
      return skillDetailMap
    case "tasks-get-params":
      return tasksGetParamsMap
    case "tasks-cancel-params":
      return tasksCancelParamsMap
  }
}

/** Map wire field names → canonical camelCase for a given type. */
export function fromWire<T extends Record<string, unknown>>(tag: TypeTag, raw: unknown): T {
  if (raw === null || typeof raw !== "object" || Array.isArray(raw)) return raw as T
  const m = mapFor(tag)
  const out: Record<string, unknown> = {}
  for (const [k, v] of Object.entries(raw)) {
    const canonical = m[k] ?? k // unknown keys pass through
    out[canonical] = v
  }

  // Recurse into nested shapes we know about.
  if (tag === "task") {
    const task = out as { artifacts?: unknown[]; history?: unknown[] }
    if (Array.isArray(task.artifacts))
      task.artifacts = task.artifacts.map((a) => fromWire("artifact", a))
    if (Array.isArray(task.history))
      task.history = task.history.map((h) => fromWire("history-message", h))
  }

  return out as T
}

// --------------------------------------------------------------------
// Outbound: canonical → wire.
// --------------------------------------------------------------------

const taskInverseMap = invert(taskMap)
const artifactInverseMap = invert(artifactMap)
const historyMessageInverseMap = invert(historyMessageMap)
const skillDetailInverseMap = invert(skillDetailMap)
const tasksGetParamsInverseMap = invert(tasksGetParamsMap)
const tasksCancelParamsInverseMap = invert(tasksCancelParamsMap)

function invert(m: Record<string, string>): Record<string, string> {
  // For inverse we pick the FIRST wire key that mapped to each canonical.
  // In our maps, camelCase wins (identity). So inverting gives camel→camel.
  // This is what we want for outbound: emit camelCase everywhere so servers
  // that accept both (most do) parse cleanly, and servers that require
  // snake (`Task.context_id` on inbound responses) don't care about our
  // outbound since we don't return Task objects.
  const out: Record<string, string> = {}
  const seen = new Set<string>()
  for (const [wire, canon] of Object.entries(m)) {
    if (seen.has(canon)) continue
    seen.add(canon)
    out[canon] = wire === canon ? canon : canon // identity
  }
  return out
}

const inverseMapFor = (tag: TypeTag): Record<string, string> => {
  switch (tag) {
    case "task":
      return taskInverseMap
    case "artifact":
      return artifactInverseMap
    case "history-message":
      return historyMessageInverseMap
    case "skill-detail":
      return skillDetailInverseMap
    case "tasks-get-params":
      return tasksGetParamsInverseMap
    case "tasks-cancel-params":
      return tasksCancelParamsInverseMap
  }
}

/**
 * Map canonical camelCase → wire. Phase 0 confirmed camelCase is accepted
 * on every inbound method we tested (`message/send`, `tasks/get`,
 * `tasks/cancel`). We emit camelCase as the default.
 */
export function toWire<T extends Record<string, unknown>>(tag: TypeTag, canonical: unknown): T {
  if (canonical === null || typeof canonical !== "object" || Array.isArray(canonical)) return canonical as T
  const m = inverseMapFor(tag)
  const out: Record<string, unknown> = {}
  for (const [k, v] of Object.entries(canonical)) {
    const wire = m[k] ?? k
    out[wire] = v
  }
  return out as T
}
