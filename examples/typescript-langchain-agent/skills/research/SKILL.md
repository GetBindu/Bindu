---
id: research-v1
name: research
version: 1.0.0
author: dev@example.com
tags:
  - research
  - question-answering
  - analysis
  - summarization
  - langchain
input_modes:
  - text/plain
  - application/json
output_modes:
  - text/plain
  - application/json
---

# Research Skill

Research and information retrieval capability powered by LangChain.js.
Uses GPT-4o to answer questions, summarize information, provide detailed
analysis, and generate structured research outputs.

## Capabilities

### Question Answering
- Direct question answering with contextual understanding
- Multi-turn conversation with history awareness
- Follow-up questions and clarification handling

### Summarization
- Summarize complex topics into clear outputs
- Bullet points, paragraphs, or structured JSON
- Adjustable depth and detail level

### Analysis
- Comparative analysis (pros/cons, trade-offs)
- Technical evaluation of tools and frameworks
- Architectural decision support

### Code Explanation
- Explain code concepts and patterns
- TypeScript, Python, Rust, Go, Java support
- Architecture and design pattern suggestions

## Examples

- "What is the current state of quantum computing?"
- "Summarize the key points of machine learning"
- "Explain the A2A protocol in simple terms"
- "Compare React vs Vue for a new project"
- "What are the best practices for API design?"
- "Analyze the pros and cons of microservices architecture"

## Performance

| Metric | Value |
|--------|-------|
| Average response time | 1-5s (model dependent) |
| Max concurrent requests | 10 |
| Context window | Up to 128k tokens |

## Requirements

- OpenAI API key (used by LangChain.js `ChatOpenAI`)
- Internet connection for API calls

## Integration

This skill is used by the TypeScript LangChain agent example:

```typescript
import { ChatOpenAI } from "@langchain/openai";

const llm = new ChatOpenAI({ model: "gpt-4o", temperature: 0.7 });

bindufy({
  skills: ["skills/research"],
}, async (messages) => {
  const response = await llm.invoke(messages);
  return response.content;
});
```

## Assessment

### Keywords
research, explain, summarize, analyze, compare, question, answer, what, how, why

### Specializations
- domain: research (confidence_boost: 0.3)
- domain: analysis (confidence_boost: 0.2)
- domain: summarization (confidence_boost: 0.2)
