import { afterEach, describe, expect, it, vi } from "vitest"
import { Effect, Layer, Stream } from "effect"
import { generateText, jsonSchema, stepCountIs } from "ai"
import {
  DEFAULT_MINIMAX_MODEL,
  MINIMAX_ENDPOINTS,
  MINIMAX_MODELS,
  normalizeMiniMaxModelId,
} from "../../src/provider/catalog"
import { layer, Service } from "../../src/provider"
import { Config, Service as ConfigService } from "../../src/config"
import { stream } from "../../src/session/llm"
import { Part, toModelMessages } from "../../src/session/message"
import { newMessageID, newSessionID, newPartID } from "../../src/session/schema"

async function resolve(modelId = "minimax/", settings: Record<string, unknown> = {}) {
  const config = Config.parse({ gateway: {}, provider: {
    minimax: { apiKey: "test-key", ...settings },
    openrouter: { apiKey: "test-key" },
  } })
  return Effect.runPromise(
    Effect.gen(function* () { return yield* (yield* Service).model(modelId) }).pipe(
      Effect.provide(layer.pipe(Layer.provide(Layer.succeed(ConfigService, {
        get: () => Effect.succeed(config),
      })))),
    ),
  )
}

function response(protocol: string) {
  return protocol === "anthropic"
    ? { id: "msg_test", type: "message", role: "assistant", model: DEFAULT_MINIMAX_MODEL,
        content: [{ type: "text", text: "done" }], stop_reason: "end_turn",
        stop_sequence: null, usage: { input_tokens: 10, output_tokens: 2 } }
    : { id: "chat_test", object: "chat.completion", created: 1, model: DEFAULT_MINIMAX_MODEL,
        choices: [{ index: 0, message: { role: "assistant", content: "done", reasoning_content: "checked" }, finish_reason: "stop" }],
        usage: { prompt_tokens: 10, completion_tokens: 2, total_tokens: 12 } }
}

afterEach(() => vi.unstubAllGlobals())

