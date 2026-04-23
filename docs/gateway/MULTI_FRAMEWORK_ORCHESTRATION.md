# Gateway: Multi-Framework Agent Orchestration

When you build a real system with multiple AI agents, you run into a problem that nobody warns you about upfront:

> _Who decides which agent runs first, which ones can run at the same time, and what happens when one agent needs the output of another?_

You could wire this up yourself. You could write code that calls Agent A, waits for the result, passes it to Agent B, and so on. But that code becomes your problem. You own the retry logic, the dependency tracking, the parallel execution, the error handling. And the moment you want to swap Agent B from Python to TypeScript, or replace LangChain with CrewAI, you're rewriting the wiring too.

The Gateway exists so you don't have to do any of that.

It sits between your users and your agents. It reads the request, figures out which agents can run immediately, which ones need to wait for others, and coordinates everything. Your agents stay simple. The Gateway handles the complexity.

---

## The idea behind orchestration

Think about how a restaurant kitchen works. When a table orders a steak, a salad, and a dessert, the head chef doesn't wait for the steak to finish before starting the salad. The salad and the steak can be prepared at the same time - they're independent. But the dessert waits. The chef won't plate it until the main course is done.

That's orchestration. Some tasks can happen in parallel. Some tasks have to wait. Someone has to know which is which.

The Gateway is that head chef.

There are four patterns it supports:

**Sequential execution** - one agent finishes before the next one starts. Use this when Agent B needs Agent A's output to do its job.

**Parallel execution** - multiple agents start at the same time because they all work from the same input and don't depend on each other. Use this when you want speed.

**Mixed execution** - some agents run in parallel first, then a dependent agent starts once those are done. The most common real-world pattern.

**Dependency-aware execution** - the Gateway reads the task descriptions and infers which agents need to wait for which. You don't declare dependencies explicitly. The Gateway figures it out.

---

## Why framework and language freedom matters

Here's a situation that comes up constantly in real teams:

Your data scientist built a summarization agent in LangChain because that's what they know. Your frontend team built a keyword extractor in TypeScript because they're not Python people. Your ML team is using CrewAI for a multi-step SEO workflow. Now someone wants all three to work together.

Without the Gateway, you'd need to pick one framework and rewrite the others. Or you'd need to build a custom integration layer. Either way, someone's work gets thrown away.

With the Gateway, none of that happens. Each agent runs as its own HTTP service. The Gateway talks to all of them using the same protocol. Agno, LangChain, CrewAI, TypeScript - they don't know about each other. They don't import each other. They just respond to requests.

The Gateway is the shared coordinator. The agents are independent specialists.

---

## The flow, walked through

Here's what happens end to end when a user sends a request to the Gateway.

```
┌──────────┐          ┌─────────────┐          ┌──────────────┐          ┌──────────────┐
│  Client  │          │   Gateway   │          │   Agent A    │          │   Agent B    │
└────┬─────┘          └──────┬──────┘          └──────┬───────┘          └──────┬───────┘
     │                       │                        │                          │
     │  1. POST /plan        │                        │                          │
     ├──────────────────────▶│                        │                          │
     │                       │                        │                          │
     │                       │  2. Plan orchestrated  │                          │
     │                       │     (who runs first?)  │                          │
     │                       │                        │                          │
     │                       │  3. Start Agent A      │                          │
     │                       ├───────────────────────▶│                          │
     │                       │                        │                          │
     │                       │  4. Agent A result     │                          │
     │                       │◀───────────────────────┤                          │
     │                       │                        │                          │
     │                       │  5. Start Agent B (now that A is done)            │
     │                       ├──────────────────────────────────────────────────▶│
     │                       │                        │                          │
     │                       │  6. Agent B result     │                          │
     │                       │◀──────────────────────────────────────────────────┤
     │                       │                        │                          │
     │  7. Synthesized result│                        │                          │
     │◀──────────────────────┤                        │                          │
     │                       │                        │                          │
```

Three things worth noting:

- **Step 2 is where the intelligence lives.** The Gateway reads the agent descriptions and the question, then decides the execution order. You don't write this logic.
- **Steps 3-6 vary by workflow.** In a parallel workflow, steps 3 and 5 happen at the same time. In a sequential workflow, step 5 waits for step 4.
- **Step 7 is synthesis.** The Gateway doesn't just return raw agent outputs. It combines them into a coherent response.

---

## Example 1: Calculator → Keywords → Rewriter

### The scenario

You want to calculate a math expression, then simultaneously extract keywords from the result and rewrite it in a more formal tone. The calculation has to happen first - the other two agents need its output. But once the number is ready, the keyword extractor and the rewriter can work at the same time.

This is the most common real-world pattern: one blocking step, then a burst of parallel work.

### Why this pattern is useful

Without the Gateway, you'd call the calculator, wait, then call the keyword extractor, wait, then call the rewriter. Three sequential calls. With the Gateway, the last two run in parallel. The total time is: calculator time + max(keyword time, rewriter time). Not calculator + keyword + rewriter.

### The flow

```
User sends request
  ↓
Gateway plans execution
  ↓
Calculator Agent starts → produces 126
  ↓
Keyword Extractor + Rewriter start simultaneously (both need only the calculator result)
  ↓
Both complete → Gateway synthesizes → Done
```

### The request

```bash
curl -N http://localhost:3779/plan \
  -H "Authorization: Bearer ${GATEWAY_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Calculate 21 * 12 / 2, identify the keywords in the response and rewrite the output text",
    "agents": [
      {"name": "agno_calculator_agent", "endpoint": "http://localhost:3775", "skills": [{"id": "agno_calculator_agent", "description": "Calculator agent built with Agno"}]},
      {"name": "langchain_keyword_agent", "endpoint": "http://localhost:3776", "skills": [{"id": "langchain_keyword_agent", "description": "Keyword extractor built with LangChain"}]},
      {"name": "typescript_rewriter_agent", "endpoint": "http://localhost:3777", "skills": [{"id": "typescript_rewriter_agent", "description": "Text rewriter built with TypeScript"}]}
    ]
  }'
```

### The result

```
🔢 Calculation: 21 × 12 ÷ 2 = 126 [agent:agno_calculator_agent]

🔑 Keywords: Result, Calculation, Multiplication, Division, Arithmetic
[agent:langchain_keyword_agent]

✍️ Rewritten: The calculation of 21 multiplied by 12, then divided by 2, yields a result of 126.
[agent:typescript_rewriter_agent]
```

### What happened

The Gateway saw that the keyword extractor and rewriter both described themselves as working on "the response" - meaning they needed the calculator's output. So it ran the calculator first, then fired both of the others in parallel once the result was ready. You didn't write any of that logic. You just described the agents and asked the question.

---

## Example 2: Summary → Keywords → Tweet

### The scenario

You have an article. You want a summary, a keyword list, and a tweet - all from the same article. None of these tasks depend on each other. They all start from the same input.

This is pure parallel execution. All three agents start at the same time.

### Why fully parallel execution matters

If each agent takes 3 seconds, sequential execution takes 9 seconds. Parallel execution takes 3 seconds. For user-facing workflows, that difference is the gap between "feels fast" and "feels broken."

### The flow

```
User sends request
  ↓
Gateway plans execution
  ↓
Summarizer + Keyword Extractor + Tweet Generator all start simultaneously
  ↓
Each completes independently → Gateway synthesizes → Done
```

### The request

```bash
curl -N http://localhost:3779/plan \
  -H "Authorization: Bearer ${GATEWAY_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Summarize this article about AI agents, extract keywords, and generate a tweet: AI agents are becoming increasingly popular because they can automate repetitive tasks, improve productivity, and assist teams in making faster decisions. Businesses are using AI agents for customer support, workflow automation, data analysis, and content generation.",
    "agents": [
      {"name": "langchain_article_summary_agent", "endpoint": "http://localhost:3776", "skills": [{"id": "langchain_article_summary_agent", "description": "Article summarization agent built with LangChain"}]},
      {"name": "typescript_keyword_agent", "endpoint": "http://localhost:3777", "skills": [{"id": "typescript_keyword_agent", "description": "Keyword extraction agent built with TypeScript"}]},
      {"name": "agno_tweet_generator_agent", "endpoint": "http://localhost:3775", "skills": [{"id": "agno_tweet_generator_agent", "description": "Tweet generation agent built with Agno"}]}
    ]
  }'
```

