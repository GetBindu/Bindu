/**
 * In-Memory Database Implementation
 * Replaces MongoDB with simple in-memory Map-based storage for Bindu demo
 */

import type { Conversation } from "$lib/types/Conversation";
import type { SharedConversation } from "$lib/types/SharedConversation";
import type { AbortedGeneration } from "$lib/types/AbortedGeneration";
import type { Settings } from "$lib/types/Settings";
import type { User } from "$lib/types/User";
import type { MessageEvent } from "$lib/types/MessageEvent";
import type { Session } from "$lib/types/Session";
import type { Assistant } from "$lib/types/Assistant";
import type { Report } from "$lib/types/Report";
import type { ConversationStats } from "$lib/types/ConversationStats";
import type { MigrationResult } from "$lib/types/MigrationResult";
import type { Semaphore } from "$lib/types/Semaphore";
import type { AssistantStats } from "$lib/types/AssistantStats";
import { logger } from "$lib/server/logger";
import { building } from "$app/environment";
import type { TokenCache } from "$lib/types/TokenCache";
import type { ConfigKey } from "$lib/types/ConfigKey";
import ObjectId from "bson-objectid";

export const CONVERSATION_STATS_COLLECTION = "conversations.stats";

/** Type for the collections object returned by Database.getCollections() */
export type DatabaseCollections = {
	conversations: InMemoryCollection<Conversation>;
	conversationStats: InMemoryCollection<ConversationStats>;
	assistants: InMemoryCollection<Assistant>;
	assistantStats: InMemoryCollection<AssistantStats>;
	reports: InMemoryCollection<Report>;
	sharedConversations: InMemoryCollection<SharedConversation>;
	abortedGenerations: InMemoryCollection<AbortedGeneration>;
	settings: InMemoryCollection<Settings>;
	users: InMemoryCollection<User>;
	sessions: InMemoryCollection<Session>;
	messageEvents: InMemoryCollection<MessageEvent>;
	bucket: InMemoryBucket;
	migrationResults: InMemoryCollection<MigrationResult>;
	semaphores: InMemoryCollection<Semaphore>;
	tokenCaches: InMemoryCollection<TokenCache>;
	tools: InMemoryCollection<Record<string, unknown>>;
	config: InMemoryCollection<ConfigKey>;
};

// Re-export ObjectId for compatibility
export { ObjectId };

/**
 * Simple in-memory collection that mimics MongoDB Collection interface
 */
class InMemoryCollection<T = Record<string, unknown>> {
	private data: Map<string, T> = new Map();
	private name: string;

	constructor(name: string) {
		this.name = name;
	}

	async findOne(filter: Record<string, unknown> = {}): Promise<T | null> {
		for (const doc of this.data.values()) {
			if (this.matchesFilter(doc, filter)) {
				return doc;
			}
		}
		return null;
	}

	find(filter: Record<string, unknown> = {}): InMemoryCursor<T> {
		const results: T[] = [];
		for (const doc of this.data.values()) {
			if (this.matchesFilter(doc, filter)) {
				results.push(doc);
			}
		}
		return new InMemoryCursor(results);
	}

	async insertOne(doc: T): Promise<{ insertedId: ObjectId; acknowledged: boolean }> {
		const id = new ObjectId();
		const docWithId = { ...doc, _id: id } as T;
		this.data.set(id.toString(), docWithId);
		return { insertedId: id, acknowledged: true };
	}

	async insertMany(docs: T[]): Promise<{ insertedIds: ObjectId[]; acknowledged: boolean }> {
		const ids: ObjectId[] = [];
		for (const doc of docs) {
			const result = await this.insertOne(doc);
			ids.push(result.insertedId);
		}
		return { insertedIds: ids, acknowledged: true };
	}

	async updateOne(
		filter: Record<string, unknown>,
		update: Record<string, unknown>,
		options: { upsert?: boolean } = {}
	): Promise<{ matchedCount: number; modifiedCount: number; upsertedId?: ObjectId }> {
		for (const [id, doc] of this.data.entries()) {
			if (this.matchesFilter(doc, filter)) {
				const updated = this.applyUpdate(doc, update);
				this.data.set(id, updated);
				return { matchedCount: 1, modifiedCount: 1 };
			}
		}
		if (options.upsert) {
			const $set = (update.$set || {}) as Partial<T>;
			const $setOnInsert = (update.$setOnInsert || {}) as Partial<T>;
			const newDoc = { ...filter, ...$set, ...$setOnInsert } as T;
			const result = await this.insertOne(newDoc);
			return { matchedCount: 0, modifiedCount: 0, upsertedId: result.insertedId };
		}
		return { matchedCount: 0, modifiedCount: 0 };
	}

