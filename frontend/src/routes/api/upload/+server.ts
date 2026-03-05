import { authCondition } from "$lib/server/auth";
import { collections } from "$lib/server/database";
import { error } from "@sveltejs/kit";
import ObjectId from "bson-objectid";
import { z } from "zod";
import { uploadFile } from "$lib/server/files/uploadFile";
import type { RequestHandler } from "./$types";

export const POST: RequestHandler = async ({ request, locals }) => {
    const userId = locals.user?._id ?? locals.sessionId;

    if (!userId) {
        error(401, "Unauthorized");
    }

    const formData = await request.formData();
    const file = formData.get("file") as File;
    const conversationId = formData.get("conversationId") as string;

    if (!file || !conversationId) {
        error(400, "Missing file or conversationId");
    }

    const convId = conversationId === "temp" ? null : new ObjectId(conversationId);

    let conv = null;
    if (convId) {
        conv = await collections.conversations.findOne({
            _id: convId,
            ...authCondition(locals),
        });

        if (!conv) {
            error(404, "Conversation not found");
        }
    }

    // size limit check (10MB)
    if (file.size > 10 * 1024 * 1024) {
        error(413, "File too large");
    }

    try {
        const uploadedFile = await uploadFile(file, conv);
        return new Response(JSON.stringify(uploadedFile), {
            headers: { "Content-Type": "application/json" },
        });
    } catch (e) {
        console.error(e);
        error(500, "Failed to upload file");
    }
}
