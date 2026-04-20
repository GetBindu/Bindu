/**
 * @bindu/sdk — Transform any TypeScript agent into a Bindu microservice.
 *
 * This is the main entry point for the TypeScript SDK. Developers import
 * bindufy() and call it with their config and handler — just like the
 * Python version. The SDK handles all gRPC plumbing internally.
 *
 * Example:
 *   import { bindufy } from '@bindu/sdk';
 *
 *   bindufy({
 *     author: 'dev@example.com',
 *     name: 'my-agent',
 *     deployment: { url: 'http://localhost:3773', expose: true },
 *   }, async (messages) => {
 *     return `Echo: ${messages[messages.length - 1].content}`;
 *   });
 */

import * as fs from "fs";
import * as path from "path";
import * as yaml from "yaml" ;
import { launchCore } from "./core-launcher";
import { registerAgent, sendHeartbeat } from "./client";
import { startAgentHandlerServer } from "./server";
import type {
  BinduConfig,
  ChatMessage,
  HandlerResponse,
  MessageHandler,
  RegistrationResult,
  SkillConfig,
} from "./types";

// Re-export types for developer use
export type {
  BinduConfig,
  ChatMessage,
  HandlerResponse,
  MessageHandler,
  RegistrationResult,
  SkillConfig,
};

/**
 * Load skills from file paths or inline definitions.
 *
 * For file paths, reads the skill.yaml or SKILL.md content from disk
 * and includes it in the registration request so the Python core
 * doesn't need filesystem access to the SDK's project.
 */
function loadSkills(
  skills: SkillConfig[] | undefined,
  baseDir: string
): any[] {
  if (!skills || skills.length === 0) return [];

  return skills.map((skill) => {
    if (typeof skill === "string") {
      // File path — read content
      const skillDir = path.resolve(baseDir, skill);
      const yamlPath = path.join(skillDir, "skill.yaml");
      const mdPath = path.join(skillDir, "SKILL.md");

      let rawContent = "";
      let format = "yaml";
      let name = path.basename(skill);
      let description = `Skill: ${name}`;

      if (fs.existsSync(yamlPath)) {
        rawContent = fs.readFileSync(yamlPath, "utf-8");
        format = "yaml";
        try {
          const parsed = yaml.parse(rawContent);
          name = parsed.name || name;
          description = parsed.description || description;
        } catch {
          // Use defaults if YAML parsing fails
        }
      } else if (fs.existsSync(mdPath)) {
        rawContent = fs.readFileSync(mdPath, "utf-8");
        format = "markdown";
      }

      return {
        name,
        description,
        tags: [],
        input_modes: ["text/plain"],
        output_modes: ["text/plain"],
        raw_content: rawContent,
        format,
      };
    } else {
      // Inline skill definition
      return {
        name: skill.name,
        description: skill.description,
        tags: skill.tags || [],
        input_modes: skill.input_modes || ["text/plain"],
        output_modes: skill.output_modes || ["text/plain"],
        version: skill.version || "1.0.0",
        author: skill.author || "",
      };
    }
  });
}

/**
 * Transform a TypeScript agent into a Bindu microservice.
 *
 * This function:
 *   1. Launches the Bindu Python core as a child process
 *   2. Starts a gRPC server for receiving HandleMessages calls
 *   3. Registers the agent with the core via RegisterAgent
 *   4. Keeps the process alive, handling tasks via gRPC
 *
 * The developer sees one function call, one terminal — all infrastructure
 * is handled internally.
 *
 * @param config - Agent configuration (author, name, deployment, skills, etc.)
 * @param handler - The handler function that processes messages.
 * @returns Registration result with agent_id, DID, and A2A URL.
 */
export async function bindufy(
  config: BinduConfig,
  handler: MessageHandler
): Promise<RegistrationResult> {
  const coreAddress = config.coreAddress || "localhost:3774";
  const callbackPort = config.callbackPort || 0; // 0 = auto-assign

  // Determine the caller's directory for skill resolution
  const callerDir = process.cwd();

  console.log(`\n  Bindufy: ${config.name || "agent"}`);
  console.log(`  Author: ${config.author}`);
  console.log("");

  // Step 1: Launch Bindu Python core (if not already running)
  const grpcPort = parseInt(coreAddress.split(":")[1] || "3774");
  const httpPort = config.deployment?.url
    ? parseInt(new URL(config.deployment.url).port || "3773")
    : 3773;

  try {
    await launchCore(grpcPort, httpPort);
  } catch (err: any) {
    // Core might already be running — try to connect anyway
    console.log("Core may already be running, attempting to connect...");
  }

  // Step 2: Start AgentHandler gRPC server (receives HandleMessages from core)
  const { server: agentServer, port: boundPort } =
    await startAgentHandlerServer(handler, callbackPort);
  console.log(`  AgentHandler gRPC server on :${boundPort}`);

  // Step 3: Load skills from filesystem
  const skills = loadSkills(config.skills, callerDir);

  // Step 4: Build config JSON (matches Python bindufy config format)
  const configForCore: Record<string, any> = {
    author: config.author,
    name: config.name,
    description: config.description || `Agent: ${config.name}`,
    version: config.version || "1.0.0",
    deployment: config.deployment,
    kind: config.kind || "agent",
    debug_mode: config.debug_mode || false,
    telemetry: config.telemetry !== undefined ? config.telemetry : true,
    num_history_sessions: config.num_history_sessions || 10,
  };

  if (config.capabilities) {
    configForCore.capabilities = config.capabilities;
  }
  if (config.execution_cost) {
    configForCore.execution_cost = config.execution_cost;
  }
  if (config.extra_metadata) {
    configForCore.extra_metadata = config.extra_metadata;
  }

  // Step 5: Register with Bindu core
  const callbackAddress = `localhost:${boundPort}`;
  console.log(`  Registering with Bindu core at ${coreAddress}...`);

  const result = await registerAgent(
    coreAddress,
    JSON.stringify(configForCore),
    skills,
    callbackAddress
  );

  console.log("");
  console.log(`  Agent registered successfully!`);
  console.log(`  Agent ID: ${result.agentId}`);
  console.log(`  DID:      ${result.did}`);
  console.log(`  A2A URL:  ${result.agentUrl}`);
  console.log("");
  console.log("  Waiting for messages...\n");

  // Step 6: Start heartbeat loop
  const heartbeatInterval = setInterval(async () => {
    try {
      await sendHeartbeat(coreAddress, result.agentId);
    } catch {
      // Silently ignore heartbeat failures
    }
  }, 30000);

  // Clean up on exit
  process.on("SIGINT", () => {
    clearInterval(heartbeatInterval);
    agentServer.forceShutdown();
    process.exit(0);
  });

  return result;
}
