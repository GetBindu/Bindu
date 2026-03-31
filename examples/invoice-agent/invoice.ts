import type { Invoice, InvoiceItem } from "./types.js"
import { saveInvoice, getInvoiceById } from "./storage.js"
import { v4 as uuidv4 } from "uuid"
import { CONFIG } from "./config.js";


export function calculateTotal(items: InvoiceItem[]): number {
  return items.reduce((sum, item) => {
    return sum + item.quantity * item.unit_price
  }, 0)
}

export function createInvoice(payload: any): Invoice {
  const total = calculateTotal(payload.items)
  

  const invoice: Invoice = {
    id: `inv_${uuidv4()}`,
    recipient: payload.recipient,
    recipient_wallet: payload.recipient_wallet ?? CONFIG.AGENT_WALLET_ADDRESS,
    items: payload.items,
    currency: payload.currency,
    total,
    status: "pending",
    due_date: payload.due_date ?? null,
    webhook_url: payload.webhook_url ?? null,
    created_at: new Date().toISOString()
  }

  saveInvoice(invoice)
  return invoice
}

export function markInvoicePaid(id: string, tx_hash: string) {
  const invoice = getInvoiceById(id)
  if (!invoice) throw new Error("Invoice not found")

  invoice.status = "paid"
  invoice.tx_hash = tx_hash

  saveInvoice(invoice)
  return invoice
}