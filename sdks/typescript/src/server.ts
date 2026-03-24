/**
 * AgentHandler gRPC Server
 *
 * Starts a gRPC server that implements the AgentHandler service.
 * The Bindu core calls HandleMessages on this server when a task arrives.
 * The server invokes the developer's handler function and returns the result.
 *
 * This is an internal module — developers never interact with it directly.
 * The bindufy() function manages the server lifecycle automatically.
 */

import * as grpc from "@grpc/grpc-js";
import * as protoLoader from "@grpc/proto-loader";
import * as path from "path";
import type { ChatMessage, HandlerResponse, MessageHandler } from "./types";

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
 * Start the AgentHandler gRPC server.
 *
 * @param handler - The developer's message handler function.
 * @param port - Port to listen on (0 = auto-assign).
 * @returns The started server and the actual bound port.
 */
export function startAgentHandlerServer(
  handler: MessageHandler,
  port: number = 0
): Promise<{ server: grpc.Server; port: number }> {
  return new Promise((resolve, reject) => {
    const server = new grpc.Server();

    server.addService(binduGrpc.AgentHandler.service, {
      // Core calls this when a task arrives
      HandleMessages: async (
        call: grpc.ServerUnaryCall<any, any>,
        callback: grpc.sendUnaryData<any>
      ) => {
        try {
          const messages: ChatMessage[] = call.request.messages.map(
            (m: any) => ({
              role: m.role,
              content: m.content,
            })
          );

          const result = await handler(messages);

          if (typeof result === "string") {
            callback(null, {
              content: result,
              state: "",
              prompt: "",
              is_final: true,
              metadata: {},
            });
          } else {
            callback(null, {
              content: result.content || "",
              state: result.state || "",
              prompt: result.prompt || "",
              is_final: true,
              metadata: result.metadata || {},
            });
          }
        } catch (err: any) {
          callback({
            code: grpc.status.INTERNAL,
            message: err.message || "Handler error",
          });
        }
      },

      // Core can query capabilities
      GetCapabilities: (
        _call: grpc.ServerUnaryCall<any, any>,
        callback: grpc.sendUnaryData<any>
      ) => {
        callback(null, {
          name: "typescript-agent",
          description: "TypeScript agent via @bindu/sdk",
          version: "1.0.0",
          supports_streaming: false,
          skills: [],
        });
      },

      // Core checks if SDK is alive
      HealthCheck: (
        _call: grpc.ServerUnaryCall<any, any>,
        callback: grpc.sendUnaryData<any>
      ) => {
        callback(null, {
          healthy: true,
          message: "OK",
        });
      },
    });

    const bindAddress = `0.0.0.0:${port}`;
    server.bindAsync(
      bindAddress,
      grpc.ServerCredentials.createInsecure(),
      (err, boundPort) => {
        if (err) {
          reject(err);
          return;
        }
        resolve({ server, port: boundPort });
      }
    );
  });
}
