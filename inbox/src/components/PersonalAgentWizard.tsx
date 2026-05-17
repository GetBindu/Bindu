import { useEffect, useState } from "react";
import clsx from "clsx";
import {
	CheckCircleIcon,
	PlugIcon,
	SparkleIcon,
	UserCircleIcon,
} from "@phosphor-icons/react";
import { Modal } from "./Modal";
import { ModalCloseButton } from "./ModalCloseButton";
import { postJson } from "~/lib/fetch";
import type { Persona, PersonalAgent, PersonalAgentTools } from "~/lib/api-types";
import { useUI } from "~/state";

interface Props {
	open: boolean;
	onClose: () => void;
}

type Step = "persona" | "tools" | "review";

/** Default persona scaffold so the form doesn't start blank — users
 * can edit or wipe each field. */
function defaultPersona(): Persona {
	return {
		name: "",
		age: undefined,
		nationality: "",
		country_of_residence: "",
		occupation: { title: "", organization: "", description: "" },
		personality_traits: [],
		interests: [],
		relationships: [],
		other_facts: [],
	};
}

const BBT_PERSONAS: Persona[] = [
	{
		name: "Sheldon Cooper",
		age: 30,
		nationality: "American",
		country_of_residence: "United States",
		occupation: {
			title: "Senior Theoretical Physicist",
			organization: "Caltech",
			description:
				"String theorist chasing the Higgs boson and bosonic string theory; lives for the 'Bazinga!' moment of discovery.",
		},
		personality_traits: [
			"Brilliant",
			"Pedantic",
			"Literal-minded",
			"Obsessive-compulsive",
			"Condescending",
		],
		interests: [
			"String theory",
			"Comic books",
			"Model trains",
			"Vintage video games",
			"Klingon",
		],
		relationships: [
			"Roommate: Leonard Hofstadter — best friend, bound by the Roommate Agreement",
			"Girlfriend: Amy Farrah Fowler — intellectual equal and Relationship Agreement co-signer",
			"Mother: Mary Cooper — devout Texan, only person on Earth he obeys",
		],
		other_facts: [
			"Knocks three times and says the name three times before entering",
			"Has a designated spot on the couch — non-negotiable",
			"Does not detect sarcasm without an explicit tone marker",
			"Holds a PhD and an ScD; will remind you of both",
		],
	},
	{
		name: "Leonard Hofstadter",
		age: 32,
		nationality: "American",
		country_of_residence: "United States",
		occupation: {
			title: "Experimental Physicist",
			organization: "Caltech",
			description:
				"Runs high-energy laser experiments; the grounded one in a circle of geniuses.",
		},
		personality_traits: [
			"Loyal",
			"Sweet",
			"Anxious",
			"Insecure",
			"Sarcastic",
		],
		interests: [
			"Sci-fi movies",
			"Dungeons & Dragons",
			"Cello",
			"Vintage cars he can't afford",
		],
		relationships: [
			"Wife: Penny — across-the-hall neighbor turned spouse",
			"Roommate: Sheldon Cooper — managed via a 47-clause Roommate Agreement",
			"Mother: Beverly Hofstadter — neuroscientist who treats him like a research subject",
		],
		other_facts: [
			"Lactose intolerant; eats cheese anyway",
			"Wears glasses and a hoodie roughly 100% of the time",
			"Keeps an inhaler in every jacket",
		],
	},
	{
		name: "Howard Wolowitz",
		age: 31,
		nationality: "American",
		country_of_residence: "United States",
		occupation: {
			title: "Aerospace Engineer",
			organization: "Caltech / NASA",
			description:
				"Designs space toilets and robotic arms; once flew to the International Space Station and will never let you forget it.",
		},
		personality_traits: [
			"Cocky",
			"Witty",
			"Insecure underneath",
			"Mama's boy",
			"Slowly improving",
		],
		interests: [
			"Magic tricks",
			"Speaking six languages (badly)",
			"Star Trek cosplay",
			"Robotics",
		],
		relationships: [
			"Wife: Bernadette Rostenkowski — actual boss of the marriage",
			"Mother: Debbie Wolowitz — disembodied yelling voice from upstairs",
			"Best friend: Rajesh Koothrappali — borderline-romantic bromance",
		],
		other_facts: [
			"The only one of the four without a PhD; reminded of it constantly",
			"Wears a Beatles haircut and dickie collars unironically",
			"Lived with his mother well into his thirties",
		],
	},
	{
		name: "Rajesh Koothrappali",
		age: 31,
		nationality: "Indian",
		country_of_residence: "United States",
		occupation: {
			title: "Astrophysicist",
			organization: "Caltech",
			description:
				"Hunts trans-Neptunian objects in the Kuiper belt; once discovered a planetoid.",
		},
		personality_traits: [
			"Sensitive",
			"Romantic",
			"Effeminate",
			"Lonely",
			"Hopeful",
		],
		interests: [
			"Bollywood films",
			"Wine",
			"His bromance with Howard",
			"Dogs — especially Cinnamon",
		],
		relationships: [
			"Best friend: Howard Wolowitz — practically married",
			"Dog: Cinnamon — emotional cornerstone of his life",
			"Parents: Dr. and Mrs. Koothrappali — Skype regularly, judge constantly",
		],
		other_facts: [
			"Selective mutism — cannot speak to women without alcohol",
			"Owns more sweater vests than is reasonable",
			"From New Delhi; family is wealthy, much to his friends' envy",
		],
	},
	{
		name: "Penny",
		age: 28,
		nationality: "American",
		country_of_residence: "United States",
		occupation: {
			title: "Pharmaceutical Sales Rep",
			organization: "Zangen Pharmaceuticals",
			description:
				"Former aspiring actress turned top-earning pharma rep; the social translator of the group.",
		},
		personality_traits: [
			"Warm",
			"Street-smart",
			"Confident",
			"Generous",
			"Impulsive",
		],
		interests: [
			"Wine",
			"Romantic comedies",
			"Volleyball",
			"Shopping",
		],
		relationships: [
			"Husband: Leonard Hofstadter — across-the-hall neighbor turned spouse",
			"Best friend: Amy Farrah Fowler — bestie bond, sleepovers included",
			"Father: Wyatt — Nebraska farmer who wanted a son",
		],
		other_facts: [
			"Last name is never canonically revealed",
			"Years at the Cheesecake Factory before breaking into pharma",
			"Reads fewer books than the boys but is wiser than all of them combined",
		],
	},
	{
		name: "Bernadette Rostenkowski-Wolowitz",
		age: 29,
		nationality: "American",
		country_of_residence: "United States",
		occupation: {
			title: "Microbiologist",
			organization: "Zangen Pharmaceuticals",
			description:
				"PhD microbiologist running pharma research; out-earns her husband and reminds him often.",
		},
		personality_traits: [
			"Sweet-sounding",
			"Steel-spined",
			"Ambitious",
			"Sneaky-mean",
			"Maternal-skeptical",
		],
		interests: [
			"Microbiology",
			"Disney movies",
			"Impressions of Howard's mother",
			"Out-earning the boys",
		],
		relationships: [
			"Husband: Howard Wolowitz — kept firmly in line",
			"Best friends: Penny and Amy — the unbreakable girls' club",
		],
		other_facts: [
			"Voice goes from squeaky to terrifying in 0.4 seconds",
			"Catholic upbringing, six siblings",
			"Has accidentally engineered doomsday-grade pathogens at work — more than once",
		],
	},
	{
		name: "Amy Farrah Fowler",
		age: 30,
		nationality: "American",
		country_of_residence: "United States",
		occupation: {
			title: "Neurobiologist",
			organization: "UCLA",
			description:
				"Studies addiction in starfish and primates; Nobel-track researcher in her own right.",
		},
		personality_traits: [
			"Deadpan",
			"Brilliant",
			"Surprisingly affectionate",
			"Devoted",
			"Lonely-turned-fulfilled",
		],
		interests: [
			"Harp playing",
			"Tiaras",
			"Neuroscience",
			"Bestie sleepovers with Penny",
		],
		relationships: [
			"Husband: Sheldon Cooper — relationship governed by a binding agreement",
			"Best friend: Penny — first bestie after a lifetime alone",
			"Mother: Mrs. Fowler — judges every life choice",
		],
		other_facts: [
			"Met Sheldon via an online dating algorithm Howard and Raj set up as a prank",
			"Plays the harp; once serenaded Sheldon with 'I Kissed a Girl'",
			"Co-won a Nobel Prize with Sheldon for super-asymmetry",
		],
	},
];

