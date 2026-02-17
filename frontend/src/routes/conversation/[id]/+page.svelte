<script lang="ts">
	import ChatWindow from "$lib/components/chat/ChatWindow.svelte";
	import { pendingMessage } from "$lib/stores/pendingMessage";
	import { isAborted } from "$lib/stores/isAborted";
	import { onMount } from "svelte";
	import { page } from "$app/state";
	import { beforeNavigate, invalidateAll } from "$app/navigation";
	import { base } from "$app/paths";
	import { ERROR_MESSAGES, error } from "$lib/stores/errors";
	import { findCurrentModel } from "$lib/utils/models";
	import type { Message } from "$lib/types/Message";
	import { MessageUpdateStatus, MessageUpdateType } from "$lib/types/MessageUpdate";
	import titleUpdate from "$lib/stores/titleUpdate";
	import file2base64 from "$lib/utils/file2base64";
	import { addChildren } from "$lib/utils/tree/addChildren";
	import { addSibling } from "$lib/utils/tree/addSibling";
	import { fetchMessageUpdates } from "$lib/utils/messageUpdates";
	import { sendAgentMessage } from "$lib/utils/agentMessageHandler";
	import type { v4 } from "uuid";
	import { useSettingsStore } from "$lib/stores/settings.js";
	import { browser } from "$app/environment";
	import {
		addBackgroundGeneration,
		removeBackgroundGeneration,
	} from "$lib/stores/backgroundGenerations";
	import type { TreeNode, TreeId } from "$lib/utils/tree/tree";
	import "katex/dist/katex.min.css";
	import { updateDebouncer } from "$lib/utils/updates.js";
	import SubscribeModal from "$lib/components/SubscribeModal.svelte";
	import { loading } from "$lib/stores/loading.js";
	import { requireAuthUser } from "$lib/utils/auth.js";
	import { invalidate } from "$app/navigation";
	import { UrlDependency } from "$lib/types/UrlDependency";

	let { data = $bindable() } = $props();

	let pending = $state(false);
	let initialRun = true;
	let showSubscribeModal = $state(false);
	let isWritingMessage = false; // Guard to prevent concurrent writeMessage calls

	let files: File[] = $state([]);

	// Track current task for A2A protocol compliance
	let currentTaskId: string | null = $state(null);
	let currentTaskState: string | null = $state(null);

	// Reply-to-task threading (explicit reply target)
	let replyToTaskId: string | null = $state(null);

	function setReplyTo(taskId: string) {
		replyToTaskId = taskId;
	}

	function clearReply() {
		replyToTaskId = null;
	}

	async function handleClearTasks() {
		// UI-only: reset local task threading state so next message starts fresh.
		currentTaskId = null;
		currentTaskState = null;
		clearReply();
	}

	async function handleClearContext() {
		// Frontend-only: for per-conversation chats, we can at least reset local state.
		// If the backend/agent is unreachable, we still keep the UI understandable.
		await handleClearTasks();
	}

	let conversations = $state(data.conversations);
	$effect(() => {
		conversations = data.conversations;
	});

	function createMessagesPath<T>(messages: TreeNode<T>[], msgId?: TreeId): TreeNode<T>[] {
		if (initialRun) {
			if (!msgId && page.url.searchParams.get("leafId")) {
				msgId = page.url.searchParams.get("leafId") as string;
				page.url.searchParams.delete("leafId");
			}
			if (!msgId && browser && localStorage.getItem("leafId")) {
				msgId = localStorage.getItem("leafId") as string;
			}
			initialRun = false;
		}

		const msg = messages.find((msg) => msg.id === msgId) ?? messages.at(-1);
		if (!msg) return [];
		// ancestor path
		const { ancestors } = msg;
		const path = [];
		if (ancestors?.length) {
			for (const ancestorId of ancestors) {
				const ancestor = messages.find((msg) => msg.id === ancestorId);
				if (ancestor) {
					path.push(ancestor);
				}
			}
		}

		// push the node itself in the middle
		path.push(msg);

		// children path
		let childrenIds = msg.children;
		while (childrenIds?.length) {
			let lastChildId = childrenIds.at(-1);
			const lastChild = messages.find((msg) => msg.id === lastChildId);
			if (lastChild) {
				path.push(lastChild);
			}
			childrenIds = lastChild?.children;
		}

		return path;
	}

	function createMessagesAlternatives<T>(messages: TreeNode<T>[]): TreeId[][] {
		const alternatives = [];
		for (const message of messages) {
			if (message.children?.length) {
				alternatives.push(message.children);
			}
		}
		return alternatives;
	}

	// this function is used to send new message to the backends
	async function writeMessage({
		prompt,
		messageId = messagesPath.at(-1)?.id ?? undefined,
		isRetry = false,
	}: {
		prompt?: string;
		messageId?: ReturnType<typeof v4>;
		isRetry?: boolean;
	}): Promise<void> {
		// Prevent concurrent calls
		if (isWritingMessage) {
			console.warn('⚠️ writeMessage already in progress, ignoring duplicate call');
			return;
		}

		isWritingMessage = true;

		try {
			$isAborted = false;
			$loading = true;
			pending = true;
			const base64Files = await Promise.all(
				(files ?? []).map((file) =>
					file2base64(file).then((value) => ({
						type: "base64" as const,
						value,
						mime: file.type,
						name: file.name,
					}))
				)
			);

			let messageToWriteToId: Message["id"] | undefined = undefined;
			// used for building the prompt, subtree of the conversation that goes from the latest message to the root

			if (isRetry && messageId) {
				// two cases, if we're retrying a user message with a newPrompt set,
				// it means we're editing a user message
				// if we're retrying on an assistant message, newPrompt cannot be set
				// it means we're retrying the last assistant message for a new answer

				const messageToRetry = messages.find((message) => message.id === messageId);

				if (!messageToRetry) {
					$error = "Message not found";
				}

				if (messageToRetry?.from === "user" && prompt) {
					// add a sibling to this message from the user, with the alternative prompt
					// add a children to that sibling, where we can write to
					const newUserMessageId = addSibling(
						{
							messages,
							rootMessageId: data.rootMessageId,
						},
						{
							from: "user",
							content: prompt,
							files: messageToRetry.files,
						},
						messageId
					);
					messageToWriteToId = addChildren(
						{
							messages,
							rootMessageId: data.rootMessageId,
						},
						{ from: "assistant", content: "" },
						newUserMessageId
					);
				} else if (messageToRetry?.from === "assistant") {
					// we're retrying an assistant message, to generate a new answer
					// just add a sibling to the assistant answer where we can write to
					messageToWriteToId = addSibling(
						{
							messages,
							rootMessageId: data.rootMessageId,
						},
						{ from: "assistant", content: "" },
						messageId
					);
				}
			} else {
				// just a normal linear conversation, so we add the user message
				// and the blank assistant message back to back
				const newUserMessageId = addChildren(
					{
						messages,
						rootMessageId: data.rootMessageId,
					},
					{
						from: "user",
						content: prompt ?? "",
						files: base64Files,
					},
					messageId
				);

				if (!data.rootMessageId) {
					data.rootMessageId = newUserMessageId;
				}

				messageToWriteToId = addChildren(
					{
						messages,
						rootMessageId: data.rootMessageId,
					},
					{
						from: "assistant",
						content: "",
					},
					newUserMessageId
				);
			}

			const userMessage = messages.find((message) => message.id === messageId);
			const messageToWriteTo = messages.find((message) => message.id === messageToWriteToId);
			if (!messageToWriteTo) {
				throw new Error("Message to write to not found");
			}

			const messageUpdatesAbortController = new AbortController();

			// Check if using Bindu agent model - use direct API
			const currentModel = findCurrentModel(data.models, data.oldModels, data.model);
			const useDirectAgentAPI = currentModel?.id === 'bindu' || currentModel?.name === 'bindu';

			let messageUpdatesIterator;

			if (useDirectAgentAPI) {
				// Use direct agent API with task state tracking and reply support
				messageUpdatesIterator = sendAgentMessage(
					prompt ?? '',
					page.params.id!,
					messageUpdatesAbortController.signal,
					currentTaskId ?? undefined,
					currentTaskState ?? undefined,
					replyToTaskId ?? undefined
				);
				// Clear reply after sending
				clearReply();
			} else {
				// Use existing backend flow
				messageUpdatesIterator = await fetchMessageUpdates(
					page.params.id!,
					{
						base,
						inputs: prompt,
						messageId,
						isRetry,
						files: isRetry ? userMessage?.files : base64Files,
					},
					messageUpdatesAbortController.signal
				).catch((err) => {
					error.set(err.message);
				});
			}

			if (messageUpdatesIterator === undefined) return;

			files = [];
			let buffer = "";
			// Initialize lastUpdateTime outside the loop to persist between updates
			let lastUpdateTime = new Date();

			for await (const update of messageUpdatesIterator) {
				if ($isAborted) {
					messageUpdatesAbortController.abort();
					return;
				}

				// Skip keep-alive updates
				if (update.type === MessageUpdateType.Status && update.status === MessageUpdateStatus.KeepAlive) {
					continue;
				}

				// Handle different update types
				switch (update.type) {
					case MessageUpdateType.Stream:
						update.token = update.token.replaceAll("\0", "");
						const updates = messageToWriteTo.updates ?? [];
						const last = updates.at(-1);
						if (last?.type === MessageUpdateType.Stream) {
							messageToWriteTo.updates = [...updates.slice(0, -1), { ...last, token: last.token + update.token }];
						} else {
							messageToWriteTo.updates = [...updates, update];
						}
						if (!$settings.disableStream) {
							buffer += update.token;
							const now = Date.now();
							if (now - lastUpdateTime.getTime() > updateDebouncer.maxUpdateTime) {
								messageToWriteTo.content += buffer;
								buffer = "";
								lastUpdateTime = new Date(now);
							}
							pending = false;
						}
						break;

					case MessageUpdateType.FinalAnswer:
						if (buffer && !$settings.disableStream) {
							messageToWriteTo.content += buffer;
							buffer = "";
						}
						// Simple logic: if interrupted keep existing, otherwise use final text
						if (!update.interrupted) {
							messageToWriteTo.content = update.text ?? "";
						} else if (!messageToWriteTo.content) {
							messageToWriteTo.content = update.text ?? "";
						}
						messageToWriteTo.updates = [...(messageToWriteTo.updates ?? []), update];
						break;

					case MessageUpdateType.Status:
						if (update.status === MessageUpdateStatus.Error) {
							if (update.statusCode === 402) {
								showSubscribeModal = true;
							} else {
								$error = update.message ?? "An error has occurred";
							}
						} else if (update.status === MessageUpdateStatus.Finished) {
							// Stop polling - message is complete
							pending = false;
						}
						messageToWriteTo.updates = [...(messageToWriteTo.updates ?? []), update];
						break;

					case MessageUpdateType.Title:
						const conv = conversations.find(({ id }) => id === page.params.id);
						if (conv) {
							conv.title = update.title;
							$titleUpdate = { title: update.title, convId: page.params.id! };
						}
						break;

					case MessageUpdateType.File:
						messageToWriteTo.files = [
							...(messageToWriteTo.files ?? []),
							{ type: "hash", value: update.sha, mime: update.mime, name: update.name }
						];
						break;

					case MessageUpdateType.RouterMetadata:
						messageToWriteTo.routerMetadata = { route: update.route, model: update.model };
						break;

					case MessageUpdateType.TaskMetadata:
						messageToWriteTo.taskMetadata = {
							taskId: update.taskId,
							contextId: update.contextId,
							status: update.status,
							...(update.referenceTaskIds && { referenceTaskIds: update.referenceTaskIds })
						};
						messageToWriteTo.updates = [...(messageToWriteTo.updates ?? []), update];

						// Track task state for A2A protocol compliance
						currentTaskId = update.taskId;
						currentTaskState = update.status;

						// Note: Don't invalidate conversation list here for agent conversations
						// as it causes data reload which clears the local message state
						break;

					default:
						messageToWriteTo.updates = [...(messageToWriteTo.updates ?? []), update];
				}
			}

			// Flush any remaining buffer
			if (buffer && !$settings.disableStream) {
				messageToWriteTo.content += buffer;
			}
		} catch (err) {
			if (err instanceof Error && err.message.includes("overloaded")) {
				$error = "Too much traffic, please try again.";
			} else if (err instanceof Error && err.message.includes("429")) {
				$error = ERROR_MESSAGES.rateLimited;
			} else {
				console.error(err);
				$error = err instanceof Error ? err.message : String(err);
			}
		} finally {
			$loading = false;
			pending = false;
			clearReply();
			isWritingMessage = false; // Reset guard
			// No invalidateAll() - causes reload loop. UI updates reactively.
		}
	}

	async function stopGeneration() {
		await fetch(`${base}/conversation/${page.params.id}/stop-generating`, {
			method: "POST",
		}).then(() => {
			// Small delay to let the stream receive the server's final update before aborting client-side
			setTimeout(() => {
				$isAborted = true;
				$loading = false;
			}, 200);
		});
	}

	function handleKeydown(event: KeyboardEvent) {
		// Stop generation on ESC key when loading
		if (event.key === "Escape" && $loading) {
			event.preventDefault();
			stopGeneration();
		}
	}

	onMount(async () => {
		if ($pendingMessage) {
			files = $pendingMessage.files;
			await writeMessage({ prompt: $pendingMessage.content });
			$pendingMessage = undefined;
			return;
		}

		// Only check streaming if not already loading (prevents re-trigger on reload)
		if (!$loading && isConversationStreaming(messages)) {
			addBackgroundGeneration({ id: page.params.id!, startedAt: Date.now() });
			$loading = true;
		}
	});

	async function onMessage(content: string) {
		await writeMessage({ prompt: content });
	}

	async function onRetry(payload: { id: Message["id"]; content?: string }) {
		if (requireAuthUser()) return;

		const lastMsgId = payload.id;
		messagesPath = createMessagesPath(messages, lastMsgId);

		await writeMessage({
			prompt: payload.content,
			messageId: payload.id,
			isRetry: true,
		});
	}

	async function onShowAlternateMsg(payload: { id: Message["id"] }) {
		const msgId = payload.id;
		messagesPath = createMessagesPath(messages, msgId);
	}

	const settings = useSettingsStore();
	let messages = $state(data.messages);
	$effect(() => {
		messages = data.messages;
	});

	function isConversationStreaming(msgs: Message[]): boolean {
		const lastAssistant = [...msgs].reverse().find((msg) => msg.from === "assistant");
		if (!lastAssistant) return false;
		const hasFinalAnswer =
			lastAssistant.updates?.some((update) => update.type === MessageUpdateType.FinalAnswer) ??
			false;
		const hasError =
			lastAssistant.updates?.some(
				(update) =>
					update.type === MessageUpdateType.Status && update.status === MessageUpdateStatus.Error
			) ?? false;
		return !hasFinalAnswer && !hasError;
	}

	$effect(() => {
		const streaming = isConversationStreaming(messages);
		if (streaming) {
			$loading = true;
		} else if (!pending) {
			$loading = false;
		}

		if (!streaming && browser) {
			removeBackgroundGeneration(page.params.id!);
		}
	});

	// create a linear list of `messagesPath` from `messages` that is a tree of threaded messages
	let messagesPath = $derived(createMessagesPath(messages));
	let messagesAlternatives = $derived(createMessagesAlternatives(messages));

	$effect(() => {
		if (browser && messagesPath.at(-1)?.id) {
			localStorage.setItem("leafId", messagesPath.at(-1)?.id as string);
		}
	});

	beforeNavigate((navigation) => {
		if (!page.params.id) return;

		const navigatingAway =
			navigation.to?.route.id !== page.route.id || navigation.to?.params?.id !== page.params.id;

		if ($loading && navigatingAway) {
			addBackgroundGeneration({ id: page.params.id, startedAt: Date.now() });
		}

		$isAborted = true;
		$loading = false;
	});

	let title = $derived.by(() => {
		const rawTitle = conversations.find((conv) => conv.id === page.params.id)?.title ?? data.title;
		return rawTitle ? rawTitle.charAt(0).toUpperCase() + rawTitle.slice(1) : rawTitle;
	});
</script>

<svelte:window onkeydown={handleKeydown} />

<svelte:head>
	<title>{title}</title>
</svelte:head>

<ChatWindow
	loading={$loading}
	{pending}
	messages={messagesPath as Message[]}
	{messagesAlternatives}
	shared={data.shared}
	preprompt={data.preprompt}
	bind:files
	onmessage={onMessage}
	onretry={onRetry}
	onshowAlternateMsg={onShowAlternateMsg}
	onstop={stopGeneration}
	onReplyToTask={setReplyTo}
	replyToTaskId={replyToTaskId}
	onClearReply={clearReply}
	onClearContext={handleClearContext}
	onClearTasks={handleClearTasks}
	models={data.models}
	currentModel={findCurrentModel(data.models, data.oldModels, data.model)}
/>

{#if showSubscribeModal}
	<SubscribeModal close={() => (showSubscribeModal = false)} />
{/if}
