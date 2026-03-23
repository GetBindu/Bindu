import type ObjectId from "bson-objectid";

export interface MigrationResult {
	_id: ObjectId;
	name: string;
	status: "success" | "failure" | "ongoing";
}