export function PersonalAgentWizard({ open, onClose }: Props) {
	const setMe = useUI((s) => s.setMe);
	const existingMe = useUI((s) => s.me);

	const [step, setStep] = useState<Step>("persona");
	const [persona, setPersona] = useState<Persona>(defaultPersona());
	const [tools, setTools] = useState<PersonalAgentTools>({});
	const [saving, setSaving] = useState(false);
	const [errMsg, setErrMsg] = useState<string | null>(null);

	// Hydrate from the existing row on open. Lets the user re-open the
	// wizard to edit their persona without losing what they had.
	useEffect(() => {
		if (!open) return;
		setErrMsg(null);
		if (existingMe) {
			setPersona({ ...defaultPersona(), ...existingMe.persona });
			setTools(existingMe.tools ?? {});
		}
		setStep("persona");
	}, [open, existingMe]);

	const canAdvancePersona = persona.name.trim().length > 0;

	async function save(): Promise<PersonalAgent | null> {
		setSaving(true);
		setErrMsg(null);
		// Strip empty strings / arrays before saving so we don't litter
		// the DB with placeholder noise. Persona.name is required by the
		// server validator; everything else is optional.
		const cleaned: Persona = {
			name: persona.name.trim(),
			age: persona.age,
			nationality: persona.nationality?.trim() || undefined,
			country_of_residence: persona.country_of_residence?.trim() || undefined,
			occupation:
				persona.occupation?.title?.trim() ||
				persona.occupation?.organization?.trim() ||
				persona.occupation?.description?.trim()
					? persona.occupation
					: undefined,
			personality_traits: persona.personality_traits?.filter(Boolean),
			interests: persona.interests?.filter(Boolean),
			relationships: persona.relationships?.filter(Boolean),
			other_facts: persona.other_facts?.filter(Boolean),
		};
		const res = await postJson<PersonalAgent>("/api/me", {
			persona: cleaned,
			tools,
		});
		setSaving(false);
		if (!res.ok || !res.data) {
			setErrMsg(res.errMsg ?? "save failed");
			return null;
		}
		setMe(res.data);
		return res.data;
	}

	async function handleNext() {
		if (step === "persona") {
			if (!canAdvancePersona) return;
			const saved = await save();
			if (saved) setStep("tools");
			return;
		}
		if (step === "tools") {
			// Saving again is cheap and persists the most-recent tools
			// state even if the user added a Pipedream account between
			// steps. Idempotent on the server.
			const saved = await save();
			if (saved) setStep("review");
			return;
		}
		// step === "review" → final save, then close. Phase 3 will hook
		// /api/me/spawn into this button.
		const saved = await save();
		if (saved) onClose();
	}

	function handleBack() {
		if (step === "tools") setStep("persona");
		else if (step === "review") setStep("tools");
	}

	return (
		<Modal open={open} onClose={onClose}>
			<div className="flex w-[720px] max-w-[95vw] flex-col rounded-lg border border-(--color-border) bg-white shadow-2xl">
				<WizardHeader step={step} onClose={onClose} />
				<div className="min-h-[400px] px-6 py-5">
					{step === "persona" && (
						<PersonaStep
							persona={persona}
							onChange={setPersona}
							onLoadExample={setPersona}
						/>
					)}
					{step === "tools" && (
						<ToolsStep tools={tools} onChange={setTools} />
					)}
					{step === "review" && (
						<ReviewStep persona={persona} tools={tools} />
					)}
				</div>
				{errMsg && (
					<div className="mx-6 mb-3 rounded-md border border-rose-200 bg-rose-50 px-3 py-2 text-[12px] text-rose-700">
						{errMsg}
					</div>
				)}
				<WizardFooter
					step={step}
					saving={saving}
					canAdvance={step === "persona" ? canAdvancePersona : true}
					onBack={handleBack}
					onNext={handleNext}
				/>
			</div>
		</Modal>
	);
}

