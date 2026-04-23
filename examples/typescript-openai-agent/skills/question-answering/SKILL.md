---
id: question-answering-v1
name: question-answering
version: 1.0.0
author: dev@example.com
tags:
  - question-answering
  - conversation
  - assistant
  - general-purpose
  - multi-model
input_modes:
  - text/plain
  - application/json
output_modes:
  - text/plain
  - application/json
---

# Question Answering Skill

General-purpose question answering capability powered by OpenRouter.
Access 300+ LLM models (GPT-4o, Claude, Llama, Gemini, Mistral, etc.) through a single unified API.
Handles conversational queries, explanations, code generation, analysis, and creative writing.

## Capabilities

### Conversational Q&A
- Direct question answering with contextual understanding
- Multi-turn conversation with history awareness
- Follow-up questions and clarification handling

### Code Assistance
- Code generation in multiple languages
- Code explanation and debugging
- Architecture and design pattern suggestions

### Analysis and Reasoning
- Data interpretation and summarization
- Comparative analysis
- Logical reasoning and problem solving

### Creative Writing
- Content generation (articles, emails, documentation)
- Tone adaptation (formal, casual, technical)
- Multi-language support

## Supported Models (via OpenRouter)

| Provider | Models | Strengths |
|----------|--------|-----------|
| OpenAI | GPT-4o, GPT-4o-mini | General purpose, fast |
| Anthropic | Claude Sonnet, Claude Haiku | Analysis, safety, long context |
| Meta | Llama 3.1 70B/405B | Open source, multilingual |
| Google | Gemini 2.0 Flash | Multimodal, fast |
| Mistral | Mistral Large, Codestral | European, code-focused |

## Examples

- "Explain how microservices work"
- "What are the pros and cons of GraphQL vs REST?"
- "Help me understand async/await in TypeScript"
- "Write a Python function to parse CSV files"
- "Compare PostgreSQL and MongoDB for my use case"
- "Summarize the key points of this document"

## Performance

| Metric | Value |
|--------|-------|
| Average response time | 1-5s (model dependent) |
| Max concurrent requests | 10 |
| Context window | Up to 128k tokens (model dependent) |
| Supported languages | 50+ natural languages |

## Requirements

- OpenRouter API key (get one at https://openrouter.ai/keys)
- Internet connection for API calls

## When to Use

- General knowledge questions
- Code assistance and review
- Content generation and editing
- Data analysis and interpretation
- Conversational AI applications

## When NOT to Use

- Real-time data (stock prices, live sports) - use a web search agent
- Image generation - use a DALL-E or Stable Diffusion agent
- File processing (PDF, Excel) - use a document processing agent
- Database queries - use a data agent with direct DB access

## Integration

This skill is used by the TypeScript OpenRouter agent example:

```typescript
bindufy({
  skills: ["skills/question-answering"],
}, async (messages) => {
  const response = await openrouter.chat.completions.create({
    model: "openai/gpt-4o",
    messages: messages,
  });
  return response.choices[0].message.content;
});
```

## Assessment

### Keywords
question, answer, explain, help, how, what, why, write, generate, analyze, summarize, compare, code, debug

### Specializations
- domain: general_knowledge (confidence_boost: 0.2)
- domain: code_assistance (confidence_boost: 0.3)
- domain: content_generation (confidence_boost: 0.2)

### Complexity Indicators
- Simple: "what is", "explain", "define", single-topic questions
- Medium: "compare", "analyze", multi-step reasoning
- Complex: "design a system", "debug this code", multi-domain synthesis
