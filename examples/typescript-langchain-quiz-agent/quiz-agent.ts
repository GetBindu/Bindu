/**
 * Quiz Generator Agent (TypeScript + LangChain + OpenRouter + Bindu)
 */

import { bindufy, ChatMessage } from "@bindu/sdk";
import { ChatOpenAI } from "@langchain/openai";
import * as dotenv from "dotenv";

dotenv.config();

/**
 * LLM Setup (OpenRouter)
 * IMPORTANT: OpenRouter works via baseURL override
 */
const llm = new ChatOpenAI({
  model: "openai/gpt-oss-120b", // same as your Python version
  temperature: 0.3,
  configuration: {
    baseURL: "https://openrouter.ai/api/v1",
    apiKey: process.env.OPENROUTER_API_KEY,
  },
});

/**
 * System Prompt (your original instructions)
 */
const SYSTEM_PROMPT = `
You are a professional teacher. Your task is to generate a quiz based on the provided text.

1. Create exactly 10 Multiple Choice Questions (MCQs).
2. For each question, provide 4 options: A, B, C, and D.
3. Ensure only one answer is correct.
4. Provide a 1-sentence explanation for why the correct answer is right.
5. Keep the language clear and academic.

Output format:

# 📝 Quiz: Knowledge Check

---

### Question 1
[Question text here]
A) [Option A]
B) [Option B]
C) [Option C]
D) [Option D]

**Correct Answer:** [A/B/C/D]
**Explanation:** [Brief explanation]

---

(Repeat for questions 2 through 10)
`;

/**
 * bindufy — converts into full microservice
 */
bindufy(
  {
    author: "your.email@example.com",
    name: "quiz-generator-agent",
    description: "Educational assessment expert for MCQ generation",
    version: "1.0.0",
    deployment: {
      url: "http://localhost:3773",
      expose: true,
      cors_origins: ["http://localhost:5173"],
    },
    skills: ["skills/quiz-generation"],
    capabilities: {
      streaming: false,
      push_notifications: false,
    },
  },

  /**
   * Handler
   */
  async (messages: ChatMessage[]) => {
    try {
      if (!messages || messages.length === 0) {
        return "Error: No input provided.";
      }

      // Extract latest user input (better than passing full history blindly)
      const userInput = messages[messages.length - 1].content;

      // Construct LangChain messages
      const langchainMessages = [
        { role: "system", content: SYSTEM_PROMPT },
        { role: "user", content: userInput },
      ];

      // Call LLM
      const response = await llm.invoke(langchainMessages);

      // Return response
      return typeof response.content === "string"
        ? response.content
        : JSON.stringify(response.content);
    } catch (error: any) {
      return `Error: ${error.message}`;
    }
  }
);