// ─── header / footer ─────────────────────────────────────────────────────

function WizardHeader({ step, onClose }: { step: Step; onClose: () => void }) {
	const steps: Array<{ id: Step; label: string; icon: React.ElementType }> = [
		{ id: "persona", label: "Persona", icon: UserCircleIcon },
		{ id: "tools", label: "Tools", icon: PlugIcon },
		{ id: "review", label: "Review", icon: SparkleIcon },
	];
	const activeIdx = steps.findIndex((s) => s.id === step);
	return (
		<div className="flex items-center gap-4 border-b border-(--color-border-soft) px-6 py-4">
			<div className="flex-1">
				<div className="text-[14px] font-medium text-fg">
					Create your personal agent
				</div>
				<div className="text-[11px] text-fg-dim">
					Your sender identity for A2A. Persona + tools + DID, all local.
				</div>
			</div>
			<div className="flex items-center gap-2">
				{steps.map((s, i) => {
					const Icon = s.icon;
					const isActive = i === activeIdx;
					const isDone = i < activeIdx;
					return (
						<div
							key={s.id}
							className={clsx(
								"flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[11px]",
								isActive && "bg-(--color-cobalt-soft) font-medium text-fg",
								isDone && "text-fg-muted",
								!isActive && !isDone && "text-fg-dim",
							)}
						>
							{isDone ? (
								<CheckCircleIcon size={12} weight="fill" className="text-(--color-cobalt)" />
							) : (
								<Icon size={12} weight="duotone" />
							)}
							{s.label}
						</div>
					);
				})}
			</div>
			<ModalCloseButton onClick={onClose} className="ml-2" />
		</div>
	);
}

