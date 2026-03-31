import { getInvoiceById } from "./storage.js"

// mock interface (real lib can replace later)
export async function verifyTransaction(
  tx_hash: string,
  invoice: any
) {
  // TODO: replace with real x402 verify lib
  return {
    success: true,
    amount: invoice.total,
    failure_reason: null
  }
}

export async function verifyPayment(
  invoice_id: string,
  tx_hash: string
) {
  const invoice = getInvoiceById(invoice_id)

  if (!invoice || invoice.status !== "pending") {
    return { verified: false, reason: "invalid invoice" }
  }

  const result = await verifyTransaction(tx_hash, invoice)

  if (result.success) {
    invoice.status = "paid"
    invoice.tx_hash = tx_hash
  }

  return {
    verified: result.success,
    settled_amount: result.amount,
    reason: result.failure_reason
  }
}