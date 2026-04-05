import { error } from "@sveltejs/kit";
import { collections } from "$lib/server/database";
import type { Conversation } from "$lib/types/Conversation";
import type { SharedConversation } from "$lib/types/SharedConversation";
import type { MessageFile } from "$lib/types/Message";

export async function downloadFile(
	sha256: string,
	convId: Conversation["_id"] | SharedConversation["_id"]
): Promise<MessageFile & { type: "base64" }> {
	const fileId = collections.bucket.find({ filename: `${convId.toString()}-${sha256}` });

	const file = await fileId.next();
	if (!file) {
		error(404, "File not found");
	}
	if (file.metadata?.conversation !== convId.toString()) {
		error(403, "You don't have access to this file.");
	}

	const mime = file.metadata?.mime;
	const name = file.filename;

	const fileStream = collections.bucket.openDownloadStream(file._id);

	const buffer = await new Promise<Buffer>((resolve, reject) => {
		const chunks: Uint8Array[] = [];
		const onData = (chunk: unknown) => {
			if (chunk instanceof Uint8Array) {
				chunks.push(chunk);
				return;
				}
				const err = new Error("Unexpected chunk type from fileStream");
				fileStream.destroy();
				cleanup();
				reject(err);
			};

		const onError = (err: Error | null | undefined) => {
			cleanup();
			reject(err ?? new Error("File download failed"));
		};

		const onEnd = () => {
			cleanup();
			resolve(Buffer.concat(chunks));
		};

		const cleanup = () => {
			fileStream.off("data", onData);
			fileStream.off("error", onError);
			fileStream.off("end", onEnd);
		};

		fileStream.on("data", onData);
		fileStream.once("error", onError);
		fileStream.once("end", onEnd);
	});

	return { type: "base64", name, value: buffer.toString("base64"), mime: String(mime ?? "") };
}
