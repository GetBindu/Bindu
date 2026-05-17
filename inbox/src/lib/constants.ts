/** Synthetic agent id used for operator-sent (outbound) events.
 * Outbound messages are recorded under this lane so the Gmail-shape
 * inbox can group an operator's outgoing send with the recipient's
 * inbound lifecycle events by `context_id`. The server uses the same
 * constant; this is the client mirror so we don't have three string
 * literals scattered across components. */
export const OUTBOX_AGENT_ID = "outbox";
