/**
 * Core Launcher — spawns the Bindu Python core as a child process.
 *
 * When a TypeScript developer calls bindufy(), the SDK needs the Python core
 * running to handle DID, auth, x402, A2A protocol, scheduler, and storage.
 * This module detects if Bindu is installed, spawns it as a child process,
 * and waits for the gRPC server to be ready.
 *
 * The developer sees one command, one terminal — the child process is hidden.
 */

import { spawn, ChildProcess } from "child_process";
import * as net from "net";

/** Check if a port is open (gRPC server is ready). */
function waitForPort(
  port: number,
  host: string = "localhost",
  timeoutMs: number = 30000
): Promise<void> {
  return new Promise((resolve, reject) => {
    const startTime = Date.now();

    const tryConnect = () => {
      const socket = new net.Socket();
      socket.setTimeout(1000);

      socket.on("connect", () => {
        socket.destroy();
        resolve();
      });

      socket.on("error", () => {
        socket.destroy();
        if (Date.now() - startTime > timeoutMs) {
          reject(
            new Error(
              `Bindu core did not start within ${timeoutMs / 1000}s on port ${port}`
            )
          );
        } else {
          setTimeout(tryConnect, 500);
        }
      });

      socket.on("timeout", () => {
        socket.destroy();
        setTimeout(tryConnect, 500);
      });

      socket.connect(port, host);
    };

    tryConnect();
  });
}

/** Find the bindu executable (checks pip-installed bindu CLI). */
function findBinduExecutable(): string | null {
  const { execSync } = require("child_process");
  try {
    const result = execSync("which bindu 2>/dev/null || where bindu 2>nul", {
      encoding: "utf-8",
    }).trim();
    return result || null;
  } catch {
    return null;
  }
}

/** Check if uv is available for running Python. */
function hasUv(): boolean {
  const { execSync } = require("child_process");
  try {
    execSync("which uv 2>/dev/null || where uv 2>nul", { encoding: "utf-8" });
    return true;
  } catch {
    return false;
  }
}

/**
 * Launch the Bindu Python core as a child process.
 *
 * Tries in order:
 *   1. `bindu serve --grpc` (pip-installed CLI)
 *   2. `uv run bindu serve --grpc` (uv-managed)
 *   3. `python -m bindu.cli serve --grpc` (fallback)
 *
 * @param grpcPort - Port for the gRPC server (default: 3774).
 * @param httpPort - Port for the HTTP A2A server (default: 3773).
 * @returns The child process and the actual ports.
 */
export async function launchCore(
  grpcPort: number = 3774,
  httpPort: number = 3773
): Promise<{ process: ChildProcess; grpcPort: number; httpPort: number }> {
  let command: string;
  let args: string[];

  const binduPath = findBinduExecutable();
  if (binduPath) {
    command = binduPath;
    args = ["serve", "--grpc", "--grpc-port", String(grpcPort)];
  } else if (hasUv()) {
    command = "uv";
    args = ["run", "bindu", "serve", "--grpc", "--grpc-port", String(grpcPort)];
  } else {
    command = "python3";
    args = ["-m", "bindu.cli", "serve", "--grpc", "--grpc-port", String(grpcPort)];
  }

  console.log(`Starting Bindu core: ${command} ${args.join(" ")}`);

  const child = spawn(command, args, {
    stdio: ["ignore", "pipe", "pipe"],
    detached: false,
  });

  // Pipe core output to console with prefix
  child.stdout?.on("data", (data: Buffer) => {
    const lines = data.toString().trim().split("\n");
    lines.forEach((line: string) => console.log(`[bindu-core] ${line}`));
  });

  child.stderr?.on("data", (data: Buffer) => {
    const lines = data.toString().trim().split("\n");
    lines.forEach((line: string) => console.error(`[bindu-core] ${line}`));
  });

  child.on("error", (err: Error) => {
    console.error(
      `Failed to start Bindu core: ${err.message}\n` +
        "Make sure Bindu is installed: pip install bindu[grpc]"
    );
    process.exit(1);
  });

  child.on("exit", (code: number | null) => {
    if (code !== null && code !== 0) {
      console.error(`Bindu core exited with code ${code}`);
    }
  });

  // Kill child process when parent exits
  const cleanup = () => {
    if (!child.killed) {
      child.kill("SIGTERM");
    }
  };
  process.on("exit", cleanup);
  process.on("SIGINT", () => {
    cleanup();
    process.exit(0);
  });
  process.on("SIGTERM", () => {
    cleanup();
    process.exit(0);
  });

  // Wait for gRPC server to be ready
  console.log(`Waiting for Bindu core gRPC on port ${grpcPort}...`);
  await waitForPort(grpcPort);
  console.log("Bindu core is ready.");

  return { process: child, grpcPort, httpPort };
}
