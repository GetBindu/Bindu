/**
 * Kotlin OpenAI Agent — Bindufied
 *
 * Demonstrates using the Bindu Kotlin SDK with an OpenAI-compatible API.
 * The developer writes their agent logic in Kotlin — Bindu handles
 * the conversion to a microservice with DID, auth, x402, and A2A protocol.
 *
 * Usage:
 *   1. Set OPENAI_API_KEY in environment
 *   2. ./gradlew run
 */

import com.getbindu.sdk.ChatMessage
import com.getbindu.sdk.bindufy
import java.net.URI
import java.net.http.HttpClient
import java.net.http.HttpRequest
import java.net.http.HttpResponse
import com.google.gson.Gson
import com.google.gson.JsonObject

val httpClient: HttpClient = HttpClient.newHttpClient()
val gson = Gson()

suspend fun callOpenAI(messages: List<ChatMessage>): String {
    val apiKey = System.getenv("OPENAI_API_KEY")
        ?: throw RuntimeException("OPENAI_API_KEY not set")

    val messagesJson = messages.map { msg ->
        mapOf("role" to msg.role, "content" to msg.content)
    }

    val body = gson.toJson(mapOf(
        "model" to "gpt-4o",
        "messages" to messagesJson
    ))

    val request = HttpRequest.newBuilder()
        .uri(URI.create("https://api.openai.com/v1/chat/completions"))
        .header("Content-Type", "application/json")
        .header("Authorization", "Bearer $apiKey")
        .POST(HttpRequest.BodyPublishers.ofString(body))
        .build()

    val response = httpClient.send(request, HttpResponse.BodyHandlers.ofString())
    val json = gson.fromJson(response.body(), JsonObject::class.java)

    return json
        .getAsJsonArray("choices")
        .get(0).asJsonObject
        .getAsJsonObject("message")
        .get("content").asString
}

fun main() {
    bindufy(
        config = mapOf(
            "author" to "dev@example.com",
            "name" to "kotlin-openai-agent",
            "description" to "An assistant built with Kotlin and Bindu",
            "version" to "1.0.0",
            "deployment" to mapOf(
                "url" to "http://localhost:3773",
                "expose" to true,
                "cors_origins" to listOf("http://localhost:5173")
            ),
        ),
        skills = listOf("skills/question-answering")
    ) { messages ->
        // Call OpenAI and return the response
        callOpenAI(messages)
    }
}
