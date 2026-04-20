/**
 * Bindu SDK for Kotlin — transform any Kotlin agent into a microservice.
 *
 * This is the main entry point. Developers call bindufy() with their
 * config and handler — the SDK handles gRPC, core launching, and registration.
 *
 * Example:
 *   bindufy(
 *       config = mapOf(
 *           "author" to "dev@example.com",
 *           "name" to "my-agent",
 *           "deployment" to mapOf("url" to "http://localhost:3773", "expose" to true),
 *       )
 *   ) { messages ->
 *       "Echo: ${messages.last().content}"
 *   }
 */

package com.getbindu.sdk

import com.google.gson.Gson
import io.grpc.ManagedChannelBuilder
import io.grpc.ServerBuilder
import io.grpc.stub.StreamObserver
import kotlinx.coroutines.runBlocking
import java.io.File
import java.net.ServerSocket
import java.util.concurrent.TimeUnit

/** A single message in conversation history. */
data class ChatMessage(
    val role: String,
    val content: String
)

/** Response from the handler. */
data class HandlerResponse(
    val content: String = "",
    val state: String = "",
    val prompt: String = "",
    val metadata: Map<String, String> = emptyMap()
)

/** Registration result from the Bindu core. */
data class RegistrationResult(
    val agentId: String,
    val did: String,
    val agentUrl: String
)

/** Handler function type. */
typealias MessageHandler = suspend (List<ChatMessage>) -> Any

/**
 * Transform a Kotlin agent into a Bindu microservice.
 *
 * This function:
 *   1. Launches the Bindu Python core as a child process
 *   2. Starts a gRPC server for receiving HandleMessages calls
 *   3. Registers the agent with the core via RegisterAgent
 *   4. Blocks, handling tasks via gRPC
 *
 * @param config Agent configuration as a map (matches Python bindufy config).
 * @param skills List of skill directory paths (relative to CWD).
 * @param coreAddress Bindu core gRPC address (default: "localhost:3774").
 * @param handler The handler function that processes messages.
 * @return Registration result with agent_id, DID, and A2A URL.
 */
fun bindufy(
    config: Map<String, Any>,
    skills: List<String> = emptyList(),
    coreAddress: String = "localhost:3774",
    handler: MessageHandler
): RegistrationResult = runBlocking {
    val agentName = config["name"] as? String ?: "kotlin-agent"
    println("\n  Bindufy: $agentName")
    println("  Author: ${config["author"]}")
    println()

    // Step 1: Launch Bindu Python core
    val grpcPort = coreAddress.split(":").last().toInt()
    val core = CoreLauncher.launch(grpcPort = grpcPort)

    // Step 2: Start AgentHandler gRPC server
    val callbackPort = findFreePort()
    val agentServer = startAgentHandlerServer(handler, callbackPort)
    println("  AgentHandler gRPC server on :$callbackPort")

    // Step 3: Load skills from filesystem
    val loadedSkills = loadSkills(skills)

    // Step 4: Register with Bindu core
    println("  Registering with Bindu core at $coreAddress...")
    val configJson = Gson().toJson(config)
    val result = registerWithCore(coreAddress, configJson, loadedSkills, "localhost:$callbackPort")

    println()
    println("  Agent registered successfully!")
    println("  Agent ID: ${result.agentId}")
    println("  DID:      ${result.did}")
    println("  A2A URL:  ${result.agentUrl}")
    println()
    println("  Waiting for messages...\n")

    // Step 5: Handle shutdown
    Runtime.getRuntime().addShutdownHook(Thread {
        agentServer.shutdown()
        core?.destroy()
    })

    // Block until interrupted
    agentServer.awaitTermination()

    result
}

/** Find a free port for the AgentHandler server. */
private fun findFreePort(): Int {
    ServerSocket(0).use { return it.localPort }
}

