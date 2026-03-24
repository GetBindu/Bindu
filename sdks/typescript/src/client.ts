/**
 * BinduService gRPC Client
 *
 * Connects to the Bindu core's gRPC server (port 3774) and calls
 * RegisterAgent to register the SDK agent. The core then runs the
 * full bindufy logic (DID, auth, x402, manifest, HTTP server).
 *
 * This is an internal module — developers never interact with it directly.
 */

import * as grpc from "@grpc/grpc-js";
import * as protoLoader from "@grpc/proto-loader";
import * as path from "path";
import type { RegistrationResult } from "./types";

// Load proto definition
// Resolve proto path relative to the package root (works from both src/ and dist/)
const PROTO_PATH = path.resolve(__dirname, "..", "proto", "agent_handler.proto");

const packageDefinition = protoLoader.loadSync(PROTO_PATH, {
  keepCase: true,
  longs: String,
  enums: String,
  defaults: true,
  oneofs: true,
});

const protoDescriptor = grpc.loadPackageDefinition(packageDefinition) as any;
const binduGrpc = protoDescriptor.bindu.grpc;

/**
 * Register an agent with the Bindu core via gRPC.
 *
 * @param coreAddress - Bindu core gRPC address (e.g., "localhost:3774").
 * @param configJson - Agent config as JSON string.
 * @param skills - Proto-compatible skill definitions.
 * @param callbackAddress - This SDK's AgentHandler address (e.g., "localhost:50052").
 * @returns Registration result with agent_id, DID, and URL.
 */
export function registerAgent(
  coreAddress: string,
  configJson: string,
  skills: any[],
  callbackAddress: string
): Promise<RegistrationResult> {
  return new Promise((resolve, reject) => {
    const client = new binduGrpc.BinduService(
      coreAddress,
      grpc.credentials.createInsecure()
    );

    const request = {
      config_json: configJson,
      skills: skills,
      grpc_callback_address: callbackAddress,
    };

    client.RegisterAgent(
      request,
      (err: grpc.ServiceError | null, response: any) => {
        if (err) {
          reject(new Error(`Registration failed: ${err.message}`));
          return;
        }

        if (!response.success) {
          reject(new Error(`Registration failed: ${response.error}`));
          return;
        }

        resolve({
          agentId: response.agent_id,
          did: response.did,
          agentUrl: response.agent_url,
        });
      }
    );
  });
}

/**
 * Send a heartbeat to the Bindu core.
 *
 * @param coreAddress - Bindu core gRPC address.
 * @param agentId - Registered agent ID.
 */
export function sendHeartbeat(
  coreAddress: string,
  agentId: string
): Promise<void> {
  return new Promise((resolve, reject) => {
    const client = new binduGrpc.BinduService(
      coreAddress,
      grpc.credentials.createInsecure()
    );

    client.Heartbeat(
      { agent_id: agentId, timestamp: Date.now() },
      (err: grpc.ServiceError | null) => {
        if (err) reject(err);
        else resolve();
      }
    );
  });
}
