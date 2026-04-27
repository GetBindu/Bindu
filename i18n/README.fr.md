<div align="center" id="top">
  <a href="https://getbindu.com">
    <picture>
      <img src="../assets/bindu.png" alt="Bindu" width="300">
    </picture>
  </a>
</div>

<p align="center">
  <em>La couche d'identité, de communication et de paiements pour les agents IA</em>
</p>

<p align="center">
  <a href="../README.md">🇬🇧 Anglais</a> •
  <a href="README.de.md">🇩🇪 Allemand</a> •
  <a href="README.es.md">🇪🇸 Espagnol</a> •
  <a href="README.fr.md">🇫🇷 Français</a> •
  <a href="README.hi.md">🇮🇳 हिंदी</a> •
  <a href="README.bn.md">🇮🇳 বাংলা</a> •
  <a href="README.zh.md">🇨🇳 中文</a> •
  <a href="README.nl.md">🇳🇱 Néerlandais</a> <p align="center">
    <img src="../assets/bindu_landscape.png" alt="Bindu - humains et agents, côte à côte" width="100%">
  </p>

  <div align="center">

  <img alt="Bindu" src="../assets/bindu_logo.png" width="80">

  # Bindu

  ### Couche d'identité, de communication et de paiement pour les agents d'IA.

  </div>

  <br>

  > **Écrivez votre agent dans n'importe quel framework. Enveloppez-le avec `bindufy()`.**
  > **Envoyez un microservice A2A signé en dix lignes de code - avec identité, OAuth2 et paiements on-chain.**

  Pas besoin d'écrire d'infrastructure. Pas besoin de réécrire des frameworks. Fonctionne avec Python, TypeScript et Kotlin, et repose sur deux protocoles ouverts : [A2A](https://github.com/a2aproject/A2A) et [x402](https://github.com/coinbase/x402).

  <div align="center">

    <p>
      <a href="../README.md">English</a> ·
      <a href="README.de.md">Deutsch</a> ·
      <a href="README.es.md">Español</a> ·
      <a href="README.fr.md">Français</a> ·
      <a href="README.hi.md">हिंदी</a> ·
      <a href="README.bn.md">বাংলা</a> ·
      <a href="README.zh.md">中文</a> ·
      <a href="README.nl.md">Nederlands</a> ·
      <a href="README.ta.md">தமிழ்</a>
    </p>

    <p>
      <a href="https://opensource.org/licenses/Apache-2.0"><img src="https://img.shields.io/badge/license-Apache%202.0-blue.svg" alt="License"></a>
      <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.12+-blue.svg" alt="Python Version"></a>
      <a href="https://pypi.org/project/bindu/"><img src="https://img.shields.io/pypi/v/bindu.svg" alt="PyPI version"></a>
      <a href="https://coveralls.io/github/Saptha-me/Bindu?branch=v0.3.18"><img src="https://coveralls.io/repos/github/Saptha-me/Bindu/badge.svg?branch=v0.3.18" alt="Coverage"></a>
      <a href="https://github.com/getbindu/Bindu/actions/workflows/release.yml"><img src="https://github.com/getbindu/Bindu/actions/workflows/release.yml/badge.svg" alt="Tests"></a>
      <a href="https://discord.gg/3w5zuYUuwt"><img src="https://img.shields.io/badge/Discord-7289DA?logo=discord&logoColor=white" alt="Discord"></a>
      <a href="https://github.com/getbindu/Bindu/graphs/contributors"><img src="https://img.shields.io/github/contributors/getbindu/Bindu" alt="Contributors"></a>
      <a href="https://hits.sh/github.com/Saptha-me/Bindu.svg"><img src="https://hits.sh/github.com/Saptha-me/Bindu.svg" alt="Hits"></a>
    </p>

    <p>
      <a href="https://getbindu.com"><strong>Enregistrez votre agent</strong></a> ·
      <a href="https://docs.getbindu.com"><strong>Documentation</strong></a> ·
      <a href="https://discord.gg/3w5zuYUuwt"><strong>Discord</strong></a>
    </p>
  </div>

  ---

  ## Ce que vous obtenez

  Lorsque vous enveloppez un handler avec `bindufy(config, handler)`, le processus parle des protocoles standards, signe chaque réponse et devient prêt à recevoir des paiements. Voici ce qu'il fait pour vous, regroupé par catégories :

  <br>

  **Protocole - Parler au monde**

  | Capacité | Ce que cela signifie |
  |---|---|
  | Endpoints JSON-RPC A2A | Le protocole standard que d'autres agents utilisent déjà. `message/send`, `tasks/get`, `message/stream` sur le port 3773. |
  | Notifications push | Callbacks webhook sur les changements d'état des tâches - pas de polling nécessaire. |
  | Agnostique de langue | Les SDK Python, TypeScript et Kotlin partagent un cœur gRPC. Même protocole, même DID, même auth. |

  <br>

  **Identité et accès - Prouvez qui appelle**

  | Capacité | Ce que cela signifie |
  |---|---|
  | Identité DID (Ed25519) | Chaque artefact retourné est signé. Les appelants vérifient avec DID standard W3C - pas de secrets partagés. |
  | OAuth2 via Ory Hydra | Tokens avec portée (`agent:read`, `agent:write`, `agent:execute`) au lieu d'un bearer tout-ou-rien. |

  <br>

  **Commerce et accessibilité - Recevez des paiements et soyez accessible**

  | Capacité | Ce que cela signifie |
  |---|---|
  | Paiements x402 | Avec un drapeau, l'agent facture USDC sur Base avant de traiter une requête. La vérification de paiement s'exécute avant votre handler. |
  | Tunnel public | `expose: true` ouvre un tunnel FRP pour que votre agent local soit accessible depuis Internet public. |

  ---

  ## Installation

  ```bash
  uv add bindu
  ```

  Pour un checkout de développement avec tests :

  ```bash
  git clone https://github.com/getbindu/Bindu.git
  cd Bindu
  uv sync --dev
  ```

  Python 3.12+ et [uv](https://github.com/astral-sh/uv) requis. Pour exécuter les exemples, une clé API pour au moins un fournisseur LLM est nécessaire (`OPENROUTER_API_KEY`, `OPENAI_API_KEY` ou `MINIMAX_API_KEY`)。

  ---

  ## Bonjour agent

  Tout le concept de Bindu est clair dans un seul fichier - créez n'importe quel agent, passez-le à `bindufy()`, et votre processus arrive comme un microservice A2A signé. Le bloc suivant est complet et exécutable.

  ```python
  import os
  from bindu.penguin.bindufy import bindufy
  from agno.agent import Agent
  from agno.models.openai import OpenAIChat
  from agno.tools.duckduckgo import DuckDuckGoTools

  # 1. Créez votre agent avec votre framework préféré. Bindu
  #    ne se soucie pas de ce qu'il y a à l'intérieur - il a juste besoin de quelque chose d'invocable.
  agent = Agent(
      instructions="You are a research assistant that finds and summarizes information.",
      model=OpenAIChat(id="gpt-4o"),
      tools=[DuckDuckGoTools()],
  )

  # 2. Dites à Bindu qui vous êtes et où vit l'agent. `expose: True`
  #    ouvre un tunnel FRP public - laissez-le pour le développement local.
  config = {
      "author": "you@example.com",
      "name": "research_agent",
      "description": "Research assistant with web search.",
      "deployment": {
          "url": os.getenv("BINDU_DEPLOYMENT_URL", "http://localhost:3773"),
          "expose": True,
      },
      "skills": ["skills/question-answering"],
  }

  # 3. Contrat du handler : (messages) -> response. C'est tout.
  def handler(messages: list[dict[str, str]]):
      return agent.run(input=messages)

  # 4. bindufy() démarre le serveur HTTP, crée votre DID, s'enregistre auprès de Hydra
  #    (si auth est activé) et commence à accepter les appels A2A.
  bindufy(config, handler)
  ```

  Exécutez-le, et l'agent est en ligne sur l'URL configurée. Besoin d'un port différent ? Exportez `BINDU_PORT=4000` - aucun changement de code.

  <details>
  <summary>Équivalent TypeScript</summary>

  ```typescript
  import { bindufy } from "@bindu/sdk";
  import OpenAI from "openai";

  const openai = new OpenAI();

  bindufy({
    author: "you@example.com",
    name: "research_agent",
    description: "Research assistant.",
    deployment: { url: "http://localhost:3773", expose: true },
    skills: ["skills/question-answering"],
  }, async (messages) => {
    const response = await openai.chat.completions.create({
      model: "gpt-4o",
      messages: messages.map(m => ({ role: m.role as "user" | "assistant" | "system", content: m.content })),
    });
    return response.choices[0].message.content || "";
  });
  ```

  Le SDK TypeScript démarre automatiquement le cœur Python. Même protocole, même DID. Exemple complet dans [`examples/typescript-openai-agent/`](examples/typescript-openai-agent/)。

  </details>

  <details>
  <summary>Appeler l'agent avec curl</summary>

  ```bash
  curl -X POST http://localhost:3773/ \
    -H 'Content-Type: application/json' \
    -d '{
      "jsonrpc": "2.0",
      "method": "message/send",
      "id": "<uuid>",
      "params": {
        "message": {
          "role": "user",
          "kind": "message",
          "parts": [{"kind": "text", "text": "Hello"}],
          "messageId": "<uuid>",
          "contextId": "<uuid>",
          "taskId": "<uuid>"
        }
      }
    }'
  ```

  Faites un polling de `tasks/get` avec le même `taskId` jusqu'à ce que l'état soit `completed`. L'artefact retourné porte une signature DID sous `metadata["did.message.signature"]`。

  </details>

  ---

  ## Comment cela s'intègre

  Alors, que se passe-t-il réellement lorsque cet appel `bindufy()` prend effet ? Le handler est le seul code que vous écrivez. Tout le reste est le scaffolding de Bindu autour de lui :

  ```mermaid
  flowchart TD
      A[your handler] --> B["bindufy(config, handler)"]

      B --> C[Bindu Core :3773]

      subgraph D[Bindu Core Internals]
          D1["OAuth2 (Hydra)"]
          D2["DID Verification"]
          D3["x402 Payment (Optional)"]
          D4["Task Manager & Scheduler"]
      end

      C --> D1
      C --> D2
      C --> D3
      C --> D4

      D4 --> E[A2A Signed Response]
  ```

  `bindufy()` est un wrapper mince. Votre handler reste pur - `(messages) -> response`. Bindu possède l'identité, le protocole, l'auth, les paiements, le stockage et la planification.

  ---

  ## Appeler un agent sécurisé

  > **TL;DR** - Lorsque `AUTH__ENABLED=true`, un token bearer Hydra et trois en-têtes `X-DID-*` sont requis pour chaque appel. Client Python : ~25 lignes, [ci-dessous](#step-2--pick-your-client). Postman : collez un script. Le reste de cette section explique pourquoi et comment cela fonctionne, et ce qui ne va pas si ça ne fonctionne pas.

  L'exemple `curl` dans *Bonjour agent* fonctionne car auth est désactivé par défaut - n'importe qui peut POST à votre agent. Lorsque vous basculez sur `AUTH__ENABLED=true AUTH__PROVIDER=hydra`, votre agent devient strict. Maintenant chaque appelant doit répondre à deux questions avant que le handler ne s'exécute :

  1. **Avez-vous la permission de m'appeler ?** - Montrez un token OAuth2 valide de Hydra.
  2. **Êtes-vous vraiment qui vous dites être ?** - Signez la requête avec une clé DID.

  Pensez-y comme l'embarquement dans un vol : la carte d'embarquement (token OAuth) dit "Oui, vous avez un siège sur ce vol", et le passeport (signature DID) dit "Et vous êtes vraiment la personne sur cette carte d'embarquement". Le serveur vérifie les deux.

  La théorie complète réside dans [`docs/AUTHENTICATION.md`](docs/AUTHENTICATION.md) et [`docs/DID.md`](docs/DID.md) - anglais simple, aucune connaissance de crypto n'est supposée. Ci-dessous, vous trouverez la version pratique "Je veux juste appeler mon agent".

  <br>

  ### Trois en-têtes supplémentaires

  Avec le `Authorization: Bearer <hydra-jwt>` habituel, chaque requête sécurisée porte :

  | En-tête | Valeur |
  |---|---|
  | `X-DID` | Votre chaîne DID, par exemple `did:bindu:you_at_example_com:myagent:<uuid>` |
  | `X-DID-Timestamp` | Secondes Unix actuelles (serveur autorise 5 minutes de marge) |
  | `X-DID-Signature` | `base58( Ed25519_sign( <signing payload> ) )` |

  **La payload de signature** est reconstruite sur le serveur comme suit :

  ```python
  json.dumps({"body": <raw-body-string>, "did": <did>, "timestamp": <ts>}, sort_keys=True)
  ```

  Deux pièges qui vous mordront jusqu'à ce que vous les compreniez :

  - **Faites correspondre l'espacement JSON de Python.** Le `json.dumps` par défaut de Python écrit `", "` et `": "` (avec espaces). En JS `JSON.stringify` les écrit sans eux. Si votre payload se sérialise différemment, Ed25519 voit des octets différents et le serveur renvoie `reason="crypto_mismatch"`。
  - **Signez ce que vous envoyez.** Si vous parsez le body, le changez, re-sérialisez et envoyez - vous avez signé les mauvais octets. Créez la chaîne du body **une fois**, signez exactement ces octets, envoyez exactement ces octets.

  <br>

  ### Étape 1 - Obtenez un token bearer de Hydra

  L'agent imprime un curl prêt à l'emploi dans la bannière de démarrage. Version courte :

  ```bash
  SECRET=$(jq -r '.[].client_secret' < .bindu/oauth_credentials.json)
  curl -X POST https://hydra.getbindu.com/oauth2/token \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "grant_type=client_credentials" \
    -d "client_id=did:bindu:you_at_example_com:myagent:<uuid>" \
    -d "client_secret=$SECRET" \
    -d "scope=openid offline agent:read agent:write"
  ```

  La réponse contient un `access_token`. Il est bon pour une heure - cachez-le, récupérez-le au besoin.

  <br>

  ### Étape 2 - Choisissez votre client

  **Python - L'exemple le plus court exécutable.** Lit les propres clés de l'agent (Bindu les écrit dans `.bindu/` au premier boot), signe une requête, fait un polling du résultat. Self-call fonctionne car la clé de l'agent est une identité d'appelant valide.

  ```python
  import base58, httpx, json, time, uuid
  from pathlib import Path
  from cryptography.hazmat.primitives import serialization

  # 1. Chargez les clés que Bindu a écrites au premier boot
  priv  = serialization.load_pem_private_key(Path(".bindu/private.pem").read_bytes(), password=None)
  creds = next(iter(json.loads(Path(".bindu/oauth_credentials.json").read_text()).values()))
  did   = creds["client_id"]            # DID fonctionne aussi comme client_id Hydra

  # 2. Échangez les identifiants contre un JWT de courte durée
  bearer = httpx.post("https://hydra.getbindu.com/oauth2/token", data={
      "grant_type": "client_credentials",
      "client_id": creds["client_id"], "client_secret": creds["client_secret"],
      "scope": "openid offline agent:read agent:write",
  }).json()["access_token"]

  # 3. Créez le body une fois - ce sont les octets que nous signerons et enverrons
  tid = str(uuid.uuid4())
  body = json.dumps({
      "jsonrpc": "2.0", "method": "message/send", "id": str(uuid.uuid4()),
      "params": {"message": {
          "role": "user", "kind": "message",
          "parts": [{"kind": "text", "text": "Hello!"}],
          "messageId": str(uuid.uuid4()), "contextId": str(uuid.uuid4()), "taskId": tid,
      }},
  })

  # 4. Signature : base58(Ed25519( json.dumps({body,did,timestamp}, sort_keys=True) ))
  ts      = int(time.time())
  payload = json.dumps({"body": body, "did": did, "timestamp": ts}, sort_keys=True)
  sig     = base58.b58encode(priv.sign(payload.encode())).decode()

  # 5. Déclenchez
  r = httpx.post("http://localhost:3773/", content=body, headers={
      "Content-Type":    "application/json",
      "Authorization":   f"Bearer {bearer}",
      "X-DID":           did,
      "X-DID-Timestamp": str(ts),
      "X-DID-Signature": sig,
  })
  print(r.status_code, r.json())
  ```

  Pour une version complète avec polling et gestion des erreurs, voir - [`examples/hermes_agent/call.py`](examples/hermes_agent/call.py)。

  <br>

  **Postman - Collez un script dans votre collection.**

  1. Ouvrez votre collection → Tab **Pre-request Script** → Collez le contenu de [`docs/postman-did-signing.js`](docs/postman-did-signing.js)。
  2. Définissez deux variables de collection : `bindu_did` (votre chaîne DID) et `bindu_did_seed` (votre graine Ed25519 de 32 octets, encodée en base64)。
  3. Ajoutez un en-tête `Authorization: Bearer {{bindu_bearer}}` et déposez votre token Hydra dans `bindu_bearer`。
  4. Appuyez sur Send. Le script signe exactement les octets du body que Postman envoie et définit les trois en-têtes `X-DID-*` pour vous.

  Postman Desktop v11+ requis (`crypto.subtle` nécessite Ed25519)。

  <br>

  **curl commun - techniquement possible, généralement gênant.** La signature dépend des octets du body que vous envoyez, vous devez donc d'abord un script auxiliaire pour calculer la signature, puis la remplacer dans l'appel curl. Si vous faites cela, vous serez probablement mieux avec le client Python ci-dessus.

  <br>

  ### Quand la signature échoue

  Le log du serveur enregistre l'une des trois raisons. Si votre requête est rejetée avec 403, demandez à l'opérateur (ou vérifiez les logs du serveur vous-même) :

  | Log dit | Ce que cela signifie | Solution |
  |---|---|---|
  | `timestamp_out_of_window` | Votre `X-DID-Timestamp` est à plus de 5 minutes de l'horloge du serveur, ou vous avez réutilisé un timestamp ancien | Recalculez `int(time.time())` à chaque requête |
  | `malformed_input` | Le décodage base58 de la signature ou de la clé publique a échoué | Vérifiez que `X-DID-Signature` n'est pas encodé en URL, tronqué ou enveloppé de guillemets |
  | `crypto_mismatch` | Octets que vous avez signés ≠ Octets que vous avez envoyés | Reconstruisez la payload avec `sort_keys=True` et l'espacement JSON par défaut de Python ; signez la chaîne du body brut une fois et envoyez les mêmes octets |

  Nous avons touché un mode d'échec aigu en tests : si `crypto_mismatch` persiste et vous êtes *sûr* que vos octets correspondent, la clé publique que Hydra a pour cette DID peut être obsolète d'un enregistrement ancien. Solution : arrêtez l'agent, supprimez `.bindu/oauth_credentials.json`, redémarrez - le registre client Hydra sera mis à jour avec la clé actuelle.

  ---

  ## Gateway - Orchestration multi-agent

  Un seul agent enveloppé avec `bindufy()` est un microservice. **Bindu Gateway** est un orchestrateur orienté tâche qui s'assied dessus : donnez-lui une requête utilisateur et un catalogue d'agents A2A, et un LLM planificateur décompose la tâche, appelle les bons agents via A2A et transmet les résultats comme événements côté serveur. Pas de moteur DAG, pas de service d'orchestration séparé - le LLM planificateur choisit des outils à chaque tour.

  Au-delà d'un seul agent, vous obtenez :

  - **Un endpoint : `POST /plan`** - Donnez-lui une requête et un catalogue d'agents, obtenez des étapes transmises.
  - **Catalogue d'agents par requête** - Une liste d'agents externes, compétences et endpoints du système est passée. Le Gateway n'héberge aucune flotte lui-même.
  - **Persistance de session (Supabase)** - Compression soutenue par Postgres, rollback et historique multi-tour.
  - **A2A TypeScript natif** - Pas de sous-processus Python, pas de dépendance `@bindu/sdk` dans le Gateway.
  - **Signature DID optionnelle + intégration Hydra** - Gateway est identité end-to-end.

  Quickstart minimal :

  ```bash
  cd gateway
  npm install
  cp .env.example .env.local         # fill SUPABASE_*, GATEWAY_API_KEY, OPENROUTER_API_KEY
  npm run dev                        # → http://localhost:3774
  curl -sS http://localhost:3774/health
  ```

  Appliquez d'abord deux migrations Supabase (`gateway/migrations/001_init.sql`, `002_compaction_revert.sql`)。 Walkthrough complet et référence de l'opérateur dans [`gateway/README.md`](gateway/README.md) et [`docs/GATEWAY.md`](docs/GATEWAY.md) (45 minutes end-to-end : clon propre → trois agents chaînés → écrire une recette → signature DID)。

  Documentation du Gateway :

  | Sujet | Lien |
  |---|---|
  | Vue d'ensemble | [docs.getbindu.com/bindu/gateway/overview](https://docs.getbindu.com/bindu/gateway/overview) |
  | Quickstart | [docs.getbindu.com/bindu/gateway/quickstart](https://docs.getbindu.com/bindu/gateway/quickstart) |
  | Planification multi-agent | [docs.getbindu.com/bindu/gateway/multi-agent](https://docs.getbindu.com/bindu/gateway/multi-agent) |
  | Recettes (playbook de divulgation progressive) | [docs.getbindu.com/bindu/gateway/recipes](https://docs.getbindu.com/bindu/gateway/recipes) |
  | Identité (signature DID, Hydra) | [docs.getbindu.com/bindu/gateway/identity](https://docs.getbindu.com/bindu/gateway/identity) |
  | Déploiement en production | [docs.getbindu.com/bindu/gateway/production](https://docs.getbindu.com/bindu/gateway/production) |
  | Référence API | [docs.getbindu.com/api/introduction](https://docs.getbindu.com/api/introduction) |

  Pour une démo multi-agent exécutable, voir [`examples/gateway_test_fleet/`](examples/gateway_test_fleet/) - cinq petits agents sur ports locaux, un gateway, une requête。

  ---

  ## Frameworks supportés et exemples

  Apportez n'importe quel framework d'agent que vous aimez déjà. Vous passez un handler à Bindu ; il vous donne un microservice A2A signé. Indépendamment de ce qui est dans le handler, le flux est le même.

  <br>

  | Langage | Frameworks testés dans ce repo |
  |---|---|
  | **Python** | [AG2](https://github.com/ag2ai/ag2) · [Agno](https://github.com/agno-agi/agno) · [CrewAI](https://github.com/joaomdmoura/crewAI) · [Hermes Agent](https://github.com/NousResearch/hermes-agent) · [LangChain](https://github.com/langchain-ai/langchain) · [LangGraph](https://github.com/langchain-ai/langgraph) · [Notte](https://github.com/nottelabs/notte) |
  | **TypeScript** | [OpenAI SDK](https://github.com/openai/openai-node) · [LangChain.js](https://github.com/langchain-ai/langchainjs) |
  | **Kotlin** | [OpenAI Kotlin SDK](https://github.com/aallam/openai-kotlin) |
  | **Toute autre langue** | Via le [cœur gRPC](docs/grpc/) - ajoutez un SDK en quelques centaines de lignes |

  Compatible avec tout fournisseur LLM qui parle avec l'API OpenAI ou Anthropic : [OpenRouter](https://openrouter.ai/) (100+ modèles), [OpenAI](https://platform.openai.com/), [MiniMax](https://platform.minimaxi.com) et autres。

  <br>

  ### Quelques exemples pour commencer

  Cinq couvrent le spectre de ce que Bindu peut faire. Tous les 20+ exemples exécutables résident sous [`examples/`](examples/)。

  | Exemple | Ce qu'il montre |
  |---|---|
  | [Agent Swarm](examples/agent_swarm/) | Collaboration multi-agent - une petite "société" d'agents Agno qui s'assignent des tâches entre eux. |
  | [Premium Advisor](examples/premium-advisor/) | **Paiements x402** - Les appelants doivent payer USDC sur Base avant que le handler ne s'exécute. |
  | [Hermes via Bindu](examples/hermes_agent/) | **Interop de framework tiers** - L'agent Hermes de Nous Research bindufied en ~90 lignes. |
  | [Gateway Test Fleet](examples/gateway_test_fleet/) | Cinq petits agents + un gateway - histoire d'orchestration multi-agent end-to-end. |
  | [TypeScript OpenAI Agent](examples/typescript-openai-agent/) | **Preuve polyglotte** - Un agent TS bindufied avec Bindu TS SDK ; pas de Python requis. |

  **Voir catalogue complet :** [`examples/`](examples/) - 20+ agents couvrent l'analyse CSV, Q&A PDF, speech-to-text, web scraping, newsletter cybersécurité, collaboration multilingue, écriture de blogs et plus.

  Votre framework manque ? Ouvrez un issue ou demandez sur [Discord](https://discord.gg/3w5zuYUuwt)。

  ---

  ## Démo

  <div align="center">
    <a href="https://www.youtube.com/watch?v=qppafMuw_KI">
      <img src="https://img.youtube.com/vi/qppafMuw_KI/maxresdefault.jpg" alt="Bindu demo video" width="640" />
    </a>
  </div>

  Après avoir exécuté `cd frontend && npm run dev`, une UI de chat intégrée est disponible sur `http://localhost:5173`。

  <p align="center">
    <img src="../assets/agent-ui.png" alt="Bindu agent UI" width="640" />
  </p>

  ---

  ## Caractéristiques principales

  Tout ci-dessous est optionnel et modulaire - l'installation minimale est seulement le serveur A2A. Chaque ligne lie à un guide spécifique dans [`docs/`](docs/)。

  <br>

  **Identité et accès**

  | Caractéristique | Guide |
  |---|---|
  | Identités décentralisées (DIDs) | [DID.md](docs/DID.md) |
  | Authentification (Ory Hydra OAuth2) | [AUTHENTICATION.md](docs/AUTHENTICATION.md) |

  <br>

  **Protocole et infrastructure**

  | Caractéristique | Guide |
  |---|---|
  | Système de compétences | [SKILLS.md](docs/SKILLS.md) |
  | Négociation d'agents | [NEGOTIATION.md](docs/NEGOTIATION.md) |
  | Notifications push | [NOTIFICATIONS.md](docs/NOTIFICATIONS.md) |
  | Stockage PostgreSQL | [STORAGE.md](docs/STORAGE.md) |
  | Planificateur Redis | [SCHEDULER.md](docs/SCHEDULER.md) |
  | Agnostique de langue via gRPC | [GRPC_LANGUAGE_AGNOSTIC.md](docs/GRPC_LANGUAGE_AGNOSTIC.md) |

  <br>

  **Commerce et accessibilité**

  | Caractéristique | Guide |
  |---|---|
  | Paiements x402 (USDC sur Base) | [PAYMENT.md](docs/PAYMENT.md) |
  | Tunnel (développement local uniquement) | [TUNNELING.md](docs/TUNNELING.md) |

  <br>

  **Fiabilité et opérations**

  | Caractéristique | Guide |
  |---|---|
  | Retry avec backoff exponentiel | [Retry docs](https://docs.getbindu.com/bindu/learn/retry/overview) |
  | Observabilité (OpenTelemetry, Sentry) | [OBSERVABILITY.md](docs/OBSERVABILITY.md) |
  | Vérifications de santé et métriques | [HEALTH_METRICS.md](docs/HEALTH_METRICS.md) |

  ---

  ## Tests

  Bindu vise 70% de couverture de tests (objectif : 80%+) :

  ```bash
  uv run pytest tests/unit/ -v                                    # Tests unitaires rapides
  uv run pytest tests/integration/grpc/ -v -m e2e                 # gRPC E2E
  uv run pytest -n auto --cov=bindu --cov-report=term-missing     # Suite complète
  ```

  CI exécute des tests unitaires, gRPC E2E et builds du SDK TypeScript à chaque PR. Voir [`.github/workflows/ci.yml`](.github/workflows/ci.yml)。

  ---

  ## Dépannage

  <details>
  <summary>Problèmes courants</summary>

  | Problème | Solution |
  |---|---|
  | `uv: command not found` | Redémarrez votre shell après avoir installé uv. |
  | `Python version not supported` | Installez Python 3.12+ de [python.org](https://www.python.org/downloads/) ou via `pyenv`. |
  | `bindu: command not found` | Activez votre virtualenv : `source .venv/bin/activate`. |
  | `Port 3773 already in use` | Définissez `BINDU_PORT=4000`, ou remplacez avec `BINDU_DEPLOYMENT_URL=http://localhost:4000`. |
  | `ModuleNotFoundError` | Exécutez `uv sync --dev`. |
  | Pre-commit a échoué | Exécutez `pre-commit run --all-files`. |
  | `Permission denied` (macOS) | Exécutez `xattr -cr .` pour supprimer les attributs étendus. |

  Réinitialiser l'environnement :

  ```bash
  rm -rf .venv && uv venv --python 3.12.9 && uv sync --dev
  ```

  Sur Windows PowerShell, vous aurez peut-être besoin de `Set-ExecutionPolicy RemoteSigned -Scope CurrentUser`。

  </details>

  ---

  ## Problèmes connus

  Si vous exécutez Bindu en production, lisez d'abord [`bugs/known-issues.md`](bugs/known-issues.md)。 C'est un catalogue par sous-système avec des workarounds. Les postmortems pour les bugs corrigés résident sous [`bugs/core/`](bugs/core/), [`bugs/gateway/`](bugs/gateway/), [`bugs/sdk/`](bugs/sdk/) et [`bugs/frontend/`](bugs/frontend/)。

  Éléments de haute priorité actuels :

  | Sous-système | Slug | Symptôme |
  |---|---|---|
  | Core | [`x402-middleware-fails-open-on-body-parse`](bugs/known-issues.md#x402-middleware-fails-open-on-body-parse) | Body JSON distordé contourne la vérification de paiement |
  | Core | [`x402-no-replay-prevention`](bugs/known-issues.md#x402-no-replay-prevention) | Un paiement travaille indéfiniment jusqu'à `validBefore` |
  | Core | [`x402-no-signature-verification`](bugs/known-issues.md#x402-no-signature-verification) | La signature EIP-3009 n'est jamais vérifiée |
  | Core | [`x402-balance-check-skipped-on-missing-contract-code`](bugs/known-issues.md#x402-balance-check-skipped-on-missing-contract-code) | RPC mal configuré contourne silencieusement la vérification de solde |
  | Gateway | [`context-window-hardcoded`](bugs/known-issues.md#context-window-hardcoded) | Le seuil de compression suppose une fenêtre de 200k tokens |
  | Gateway | [`poll-budget-unbounded-wall-clock`](bugs/known-issues.md#poll-budget-unbounded-wall-clock) | `sendAndPoll` peut bloquer 5 minutes par appel d'outil |
  | Gateway | [`no-session-concurrency-guard`](bugs/known-issues.md#no-session-concurrency-guard) | Deux appels `/plan` dans la même session confondent l'historique |

  Nouveau problème ? Ouvrez un issue GitHub avec référence de slug (ex. *"Fixes `context-window-hardcoded`"*)。 Avez-vous un fix ? Supprimez l'entrée de `known-issues.md` et ajoutez un postmortem daté - voir [`bugs/README.md`](bugs/README.md) pour modèle。

  ---

  ## Contribution

  Clonez, configurez et exécutez les hooks pre-commit :

  ```bash
  git clone https://github.com/getbindu/Bindu.git
  cd Bindu
  uv venv --python 3.12.9 && source .venv/bin/activate
  uv sync --dev
  pre-commit run --all-files
  ```

  Discussion et aide sur [Discord](https://discord.gg/3w5zuYUuwt)。 Guide complet dans [`.github/contributing.md`](.github/contributing.md)。 Nous avons une liste ouverte d'agents que nous aimerions voir bindufied - [contribuez](https://www.notion.so/getbindu/305d3bb65095808eac2bf720368e9804?v=305d3bb6509580189941000cfad83ae7&source=copy_link)。

  ---

  ## Mainteneurs

  <table>
    <tr>
      <td align="center"><a href="https://github.com/raahulrahl"><img src="https://avatars.githubusercontent.com/u/157174139?v=4" width="80" alt="Raahul Dutta"/><br /><sub><b>Raahul Dutta</b></sub></a></td>
      <td align="center"><a href="https://github.com/Paraschamoli"><img src="https://avatars.githubusercontent.com/u/157124537?v=4" width="80" alt="Paras Chamoli"/><br /><sub><b>Paras Chamoli</b></sub></a></td>
      <td align="center"><a href="https://github.com/chandan-1427"><img src="https://avatars.githubusercontent.com/u/202320492?v=4" width="80" alt="Chandan"/><br /><sub><b>Chandan</b></sub></a></td>
    </tr>
  </table>

  ---

  ## Remerciements

  Bindu repose sur les épaules de :

  [FastA2A](https://github.com/pydantic/fasta2a) · [A2A](https://github.com/a2aproject/A2A) · [x402](https://github.com/coinbase/x402) · [Hugging Face chat-ui](https://github.com/huggingface/chat-ui) · [12 Factor Agents](https://github.com/humanlayer/12-factor-agents/blob/main/content/factor-11-trigger-from-anywhere.md) · [OpenCode](https://github.com/anomalyco/opencode) · [OpenMoji](https://openmoji.org/library/emoji-1F33B/) · [ASCII Space Art](https://www.asciiart.eu/space/other)

  ---

  ## Licence

  Apache 2.0. Voir [LICENSE.md](LICENSE.md)。

  <p align="center">
    <a href="https://api.star-history.com/svg?repos=getbindu/Bindu&type=Date">
      <img src="https://api.star-history.com/svg?repos=getbindu/Bindu&type=Date" alt="Star history">
    </a>
  </p>

  <br/>
  <br/>

  <p align="center">
    <img src="../assets/sunflower-mountains.jpeg" alt="Bindu" width="720" />
  </p>

  <p align="center">
    <em>"Nous croyons en la théorie du tournesol - debout ensemble, apportant espoir et lumière à l'internet des agents."</em>
  </p>

  <p align="center">
    <em>De l'idée à l'internet des agents en 2 minutes.</em>
    <em>Votre agent. Votre framework. Protocole universel.</em>
  </p>

  <p align="center">
    <a href="https://github.com/getbindu/Bindu">Donnez-nous une étoile sur GitHub</a> •
    <a href="https://discord.gg/3w5zuYUuwt">Rejoignez Discord</a> •
    <a href="https://docs.getbindu.com">Lire la documentation</a>
  </p>

  <p align="center">
    <sub>
      Fait entre Amsterdam et l'Inde · Open Source sous Apache 2.0 ·
      <a href="https://getbindu.com">getbindu.com</a>
    </sub>
  </p>
  •
  <a href="README.ta.md">🇮🇳 தமிழ்</a>
</p>

<p align="center">
  <a href="https://opensource.org/licenses/Apache-2.0"><img src="https://img.shields.io/badge/license-Apache%202.0-blue.svg" alt="License"></a>
  <a href="https://hits.sh/github.com/Saptha-me/Bindu.svg"><img src="https://hits.sh/github.com/Saptha-me/Bindu.svg" alt="Hits"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.12+-blue.svg" alt="Python Version"></a>
  <a href="https://pypi.org/project/bindu/"><img src="https://img.shields.io/pypi/v/bindu.svg" alt="PyPI version"></a>
  <a href="https://coveralls.io/github/Saptha-me/Bindu?branch=v0.3.18"><img src="https://coveralls.io/repos/github/Saptha-me/Bindu/badge.svg?branch=v0.3.18" alt="Coverage"></a>
  <a href="https://github.com/getbindu/Bindu/actions/workflows/release.yml"><img src="https://github.com/getbindu/Bindu/actions/workflows/release.yml/badge.svg" alt="Tests"></a>
  <a href="https://discord.gg/3w5zuYUuwt"><img src="https://img.shields.io/badge/Join%20Discord-7289DA?logo=discord&logoColor=white" alt="Discord"></a>
  <a href="https://github.com/getbindu/Bindu/graphs/contributors"><img src="https://img.shields.io/github/contributors/getbindu/Bindu" alt="Contributors"></a>
</p>

<br/>

<p align="center">
  <img src="../assets/sunflower-mountains.jpeg" alt="Bindu — The Internet of Agents" width="720" />
</p>

<p align="center">
  <em>"Comme des tournesols se tournant vers la lumière, les agents collaborent en essaims - chacun indépendant, mais ensemble ils créent quelque chose de plus grand."</em>
</p>

<br/>

<div align="center">
  <h3>Intégrez votre agent en une seule ligne</h3>
</div>

<div align="center">
  <pre><code>curl -fsSL https://getbindu.com/install-bindu.sh | bash</code></pre>
</div>

---

**Bindu** (prononcé : _binduu_) est une couche opérationnelle pour les agents IA qui fournit des capacités d'identité, de communication et de paiement. Elle offre un service prêt pour la production avec une API pratique pour connecter, authentifier et orchestrer des agents à travers des systèmes distribués en utilisant des protocoles ouverts : **A2A**, **AP2**, et **X402**.Construit avec une architecture distribuée (Gestionnaire de tâches, planificateur, stockage), Bindu permet un développement rapide et une intégration facile avec n'importe quel cadre d'IA. Transformez n'importe quel cadre d'agent en un service entièrement interopérable pour la communication, la collaboration et le commerce dans l'Internet des Agents.

<p align="center">
  <strong>🌟 <a href="https://getbindu.com">Enregistrez votre agent</a> • 🌻 <a href="https://docs.getbindu.com">Documentation</a> • 💬 <a href="https://discord.gg/3w5zuYUuwt">Communauté Discord</a></strong>
</p>


---

<br/>

## 🎥 Regardez Bindu en Action

<div align="center">
  <a href="https://www.youtube.com/watch?v=qppafMuw_KI" target="_blank">
    <img src="https://img.youtube.com/vi/qppafMuw_KI/maxresdefault.jpg" alt="Bindu Demo" width="640" style="border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);" />
  </a>
</div>

<br/>

## 📋 Prérequis

Avant d'installer Bindu, assurez-vous d'avoir :

- **Python 3.12 ou supérieur** - [Download here](https://www.python.org/downloads/)
- **Gestionnaire de paquets UV** - [Installation guide](https://github.com/astral-sh/uv)
- **Clé API requise** : Définissez `OPENROUTER_API_KEY` ou `OPENAI_API_KEY` dans vos variables d'environnement. Des modèles OpenRouter gratuits sont disponibles pour les tests.


### Vérifiez votre configuration

```bash
# Check Python version
uv run python --version  # Should show 3.12 or higher

# Check UV installation
uv --version
```

---

<br/>

## 📦 Installation
<details>
<summary><b>Remarque pour les utilisateurs (Git & GitHub Desktop)</b></summary>

Sur certains systèmes Windows, git peut ne pas être reconnu dans l'invite de commandes même après l'installation en raison de problèmes de configuration de PATH.

Si vous rencontrez ce problème, vous pouvez utiliser *GitHub Desktop* comme alternative :

1. Installez GitHub Desktop depuis https://desktop.github.com/
2. Connectez-vous avec votre compte GitHub
3. Clonez le dépôt en utilisant l'URL du dépôt :
   https://github.com/getbindu/Bindu.git

GitHub Desktop vous permet de cloner, gérer des branches, valider des modifications et ouvrir des demandes de tirage sans utiliser la ligne de commande.

</details>

```bash
# Install Bindu
uv add bindu

# For development (if contributing to Bindu)
# Create and activate virtual environment
uv venv --python 3.12.9
source .venv/bin/activate  # On macOS/Linux
# .venv\Scripts\activate  # On Windows

uv sync --dev
```

<details>
<summary><b>Problèmes d'installation courants</b> (cliquez pour développer)</summary>

<br/>

| Problème | Solution |
|-------|----------|| `uv: command not found` | Redémarrez votre terminal après avoir installé UV. Sur Windows, utilisez PowerShell |
| `Python version not supported` | Installez Python 3.12+ depuis [python.org](https://www.python.org/downloads/) |
| Virtual environment not activating (Windows) | Utilisez PowerShell et exécutez `.venv\Scripts\activate` |
| `Microsoft Visual C++ required` | Téléchargez [Visual C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/) |
| `ModuleNotFoundError` | Activez venv et exécutez `uv sync --dev` |

</details>

---

<br/>

## 🚀 Démarrage rapide

### Option 1 : Utilisation de Cookiecutter (Recommandé)

**Temps jusqu'au premier agent : ~2 minutes ⏱️**

```bash
# Install cookiecutter
uv add cookiecutter

# Create your Bindu agent
uvx cookiecutter https://github.com/getbindu/create-bindu-agent.git
```

<div align="center">
  <a href="https://youtu.be/obY1bGOoWG8?si=uEeDb0XWrtYOQTL7" target="_blank">
    <img src="https://img.youtube.com/vi/obY1bGOoWG8/maxresdefault.jpg" alt="Create Production Ready Agent" width="640" style="border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);" />
  </a>
</div>

Votre agent local devient un service en direct, sécurisé et découvrable. [Learn more →](https://docs.getbindu.com/bindu/create-bindu-agent/overview)

> **💡 Conseil Pro :** Les agents créés avec cookiecutter incluent des actions GitHub qui enregistrent automatiquement votre agent dans le [GetBindu.com](https://getbindu.com) lorsque vous poussez vers votre dépôt.

### Option 2 : Configuration manuelle

Créez votre script d'agent `my_agent.py` :

```python
import os

from bindu.penguin.bindufy import bindufy
from agno.agent import Agent
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.models.openai import OpenAIChat

# Define your agent
agent = Agent(
    instructions="You are a research assistant that finds and summarizes information.",
    model=OpenAIChat(id="gpt-4o"),
    tools=[DuckDuckGoTools()],
)

# Configuration
config = {
    "author": "your.email@example.com",
    "name": "research_agent",
    "description": "A research assistant agent",
    "deployment": {
        "url": os.getenv("BINDU_DEPLOYMENT_URL", "http://localhost:3773"),
        "expose": True,
    },
    "skills": ["skills/question-answering", "skills/pdf-processing"]
}

# Handler function
def handler(messages: list[dict[str, str]]):
    """Process messages and return agent response.

    Args:
        messages: List of message dictionaries containing conversation history

    Returns:
        Agent response result
    """
    result = agent.run(input=messages)
    return result

# Bindu-fy it
bindufy(config, handler)

# Use tunnel to expose your agent to the internet
# bindufy(config, handler, launch=True)
```

![Sample Agent](../assets/agno-simple.png)

Votre agent est maintenant en direct à l'URL configurée dans `deployment.url`.

Définissez un port personnalisé sans modifications de code :

```bash
# Linux/macOS
export BINDU_PORT=4000

# Windows PowerShell
$env:BINDU_PORT="4000"
```

Les exemples existants qui utilisent `http://localhost:3773` sont automatiquement remplacés lorsque `BINDU_PORT` est défini.

### Option 3 : Agent local sans configuration

Essayez Bindu sans configurer Postgres, Redis ou tout service cloud. Fonctionne entièrement localement en utilisant un stockage en mémoire et un planificateur.

```bash
python examples/beginner_zero_config_agent.py
```

### Option 4 : Agent Echo minimal (Test)

<details>
<summary><b>Voir l'exemple minimal</b> (cliquez pour développer)</summary>

Agent fonctionnel le plus petit possible :

```python
import os

from bindu.penguin.bindufy import bindufy

def handler(messages):
    return [{"role": "assistant", "content": messages[-1]["content"]}]

config = {
    "author": "your.email@example.com",
    "name": "echo_agent",
    "description": "A basic echo agent for quick testing.",
    "deployment": {
        "url": os.getenv("BINDU_DEPLOYMENT_URL", "http://localhost:3773"),
        "expose": True,
    },
    "skills": []
}

bindufy(config, handler)

# Use tunnel to expose your agent to the internet
# bindufy(config, handler, launch=True)
```

**Exécutez l'agent :**

```bash
# Start the agent
python examples/echo_agent.py
```

</details>

<details>
<summary><b>Testez l'agent avec curl</b> (cliquez pour développer)</summary>

<br/>

Entrée :
```bash
curl --location 'http://localhost:3773/' \
--header 'Content-Type: application/json' \
--data '{
    "jsonrpc": "2.0",
    "method": "message/send",
    "params": {
        "message": {
            "role": "user",
            "parts": [
                {
                    "kind": "text",
                    "text": "Quote"
                }
            ],
            "kind": "message",
            "messageId": "550e8400-e29b-41d4-a716-446655440038",
            "contextId": "550e8400-e29b-41d4-a716-446655440038",
            "taskId": "550e8400-e29b-41d4-a716-446655440300"
        },
        "configuration": {
            "acceptedOutputModes": [
                "application/json"
            ]
        }
    },
    "id": "550e8400-e29b-41d4-a716-446655440024"
}'
```

Sortie :
```bash
{
    "jsonrpc": "2.0",
    "id": "550e8400-e29b-41d4-a716-446655440024",
    "result": {
        "id": "550e8400-e29b-41d4-a716-446655440301",
        "context_id": "550e8400-e29b-41d4-a716-446655440038",
        "kind": "task",
        "status": {
            "state": "submitted",
            "timestamp": "2025-12-16T17:10:32.116980+00:00"
        },
        "history": [
            {
                "message_id": "550e8400-e29b-41d4-a716-446655440038",
                "context_id": "550e8400-e29b-41d4-a716-446655440038",
                "task_id": "550e8400-e29b-41d4-a716-446655440301",
                "kind": "message",
                "parts": [
                    {
                        "kind": "text",
                        "text": "Quote"
                    }
                ],
                "role": "user"
            }
        ]
    }
}
```

Vérifiez l'état de la tâche
```bash
curl --location 'http://localhost:3773/' \
--header 'Content-Type: application/json' \
--data '{
    "jsonrpc": "2.0",
    "method": "tasks/get",
    "params": {
        "taskId": "550e8400-e29b-41d4-a716-446655440301"
    },
    "id": "550e8400-e29b-41d4-a716-446655440025"
}'
```

Sortie :
```bash
{
    "jsonrpc": "2.0",
    "id": "550e8400-e29b-41d4-a716-446655440025",
    "result": {
        "id": "550e8400-e29b-41d4-a716-446655440301",
        "context_id": "550e8400-e29b-41d4-a716-446655440038",
        "kind": "task",
        "status": {
            "state": "completed",
            "timestamp": "2025-12-16T17:10:32.122360+00:00"
        },
        "history": [
            {
                "message_id": "550e8400-e29b-41d4-a716-446655440038",
                "context_id": "550e8400-e29b-41d4-a716-446655440038",
                "task_id": "550e8400-e29b-41d4-a716-446655440301",
                "kind": "message",
                "parts": [
                    {
                        "kind": "text",
                        "text": "Quote"
                    }
                ],
                "role": "user"
            },
            {
                "role": "assistant",
                "parts": [
                    {
                        "kind": "text",
                        "text": "Quote"
                    }
                ],
                "kind": "message",
                "message_id": "2f2c1a8e-68fa-4bb7-91c2-eac223e6650b",
                "task_id": "550e8400-e29b-41d4-a716-446655440301",
                "context_id": "550e8400-e29b-41d4-a716-446655440038"
            }
        ],
        "artifacts": [
            {
                "artifact_id": "22ac0080-804e-4ff6-b01c-77e6b5aea7e8",
                "name": "result",
                "parts": [
                    {
                        "kind": "text",
                        "text": "Quote",
                        "metadata": {
                            "did.message.signature": "5opJuKrBDW4woezujm88FzTqRDWAB62qD3wxKz96Bt2izfuzsneo3zY7yqHnV77cq3BDKepdcro2puiGTVAB52qf"  # pragma: allowlist secret
                        }
                    }
                ]
            }
        ]
    }
}
```

</details>

 

---

 

## 🚀 Fonctionnalités principales
| Fonctionnalité | Description | Documentation |
| :--- | :--- | :--- |
| **Authentification** | Accès API sécurisé avec Ory Hydra OAuth2 (optionnel pour le développement) | [Guide →](../docs/AUTHENTICATION.md) |
| 💰 **Intégration de Paiement (X402)** | Accepter les paiements USDC sur la blockchain Base avant d'exécuter des méthodes protégées | [Guide →](../docs/PAYMENT.md) |
| 💾 **Stockage PostgreSQL** | Stockage persistant pour les déploiements en production (optionnel - InMemoryStorage par défaut) | [Guide →](../docs/STORAGE.md) |
| 📋 **Planificateur Redis** | Planification de tâches distribuées pour des déploiements multi-travailleurs (optionnel - InMemoryScheduler par défaut) | [Guide →](../docs/SCHEDULER.md) |
| 🎯 **Système de Compétences** | Capacités réutilisables que les agents annoncent et exécutent pour un routage intelligent des tâches | [Guide →](../docs/SKILLS.md) |
| 🤝 **Négociation d'Agent** | Sélection d'agent basée sur les capacités pour une orchestration intelligente | [Guide →](../docs/NEGOTIATION.md) |
| 🌐 **Tunneling** | Exposer des agents locaux à Internet pour des tests (**développement local uniquement, pas pour la production**) | [Guide →](../docs/TUNNELING.md) |
| 📬 **Notifications Push** | Notifications webhook en temps réel pour les mises à jour de tâches - aucun sondage requis | [Guide →](../docs/NOTIFICATIONS.md) |
| 📊 **Observabilité & Surveillance** | Suivre les performances et déboguer les problèmes avec OpenTelemetry et Sentry | [Guide →](../docs/OBSERVABILITY.md) |
| 🔄 **Mécanisme de Réessai** | Réessai automatique avec un backoff exponentiel pour des agents résilients | [Guide →](docs.getbindu.com/bindu/learn/retry/overview) |
| 🔑 **Identifiants Décentralisés (DIDs)** | Identité cryptographique pour des interactions d'agent vérifiables et sécurisées et intégration de paiement | [Guide →](../docs/DID.md) |
| 🏥 **Vérification de Santé & Métriques** | Surveiller la santé et les performances des agents avec des points de terminaison intégrés | [Guide →](../docs/HEALTH_METRICS.md) |

---

<br/>

## 🎨 Interface de Chat

Bindu comprend une belle interface de chat à `http://localhost:5173`. Accédez au dossier `frontend` et exécutez `npm run dev` pour démarrer le serveur.

<p align="center">
  <img src="../assets/agent-ui.png" alt="Bindu Agent UI" width="640" style="border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);" />
</p>

---

<br/>

## 🌐 GetBindu.comLe [**GetBindu.com**](https://getbindu.com) est un registre public de tous les agents Bindu, les rendant découvrables et accessibles à l'écosystème plus large des agents.

### ✨ Inscription Automatique avec Cookiecutter

Lorsque vous créez un agent en utilisant le modèle cookiecutter, il inclut une action GitHub préconfigurée qui enregistre automatiquement votre agent dans le répertoire :

1. **Créez votre agent** en utilisant cookiecutter
2. **Poussez sur GitHub** - L'action GitHub se déclenche automatiquement
3. **Votre agent apparaît** dans le [GetBindu.com](https://getbindu.com)

> **Remarque** : Récupérez votre `BINDU_PAT_TOKEN` depuis [getbindu.com](https://getbindu.com) pour enregistrer votre agent.

### 📝 Inscription Manuelle

Le processus d'inscription manuelle est actuellement en développement.

---

<br/>

## 🌌 La Vision

```
a peek into the night sky
}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}}
{{            +             +                  +   @          {{
}}   |                *           o     +                .    }}
{{  -O-    o               .               .          +       {{
}}   |                    _,.-----.,_         o    |          }}
{{           +    *    .-'.         .'-.          -O-         {{
}}      *            .'.-'   .---.   `'.'.         |     *    }}
{{ .                /_.-'   /     \   .'-.\.                   {{
}}         ' -=*<  |-._.-  |   @   |   '-._|  >*=-    .     + }}
{{ -- )--           \`-.    \     /    .-'/                   }}
}}       *     +     `.'.    '---'    .'.'    +       o       }}
{{                  .  '-._         _.-'  .                   }}
}}         |               `~~~~~~~`       - --===D       @   }}
{{   o    -O-      *   .                  *        +          {{
}}         |                      +         .            +    }}
{{ jgs          .     @      o                        *       {{
}}       o                          *          o           .  }}
{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{{
```

_Chaque symbole est un agent — une étincelle d'intelligence. Le petit point est Bindu, le point d'origine dans l'Internet des Agents._

### Connexion NightSky (En Cours)

NightSky permet des essaims d'agents. Chaque Bindu est un point annotant les agents avec le langage partagé de A2A, AP2 et X402. Les agents peuvent être hébergés n'importe où—ordinateurs portables, nuages ou clusters—tout en parlant le même protocole, se faisant confiance par conception, et travaillant ensemble comme un esprit distribué unique.

> **💭 Un Objectif Sans Plan N'est Qu'un Souhait.**

---

<br/>

## 🛠️ Cadres d'Agent Supportés

Bindu est **indépendant du cadre** et testé avec :

- **AG2** (anciennement AutoGen)
- **Agno**
- **CrewAI**
- **LangChain**
- **LlamaIndex**
- **FastAgent**

Vous souhaitez une intégration avec votre cadre préféré ? [Let us know on Discord](https://discord.gg/3w5zuYUuwt) !

---

<br/>

## 🧪 Tests

Bindu maintient une **couverture de test de 70%+** (objectif : 80%+) :

```bash
uv run pytest -n auto --cov=bindu --cov-report=term-missing
uv run coverage report --skip-covered --fail-under=70
```

---

<br/>

## 🔧 Dépannage

<details>
<summary>Problèmes Courants</summary>

<br/>

| Problème | Solution |
|----------|----------|
| `Python 3.12 not found` | Installez Python 3.12+ et définissez dans PATH, ou utilisez `pyenv` |
| `bindu: command not found` | Activez l'environnement virtuel : `source .venv/bin/activate` || `Port 3773 already in use` | Définir `BINDU_PORT=4000` ou remplacer l'URL par `BINDU_DEPLOYMENT_URL=http://localhost:4000` |
| L'échec de pré-validation | Exécuter `pre-commit run --all-files` |
| Les tests échouent | Installer les dépendances de développement : `uv sync --dev` |
| `Permission denied` (macOS) | Exécuter `xattr -cr .` pour effacer les attributs étendus |

**Réinitialiser l'environnement :**
```bash
rm -rf .venv
uv venv --python 3.12.9
uv sync --dev
```

**Windows PowerShell :**
```bash
Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
```

</details>

---

<br/>

## 🤝 Contribuer

Nous accueillons les contributions ! Rejoignez-nous sur [Discord](https://discord.gg/3w5zuYUuwt). Choisissez le canal qui correspond le mieux à votre contribution.

```bash
git clone https://github.com/getbindu/Bindu.git
cd Bindu
uv venv --python 3.12.9
source .venv/bin/activate
uv sync --dev
pre-commit run --all-files
```

> 📖 [Contributing Guidelines](../.github/contributing.md)

---

<br/>

## 📜 Licence

Bindu est open-source sous la [Apache License 2.0](https://choosealicense.com/licenses/apache-2.0/).

---

<br/>

## 💬 Communauté

Nous 💛 les contributions ! Que vous corrigiez des bogues, amélioriez la documentation ou construisiez des démos, vos contributions rendent Bindu meilleur.

- 💬 [Join Discord](https://discord.gg/3w5zuYUuwt) pour les discussions et le support
- ⭐ [Star the repository](https://github.com/getbindu/Bindu) si vous le trouvez utile !

---

<br/>

## 👥 Modérateurs actifs

Nos modérateurs dédiés aident à maintenir une communauté accueillante et productive :

<table>
  <tr>
    <td align="center">
      <a href="https://github.com/raahulrahl">
        <img src="https://avatars.githubusercontent.com/u/157174139?v=4" width="100px;" alt="Raahul Dutta"/>
        <br />
        <sub><b>Raahul Dutta</b></sub>
      </a>
      <br />
    </td>
    <td align="center">
      <a href="https://github.com/Paraschamoli">
        <img src="https://avatars.githubusercontent.com/u/157124537?v=4" width="100px;" alt="Paras Chamoli"/>
        <br />
        <sub><b>Paras Chamoli</b></sub>
      </a>
      <br />
    </td>
    <td align="center">
      <a href="https://github.com/chandan-1427">
        <img src="https://avatars.githubusercontent.com/u/202320492?v=4" width="100px;" alt="Chandan"/>
        <br />
        <sub><b>Chandan</b></sub>
      </a>
      <br />
    </td>
    </tr>
</table>

> Vous voulez devenir modérateur ? Contactez-nous sur [Discord](https://discord.gg/3w5zuYUuwt) !

---

<br/>

## 🙏 Remerciements

Reconnaissant envers ces projets :

- [FastA2A](https://github.com/pydantic/fasta2a)
- [12 Factor Agents](https://github.com/humanlayer/12-factor-agents/blob/main/content/factor-11-trigger-from-anywhere.md)
- [A2A](https://github.com/a2aproject/A2A)
- [AP2](https://github.com/google-agentic-commerce/AP2)
- [Huggingface chatui](https://github.com/huggingface/chat-ui)
- [X402](https://github.com/coinbase/x402)
- [Bindu Logo](https://openmoji.org/library/emoji-1F33B/)
- [ASCII Space Art](https://www.asciiart.eu/space/other)

---

<br/>

## 🗺️ Feuille de route

- [ ] Support de transport GRPC- [ ] Augmenter la couverture des tests à 80 % (en cours)
- [ ] Support de bout en bout pour AP2
- [ ] Intégration de DSPy (en cours)
- [ ] Support de MLTS
- [ ] Support de X402 avec d'autres facilitateurs

> 💡 [Suggest features on Discord](https://discord.gg/3w5zuYUuwt)!

---

<br/>

## [We will make this agents bidufied and we do need your help.](https://www.notion.so/getbindu/305d3bb65095808eac2bf720368e9804?v=305d3bb6509580189941000cfad83ae7&source=copy_link)

---

<br/>

## 🎓 Ateliers

- [AI Native in Action: Agent Symphony](https://www.meetup.com/ai-native-Amsterdam && India/events/311066899/) - [Slides](https://docs.google.com/presentation/d/1SqGXI0Gv_KCWZ1Mw2SOx_kI0u-LLxwZq7lMSONdl8oQ/edit)

---

<br/>

## ⭐ Historique des étoiles

[![Star History Chart](https://api.star-history.com/svg?repos=getbindu/Bindu&type=Date)](https://www.star-history.com/#getbindu/Bindu&Date)

---

<p align="center">
  <strong>Construit avec 💛 par l'équipe d'Amsterdam && Inde </strong><br/>
  <em>Joyeux Bindu ! 🌻🚀✨</em>
</p>

<p align="center">
  <strong>De l'idée à l'Internet des Agents en 2 minutes.</strong><br/>
  <em>Votre agent. Votre cadre. Protocoles universels.</em>
</p>

<p align="center">
  <a href="https://github.com/getbindu/Bindu">⭐ Étoilez-nous sur GitHub</a> •
  <a href="https://discord.gg/3w5zuYUuwt">💬 Rejoignez Discord</a> •
  <a href="https://docs.getbindu.com">🌻 Lisez la documentation</a>
</p>

<br/>

<p align="center">
  <img src="../assets/sunflower-footer.jpeg" alt="Bindu" width="720" />
</p>

<p align="center">
  <em>"Nous croyons en la théorie du tournesol - se tenir debout ensemble, apportant espoir et lumière à l'Internet des Agents."</em>
</p>
