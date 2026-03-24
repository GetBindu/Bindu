# Documentation Summary

## What's Covered

| Page | Content | Status |
|------|---------|--------|
| [README](./README.md) | The problem, the solution, how it works, quick test | Complete |
| [Architecture](./overview.md) | Two-process design, two services, message flow, component breakdown | Complete |
| [API Reference](./api-reference.md) | Every gRPC method, message type, config variable, grpcurl examples | Complete |
| [GrpcAgentClient](./client.md) | How the core calls remote agents, response contract, connection lifecycle | Complete |
| [TypeScript SDK](./sdk-typescript.md) | Installation, handler patterns, config, types, debugging | Complete |
| [Building New SDKs](./sdk-development.md) | Step-by-step guide for adding Rust/Go/Swift support | Complete |
| [Limitations](./limitations.md) | Streaming gap, no TLS, no reconnection, feature comparison | Complete |

## Reading Order

**If you're using the TypeScript SDK:** README -> TypeScript SDK -> examples

**If you're building a new SDK:** README -> Architecture -> API Reference -> Building New SDKs

**If you're a core contributor:** Architecture -> GrpcAgentClient -> API Reference -> Limitations