function WizardFooter({
	step,
	saving,
	canAdvance,
	onBack,
	onNext,
}: {
	step: Step;
	saving: boolean;
	canAdvance: boolean;
	onBack: () => void;
	onNext: () => void;
}) {
	const nextLabel =
		step === "persona" ? "Continue" : step === "tools" ? "Continue" : "Save";
	return (
		<div className="flex items-center justify-between border-t border-(--color-border-soft) bg-slate-50 px-6 py-3">
			<button
				type="button"
				onClick={onBack}
				disabled={step === "persona"}
				className={clsx(
					"rounded-md border px-3 py-1.5 text-[12px] transition",
					step === "persona"
						? "cursor-not-allowed border-slate-200 text-slate-300"
						: "border-(--color-border) bg-white text-fg-muted hover:border-(--color-cobalt) hover:text-(--color-cobalt)",
				)}
			>
				Back
			</button>
			<div className="text-[11px] text-fg-dim">
				{step === "review"
					? "Persona is saved. Phase 3 will spawn the agent here."
					: ""}
			</div>
			<button
				type="button"
				onClick={onNext}
				disabled={!canAdvance || saving}
				className={clsx(
					"rounded-md px-3 py-1.5 text-[12px] font-medium shadow-sm transition",
					canAdvance && !saving
						? "bg-blue-700 text-white hover:bg-blue-800"
						: "bg-slate-200 text-slate-400",
				)}
			>
				{saving ? "Saving…" : nextLabel}
			</button>
		</div>
	);
}

// ─── step 1: persona ─────────────────────────────────────────────────────