/** Load skill files from directories. */
private fun loadSkills(skillPaths: List<String>): List<Map<String, Any>> {
    return skillPaths.map { skillPath ->
        val dir = File(skillPath)
        val yamlFile = File(dir, "skill.yaml")
        val mdFile = File(dir, "SKILL.md")

        val name = dir.name
        val rawContent: String
        val format: String

        when {
            yamlFile.exists() -> {
                rawContent = yamlFile.readText()
                format = "yaml"
            }
            mdFile.exists() -> {
                rawContent = mdFile.readText()
                format = "markdown"
            }
            else -> {
                rawContent = ""
                format = "yaml"
            }
        }

        mapOf(
            "name" to name,
            "description" to "Skill: $name",
            "tags" to emptyList<String>(),
            "input_modes" to listOf("text/plain"),
            "output_modes" to listOf("text/plain"),
            "raw_content" to rawContent,
            "format" to format
        )
    }
}

/** Register agent with Bindu core via gRPC. */
private fun registerWithCore(
    coreAddress: String,
    configJson: String,
    skills: List<Map<String, Any>>,
    callbackAddress: String
): RegistrationResult {
    val channel = ManagedChannelBuilder.forTarget(coreAddress)
        .usePlaintext()
        .build()

    try {
        val stub = bindu.grpc.BinduServiceGrpc.newBlockingStub(channel)
            .withDeadlineAfter(60, TimeUnit.SECONDS)

        val skillProtos = skills.map { skill ->
            bindu.grpc.AgentHandlerProto.SkillDefinition.newBuilder()
                .setName(skill["name"] as String)
                .setDescription(skill["description"] as String)
                .setRawContent(skill["raw_content"] as String)
                .setFormat(skill["format"] as String)
                .build()
        }

        val request = bindu.grpc.AgentHandlerProto.RegisterAgentRequest.newBuilder()
            .setConfigJson(configJson)
            .addAllSkills(skillProtos)
            .setGrpcCallbackAddress(callbackAddress)
            .build()

        val response = stub.registerAgent(request)

        if (!response.success) {
            throw RuntimeException("Registration failed: ${response.error}")
        }

        return RegistrationResult(
            agentId = response.agentId,
            did = response.did,
            agentUrl = response.agentUrl
        )
    } finally {
        channel.shutdown()
    }
}

/** Start AgentHandler gRPC server. */
private fun startAgentHandlerServer(
    handler: MessageHandler,
    port: Int
): io.grpc.Server {
    val server = ServerBuilder.forPort(port)
        .addService(AgentHandlerService(handler))
        .build()
        .start()
    return server
}

/** AgentHandler gRPC service implementation. */
private class AgentHandlerService(
    private val handler: MessageHandler
) : bindu.grpc.AgentHandlerGrpc.AgentHandlerImplBase() {

    override fun handleMessages(
        request: bindu.grpc.AgentHandlerProto.HandleRequest,
        responseObserver: StreamObserver<bindu.grpc.AgentHandlerProto.HandleResponse>
    ) {
        try {
            val messages = request.messagesList.map { msg ->
                ChatMessage(role = msg.role, content = msg.content)
            }

            val result = runBlocking { handler(messages) }

            val response = when (result) {
                is String -> bindu.grpc.AgentHandlerProto.HandleResponse.newBuilder()
                    .setContent(result)
                    .setIsFinal(true)
                    .build()
                is HandlerResponse -> bindu.grpc.AgentHandlerProto.HandleResponse.newBuilder()
                    .setContent(result.content)
                    .setState(result.state)
                    .setPrompt(result.prompt)
                    .setIsFinal(true)
                    .putAllMetadata(result.metadata)
                    .build()
                else -> bindu.grpc.AgentHandlerProto.HandleResponse.newBuilder()
                    .setContent(result.toString())
                    .setIsFinal(true)
                    .build()
            }

            responseObserver.onNext(response)
            responseObserver.onCompleted()
        } catch (e: Exception) {
            responseObserver.onError(
                io.grpc.Status.INTERNAL
                    .withDescription(e.message)
                    .asRuntimeException()
            )
        }
    }

    override fun healthCheck(
        request: bindu.grpc.AgentHandlerProto.HealthCheckRequest,
        responseObserver: StreamObserver<bindu.grpc.AgentHandlerProto.HealthCheckResponse>
    ) {
        responseObserver.onNext(
            bindu.grpc.AgentHandlerProto.HealthCheckResponse.newBuilder()
                .setHealthy(true)
                .setMessage("OK")
                .build()
        )
        responseObserver.onCompleted()
    }
}
