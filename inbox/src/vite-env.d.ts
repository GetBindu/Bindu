/// <reference types="vite/client" />

interface ImportMetaEnv {
	readonly VITE_COMMS_TOKEN?: string;
}

interface ImportMeta {
	readonly env: ImportMetaEnv;
}