function PersonaStep({
	persona,
	onChange,
	onLoadExample,
}: {
	persona: Persona;
	onChange: (p: Persona) => void;
	onLoadExample: (p: Persona) => void;
}) {
	return (
		<div className="space-y-4">
			<div className="flex items-start justify-between gap-4">
				<div>
					<h3 className="text-[13px] font-medium text-fg">Who is your agent?</h3>
					<p className="mt-1 text-[11px] leading-relaxed text-fg-dim">
						This persona shapes how your agent talks to others. Fill in
						only what you care about — every field except name is optional.
					</p>
				</div>
				<ExampleMenu onSelect={onLoadExample} />
			</div>

			<div className="grid grid-cols-2 gap-3">
				<Field label="Name (required)">
					<input
						value={persona.name}
						onChange={(e) => onChange({ ...persona, name: e.target.value })}
						placeholder="Raahul Dutta"
						className={inputCls}
					/>
				</Field>
				<Field label="Age">
					<input
						type="number"
						value={persona.age ?? ""}
						onChange={(e) =>
							onChange({
								...persona,
								age: e.target.value === "" ? undefined : Number(e.target.value),
							})
						}
						placeholder="28"
						className={inputCls}
					/>
				</Field>
				<Field label="Nationality">
					<input
						value={persona.nationality ?? ""}
						onChange={(e) =>
							onChange({ ...persona, nationality: e.target.value })
						}
						placeholder="Indian"
						className={inputCls}
					/>
				</Field>
				<Field label="Country of residence">
					<input
						value={persona.country_of_residence ?? ""}
						onChange={(e) =>
							onChange({ ...persona, country_of_residence: e.target.value })
						}
						placeholder="Germany"
						className={inputCls}
					/>
				</Field>
				<Field label="Occupation title">
					<input
						value={persona.occupation?.title ?? ""}
						onChange={(e) =>
							onChange({
								...persona,
								occupation: { ...persona.occupation, title: e.target.value },
							})
						}
						placeholder="Engineer"
						className={inputCls}
					/>
				</Field>
				<Field label="Organization">
					<input
						value={persona.occupation?.organization ?? ""}
						onChange={(e) =>
							onChange({
								...persona,
								occupation: {
									...persona.occupation,
									organization: e.target.value,
								},
							})
						}
						placeholder="Bindu"
						className={inputCls}
					/>
				</Field>
			</div>

			<ChipsField
				label="Personality traits"
				placeholder="Curious, direct, patient…"
				values={persona.personality_traits ?? []}
				onChange={(v) => onChange({ ...persona, personality_traits: v })}
			/>
			<ChipsField
				label="Interests"
				placeholder="Decentralized systems, hiking, espresso…"
				values={persona.interests ?? []}
				onChange={(v) => onChange({ ...persona, interests: v })}
			/>
			<BulletsField
				label="Other facts"
				placeholder="One per line. Things other agents should know."
				values={persona.other_facts ?? []}
				onChange={(v) => onChange({ ...persona, other_facts: v })}
			/>
		</div>
	);
}

/** Dropdown picker for the Big Bang Theory example personas. Click outside
 * or pick a character to close. */
function ExampleMenu({ onSelect }: { onSelect: (p: Persona) => void }) {
	const [open, setOpen] = useState(false);
	useEffect(() => {
		if (!open) return;
		const close = () => setOpen(false);
		window.addEventListener("click", close);
		return () => window.removeEventListener("click", close);
	}, [open]);
	return (
		<div className="relative shrink-0">
			<button
				type="button"
				onClick={(e) => {
					e.stopPropagation();
					setOpen((o) => !o);
				}}
				className="rounded-md border border-(--color-border) bg-white px-2.5 py-1 text-[11px] text-fg-muted transition hover:border-(--color-cobalt) hover:text-(--color-cobalt)"
			>
				Load example ▾
			</button>
			{open && (
				<div
					onClick={(e) => e.stopPropagation()}
					className="absolute right-0 z-10 mt-1 w-64 overflow-hidden rounded-md border border-(--color-border) bg-white shadow-lg"
				>
					<div className="border-b border-(--color-border-soft) bg-slate-50 px-3 py-1.5 text-[10px] uppercase tracking-[0.1em] text-fg-dim">
						The Big Bang Theory
					</div>
					{BBT_PERSONAS.map((p) => (
						<button
							key={p.name}
							type="button"
							onClick={() => {
								onSelect(p);
								setOpen(false);
							}}
							className="block w-full px-3 py-1.5 text-left transition hover:bg-(--color-cobalt-soft)"
						>
							<div className="text-[12px] font-medium text-fg">{p.name}</div>
							<div className="text-[10px] text-fg-dim">
								{p.occupation?.title}
								{p.occupation?.organization
									? ` · ${p.occupation.organization}`
									: ""}
							</div>
						</button>
					))}
				</div>
			)}
		</div>
	);
}

// ─── step 2: tools ───────────────────────────────────────────────────────