	async updateMany(
		filter: Record<string, unknown>,
		update: Record<string, unknown>
	): Promise<{ matchedCount: number; modifiedCount: number }> {
		let count = 0;
		for (const [id, doc] of this.data.entries()) {
			if (this.matchesFilter(doc, filter)) {
				const updated = this.applyUpdate(doc, update);
				this.data.set(id, updated);
				count++;
			}
		}
		return { matchedCount: count, modifiedCount: count };
	}

	async deleteOne(filter: Record<string, unknown>): Promise<{ deletedCount: number }> {
		for (const [id, doc] of this.data.entries()) {
			if (this.matchesFilter(doc, filter)) {
				this.data.delete(id);
				return { deletedCount: 1 };
			}
		}
		return { deletedCount: 0 };
	}

	async deleteMany(filter: Record<string, unknown>): Promise<{ deletedCount: number }> {
		let count = 0;
		const toDelete: string[] = [];
		for (const [id, doc] of this.data.entries()) {
			if (this.matchesFilter(doc, filter)) {
				toDelete.push(id);
				count++;
			}
		}
		for (const id of toDelete) {
			this.data.delete(id);
		}
		return { deletedCount: count };
	}

	async countDocuments(filter: Record<string, unknown> = {}): Promise<number> {
		let count = 0;
		for (const doc of this.data.values()) {
			if (this.matchesFilter(doc, filter)) {
				count++;
			}
		}
		return count;
	}

	async createIndex(_spec: Record<string, unknown>, _options?: Record<string, unknown>): Promise<string> {
		// No-op for in-memory storage
		return "index_" + Date.now();
	}

	aggregate<R = T>(_pipeline: Record<string, unknown>[]): InMemoryCursor<R> {
		// Simplified aggregation - just return all docs
		return new InMemoryCursor(Array.from(this.data.values()) as unknown as R[]);
	}

	listIndexes() {
		// Return an async iterable that yields nothing (no indexes in memory)
		return {
			toArray: async () => [],
			async *[Symbol.asyncIterator]() {},
		};
	}

	async bulkWrite(
		operations: Array<{ updateOne?: { filter: Record<string, unknown>; update: Record<string, unknown> } }>,
		_options?: Record<string, unknown>
	): Promise<{ matchedCount: number; modifiedCount: number }> {
		let matchedCount = 0;
		let modifiedCount = 0;
		for (const op of operations) {
			if (op.updateOne) {
				const result = await this.updateOne(op.updateOne.filter, op.updateOne.update);
				matchedCount += result.matchedCount;
				modifiedCount += result.modifiedCount;
			}
		}
		return { matchedCount, modifiedCount };
	}

	private matchesFilter(doc: T, filter: Record<string, unknown>): boolean {
		if (Object.keys(filter).length === 0) return true;

		for (const [key, value] of Object.entries(filter)) {
			if (key === "$or") {
				const orConditions = value as Record<string, unknown>[];
				if (!orConditions.some((cond) => this.matchesFilter(doc, cond))) {
					return false;
				}
				continue;
			}
			if (key === "$and") {
				const andConditions = value as Record<string, unknown>[];
				if (!andConditions.every((cond) => this.matchesFilter(doc, cond))) {
					return false;
				}
				continue;
			}

			const docValue = this.getNestedValue(doc, key);

			if (typeof value === "object" && value !== null && !Array.isArray(value)) {
				const ops = value as Record<string, unknown>;
				if ("$exists" in ops) {
					if (ops.$exists && docValue === undefined) return false;
					if (!ops.$exists && docValue !== undefined) return false;
					continue;
				}
				if ("$in" in ops) {
					if (!(ops.$in as unknown[]).includes(docValue)) return false;
					continue;
				}
				if ("$gt" in ops) {
					if (!((docValue as number) > (ops.$gt as number))) return false;
					continue;
				}
				if ("$gte" in ops) {
					if (!((docValue as number) >= (ops.$gte as number))) return false;
					continue;
				}
				if ("$lt" in ops) {
					if (!((docValue as number) < (ops.$lt as number))) return false;
					continue;
				}
				if ("$lte" in ops) {
					if (!((docValue as number) <= (ops.$lte as number))) return false;
					continue;
				}
			}

			// Handle ObjectId comparison
			if (value && typeof value === "object" && "toString" in value) {
				if (docValue?.toString() !== value.toString()) return false;
			} else if (docValue !== value) {
				return false;
			}
		}
		return true;
	}