### The result

```
📝 Article Summary
- AI agents are gaining popularity for automating tasks and enhancing productivity
- Used across customer support, workflow automation, data analysis, and content generation
- Expected to become integral to modern software systems
[agent:langchain_article_summary_agent]

 Keywords
AI Agents · Automation · Productivity · Customer Support · Workflow Automation
[agent:typescript_keyword_agent]

🐦 Twitter/X Post
AI agents are revolutionizing the way we work!  From automating repetitive tasks to enhancing productivity, these tools are streamlining everything from customer support to content generation. #AI #Automation
[agent:agno_tweet_generator_agent]
```

### What the Gateway did

It looked at the three agent descriptions, saw that all three could work from the original article without needing each other's output, and started all three at the same time. The total time was the slowest of the three - not the sum of all three.

---

## Example 3: Blog Outline + Blog Content → SEO Metadata

### The scenario

You want to write a blog post about AI agents. You need an outline, the full content, and SEO metadata. The outline and the content can be written independently - they both just need the topic. But the SEO metadata needs the actual blog content to generate accurate keywords and a meta description.

This is dependency-aware orchestration. Some tasks run in parallel. One task waits.

### Why this matters

This example also mixes three different frameworks: Agno writes the outline, TypeScript writes the blog content, and CrewAI handles the SEO. They're running on different ports, written in different languages, using different libraries. The Gateway doesn't care. It coordinates them the same way regardless.

### The flow

```
User sends request
  ↓
Gateway plans execution
  ↓
Agno Outline Agent + TypeScript Blog Writer start in parallel (both need only the topic)
  ↓
Both complete → Blog content is now available
  ↓
CrewAI SEO Optimizer starts (it was waiting for the blog content)
  ↓
All results synthesized → Done
```

### The request

```bash
curl -N http://localhost:3779/plan \
  -H "Authorization: Bearer ${GATEWAY_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Create a blog outline about AI agents in software development, write the blog content, and generate SEO metadata for it.",
    "agents": [
      {"name": "agno_blog_outline_agent", "endpoint": "http://localhost:3775", "skills": [{"id": "agno_blog_outline_agent", "description": "Blog outline generator built with Agno"}]},
      {"name": "typescript_blog_writer_agent", "endpoint": "http://localhost:3777", "skills": [{"id": "typescript_blog_writer_agent", "description": "Blog writer built with TypeScript"}]},
      {"name": "crewai_seo_optimizer_agent", "endpoint": "http://localhost:3778", "skills": [{"id": "crewai_seo_optimizer_agent", "description": "SEO optimizer built with CrewAI"}]}
    ]
  }'
```

### The result

```
📋 Blog Outline: The Impact of AI Agents in Modern Software Development
- Section 1: Understanding AI Agents
- Section 2: Role in Modern Software Development
- Section 3: Key Use Cases (code generation, testing, debugging, CI/CD)
- Section 4: Benefits (efficiency, code quality, time to market)
- Section 5: Challenges & Considerations
- Conclusion: Future Outlook
[agent:agno_blog_outline_agent]

✍️ Blog Content: The Role of AI Agents in Modern Software Development
[Full article covering what AI agents are, their role in development, key use cases with examples, benefits for developers and teams, challenges, and future outlook]
[agent:typescript_blog_writer_agent]

 SEO Metadata
- SEO Title: The Impact of AI Agents on Software Development
- Meta Description: Discover how AI agents enhance software development through automation, code generation, and improved collaboration.
- Primary Keywords: AI agents in software development, software development automation
- URL Slug: /ai-agents-software-development
[agent:crewai_seo_optimizer_agent]
```

