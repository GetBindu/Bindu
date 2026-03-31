export type InvoiceItem = {
  description: string
  quantity: number
  unit_price: number
}

export type Invoice = {
  id: string
  recipient: string
  recipient_wallet: string
  items: InvoiceItem[]
  currency: string
  total: number
  status: "pending" | "paid" | "failed"
  due_date?: string
  tx_hash?: string
  webhook_url?: string
  created_at: string
}