	private getNestedValue(obj: unknown, path: string): unknown {
		const parts = path.split(".");
		let current = obj;
		for (const part of parts) {
			if (current === null || current === undefined) return undefined;
			current = (current as Record<string, unknown>)[part];
		}
		return current;
	}

	private applyUpdate(doc: T, update: Record<string, unknown>): T {
		let result = { ...doc };
		if (update.$set) {
			result = { ...result, ...(update.$set as Partial<T>) };
		}
		if (update.$inc) {
			for (const [key, value] of Object.entries(update.$inc as Record<string, number>)) {
				(result as Record<string, unknown>)[key] =
					((result as Record<string, unknown>)[key] as number || 0) + value;
			}
		}
		if (update.$push) {
			for (const [key, value] of Object.entries(update.$push as Record<string, unknown>)) {
				const arr = ((result as Record<string, unknown>)[key] as unknown[]) || [];
				(result as Record<string, unknown>)[key] = [...arr, value];
			}
		}
		if (update.$unset) {
			for (const key of Object.keys(update.$unset as Record<string, unknown>)) {
				delete (result as Record<string, unknown>)[key];
			}
		}
		return result;
	}
}

/**
 * Simple cursor for iterating results
 */
class InMemoryCursor<T> {
	private results: T[];
	private _limit?: number;
	private _skip?: number;
	private _sort?: Record<string, 1 | -1>;
	private _projection?: Record<string, unknown>;
	private _index: number = 0;
	private _processed: T[] | null = null;

	constructor(results: T[]) {
		this.results = results;
	}

	limit(n: number): this {
		this._limit = n;
		return this;
	}

	skip(n: number): this {
		this._skip = n;
		return this;
	}

	sort(spec: Record<string, 1 | -1>): this {
		this._sort = spec;
		return this;
	}

	project<R = T>(_spec: Record<string, unknown>): InMemoryCursor<R> {
		this._projection = _spec;
		return this as unknown as InMemoryCursor<R>;
	}

	batchSize(_n: number): this {
		// No-op for in-memory
		return this;
	}

	private getProcessed(): T[] {
		if (this._processed) return this._processed;

		let result = [...this.results];

		if (this._sort) {
			const sortKey = Object.keys(this._sort)[0];
			const sortDir = this._sort[sortKey];
			result.sort((a, b) => {
				const aVal = (a as Record<string, unknown>)[sortKey] as number;
				const bVal = (b as Record<string, unknown>)[sortKey] as number;
				if (aVal < bVal) return -1 * sortDir;
				if (aVal > bVal) return 1 * sortDir;
				return 0;
			});
		}

		if (this._skip) {
			result = result.slice(this._skip);
		}
		if (this._limit) {
			result = result.slice(0, this._limit);
		}

		this._processed = result;
		return result;
	}

	async toArray(): Promise<T[]> {
		return this.getProcessed();
	}

	async hasNext(): Promise<boolean> {
		return this._index < this.getProcessed().length;
	}

	async next(): Promise<T | null> {
		const processed = this.getProcessed();
		if (this._index < processed.length) {
			return processed[this._index++];
		}
		return null;
	}

	async tryNext(): Promise<T | null> {
		return this.next();
	}

	async *[Symbol.asyncIterator](): AsyncGenerator<T> {
		const arr = await this.toArray();
		for (const item of arr) {
			yield item;
		}
	}
}

/**
 * Simple in-memory file storage (replaces GridFS)
 */
class InMemoryBucket {
	private files: Map<string, { _id: string; data: Buffer; filename: string; metadata?: Record<string, unknown> }> = new Map();