describe("MiniMax provider", () => {
  it("offers Flash first and M3 second with current metadata", () => {
    expect(DEFAULT_MINIMAX_MODEL).toBe("MiniMax-M3.1-Flash")
    expect(MINIMAX_MODELS.map((model) => model.id)).toEqual(["MiniMax-M3.1-Flash", "MiniMax-M3"])
    expect(MINIMAX_MODELS[0]).toMatchObject({
      contextWindow: 1_000_000, maxOutputTokens: 524_288, thinking: ["adaptive"],
      pricingUsdPerMillionTokens: { input: 0.15, output: 0.6, cacheRead: 0.015, cacheWrite: null },
    })
    expect(MINIMAX_MODELS[1].pricingUsdPerMillionTokens).toMatchObject({ input: 0.3, output: 1.2 })
    expect(normalizeMiniMaxModelId("minimax-m2.7")).toBe("MiniMax-M2.7")
    expect(normalizeMiniMaxModelId("custom/deployment")).toBe("custom/deployment")
  })

  for (const region of ["global_en", "cn_zh"] as const) {
    for (const protocol of ["openai", "anthropic"] as const) {
      for (const id of ["", "minimax-m3.1-flash", "MiniMax-M3", "MiniMax-M2.7", "custom-deployment"]) {
        it(`serializes ${region}/${protocol}/${id || "default"} through the SDK`, async () => {
          let sent: any
          let url = ""
          vi.stubGlobal("fetch", vi.fn(async (input, init) => {
            url = String(input)
            sent = JSON.parse(init.body)
            return Response.json(response(protocol))
          }))
          const model = await resolve(`minimax/${id}`, { region, protocol })
          await generateText({ model, prompt: "hello", maxRetries: 0 })
          expect(sent.model).toBe(normalizeMiniMaxModelId(id))
          expect(url).toBe(protocol === "openai"
            ? `${MINIMAX_ENDPOINTS[region].openaiBaseURL}/chat/completions`
            : `${MINIMAX_ENDPOINTS[region].anthropicBaseURL}/v1/messages`)
          expect(sent).not.toHaveProperty("service_tier")
          expect(sent).not.toHaveProperty("reasoning_split", false)
          if (protocol === "anthropic" && normalizeMiniMaxModelId(id) === DEFAULT_MINIMAX_MODEL) {
            expect(sent.thinking).toEqual({ type: "adaptive" })
          }
        })
      }
    }
  }

  for (const protocol of ["openai", "anthropic"] as const) {
    it(`serializes supported Flash effort using the ${protocol} contract`, async () => {
      let sent: any
      vi.stubGlobal("fetch", vi.fn(async (_input, init) => {
        sent = JSON.parse(init.body)
        return Response.json(response(protocol))
      }))
      const model = await resolve("minimax/", { protocol })
      for (const effort of ["low", "medium", "high", "xhigh", "max"]) {
        await generateText({ model, prompt: "hello", maxRetries: 0,
          providerOptions: protocol === "openai" ? { minimax: { reasoningEffort: effort } } : { anthropic: { effort } },
        })
        expect(protocol === "openai" ? sent.reasoning_effort : sent.output_config.effort).toBe(effort)
      }
    })

    it(`preserves image, reasoning and tool history for ${protocol}`, async () => {
      let sent: any
      vi.stubGlobal("fetch", vi.fn(async (_input, init) => {
        sent = JSON.parse(init.body)
        return Response.json(response(protocol))
      }))
      const model = await resolve("minimax/", { protocol })
      await generateText({
        model, maxRetries: 0,
        tools: { lookup: { inputSchema: jsonSchema({ type: "object", properties: {} }) } },
        messages: [
          { role: "user", content: [{ type: "text", text: "inspect" },
            { type: "image", image: new Uint8Array([1, 2, 3]), mediaType: "image/png" }] },
          { role: "assistant", content: [
            { type: "reasoning", text: "inspect the image", providerOptions: { anthropic: { signature: "test-signature" } } },
            { type: "tool-call", toolCallId: "call_1", toolName: "lookup", input: {} },
          ] },
          { role: "tool", content: [{ type: "tool-result", toolCallId: "call_1", toolName: "lookup", output: { type: "text", value: "found" } }] },
        ],
      })
      expect(sent.tools).toHaveLength(1)
      if (protocol === "openai") {
        expect(sent.messages[0].content[1]).toEqual({ type: "image_url", image_url: { url: "data:image/png;base64,AQID" } })
        expect(sent.messages[1].reasoning_content).toBe("inspect the image")
        expect(sent.messages[1].tool_calls[0].id).toBe("call_1")
        expect(sent.messages[2]).toMatchObject({ role: "tool", tool_call_id: "call_1", content: "found" })
      } else {
        expect(sent.messages[0].content[1]).toMatchObject({ type: "image", source: { data: "AQID", media_type: "image/png" } })
        expect(sent.messages[1].content[0]).toMatchObject({ type: "thinking", thinking: "inspect the image", signature: "test-signature" })
        expect(sent.messages[1].content[1]).toMatchObject({ type: "tool_use", id: "call_1" })
        expect(sent.messages[2].content[0]).toMatchObject({ type: "tool_result", tool_use_id: "call_1" })
      }
    })

    it(`replays returned reasoning in an automatic ${protocol} tool round trip`, async () => {
      const bodies: any[] = []
      vi.stubGlobal("fetch", vi.fn(async (_input, init) => {
        bodies.push(JSON.parse(init.body))
        if (bodies.length > 1) return Response.json(response(protocol))
        return Response.json(protocol === "openai" ? {
          id: "chat_tool", choices: [{ index: 0, finish_reason: "tool_calls", message: {
            role: "assistant", content: null, reasoning_content: "look up the answer",
            tool_calls: [{ id: "call_roundtrip", type: "function", function: { name: "lookup", arguments: "{}" } }],
          } }], usage: { prompt_tokens: 10, completion_tokens: 5, total_tokens: 15 },
        } : {
          id: "msg_tool", type: "message", role: "assistant", model: DEFAULT_MINIMAX_MODEL,
          content: [{ type: "thinking", thinking: "look up the answer", signature: "roundtrip-signature" },
            { type: "tool_use", id: "call_roundtrip", name: "lookup", input: {} }],
          stop_reason: "tool_use", stop_sequence: null, usage: { input_tokens: 10, output_tokens: 5 },
        })
      }))
      const result = await generateText({ model: await resolve("minimax/", { protocol }), prompt: "look it up", maxRetries: 0,
        stopWhen: stepCountIs(2), tools: { lookup: {
          inputSchema: jsonSchema({ type: "object", properties: {} }), execute: async () => "found",
        } },
      })
      expect(result.text).toBe("done")
      expect(bodies).toHaveLength(2)
      const assistant = bodies[1].messages.find((message: any) => message.role === "assistant")
      if (protocol === "openai") {
        expect(assistant.reasoning_content).toBe("look up the answer")
        expect(assistant.tool_calls[0].id).toBe("call_roundtrip")
      } else {
        expect(assistant.content[0]).toMatchObject({ type: "thinking", thinking: "look up the answer", signature: "roundtrip-signature" })
        expect(assistant.content[1]).toMatchObject({ type: "tool_use", id: "call_roundtrip" })
      }
      expect(JSON.stringify(bodies[1].messages)).toContain("found")
    })

    it(`uses custom ${protocol} endpoints without changing model IDs`, async () => {
      let url = ""
      vi.stubGlobal("fetch", vi.fn(async (input) => {
        url = String(input)
        return Response.json(response(protocol))
      }))
      await generateText({ model: await resolve("minimax/custom", { protocol, baseURL: "https://fixture.invalid/v1/" }), prompt: "hello", maxRetries: 0 })
      expect(url).toBe(`https://fixture.invalid/v1/${protocol === "openai" ? "chat/completions" : "messages"}`)
    })
  }

  it("leaves the existing gateway transport unchanged", async () => {
    let sent: any
    let url = ""
    vi.stubGlobal("fetch", vi.fn(async (input, init) => {
      url = String(input)
      sent = JSON.parse(init.body)
      return Response.json(response("openai"))
    }))
    await generateText({ model: await resolve("openrouter/custom/model"), prompt: "hello", maxRetries: 0 })
    expect(url).toBe("https://openrouter.ai/api/v1/chat/completions")
    expect(sent.model).toBe("custom/model")
    expect(sent.cache_control).toEqual({ type: "ephemeral" })
    expect(sent).not.toHaveProperty("thinking")
  })

  it("round-trips stored reasoning metadata into model history", () => {
    const part = Part.parse({ id: newPartID(), type: "reasoning", text: "check first",
      providerMetadata: { anthropic: { signature: "test-signature" } } })
    const messages = toModelMessages([{
      info: { id: newMessageID(), sessionID: newSessionID(),
        role: "assistant", modelID: DEFAULT_MINIMAX_MODEL, providerID: "minimax", agent: "planner",
        tokens: { input: 0, output: 0, total: 0, cache: { read: 0, write: 0 } }, time: { created: 1 } },
      parts: [part],
    }])
    expect(messages).toEqual([{ role: "assistant", content: [{ type: "reasoning", text: "check first",
      providerOptions: { anthropic: { signature: "test-signature" } } }] }])
  })

  it("preserves streamed reasoning in the actual session LLM path", async () => {
    let sent: any
    vi.stubGlobal("fetch", vi.fn(async (_input, init) => {
      sent = JSON.parse(init.body)
      const chunks = [
        { choices: [{ index: 0, delta: { reasoning_content: "check first" }, finish_reason: null }] },
        { choices: [{ index: 0, delta: { content: "done" }, finish_reason: "stop" }] },
      ]
      return new Response(chunks.map((chunk) => `data: ${JSON.stringify(chunk)}\n\n`).join("") + "data: [DONE]\n\n", { headers: { "Content-Type": "text/event-stream" } })
    }))
    const events = await Effect.runPromise(Stream.runCollect(stream({
      model: await resolve(), systemPrompt: "assist", messages: [{ role: "user", content: "hello" }], tools: {},
    })))
    expect(sent.model).toBe(DEFAULT_MINIMAX_MODEL)
    expect(sent.stream).toBe(true)
    expect(Array.from(events)).toContainEqual(expect.objectContaining({ type: "reasoning-delta", delta: "check first" }))
    expect(Array.from(events)).toContainEqual(expect.objectContaining({ type: "text-delta", delta: "done" }))
  })
})
