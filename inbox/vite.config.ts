import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));

export default defineConfig({
	plugins: [react(), tailwindcss()],
	resolve: {
		alias: {
			"~": path.resolve(here, "src"),
		},
	},
	server: {
		// 3773 = bindufy agents, 3774 = gateway, 3775 = comms UI.
		// strictPort: refuse to silently shift up when the port is taken;
		// that's masked too many "old comms still running" bugs already.
		port: 3775,
		strictPort: true,
		host: "127.0.0.1",
		proxy: {
			"/api": "http://127.0.0.1:3787",
		},
	},
});