function ToolsStep({
	tools,
	onChange,
}: {
	tools: PersonalAgentTools;
	onChange: (t: PersonalAgentTools) => void;
}) {
	return (
		<div className="space-y-4">
			<div>
				<h3 className="text-[13px] font-medium text-fg">
					Connect Gmail and Notion
				</h3>
				<p className="mt-1 text-[11px] leading-relaxed text-fg-dim">
					Your agent uses Pipedream Connect to act on your accounts. We
					never see your tokens — Pipedream brokers them. Each connection
					opens their popup and stores only the account ID.
				</p>
			</div>

			<ToolConnector
				name="Gmail"
				app="gmail"
				accountId={tools.gmail?.accountId}
				onConnected={(accountId) =>
					onChange({ ...tools, gmail: { accountId } })
				}
				onDisconnect={() => {
					const { gmail: _gmail, ...rest } = tools;
					onChange(rest);
				}}
			/>
			<ToolConnector
				name="Notion"
				app="notion"
				accountId={tools.notion?.accountId}
				onConnected={(accountId) =>
					onChange({ ...tools, notion: { accountId } })
				}
				onDisconnect={() => {
					const { notion: _notion, ...rest } = tools;
					onChange(rest);
				}}
			/>

			<div className="rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-[11px] leading-relaxed text-amber-800">
				<strong>You can skip this step</strong> and connect tools later — your
				agent will still spawn with a DID and respond to A2A messages, just
				without Gmail/Notion abilities.
			</div>
		</div>
	);
}

function ToolConnector({
	name,
	app,
	accountId,
	onConnected,
	onDisconnect,
}: {
	name: string;
	app: "gmail" | "notion";
	accountId: string | undefined;
	onConnected: (accountId: string) => void;
	onDisconnect: () => void;
}) {
	const [busy, setBusy] = useState(false);
	const [err, setErr] = useState<string | null>(null);

	async function connect() {
		setBusy(true);
		setErr(null);
		try {
			const { connectPipedreamApp } = await import("~/lib/pipedream");
			const result = await connectPipedreamApp(app);
			if (result.ok) {
				onConnected(result.accountId);
			} else {
				setErr(result.errMsg);
			}
		} catch (e) {
			setErr((e as Error).message);
		}
		setBusy(false);
	}

	return (
		<div className="flex items-center justify-between rounded-md border border-(--color-border) bg-white px-3 py-2.5">
			<div className="min-w-0 flex-1">
				<div className="text-[12px] font-medium text-fg">{name}</div>
				{accountId ? (
					<div className="mt-0.5 flex items-center gap-1.5 text-[10px] text-(--color-cobalt)">
						<CheckCircleIcon size={11} weight="fill" />
						Connected · {accountId.slice(0, 14)}…
					</div>
				) : (
					<div className="mt-0.5 text-[10px] text-fg-dim">Not connected</div>
				)}
				{err && (
					<div className="mt-1 text-[10px] text-rose-700">{err}</div>
				)}
			</div>
			{accountId ? (
				<button
					type="button"
					onClick={onDisconnect}
					className="shrink-0 rounded-md border border-(--color-border) bg-white px-2.5 py-1 text-[11px] text-fg-muted transition hover:border-rose-300 hover:text-rose-700"
				>
					Disconnect
				</button>
			) : (
				<button
					type="button"
					onClick={connect}
					disabled={busy}
					className={clsx(
						"shrink-0 rounded-md px-2.5 py-1 text-[11px] font-medium shadow-sm transition",
						busy
							? "bg-slate-200 text-slate-400"
							: "bg-blue-700 text-white hover:bg-blue-800",
					)}
				>
					{busy ? "Connecting…" : "Connect"}
				</button>
			)}
		</div>
	);
}

// ─── step 3: review ──────────────────────────────────────────────────────

function ReviewStep({
	persona,
	tools,
}: {
	persona: Persona;
	tools: PersonalAgentTools;
}) {
	return (
		<div className="space-y-4">
			<div>
				<h3 className="text-[13px] font-medium text-fg">Review</h3>
				<p className="mt-1 text-[11px] leading-relaxed text-fg-dim">
					This is what gets saved. Edit anything by clicking Back. After
					save, Phase 3 will spawn your bindufied agent and capture its DID.
				</p>
			</div>
			<dl className="space-y-2 rounded-md border border-(--color-border) bg-slate-50 px-4 py-3 text-[12px]">
				<Row label="Name" value={persona.name} />
				{persona.occupation?.title && (
					<Row
						label="Occupation"
						value={[persona.occupation.title, persona.occupation.organization]
							.filter(Boolean)
							.join(" @ ")}
					/>
				)}
				{persona.personality_traits?.length ? (
					<Row label="Traits" value={persona.personality_traits.join(", ")} />
				) : null}
				{persona.interests?.length ? (
					<Row label="Interests" value={persona.interests.join(", ")} />
				) : null}
				<Row
					label="Gmail"
					value={tools.gmail ? "✓ Connected" : "Not connected"}
				/>
				<Row
					label="Notion"
					value={tools.notion ? "✓ Connected" : "Not connected"}
				/>
				<Row label="DID" value="(generated on spawn — Phase 3)" muted />
			</dl>
		</div>
	);
}

