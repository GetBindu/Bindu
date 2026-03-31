import "dotenv/config"

export const CONFIG = {
  AGENT_WALLET_ADDRESS: process.env.AGENT_WALLET_ADDRESS
    || (() => {
        throw new Error("AGENT_WALLET_ADDRESS not set")
      })()
}