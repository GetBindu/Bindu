---
id: invoice-agent-v1
name: invoice-agent
version: 1.0.0
author: akash
tags:
  - billing
  - payments
  - x402
input_modes:
  - application/json
output_modes:
  - application/json
---

# Invoice Agent

## generate_invoice
Create invoice and emit X402 payment request

## get_invoice
Fetch invoice by ID

## list_invoices
List invoices

## verify_payment
Verify payment and update invoice state