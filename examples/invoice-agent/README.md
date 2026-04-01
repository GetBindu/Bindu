Invoice Agent with X402 Payment Flow
====================================

## Overview
--------

This example implements a billing agent that:

*   Generates invoices with structured line items
    
*   Emits X402-compatible payment requests
    
*   Verifies payments and updates invoice state
    

It demonstrates a complete payment lifecycle:
```bash
   create → pay → verify → settled  
   ```

## Features
--------

*   Invoice creation with structured payload
    
*   X402 payment header generation
    
*   Payment verification (mocked for demo)
    
*   Persistent invoice state tracking (in-memory, pluggable)
    

## Example Run
--------
```bash
  npm run dev   
  ```

## Output:

```json
--- Creating Invoice ---
{
  "invoice_id": "inv_406086b8-9e87-443e-831d-037c069cdccc",        
  "total": 90,
  "payment_header": "X402 0xE5bC3b8796432A70aC8450E2aaD54055d9e2DBb8:90"
}

--- Fetch Invoice ---
{
  "invoice": {
    "id": "inv_406086b8-9e87-443e-831d-037c069cdccc",
    "recipient": "acme@example.com",
    "recipient_wallet": "0xE5bC3b8796432A70aC8450E2aaD54055d9e2DBb8",
    "items": [
      {
        "description": "API",
        "quantity": 1,
        "unit_price": 50
      },
      {
        "description": "Compute",
        "quantity": 2,
        "unit_price": 20
      }
    ],
    "currency": "USDC",
    "total": 90,
    "status": "pending",
    "due_date": null,
    "webhook_url": null,
    "created_at": "2026-03-31T19:51:49.652Z"
  }
}

--- Verify Payment ---
{
  "verified": true,
  "settled_amount": 90,
  "reason": null
}

--- Final Invoice ---
{
  "invoice": {
    "id": "inv_406086b8-9e87-443e-831d-037c069cdccc",
    "recipient": "acme@example.com",
    "recipient_wallet": "0xE5bC3b8796432A70aC8450E2aaD54055d9e2DBb8",
    "items": [
      {
        "description": "API",
        "quantity": 1,
        "unit_price": 50
      },
      {
        "description": "Compute",
        "quantity": 2,
        "unit_price": 20
      }
    ],
    "currency": "USDC",
    "total": 90,
    "status": "paid",
    "due_date": null,
    "webhook_url": null,
    "created_at": "2026-03-31T19:51:49.652Z",
    "tx_hash": "0xabc123"
  }
}
```

## Example Input
--------
```json
   {  "recipient": "acme@example.com",  "items": [    { "description": "API access", "quantity": 1, "unit_price": 50 },    { "description": "Compute", "quantity": 2, "unit_price": 20 }  ],  "currency": "USDC"}   
   ```

## Skills
--------

*   generate\_invoice – create invoice and emit X402 payment request
    
*   get\_invoice – fetch invoice by ID
    
*   list\_invoices – list invoices
    
*   verify\_payment – verify payment and update invoice state
    

## Setup
--------
```bash
   npm install   
   ```

Create .env:
```bash
   AGENT_WALLET_ADDRESS=0x_your_wallet_here   
   ```

Run:
```bash
   npm run dev   
   ```

## Notes
--------
*   Payment verification is mocked for demonstration
*   Storage is in-memory and can be replaced with a database
*   Wallet address can be any valid EVM address