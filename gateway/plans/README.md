# Bindu Gateway — Plan Index

The Bindu Gateway is a TypeScript/Bun service that sits in front of one or more Bindu agents and exposes them behind a single `POST /plan` endpoint with an SSE response. Fork of OpenCode, stripped of coding tools, re-purposed for multi-agent collaboration.

## Why this directory exists

Planning artifacts co-located with the code they'll produce. When `gateway/src/` lands, these plans become the "what and why" reference.

## Files

- **[PLAN.md](./PLAN.md)** — the master plan (scope, architecture, protocol, config, session state, fork & extract plan, risks).
- **[phase-0-dryrun.md](./phase-0-dryrun.md)** — 1 day. Prove the Bindu wire format with a throwaway script. Zero repo impact.
- **[phase-1-mvp.md](./phase-1-mvp.md)** — 10 working days. Fork, extract, ship `POST /plan` with Supabase sessions. The real product.
- **[phase-2-production.md](./phase-2-production.md)** — ~2 weeks. Reconnect, Realtime replay, RLS tenancy, circuit breakers, rate limits, Otel, Docker deploy.
- **[phase-3-inbound.md](./phase-3-inbound.md)** — ~2 weeks **(optional)**. Only if the gateway itself must be a callable Bindu agent. DID signing, OAuth/mTLS server, `.well-known`.
- **[phase-4-public-network.md](./phase-4-public-network.md)** — ~2–3 weeks. Registry discovery, AgentCard auto-refresh, trust scoring, reputation UI, cycle limits. **6-month north star.**
- **[phase-5-opportunistic.md](./phase-5-opportunistic.md)** — per-bucket advanced features (payments, negotiation, push notifications, marketplace, policy-as-code).

## Phase dependency graph

```
Phase 0  →  Phase 1  →  Phase 2  →  Phase 4   (main path to public network)
                         │
                         └──→  Phase 3  (optional, only if inbound needed)
                                          │
                                          └──→ Phase 5  (pull items anytime after Phase 2)
```

## Quick-reference table

| Phase | Duration | Status | Ships |
|---|---|---|---|
| 0 | 1 day | required | protocol fixtures (no code) |
| 1 | 10 days | required | `v0.1` MVP gateway |
| 2 | ~2 weeks | required | `v0.2` production-grade |
| 3 | ~2 weeks | optional | `v0.3` inbound exposure |
| 4 | ~2–3 weeks | required (north star) | `v0.4` public network |
| 5 | ongoing | opportunistic | per-bucket patch releases |

## Key product decisions (locked in)

1. **Single endpoint, `POST /plan`.** External sends `{question, agents[], prefs}`, gets SSE back.
2. **Planner = primary LLM.** No DAG engine, no separate orchestrator service. The LLM picks tools per turn.
3. **Agent catalog per request.** External provides the list of agents + skills + endpoints. No fleet hosting.
4. **Fork OpenCode, extract modules.** Not an extension or plugin. Forked snapshot, diverge cleanly.
5. **Native TS A2A 0.3.0 implementation.** No Python subprocess, no `@bindu/sdk` dependency.
6. **Supabase Postgres for session state.** Three tables, service-role key, RLS as defense-in-depth.
7. **DID `did:bindu` when author set, else `did:key`.** Both supported by same sign/verify path.
8. **Skills opt-in per frontmatter.** Local skills advertised in AgentCard only if `bindu.expose: true`.
9. **Public / open agent network** as 6-month north star. Phases 2–4 mandatory inside that window.

## How to use this plan

- **Before starting any phase:** read its detail file end-to-end.
- **During a phase:** treat the Work Breakdown section as a per-day checklist; check off as you go.
- **At the end of a phase:** all Exit Gate criteria must pass before starting the next. No skipping.
- **If a phase slips:** don't compress downstream phases — ship the smaller thing.
