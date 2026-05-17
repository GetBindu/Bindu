import { useMemo, useRef, useState } from "react";
import clsx from "clsx";
import { XIcon } from "@phosphor-icons/react";
import { shortDid } from "~/lib/format";
import { isGateway } from "~/lib/agent-kind";
import type { EcosystemAgent } from "~/lib/api-types";

interface Props {
	agents: EcosystemAgent[];
	selected: string[];
	onChange: (ids: string[]) => void;
	autoFocus?: boolean;
}

/** Gmail-shaped recipient picker.
 *
 * Behaves like the To: field in any modern mail client — typed text
 * narrows a dropdown of agents from Contacts, click a row to drop a
 * chip, click the × on a chip to remove. Backspace at an empty input
 * removes the last chip; Enter on an open dropdown picks the
 * highlighted suggestion.
 *
 * Gateways are filtered out of the suggestion list on purpose. They're
 * infrastructure — the operator picks the agents they want to talk to,
 * and comms routes through a gateway transparently when there's more
 * than one chip. This keeps the mental model "who am I talking to?"
 * instead of "what am I routing through?". */
export function AgentPicker({
	agents,
	selected,
	onChange,
	autoFocus,
}: Props) {
	const [query, setQuery] = useState("");
	const [open, setOpen] = useState(false);
	const [highlightIdx, setHighlightIdx] = useState(0);
	const inputRef = useRef<HTMLInputElement>(null);

	// Index by id once per render — chip lookups + dedup of suggestions.
	const byId = useMemo(() => {
		const m = new Map<string, EcosystemAgent>();
		for (const a of agents) m.set(a.id, a);
		return m;
	}, [agents]);

	const suggestions = useMemo(() => {
		const q = query.trim().toLowerCase();
		const picked = new Set(selected);
		return agents
			.filter((a) => !picked.has(a.id))
			.filter((a) => !isGateway(a)) // gateways are infra, not contacts
			.filter((a) => {
				if (!q) return true;
				const name = (a.agentCard?.name ?? "").toLowerCase();
				const id = a.id.toLowerCase();
				const did = (a.did?.id ?? "").toLowerCase();
				return (
					name.includes(q) || id.includes(q) || did.includes(q)
				);
			})
			.slice(0, 8);
	}, [agents, selected, query]);

	function addId(id: string) {
		if (selected.includes(id)) return;
		onChange([...selected, id]);
		setQuery("");
		setHighlightIdx(0);
		inputRef.current?.focus();
	}
	function removeId(id: string) {
		onChange(selected.filter((x) => x !== id));
		inputRef.current?.focus();
	}

	function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
		if (e.key === "Backspace" && query === "" && selected.length > 0) {
			e.preventDefault();
			removeId(selected[selected.length - 1]);
			return;
		}
		if (e.key === "ArrowDown" && open && suggestions.length > 0) {
			e.preventDefault();
			setHighlightIdx((i) => Math.min(i + 1, suggestions.length - 1));
			return;
		}
		if (e.key === "ArrowUp" && open) {
			e.preventDefault();
			setHighlightIdx((i) => Math.max(i - 1, 0));
			return;
		}
		if (e.key === "Enter" && open && suggestions[highlightIdx]) {
			e.preventDefault();
			addId(suggestions[highlightIdx].id);
			return;
		}
		if (e.key === "Escape") {
			setOpen(false);
			return;
		}
	}

	return (
		<div className="relative">
			<div
				className="flex flex-wrap items-center gap-1.5 rounded-md border border-slate-300 bg-white px-2 py-1.5 transition focus-within:border-blue-700 focus-within:ring-2 focus-within:ring-blue-200"
				onClick={() => inputRef.current?.focus()}
			>
				{selected.map((id) => {
					const a = byId.get(id);
					const name = a?.agentCard?.name ?? id;
					return (
						<span
							key={id}
							className="inline-flex max-w-[180px] items-center gap-1 rounded-full bg-blue-50 px-2 py-0.5 text-[11px] text-blue-900"
							title={a?.did?.id ?? a?.url ?? id}
						>
							<span className="mr-0.5">🌻</span>
							<span className="truncate font-medium">{name}</span>
							<button
								type="button"
								onClick={(e) => {
									e.stopPropagation();
									removeId(id);
								}}
								className="ml-0.5 rounded-full p-0.5 text-blue-700 hover:bg-blue-100 hover:text-blue-900"
							>
								<XIcon size={9} weight="bold" />
							</button>
						</span>
					);
				})}
				<input
					ref={inputRef}
					autoFocus={autoFocus}
					value={query}
					onChange={(e) => {
						setQuery(e.target.value);
						setOpen(true);
						setHighlightIdx(0);
					}}
					onFocus={() => setOpen(true)}
					// Defer close so clicks on suggestions land before blur
					// hides the dropdown.
					onBlur={() => setTimeout(() => setOpen(false), 120)}
					onKeyDown={handleKeyDown}
					placeholder={
						selected.length === 0
							? "Type an agent name or DID…"
							: "Add another…"
					}
					className="min-w-[140px] flex-1 bg-transparent text-[12px] text-slate-900 outline-none placeholder:text-slate-400"
				/>
			</div>

			{open && suggestions.length > 0 && (
				<ul className="absolute left-0 right-0 z-10 mt-1 max-h-[220px] overflow-y-auto rounded-md border border-slate-200 bg-white py-1 shadow-lg">
					{suggestions.map((a, i) => {
						const name = a.agentCard?.name ?? a.id;
						const did = a.did?.id;
						return (
							<li
								key={a.id}
								onMouseDown={(e) => {
									// Use onMouseDown so this fires before the
									// input's onBlur closes the dropdown.
									e.preventDefault();
									addId(a.id);
								}}
								onMouseEnter={() => setHighlightIdx(i)}
								className={clsx(
									"flex cursor-pointer items-center gap-2 px-3 py-1.5 text-[12px]",
									i === highlightIdx
										? "bg-blue-50"
										: "hover:bg-slate-50",
								)}
							>
								<span aria-hidden>🌻</span>
								<div className="min-w-0 flex-1">
									<div className="truncate text-slate-900">{name}</div>
									<div className="truncate font-mono text-[10px] text-slate-500">
										{did ? shortDid(did) : a.id}
									</div>
								</div>
							</li>
						);
					})}
				</ul>
			)}

			{open && suggestions.length === 0 && query.trim() && (
				<div className="absolute left-0 right-0 z-10 mt-1 rounded-md border border-slate-200 bg-white px-3 py-2 text-[11px] italic text-slate-500 shadow-lg">
					No agents match "{query.trim()}".
				</div>
			)}
		</div>
	);
}
