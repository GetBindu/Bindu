/**
 * TypeScript LangChain Agent — Bindufied
 *
 * Demonstrates using the Bindu TypeScript SDK with LangChain.js.
 * The developer writes their agent using any TS framework — Bindu handles
 * the conversion to a microservice with DID, auth, x402, and A2A protocol.
 *
 * Usage:
 *   1. Set OPENAI_API_KEY in .env or environment
 *   2. npx tsx index.ts
 *
 * The SDK will:
 *   - Start the Bindu Python core in the background
 *   - Register this agent with DID identity and A2A endpoints
 *   - Listen for tasks via gRPC and execute them with LangChain
 */

import { bindufy, ChatMessage } from "@bindu/sdk";
import { ChatOpenAI } from "@langchain/openai";
import * as dotenv from "dotenv";

dotenv.config();

// Create LangChain agent — this is the developer's choice
const llm = new ChatOpenAI({
  model: "gpt-4o",
  temperature: 0.7,
});

// bindufy — one call, full microservice
bindufy(
  {
    author: "dev@example.com",
    name: "langchain-research-agent",
    description: "A research assistant built with LangChain.js and Bindu",
    version: "1.0.0",
    deployment: {
      url: "http://localhost:3773",
      expose: true,
      cors_origins: ["http://localhost:5173"],
    },
    skills: ["skills/research"],
    capabilities: {
      streaming: false,
      push_notifications: false,
    },
  },
  async (messages: ChatMessage[]) => {
    // Convert Bindu messages to LangChain format
    const langchainMessages = messages.map((m) => ({
      role: m.role as "user" | "assistant" | "system",
      content: m.content,
    }));

    // Invoke LangChain
    const response = await llm.invoke(langchainMessages);

    // Return the content — Bindu handles the rest
    return typeof response.content === "string"
      ? response.content
      : JSON.stringify(response.content);
  }
);