	openUploadStream(filename: string, _options?: { metadata?: Record<string, unknown> }) {
		const id = new ObjectId();
		const chunks: Buffer[] = [];

		const stream = {
			id,
			write: (chunk: Buffer) => {
				chunks.push(chunk);
			},
			end: () => {
				const data = Buffer.concat(chunks);
				this.files.set(id.toString(), { _id: id.toString(), data, filename, metadata: _options?.metadata });
			},
			on: (_event: string, cb: (err?: Error) => void) => {
				if (_event === "finish") setTimeout(() => cb(), 0);
				return stream;
			},
		};
		return stream;
	}

	openDownloadStream(id: ObjectId | string) {
		const file = this.files.get(id.toString());
		const downloadStream = {
			pipe<T extends { write: (d: Buffer) => void; end: () => void }>(dest: T): T {
				if (file) dest.write(file.data);
				dest.end();
				return dest;
			},
			on(_event: string, cb: (err?: Error) => void) {
				if (_event === "error" && !file) cb(new Error("File not found"));
				return downloadStream;
			},
		};
		return downloadStream;
	}

	async delete(id: ObjectId): Promise<void> {
		this.files.delete(id.toString());
	}

	find(_filter: Record<string, unknown> = {}) {
		return new InMemoryCursor(Array.from(this.files.values()));
	}
}

/**
 * In-Memory Database singleton
 */
export class Database {
	private static instance: Database;
	private collectionsCache: DatabaseCollections | null = null;

	private constructor() {}

	private async init() {
		logger.info("[database] Using in-memory storage (no MongoDB required)");
	}

	public static async getInstance(): Promise<Database> {
		if (!Database.instance) {
			Database.instance = new Database();
			await Database.instance.init();
		}
		return Database.instance;
	}

	public getClient() {
		// Return a mock client for compatibility with MongoDB client interface
		return {
			connect: async () => ({
				db: () => ({
					collection: (name: string) => new InMemoryCollection(name),
				}),
			}),
			db: () => ({
				collection: (name: string) => new InMemoryCollection(name),
			}),
			startSession: () => ({
				withTransaction: async (fn: () => Promise<void>) => { await fn(); },
				endSession: async () => {},
			}),
		};
	}

	public getCollections(): DatabaseCollections {
		if (this.collectionsCache) return this.collectionsCache;

		const conversations = new InMemoryCollection<Conversation>("conversations");
		const conversationStats = new InMemoryCollection<ConversationStats>("conversations.stats");
		const assistants = new InMemoryCollection<Assistant>("assistants");
		const assistantStats = new InMemoryCollection<AssistantStats>("assistants.stats");
		const reports = new InMemoryCollection<Report>("reports");
		const sharedConversations = new InMemoryCollection<SharedConversation>("sharedConversations");
		const abortedGenerations = new InMemoryCollection<AbortedGeneration>("abortedGenerations");
		const settings = new InMemoryCollection<Settings>("settings");
		const users = new InMemoryCollection<User>("users");
		const sessions = new InMemoryCollection<Session>("sessions");
		const messageEvents = new InMemoryCollection<MessageEvent>("messageEvents");
		const migrationResults = new InMemoryCollection<MigrationResult>("migrationResults");
		const semaphores = new InMemoryCollection<Semaphore>("semaphores");
		const tokenCaches = new InMemoryCollection<TokenCache>("tokens");
		const tools = new InMemoryCollection<Record<string, unknown>>("tools");
		const configCollection = new InMemoryCollection<ConfigKey>("config");
		const bucket = new InMemoryBucket();

		this.collectionsCache = {
			conversations,
			conversationStats,
			assistants,
			assistantStats,
			reports,
			sharedConversations,
			abortedGenerations,
			settings,
			users,
			sessions,
			messageEvents,
			bucket,
			migrationResults,
			semaphores,
			tokenCaches,
			tools,
			config: configCollection,
		};

		return this.collectionsCache;
	}
}

export let collections: ReturnType<typeof Database.prototype.getCollections>;

export const ready = (async () => {
	if (!building) {
		const db = await Database.getInstance();
		collections = db.getCollections();
		logger.info("[database] In-memory database ready");
	} else {
		collections = {} as unknown as ReturnType<typeof Database.prototype.getCollections>;
	}
})();

export async function getCollectionsEarly(): Promise<
	ReturnType<typeof Database.prototype.getCollections>
> {
	await ready;
	if (!collections) {
		throw new Error("Database not initialized");
	}
	return collections;
}
