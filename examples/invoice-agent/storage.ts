import type { Invoice } from "./types.js"

const db: Record<string, Invoice> = {}

export function saveInvoice(invoice: Invoice) {
  db[invoice.id] = invoice
}

export function getInvoiceById(id: string): Invoice | null {
  return db[id] ?? null
}

export function listInvoices(): Invoice[] {
  return Object.values(db)
}