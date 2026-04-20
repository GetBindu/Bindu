/**
 * TypeScript OpenAI Agent — Bindufied
 *
 * Demonstrates using the Bindu TypeScript SDK with the OpenAI SDK.
 * Uses GPT-4o to answer questions and assist users.
 *
 * Usage:
 *   1. Set OPENAI_API_KEY in .env
 *   2. npx tsx index.ts
 */

import { bindufy, ChatMessage } from "@bindu/sdk";
import OpenAI from "openai";
import * as dotenv from "dotenv";

dotenv.config();

const openai = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY,
});

// bindufy — one call, full microservice
bindufy(
  {
    author: "opnai-sample-ts@getbindu.com",
    name: "openai-assistant-agent",
    description:
      "An assistant built with the OpenAI SDK and Bindu. Powered by GPT-4o.",
    version: "1.0.0",
    deployment: {
      url: "http://localhost:3773",
      expose: true,
      cors_origins: ["http://localhost:5173"],
    },
    skills: ["skills/question-answering"],
  },
  async (messages: ChatMessage[]) => {
    // Call OpenAI GPT-4o
    const response = await openai.chat.completions.create({
      model: process.env.OPENAI_MODEL || "gpt-4o",
      messages: messages.map((m) => ({
        role: m.role as "user" | "assistant" | "system",
        content: m.content,
      })),
    });

    return response.choices[0].message.content || "";
  }
);
