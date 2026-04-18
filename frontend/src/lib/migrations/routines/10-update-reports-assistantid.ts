import { collections } from "$lib/server/database";
import type { Migration } from ".";
import ObjectId from "bson-objectid";

const migration: Migration = {
	_id: new ObjectId("000000000000000000000010"),
	name: "Update reports with assistantId to use contentId",
	up: async () => {
		const reports = await collections.reports
			.find({
				assistantId: { $exists: true, $ne: null },
			})
			.toArray();

		for (const report of reports) {
			const assistantId = report.assistantId;
			if (!assistantId) {
				continue;
			}
			await collections.reports.updateOne(
				{ _id: report._id },
				{
					$set: {
						object: "assistant",
						contentId: assistantId,
					},
					$unset: { assistantId: "" },
				}
			);
		}
		return true;
	},
};

export default migration;
