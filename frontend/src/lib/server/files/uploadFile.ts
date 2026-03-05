import type { Conversation } from "$lib/types/Conversation";
import type { MessageFile } from "$lib/types/Message";
import { sha256 } from "$lib/utils/sha256";
import { fileTypeFromBuffer } from "file-type";
import { collections } from "$lib/server/database";

export async function uploadFile(file: File, conv: Conversation | null): Promise<MessageFile> {
	const sha = await sha256(await file.text());
	const buffer = Buffer.from(await file.arrayBuffer());

	// Attempt to detect the mime type of the file, fallback to the uploaded mime
	const mime = await fileTypeFromBuffer(buffer).then((fileType) => fileType?.mime ?? file.type);

	const upload = collections.bucket.openUploadStream(`${conv?._id ?? "temp"}-${sha}`, {
		metadata: { conversation: conv?._id.toString() ?? "temp", mime },
	});

	upload.write(buffer);
	upload.end();

	// only return the filename when upload throws a finish event or a 20s time out occurs
	return new Promise((resolve, reject) => {
		(upload as any).on("finish", () =>
			resolve({ type: "hash", value: (upload as any).id.toString(), mime: file.type, name: file.name })
		);
		(upload as any).on("error", reject);
		setTimeout(() => reject(new Error("Upload timed out")), 20_000);
	});
}
