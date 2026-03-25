import { writable, derived } from "svelte/store";

export interface UploadProgress {
	fileId: string;
	fileName: string;
	progress: number; // 0-100
	status: "pending" | "uploading" | "success" | "error";
	error?: string;
	startTime?: number;
	endTime?: number;
}

interface UploadState {
	uploads: Map<string, UploadProgress>;
	totalProgress: number;
}

function createUploadStore() {
	const initialState: UploadState = {
		uploads: new Map(),
		totalProgress: 0,
	};

	const { subscribe, set, update } = writable<UploadState>(initialState);

	function generateFileId(file: File): string {
		return `${file.name}-${file.size}-${file.lastModified}`;
	}

	function addUpload(file: File) {
		const fileId = generateFileId(file);
		update((state) => {
			state.uploads.set(fileId, {
				fileId,
				fileName: file.name,
				progress: 0,
				status: "pending",
				startTime: Date.now(),
			});
			return state;
		});
		return fileId;
	}

	function updateProgress(fileId: string, progress: number) {
		update((state) => {
			const upload = state.uploads.get(fileId);
			if (upload) {
				upload.progress = Math.min(100, Math.max(0, progress));
				upload.status = progress === 100 ? "success" : "uploading";
				if (progress === 100) {
					upload.endTime = Date.now();
				}
			}
			return state;
		});
	}

	function setError(fileId: string, error: string) {
		update((state) => {
			const upload = state.uploads.get(fileId);
			if (upload) {
				upload.status = "error";
				upload.error = error;
				upload.endTime = Date.now();
				upload.progress = 0;
			}
			return state;
		});
	}

	function removeUpload(fileId: string) {
		update((state) => {
			state.uploads.delete(fileId);
			return state;
		});
	}

	function clearAll() {
		set(initialState);
	}

	return {
		subscribe,
		addUpload,
		updateProgress,
		setError,
		removeUpload,
		clearAll,
	};
}

export const fileUploadStore = createUploadStore();

// Derived stores for easier access
export const activeUploads = derived(
	fileUploadStore,
	($state) =>
		Array.from($state.uploads.values()).filter(
			(u) => u.status === "pending" || u.status === "uploading"
		)
);

export const uploadErrors = derived(
	fileUploadStore,
	($state) => Array.from($state.uploads.values()).filter((u) => u.status === "error")
);

export const overallProgress = derived(
	fileUploadStore,
	($state) => {
		const uploads = Array.from($state.uploads.values());
		if (uploads.length === 0) return 0;
		const total = uploads.reduce((sum, u) => sum + u.progress, 0);
		return Math.round(total / uploads.length);
	}
);