### What the Gateway did

It inferred that the SEO optimizer's description - "generate SEO metadata for it" - meant it needed the blog content to exist first. So it held the SEO agent back while the outline and blog writer ran in parallel. Once both finished, it released the SEO agent with the full context. Three frameworks, two languages, one request.

---

## Proper Agent Example: Research → Explanation → Screenplay

### The scenario

You want to create a screenplay scene based on a deep research topic. The process involves three steps:
1. Conducting in-depth research on the topic.
2. Simplifying the research findings into a structured explanation.
3. Writing a screenplay scene inspired by the explanation.

Each step depends on the output of the previous one. The research must be completed before the explanation can be written, and the screenplay requires the explanation as its foundation.

### Agents used
Deep research agent -
https://www.getbindu.com/agent/deep-research-agent

Article explainer agent -
https://www.getbindu.com/agent/article-explainer-agent

Screenplay writer agent -
https://www.getbindu.com/agent/screenplay-writer-agent

### Why this pattern is useful

This pattern is ideal for workflows where each step builds directly on the previous one. By enforcing a strict sequence, the Gateway ensures that each agent receives the full context it needs to produce high-quality results. Without the Gateway, you would need to manually coordinate the execution order and pass outputs between agents.

### The flow

```
User sends request
  ↓
Gateway plans execution
  ↓
Deep Research Agent starts → produces detailed research report
  ↓
Article Explainer Agent starts → simplifies research into structured explanation
  ↓
Screenplay Writer Agent starts → creates screenplay scene based on explanation
  ↓
All results synthesized → Done
```

### The request

```bash
curl -N http://localhost:3779/plan \
  -H "Authorization: Bearer ${GATEWAY_API_KEY}" \
  -d '{
    "agents": [
      {"name": "deep-research-agent"},
      {"name": "article-explainer-agent"},
      {"name": "screenplay-writer-agent"}
    ],
    "input": "How has street food culture evolved in major cities around the world? Cover historical context, key developments, notable examples from different cities (e.g., Bangkok, New York, Mexico City, Tokyo, Mumbai), and modern trends like food trucks, fusion cuisine, and gourmet street food."
  }'
```

### The result

#### Research Summary

Street food culture has evolved significantly over centuries, starting as a necessity for affordable urban meals and transforming into a global culinary phenomenon. Key developments include the rise of food trucks, fusion cuisines, and gourmet street food. Cities like Bangkok, New York, Mexico City, Tokyo, and Mumbai showcase unique street food traditions, blending historical roots with modern trends.

#### Simplified Explanation

Street food originated as a quick, affordable option for urban workers and has become a vibrant part of global culture. Each city reflects its unique heritage: Bangkok’s Pad Thai, New York’s food trucks, Mexico City’s tacos, Tokyo’s takoyaki, and Mumbai’s vada pav. Modern trends emphasize sustainability, fusion dishes, and visually appealing presentations.

#### Screenplay Scene

*INT. BUSTLING STREET MARKET - NIGHT*

The camera pans across a vibrant market. Vendors shout, steam rises from grills, and the air is filled with the aroma of spices. A young chef, inspired by global street food trends, prepares a fusion dish: Korean tacos with a twist of Mumbai spices. A food critic watches, intrigued.

CRITIC: (to the chef) "This... this is the future of street food. Tradition meets innovation."

The chef smiles, plating the dish with care as the scene fades out.

### What the Gateway did

The Gateway inferred the dependencies from the agent descriptions:
- The Deep Research Agent’s description specified that it generates a detailed report on a given topic.
- The Article Explainer Agent’s description indicated that it simplifies research findings into a structured explanation.
- The Screenplay Writer Agent’s description stated that it creates a screenplay scene based on an explanation.

By analyzing these descriptions, the Gateway planned a fully sequential execution. It ensured that each agent ran only after its prerequisite task was complete. This eliminated the need for manual coordination and guaranteed that each agent received the context it needed.

More agents are available in the Bindu directory: https://www.getbindu.com/directory
