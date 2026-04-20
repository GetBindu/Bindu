---
id: quiz-generation-v1
name: quiz-generation
version: 1.0.0
author: dev@example.com
tags:
  - quiz-generation
  - education
  - mcq-creation
  - assessment
  - langchain
  - openrouter
input_modes:
  - text/plain
  - application/json
output_modes:
  - text/plain
  - application/json
---

# Quiz Generation Skill

Educational assessment expert that generates high-quality multiple-choice quizzes
from any provided text. Creates exactly 10 MCQs with 4 options each, correct answer
identification, and concise explanations.

## Capabilities

### Quiz Generation
- Generate exactly 10 Multiple Choice Questions (MCQs)
- 4 options per question (A, B, C, D)
- Only one correct answer per question
- 1-sentence explanation for each correct answer
- Clear, academic language

### Assessment Design
- Pedagogically sound question design
- Plausible distractors for wrong answers
- Appropriate difficulty levels
- Subject-agnostic content processing

### Content Analysis
- Extract key concepts from provided text
- Identify important topics for testing
- Generate questions that cover main points
- Ensure comprehensive coverage

## Output Format

Each quiz follows this standardized structure:

```markdown
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
```

## Examples

- "Generate a quiz from this chapter about photosynthesis"
- "Create 10 MCQs based on the following text about World War II"
- "Make a quiz from this article about machine learning basics"
- "Generate assessment questions from this study material"
- "Create a knowledge check from this documentation"

## Performance

| Metric | Value |
|--------|-------|
| Average response time | 3-8s (model dependent) |
| Max concurrent requests | 5 |
| Context window | Up to 128k tokens |
| Questions per quiz | Exactly 10 |

## Requirements

- OpenRouter API key (configured for OpenAI models)
- Internet connection for API calls
- Text input (any subject matter)

## Integration

This skill is used by the TypeScript LangChain Quiz Agent:

```typescript
import { ChatOpenAI } from "@langchain/openai";

const llm = new ChatOpenAI({
  model: "openai/gpt-oss-120b",
  temperature: 0.3,
  configuration: {
    baseURL: "https://openrouter.ai/api/v1",
    apiKey: process.env.OPENROUTER_API_KEY,
  },
});

bindufy({
  skills: ["skills/quiz-generation"],
}, async (messages) => {
  const response = await llm.invoke([
    { role: "system", content: QUIZ_SYSTEM_PROMPT },
    { role: "user", content: userInput },
  ]);
  return response.content;
});
```

## Assessment

### Keywords
quiz, test, assessment, questions, mcq, multiple-choice, generate, create, questions, knowledge, check, exam, evaluate

### Specializations
- domain: education (confidence_boost: 0.4)
- domain: assessment (confidence_boost: 0.3)
- domain: quiz-generation (confidence_boost: 0.5)

### Anti-Patterns
Avoid requests for:
- Real-time data processing
- Image or video content
- Audio processing
- Database queries
- File uploads
- Code execution
