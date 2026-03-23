// Client-safe HF utilities used in UI components

export function isStrictHfLogin(urlString: string): boolean {
	try {
		const u = new URL(urlString);
		const host = u.hostname.toLowerCase();
		const allowedHosts = new Set(["huggingface.co", "login.huggingface.co"]);
		return (
			u.protocol === "https:" &&
			allowedHosts.has(host)
		);
	} catch {
		return false;
	}
}
