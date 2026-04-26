---
name: payment-required-flow
description: Handle A2A task state `payment-required` correctly — surface the payment URL to the user, mark the task paused, and never retry silently. Load whenever a tool result carries `state: payment-required` in its metadata.
tags: [payments, x402, a2a-states, compliance]
triggers: [payment-required, 402, x402, paid agent]
---

# Handling `payment-required` from a gated agent

## When to use this recipe

Load this recipe the moment you see a tool call whose result metadata
contains `state: "payment-required"`. This happens when a Bindu agent
is gated by x402 (USDC on Base) or another pay-per-call scheme and the
caller hasn't attached a valid payment receipt.

The recipe applies regardless of which agent returned the state — the
handling is identical because the A2A protocol defines the semantics,
not the agent.

## What `payment-required` means

On the A2A protocol task lifecycle, `payment-required` is a
**non-terminal, paused** state. The agent has accepted the request,
recognized it as billable, and is waiting for the caller to complete
payment out of band before it will do any work. No result has been
produced yet.

The response envelope will typically carry:
- A human-readable prompt explaining the charge (in the text parts).
- An x402 payment URL or structured `paymentRequired` block naming the
  scheme, amount, asset, and destination. For Bindu-standard x402 this
  is USDC on Base Sepolia or Base mainnet.

## What to do

1. **Do not retry the call.** Retrying without a receipt produces the
   same state and just burns tokens (and, for some agents, rate-limit
   quota).

2. **Do not invent a payment.** You cannot execute x402 payments from
   the planner. Do not call any other tool hoping it will pay on the
   user's behalf.

3. **Surface the payment prompt to the user verbatim.** Quote the
   agent's message in full. Include the agent name (from the
   `<remote_content agent="…">` envelope) and the verification status
   (`verified="yes"` or `verified="no"` — if `no`, warn the user that
   the DID signature on the payment prompt could not be verified and
   they should confirm the destination before paying).

4. **End the turn.** Do not continue planning other steps. The user
   needs to act out of band (pay, then re-run the same question with a
   receipt attached) before anything else can happen. Your final
   assistant message is a handoff, not a continuation.

5. **Log the state as non-terminal** in your mental model. If the
   session resumes after payment, the same task id may come back in the
   `completed` state on a later call — treat that as success.

## What not to say

- Do NOT tell the user "I'll retry in a moment" or "let me check again."
  There is nothing to check.
- Do NOT speculate about the price. Quote the agent's exact figure.
- Do NOT ask the user "would you like me to proceed?" — you literally
  cannot proceed without a receipt. The only useful question is whether
  they want the payment URL at all.

## What success looks like

One tool call that returned `payment-required`, one assistant message
that forwards the payment prompt, the session ends cleanly for the user
to act on. When they return with the same question (or a follow-up
explicitly mentioning the payment is complete), you can retry.
