import type { Migration } from ".";
import { collections } from "$lib/server/database";
import ObjectId from "bson-objectid";
type AnyBulkWriteOperation = { updateOne: { filter: Record<string, unknown>; update: Record<string, unknown> } };
import type { Assistant } from "$lib/types/Assistant";
import { generateSearchTokens } from "$lib/utils/searchTokens";

const migration: Migration = {
	_id: new ObjectId("5f9f3e3e3e3e3e3e3e3e3e3e"),
	name: "Update search assistants",
	up: async () => {
		const { assistants } = collections;
		let ops: AnyBulkWriteOperation[] = [];

		for await (const assistant of assistants.find({}) as AsyncIterable<Assistant>) {
			ops.push({
				updateOne: {
					filter: {
						_id: assistant._id,
					},
					update: {
						$set: {
							searchTokens: generateSearchTokens(assistant.name),
						},
					},
				},
			});

			if (ops.length >= 1000) {
				process.stdout.write(".");
				await assistants.bulkWrite(ops, { ordered: false });
				ops = [];
			}
		}

		if (ops.length) {
			await assistants.bulkWrite(ops, { ordered: false });
		}

		return true;
	},
	down: async () => {
		const { assistants } = collections;
		await assistants.updateMany({}, { $unset: { searchTokens: "" } });
		return true;
	},
};

export default migration;
