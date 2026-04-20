/**
 * Core Launcher — spawns the Bindu Python core as a child process.
 *
 * Same pattern as the TypeScript SDK: detect bindu CLI, spawn it,
 * wait for the gRPC port to be ready.
 */

package com.getbindu.sdk

import java.io.BufferedReader
import java.io.InputStreamReader
import java.net.Socket

object CoreLauncher {

    /**
     * Launch the Bindu Python core.
     *
     * Tries in order:
     *   1. `bindu serve --grpc`
     *   2. `uv run bindu serve --grpc`
     *   3. `python3 -m bindu.cli serve --grpc`
     *
     * @param grpcPort gRPC server port (default: 3774).
     * @param httpPort HTTP server port (default: 3773).
     * @param timeoutMs Maximum time to wait for core to start.
     * @return The child process, or null if core is already running.
     */
    fun launch(
        grpcPort: Int = 3774,
        httpPort: Int = 3773,
        timeoutMs: Long = 30000
    ): Process? {
        // Check if core is already running
        if (isPortOpen(grpcPort)) {
            println("  Bindu core already running on :$grpcPort")
            return null
        }

        val (command, args) = findCommand(grpcPort, httpPort)
        println("  Starting Bindu core: $command ${args.joinToString(" ")}")

        val processBuilder = ProcessBuilder(listOf(command) + args)
            .redirectErrorStream(true)

        val process = processBuilder.start()

        // Pipe output with prefix
        Thread {
            BufferedReader(InputStreamReader(process.inputStream)).use { reader ->
                reader.lines().forEach { line ->
                    println("[bindu-core] $line")
                }
            }
        }.apply { isDaemon = true }.start()

        // Wait for gRPC port to be ready
        println("  Waiting for Bindu core gRPC on port $grpcPort...")
        waitForPort(grpcPort, timeoutMs)
        println("  Bindu core is ready.")

        return process
    }

    private fun findCommand(grpcPort: Int, httpPort: Int): Pair<String, List<String>> {
        val args = listOf("serve", "--grpc", "--grpc-port", grpcPort.toString(), "--port", httpPort.toString())

        // Try bindu CLI
        if (commandExists("bindu")) {
            return "bindu" to args
        }

        // Try uv
        if (commandExists("uv")) {
            return "uv" to listOf("run", "bindu") + args
        }

        // Fallback to python3
        return "python3" to listOf("-m", "bindu.cli") + args
    }

    private fun commandExists(command: String): Boolean {
        return try {
            val process = ProcessBuilder("which", command)
                .redirectErrorStream(true)
                .start()
            process.waitFor() == 0
        } catch (_: Exception) {
            false
        }
    }

    private fun isPortOpen(port: Int, host: String = "localhost"): Boolean {
        return try {
            Socket(host, port).use { true }
        } catch (_: Exception) {
            false
        }
    }

    private fun waitForPort(port: Int, timeoutMs: Long) {
        val start = System.currentTimeMillis()
        while (System.currentTimeMillis() - start < timeoutMs) {
            if (isPortOpen(port)) return
            Thread.sleep(500)
        }
        throw RuntimeException("Bindu core did not start within ${timeoutMs / 1000}s on port $port")
    }
}