function Row({
	label,
	value,
	muted,
}: {
	label: string;
	value: string;
	muted?: boolean;
}) {
	return (
		<div className="flex gap-3">
			<dt className="w-24 shrink-0 text-[11px] uppercase tracking-[0.08em] text-fg-dim">
				{label}
			</dt>
			<dd className={clsx("flex-1", muted ? "text-fg-dim italic" : "text-fg")}>
				{value || <span className="text-fg-dim">—</span>}
			</dd>
		</div>
	);
}

// ─── form atoms ──────────────────────────────────────────────────────────

const inputCls =
	"w-full rounded-md border border-slate-300 bg-white px-3 py-1.5 text-[12px] text-slate-900 placeholder:text-slate-400 outline-none transition focus:border-blue-700 focus:ring-2 focus:ring-blue-200";

function Field({
	label,
	children,
}: {
	label: string;
	children: React.ReactNode;
}) {
	return (
		<label className="block">
			<span className="block pb-1 text-[10px] uppercase tracking-[0.12em] text-fg-dim">
				{label}
			</span>
			{children}
		</label>
	);
}

/** Comma-separated chips with backspace-to-delete-last. Mirrors the
 * Gmail to-field pattern operators already know. */
function ChipsField({
	label,
	placeholder,
	values,
	onChange,
}: {
	label: string;
	placeholder: string;
	values: string[];
	onChange: (v: string[]) => void;
}) {
	const [draft, setDraft] = useState("");
	function commit() {
		const t = draft.trim();
		if (!t) return;
		onChange([...values, t]);
		setDraft("");
	}
	return (
		<Field label={label}>
			<div className="flex flex-wrap items-center gap-1.5 rounded-md border border-slate-300 bg-white px-2 py-1.5">
				{values.map((v, i) => (
					<span
						key={`${v}-${i}`}
						className="inline-flex items-center gap-1 rounded-full bg-(--color-cobalt-soft) px-2 py-0.5 text-[11px] text-fg"
					>
						{v}
						<button
							type="button"
							onClick={() => onChange(values.filter((_, idx) => idx !== i))}
							className="text-fg-dim transition hover:text-rose-700"
						>
							×
						</button>
					</span>
				))}
				<input
					value={draft}
					onChange={(e) => setDraft(e.target.value)}
					onKeyDown={(e) => {
						if (e.key === "Enter" || e.key === ",") {
							e.preventDefault();
							commit();
						} else if (e.key === "Backspace" && !draft && values.length) {
							onChange(values.slice(0, -1));
						}
					}}
					onBlur={commit}
					placeholder={values.length === 0 ? placeholder : ""}
					className="min-w-[120px] flex-1 bg-transparent text-[12px] text-slate-900 placeholder:text-slate-400 outline-none"
				/>
			</div>
		</Field>
	);
}

/** Multi-line bullets — one per line. Friendlier than chips for longer
 * sentences like relationships and other facts. */
function BulletsField({
	label,
	placeholder,
	values,
	onChange,
}: {
	label: string;
	placeholder: string;
	values: string[];
	onChange: (v: string[]) => void;
}) {
	const [draft, setDraft] = useState(values.join("\n"));
	useEffect(() => {
		setDraft(values.join("\n"));
	}, [values]);
	return (
		<Field label={label}>
			<textarea
				value={draft}
				onChange={(e) => setDraft(e.target.value)}
				onBlur={() =>
					onChange(
						draft
							.split("\n")
							.map((l) => l.trim())
							.filter(Boolean),
					)
				}
				placeholder={placeholder}
				rows={3}
				className={clsx(inputCls, "resize-y")}
			/>
		</Field>
	);
}
