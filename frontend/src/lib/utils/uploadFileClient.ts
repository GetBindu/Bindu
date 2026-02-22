import { base } from "$app/paths";
import type { MessageFile } from "$lib/types/Message";

export function uploadFile(
    file: File,
    conversationId?: string,
    onProgress?: (progress: number) => void
): Promise<MessageFile> {
    return new Promise((resolve, reject) => {
        const formData = new FormData();
        formData.append("file", file);
        formData.append("conversationId", conversationId ?? "temp");

        const xhr = new XMLHttpRequest();

        xhr.upload.addEventListener("progress", (event) => {
            if (event.lengthComputable && onProgress) {
                const percentComplete = (event.loaded / event.total) * 100;
                onProgress(percentComplete);
            }
        });

        xhr.addEventListener("load", () => {
            if (xhr.status >= 200 && xhr.status < 300) {
                try {
                    const res = JSON.parse(xhr.responseText);
                    resolve(res);
                } catch (e) {
                    reject(new Error("Invalid JSON response"));
                }
            } else {
                reject(new Error(xhr.statusText || "Upload failed"));
            }
        });

        xhr.addEventListener("error", () => {
            reject(new Error("Network error"));
        });

        xhr.open("POST", `${base}/api/upload`);
        xhr.send(formData);
    });
}
