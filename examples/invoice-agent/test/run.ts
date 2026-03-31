import { invoiceAgent } from "../agent.js"

async function testFlow() {
  console.log("\n--- Creating Invoice ---")
  const skills = invoiceAgent.skills

  const invoice = await skills.generate_invoice({
    recipient: "acme@example.com",
    items: [
      { description: "API", quantity: 1, unit_price: 50 },
      { description: "Compute", quantity: 2, unit_price: 20 }
    ],
    currency: "USDC"
  })

  console.log(JSON.stringify(invoice, null, 2))

  console.log("\n--- Fetch Invoice ---")

  const fetched = await skills.get_invoice({
    invoice_id: invoice.invoice_id
  })

  console.log(JSON.stringify(fetched, null, 2))

  console.log("\n--- Verify Payment ---")

  const payment = await skills.verify_payment({
    invoice_id: invoice.invoice_id,
    tx_hash: "0xabc123"
  })

  console.log(JSON.stringify(payment, null, 2))

  console.log("\n--- Final Invoice ---")

  const final = await skills.get_invoice({
    invoice_id: invoice.invoice_id
  })

  console.log(JSON.stringify(final, null, 2))
}

testFlow()