import { writable } from "svelte/store";

export interface Toast {
	id: string;
	message: string;
	type: "success" | "error" | "info" | "warning";
	duration?: number; // ms, 0 = persistent
	action?: {
		label: string;
		onClick: () => void;
	};
}

function createToastStore() {
	const { subscribe, update } = writable<Toast[]>([]);

	let toastId = 0;

	function addToast(
		message: string,
		type: "success" | "error" | "info" | "warning" = "info",
		duration = 4000
	): string {
		const id = `toast-${++toastId}`;
		const toast: Toast = { id, message, type, duration };

		update((toasts) => [...toasts, toast]);

		if (duration > 0) {
			setTimeout(() => removeToast(id), duration);
		}

		return id;
	}

	function removeToast(id: string) {
		update((toasts) => toasts.filter((t) => t.id !== id));
	}

	function success(message: string, duration?: number) {
		return addToast(message, "success", duration);
	}

	function error(message: string, duration?: number) {
		return addToast(message, "error", duration ?? 6000);
	}

	function info(message: string, duration?: number) {
		return addToast(message, "info", duration);
	}

	function warning(message: string, duration?: number) {
		return addToast(message, "warning", duration);
	}

	return {
		subscribe,
		addToast,
		removeToast,
		success,
		error,
		info,
		warning,
	};
}

export const toastStore = createToastStore();
