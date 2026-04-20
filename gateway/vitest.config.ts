import { defineConfig } from "vitest/config"
import { resolve } from "path"

export default defineConfig({
  test: {
    environment: "node",
    env: {
      ...(() => {
        try {
          // load .env.local for tests
          const fs = require("fs")
          const path = resolve(process.cwd(), ".env.local")
          if (fs.existsSync(path)) {
            const raw = fs.readFileSync(path, "utf8")
            const out: Record<string, string> = {}
            for (const line of raw.split(/\r?\n/)) {
              const m = line.match(/^\s*([A-Z0-9_]+)\s*=\s*(.*)\s*$/)
              if (m) out[m[1]] = m[2].replace(/^['"]|['"]$/g, "")
            }
            return out
          }
        } catch {
          /* ignore */
        }
        return {}
      })(),
    },
    include: ["tests/**/*.test.ts"],
  },
  resolve: {
    alias: {
      "@": resolve(__dirname, "src"),
    },
  },
})
