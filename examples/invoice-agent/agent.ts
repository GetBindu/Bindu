// agent.ts

import { createInvoice } from "./invoice.js"
import { verifyPayment } from "./x402Handler.js"
import { getInvoiceById, listInvoices } from "./storage.js"

export const invoiceAgent = {
  name: "invoice-agent",

  skills: {
    generate_invoice: async (input: any) => {
      const invoice = createInvoice(input)

      return {
        invoice_id: invoice.id,
        total: invoice.total,
        payment_header: `X402 ${invoice.recipient_wallet}:${invoice.total}`
      }
    },

    get_invoice: async ({ invoice_id }: any) => {
      return { invoice: getInvoiceById(invoice_id) }
    },

    list_invoices: async () => {
      return { invoices: listInvoices() }
    },

    verify_payment: async ({ invoice_id, tx_hash }: any) => {
      return await verifyPayment(invoice_id, tx_hash)
    }
  }
}