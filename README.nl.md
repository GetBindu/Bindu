<div align="center" id="top">
  <a href="https://getbindu.com">
    <picture>
      <img src="assets/bindu.png" alt="Bindu" width="300">
    </picture>
  </a>
</div>

<p align="center">
  <em>Identiteit, communicatie en betalingslaag voor AI-agents</em>
</p>

<p align="center">
  <a href="README.md">🇬🇧 English</a> •
  <a href="README.de.md">🇩🇪 Deutsch</a> •
  <a href="README.es.md">🇪🇸 Español</a> •
  <a href="README.fr.md">🇫🇷 Français</a> •
  <a href="README.hi.md">🇮🇳 हिंदी</a> •
  <a href="README.bn.md">🇮🇳 বাংলা</a> •
  <a href="README.zh.md">🇨🇳 中文</a> •
  <a href="README.nl.md">🇳🇱 Nederlands</a> •
  <a href="README.ta.md">🇮🇳 தமிழ்</a>
</p>

<p align="center">
  <a href="https://opensource.org/licenses/Apache-2.0"><img src="https://img.shields.io/badge/license-Apache%202.0-blue.svg" alt="License"></a>
  <a href="https://hits.sh/github.com/Saptha-me/Bindu.svg"><img src="https://hits.sh/github.com/Saptha-me/Bindu.svg" alt="Hits"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.12+-blue.svg" alt="Python Version"></a>
  <a href="https://pepy.tech/projects/bindu"><img src="https://static.pepy.tech/personalized-badge/bindu?period=total&units=INTERNATIONAL_SYSTEM&left_color=BLACK&right_color=GREEN&left_text=downloads" alt="PyPI Downloads"></a>
  <a href="https://pypi.org/project/bindu/"><img src="https://img.shields.io/pypi/v/bindu.svg" alt="PyPI version"></a>
  <a href="https://pypi.org/project/bindu/"><img src="https://img.shields.io/pypi/dm/bindu" alt="PyPI Downloads"></a>
  <a href="https://coveralls.io/github/Saptha-me/Bindu?branch=v0.3.18"><img src="https://coveralls.io/repos/github/Saptha-me/Bindu/badge.svg?branch=v0.3.18" alt="Coverage"></a>
  <a href="https://github.com/getbindu/Bindu/actions/workflows/release.yml"><img src="https://github.com/getbindu/Bindu/actions/workflows/release.yml/badge.svg" alt="Tests"></a>
  <a href="https://discord.gg/3w5zuYUuwt"><img src="https://img.shields.io/badge/Join%20Discord-7289DA?logo=discord&logoColor=white" alt="Discord"></a>
  <a href="https://github.com/getbindu/Bindu/graphs/contributors"><img src="https://img.shields.io/github/contributors/getbindu/Bindu" alt="Contributors"></a>
</p>

---

**Bindu** (uitspraak: _bin-doe_) is een operating layer voor AI-agents die identiteit, communicatie en betalingsmogelijkheden biedt. Het is een production-ready service die agents verbindt, authenticeert en orkestreert over gedistribueerde systemen met handige API's – gebruikmakend van open protocollen: **A2A**, **AP2**, en **X402**.

Gebouwd met een gedistribueerde architectuur (Task Manager, scheduler, storage), maakt Bindu het eenvoudig om snel te ontwikkelen en te integreren met elk AI-framework. Transformeer elk agent-framework in een volledig interoperabele service voor communicatie, samenwerking en commerce in het Internet of Agents.

<p align="center">
  <strong>🌟 <a href="https://bindus.directory">Registreer je agent</a> • 🌻 <a href="https://docs.getbindu.com">Documentatie</a> • 💬 <a href="https://discord.gg/3w5zuYUuwt">Discord Community</a></strong>
</p>

---

<br/>

## 🎥 Zie Bindu in actie

<div align="center">
  <a href="https://www.youtube.com/watch?v=qppafMuw_KI" target="_blank">
    <img src="https://img.youtube.com/vi/qppafMuw_KI/maxresdefault.jpg" alt="Bindu Demo" width="640" style="border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);" />
  </a>
</div>

## 📋 Vereisten

Voordat je Bindu installeert, zorg ervoor dat je hebt:

- **Python 3.12 of hoger** - [Download hier](https://www.python.org/downloads/)
- **UV Package Manager** - [Installatiegids](https://github.com/astral-sh/uv)

### Verifieer je setup

```bash
# Controleer Python versie
uv run python --version  # Moet 3.12 of hoger tonen

# Controleer UV installatie
uv --version
```

---

<br/>

## 📦 Installatie

<details>
<summary><b>Opmerking voor Windows-gebruikers (Git & GitHub Desktop)</b></summary>

Op sommige Windows-systemen wordt git mogelijk niet herkend in de Command Prompt, zelfs na installatie – vanwege PATH-configuratieproblemen.

Als je dit probleem tegenkomt, kun je _GitHub Desktop_ als alternatief gebruiken:

1. Installeer GitHub Desktop van <https://desktop.github.com/>
2. Log in met je GitHub-account
3. Kloon met de repository URL:
   <https://github.com/getbindu/Bindu.git>

GitHub Desktop stelt je in staat om repositories te klonen, branches te beheren, wijzigingen te committen en pull requests te openen zonder de command line.

</details>

```bash
# Installeer Bindu
uv add bindu

# Voor ontwikkeling (als je bijdraagt aan Bindu)
# Maak en activeer een virtuele omgeving
uv venv --python 3.12.9
source .venv/bin/activate  # Op macOS/Linux
# .venv\Scripts\activate  # Op Windows

uv sync --dev
```

<details>
<summary><b>Veelvoorkomende installatieproblemen</b> (Klik om uit te vouwen)</summary>

<br/>

| Probleem | Oplossing |
|-------|----------|
| `uv: command not found` | Herstart terminal na het installeren van UV. Gebruik PowerShell op Windows |
| `Python version not supported` | Installeer Python 3.12+ van [python.org](https://www.python.org/downloads/) |
| Virtuele omgeving activeert niet (Windows) | Gebruik PowerShell en voer `.venv\Scripts\activate` uit |
| `Microsoft Visual C++ required` | Download [Visual C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/) |
| `ModuleNotFoundError` | Activeer venv en voer `uv sync --dev` uit |

</details>

---

<br/>

## 🚀 Snel starten

### Optie 1: Gebruik Cookiecutter (Aanbevolen)

**Tijd tot eerste agent: ~2 minuten ⏱️**

```bash
# Installeer Cookiecutter
uv add cookiecutter

# Maak je Bindu agent
uvx cookiecutter https://github.com/getbindu/create-bindu-agent.git
```

## 🎥 Bouw production-ready agents in minuten

<div align="center">
  <a href="https://youtu.be/obY1bGOoWG8?si=uEeDb0XWrtYOQTL7" target="_blank">
    <img src="https://img.youtube.com/vi/obY1bGOoWG8/maxresdefault.jpg" alt="Bindu Demo" width="640" style="border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);" />
  </a>
</div>

Dat is alles! Je lokale agent is nu een live, veilige en vindbare service. [Meer informatie →](https://docs.getbindu.com/bindu/create-bindu-agent/overview)

> **💡 Pro tip:** Agents die met Cookiecutter zijn gemaakt, bevatten GitHub Actions die je agent automatisch registreren in de [Bindu Directory](https://bindus.directory) wanneer je naar je repository pusht. Geen handmatige registratie nodig!

### Optie 2: Handmatige setup

Maak je agent script `my_agent.py`:

```python
from bindu.penguin.bindufy import bindufy
from agno.agent import Agent
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.models.openai import OpenAIChat

from bindu.dspy.prompts import Prompt

# Definieer je agent
agent = Agent(
    instructions=Prompt("Je bent een onderzoeksassistent die informatie vindt en samenvat."),
    model=OpenAIChat(id="gpt-4o"),
    tools=[DuckDuckGoTools()],
)

# Configuratie
config = {
    "author": "your.email@example.com",
    "name": "research_agent",
    "description": "Een onderzoeksassistent agent",
    "deployment": {"url": "http://localhost:3773", "expose": True},
    "skills": ["skills/question-answering", "skills/pdf-processing"]
}

# Handler functie
def handler(messages: list[dict[str, str]]):
    """Verwerkt berichten en retourneert agent response.

    Args:
        messages: Lijst van bericht dictionaries met conversatiegeschiedenis

    Returns:
        Agent response resultaat
    """
    result = agent.run(input=messages)
    return result

# Bindu-fy
bindufy(config, handler)
```

![Sample Agent](assets/agno-simple.png)

Je agent draait nu live op `http://localhost:3773` en is klaar om te communiceren met andere agents.

---

### Optie 3: Minimale Echo Agent (Testen)

<details>
<summary><b>Bekijk minimaal voorbeeld</b> (Klik om uit te vouwen)</summary>

De kleinste werkende agent:

```python
from bindu.penguin.bindufy import bindufy

def handler(messages):
    return [{"role": "assistant", "content": messages[-1]["content"]}]

config = {
    "author": "your.email@example.com",
    "name": "echo_agent",
    "description": "Een basis echo agent voor snel testen.",
    "deployment": {"url": "http://localhost:3773", "expose": True},
    "skills": []
}

bindufy(config, handler)
```

**Uitvoeren en testen:**

```bash
# Start de agent
python examples/echo_agent.py
```

</details>

<details>
<summary><b>Test agent met curl</b> (Klik om uit te vouwen)</summary>

<br/>

Input:

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

Output:

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

Controleer task status

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

Output:

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

<br/>

## [Postgres Storage](https://docs.getbindu.com/bindu/learn/storage/overview)

Bindu gebruikt PostgreSQL als zijn persistente storage backend voor productie-implementaties. De storage layer is gebouwd met SQLAlchemy's async engine en gebruikt imperatieve mapping met protocol TypeDicts.

Dit is optioneel – standaard wordt InMemoryStorage gebruikt.

### 📊 Storage structuur

De storage layer gebruikt drie hoofdtabellen:

1. **tasks_table**: Slaat alle tasks op met JSONB history en artifacts
2. **contexts_table**: Onderhoudt context metadata en message history
3. **task_feedback_table**: Optionele feedback storage voor tasks

### ⚙️ Configuratie

<details>
<summary><b>Bekijk configuratievoorbeeld</b> (Klik om uit te vouwen)</summary>

Configureer PostgreSQL-verbinding in je environment of settings:
Geef de connection string op in de agent config.

```json
config = {
    "author": "your.email@example.com",
    "name": "research_agent",
    "description": "Een onderzoeksassistent agent",
    "deployment": {"url": "http://localhost:3773", "expose": True},
    "skills": ["skills/question-answering", "skills/pdf-processing"],
    "storage": {
        "type": "postgres",
        "database_url": "postgresql+asyncpg://bindu:bindu@localhost:5432/bindu",  # pragma: allowlist secret
        "run_migrations_on_startup": False,
    },
}
```

</details>

**💡 Task-First Pattern**: Storage ondersteunt Bindu's task-first benadering waarbij tasks kunnen worden voortgezet door berichten toe te voegen aan non-terminal tasks, wat incrementele verfijningen en multi-turn gesprekken mogelijk maakt.

---

<br/>

## [Redis Scheduler](https://docs.getbindu.com/bindu/learn/scheduler/overview)

Bindu gebruikt Redis als zijn gedistribueerde task scheduler om werk te coördineren over meerdere workers en processen. De scheduler gebruikt Redis lists met blocking operations voor efficiënte task distributie.

Dit is optioneel – standaard wordt InMemoryScheduler gebruikt.

### ⚙️ Configuratie

<details>
<summary><b>Bekijk configuratievoorbeeld</b> (Klik om uit te vouwen)</summary>

Configureer Redis-verbinding in je agent config:

```json
config = {
    "author": "your.email@example.com",
    "name": "research_agent",
    "description": "Een onderzoeksassistent agent",
    "deployment": {"url": "http://localhost:3773", "expose": True},
    "skills": ["skills/question-answering", "skills/pdf-processing"],
     "scheduler": {
        "type": "redis",
        "redis_url": "redis://localhost:6379/0",
    },
}
```

</details>

Alle operaties worden in Redis in de wachtrij geplaatst en verwerkt door beschikbare workers met behulp van een blocking pop-mechanisme, wat efficiënte distributie zonder polling overhead garandeert.

---

<br/>

## [Retry Mechanism](https://docs.getbindu.com/bindu/learn/retry/overview)

> Automatische retry logic met exponential backoff voor veerkrachtige Bindu agents

Bindu heeft een ingebouwd Tenacity-gebaseerd retry-mechanisme dat tijdelijke fouten in workers, storage, schedulers en API-aanroepen netjes afhandelt. Dit zorgt ervoor dat je agents veerkrachtig blijven in productieomgevingen.

### ⚙️ Standaardinstellingen

Als niet geconfigureerd, gebruikt Bindu deze standaardwaarden:

| Operatietype | Max pogingen | Min wacht | Max wacht |
| -------------- | ------------ | -------- | -------- |
| Worker         | 3            | 1.0s     | 10.0s    |
| Storage        | 5            | 0.5s     | 5.0s     |
| Scheduler      | 3            | 1.0s     | 8.0s     |
| API            | 4            | 1.0s     | 15.0s    |

---

<br/>

## [Sentry Integration](https://docs.getbindu.com/bindu/learn/sentry/overview)

> Real-time error tracking en performance monitoring voor Bindu agents

Sentry is een real-time error tracking en performance monitoring platform dat je helpt problemen in productie te identificeren, diagnosticeren en oplossen. Bindu heeft ingebouwde Sentry-integratie om uitgebreide observability voor je AI-agents te bieden.

### ⚙️ Configuratie

<details>
<summary><b>Bekijk configuratievoorbeeld</b> (Klik om uit te vouwen)</summary>

Configureer Sentry direct in je `bindufy()` config:

```python
config = {
    "author": "gaurikasethi88@gmail.com",
    "name": "echo_agent",
    "description": "Een basis echo agent voor snel testen.",
    "deployment": {"url": "http://localhost:3773", "expose": True},
    "skills": [],
    "storage": {
        "type": "postgres",
        "database_url": "postgresql+asyncpg://bindu:bindu@localhost:5432/bindu",  # pragma: allowlist secret
        "run_migrations_on_startup": False,
    },
    # Scheduler configuratie (optioneel)
    # Gebruik "memory" (standaard) voor single-process of "redis" voor gedistribueerde multi-process
    "scheduler": {
        "type": "redis",
        "redis_url": "redis://localhost:6379/0",
    },
    # Sentry error tracking (optioneel)
    # Configureer Sentry direct in code in plaats van environment variables
    "sentry": {
        "enabled": True,
        "dsn": "https://252c0197ddeafb621f91abdbb59fa819@o4510504294612992.ingest.de.sentry.io/4510504299069520",
        "environment": "development",
        "traces_sample_rate": 1.0,
        "profiles_sample_rate": 0.1,
    },
}

def handler(messages):
    # Je agent logic
    pass

bindufy(config, handler)
```

</details>

### 🚀 Aan de slag

1. **Maak een Sentry Account**: Meld je aan op [sentry.io](https://sentry.io)
2. **Verkrijg je DSN**: Kopieer uit project settings
3. **Configureer Bindu**: Voeg `sentry` config toe (zie hierboven)
4. **Voer je agent uit**: Sentry initialiseert automatisch

> 📚 Zie de [volledige Sentry documentatie](https://docs.getbindu.com/bindu/learn/sentry/overview) voor complete details.

---

<br/>

## [Skills System](https://docs.getbindu.com/bindu/skills/introduction/overview)

> Rijke capability advertisement voor intelligente agent orchestration

Het Bindu Skills System biedt rijke agent capability advertisement voor intelligente orchestration en agent discovery. Geïnspireerd door Claude's skills architectuur, stelt het agents in staat om gedetailleerde documentatie over hun mogelijkheden te verstrekken, zodat orchestrators geïnformeerde routing-beslissingen kunnen nemen.

### 💡 Wat zijn Skills?

In Bindu fungeren Skills als **rijke advertisement metadata** die orchestrators helpen:

- 🔍 **Ontdekken** van de juiste agent voor een taak
- 📖 **Begrijpen** van gedetailleerde mogelijkheden en beperkingen
- ✅ **Verifiëren** van vereisten vóór uitvoering
- 📊 **Schatten** van prestaties en resource-behoeften
- 🔗 **Koppelen** van meerdere agents intelligent

> **Opmerking**: Skills zijn geen uitvoerbare code—het is gestructureerde metadata die beschrijft wat je agent kan doen.

### 🔌 API Endpoints

**Lijst alle Skills**:

```bash
GET /agent/skills
```

**Verkrijg Skill details**:

```bash
GET /agent/skills/{skill_id}
```

**Verkrijg Skill documentatie**:

```bash
GET /agent/skills/{skill_id}/documentation
```

> 📚 Zie de [Skills documentatie](https://github.com/getbindu/Bindu/tree/main/examples/skills) voor volledige voorbeelden.

---

<br/>

## Negotiation

> Capability-based agent selectie voor intelligente orchestration

Bindu's negotiation systeem stelt orchestrators in staat om meerdere agents te bevragen en intelligent de beste agent voor een taak te selecteren op basis van skills, prestaties, belasting en kosten.

### 🔄 Hoe het werkt

1. **Orchestrator broadcast** assessment request naar meerdere agents
2. **Agents self-assess** capability met behulp van skill matching en load analysis
3. **Orchestrator rankt** responses met behulp van multi-factor scoring
4. **Beste agent wordt geselecteerd** en task wordt uitgevoerd

### 🔌 Assessment Endpoint

<details>
<summary><b>Bekijk API details</b> (Klik om uit te vouwen)</summary>

```bash
POST /agent/negotiation
```

**Request:**

```json
{
  "task_summary": "Extraheer tabellen uit PDF facturen",
  "task_details": "Verwerk factuur PDF's en extraheer gestructureerde data",
  "input_mime_types": ["application/pdf"],
  "output_mime_types": ["application/json"],
  "max_latency_ms": 5000,
  "max_cost_amount": "0.001",
  "min_score": 0.7,
  "weights": {
    "skill_match": 0.6,
    "io_compatibility": 0.2,
    "performance": 0.1,
    "load": 0.05,
    "cost": 0.05
  }
}
```

**Response:**

```json
{
  "accepted": true,
  "score": 0.89,
  "confidence": 0.95,
  "skill_matches": [
    {
      "skill_id": "pdf-processing-v1",
      "skill_name": "pdf-processing",
      "score": 0.92,
      "reasons": [
        "semantic similarity: 0.95",
        "tags: pdf, tables, extraction",
        "capabilities: text_extraction, table_extraction"
      ]
    }
  ],
  "matched_tags": ["pdf", "tables", "extraction"],
  "matched_capabilities": ["text_extraction", "table_extraction"],
  "latency_estimate_ms": 2000,
  "queue_depth": 2,
  "subscores": {
    "skill_match": 0.92,
    "io_compatibility": 1.0,
    "performance": 0.85,
    "load": 0.90,
    "cost": 1.0
  }
}
```

</details>

### 📊 Scoring Algoritme

Agents berekenen een confidence score op basis van meerdere factoren:

```python
score = (
    skill_match * 0.6 +        # Primair: skill matching
    io_compatibility * 0.2 +   # Input/output format ondersteuning
    performance * 0.1 +        # Snelheid en betrouwbaarheid
    load * 0.05 +              # Huidige beschikbaarheid
    cost * 0.05                # Prijsstelling
)
```

> 📚 Zie de [Negotiation documentatie](https://docs.getbindu.com/bindu/negotiation/overview) voor volledige details.

---

<br/>

## [DSPy Integratie](https://docs.getbindu.com/bindu/learn/dspy/overview)

> Geautomatiseerde prompt optimalisatie en continue verbetering door machine learning

Bindu's DSPy integratie biedt geautomatiseerde prompt optimalisatie en A/B testing voor AI-agents. In plaats van handmatig prompts aan te passen, gebruikt DSPy machine learning om prompts te optimaliseren op basis van echte gebruikersinteracties en feedback, waarbij een continue verbeteringscyclus wordt gecreëerd.

Optioneel - Vereist PostgreSQL storage en wordt ingeschakeld via agent config.

### ⚙️ Configuratie

<details>
<summary><b>Bekijk configuratievoorbeeld</b> (klik om uit te vouwen)</summary>

Schakel DSPy in je agent config in:

```python
config = {
    "author": "your.email@example.com",
    "name": "research_agent",
    "description": "Een onderzoeksassistent met continue verbetering",
    "deployment": {"url": "http://localhost:3773", "expose": True},
    "enable_dspy": True,  # ← Schakel DSPy optimalisatie in
}
```

Configureer via omgevingsvariabelen:

```bash
# Vereist: PostgreSQL verbinding
STORAGE_TYPE=postgres
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/bindu

# OpenRouter API key voor training
OPENROUTER_API_KEY=your_openrouter_api_key

# Zie examples/.env.example voor volledige configuratie
```

</details>

Wanneer ingeschakeld, worden systeemprompts geladen vanuit de database met automatische A/B testing, wat geleidelijke uitrol van geoptimaliseerde prompts mogelijk maakt op basis van gebruikersfeedback.

> 📚 Voor volledige DSPy documentatie, training en canary deployment, zie [bindu/dspy/README.md](bindu/dspy/README.md)

---

<br/>

## 📬 Push Notifications

Bindu ondersteunt **real-time webhook notifications** voor langlopende taken, volgens de [A2A Protocol specification](https://a2a-protocol.org/latest/specification/). Dit stelt clients in staat om push notifications te ontvangen over task state changes en artifact generation zonder polling.

### Snel starten

1. **Start webhook receiver:** `python examples/webhook_client_example.py`
2. **Configureer agent** in `examples/echo_agent_with_webhooks.py`:

   ```python
   manifest = {
       "capabilities": {"push_notifications": True},
       "global_webhook_url": "http://localhost:8000/webhooks/task-updates",
       "global_webhook_token": "secret_abc123",
   }
   ```

3. **Voer agent uit:** `python examples/echo_agent_with_webhooks.py`
4. **Verstuur tasks** - webhook notifications komen automatisch binnen

📖 **[Volledige documentatie](docs/long-running-task-notifications.md)** - Gedetailleerde gids met architectuur, beveiliging, voorbeelden en probleemoplossing.

---

<br/>

## 🎨 Chat UI

Bindu bevat een mooie chat interface op `http://localhost:3773/docs`

<p align="center">
  <img src="assets/agent-ui.png" alt="Bindu Agent UI" width="640" style="border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);" />
</p>

---

<br/>

## 🌐 Bindu Directory

De [**Bindu Directory**](https://bindus.directory) is een openbaar register van alle Bindu agents, waardoor ze vindbaar en toegankelijk zijn voor het bredere agent ecosysteem.

### ✨ Automatische registratie met Cookiecutter

Wanneer je een agent maakt met de cookiecutter template, bevat deze een vooraf geconfigureerde GitHub Action die je agent automatisch registreert in de directory:

1. **Maak je agent** met cookiecutter
2. **Push naar GitHub** - De GitHub Action triggert automatisch
3. **Je agent verschijnt** in de [Bindu Directory](https://bindus.directory)

> **🔑 Opmerking**: Je moet de BINDU_PAT_TOKEN verzamelen van bindus.directory en deze gebruiken om je agent te registreren.

### 📝 Handmatige registratie

We werken aan een handmatig registratieproces.

---

<br/>

## 🌌 De Visie

```
een blik op de nachtelijke hemel
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

_Elk symbool is een agent – een vonk van intelligentie. Het kleine puntje is Bindu, het oorsprongspunt in het Internet of Agents._

### NightSky Verbinding [In ontwikkeling]

NightSky maakt zwermen van agents mogelijk. Elke Bindu is een punt dat agents annoteert met de gedeelde taal van A2A, AP2 en X402. Agents kunnen overal worden gehost – laptops, clouds of clusters – maar spreken hetzelfde protocol, vertrouwen elkaar by design en werken samen als één gedistribueerde geest.

> **💭 Een doel zonder plan is slechts een wens.**

---

<br/>

## 🛠️ Ondersteunde Agent Frameworks

Bindu is **framework-agnostisch** en getest met:

- **Agno**
- **CrewAI**
- **LangChain**
- **LlamaIndex**
- **FastAgent**

Wil je integratie met je favoriete framework? [Laat het ons weten op Discord](https://discord.gg/3w5zuYUuwt)!

---

<br/>

## 🧪 Testen

Bindu handhaaft **70%+ test coverage**:

```bash
pytest -n auto --cov=bindu --cov-report= && coverage report --skip-covered --fail-under=70
```

---

<br/>

## Probleemoplossing

<details>
<summary>Veelvoorkomende problemen</summary>

<br/>

| Probleem | Oplossing |
|---------|----------|
| `Python 3.12 not found` | Installeer Python 3.12+ en stel in PATH in, of gebruik `pyenv` |
| `bindu: command not found` | Activeer virtuele omgeving: `source .venv/bin/activate` |
| `Port 3773 already in use` | Wijzig poort in config: `"url": "http://localhost:4000"` |
| Pre-commit faalt | Voer `pre-commit run --all-files` uit |
| Tests falen | Installeer dev dependencies: `uv sync --dev` |
| `Permission denied` (macOS) | Voer `xattr -cr .` uit om extended attributes te wissen |

**Reset omgeving:**

```bash
rm -rf .venv
uv venv --python 3.12.9
uv sync --dev
```

**Windows PowerShell:**

```bash
Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
```

</details>

<br/>

## 🤝 Bijdragen

We verwelkomen bijdragen! Sluit je aan bij ons op [Discord](https://discord.gg/3w5zuYUuwt). Kies het kanaal dat het beste past bij je bijdrage.

```bash
git clone https://github.com/getbindu/Bindu.git
cd Bindu
uv venv --python 3.12.9
source .venv/bin/activate
uv sync --dev
pre-commit run --all-files
```

> 📖 [Bijdrage richtlijnen](.github/contributing.md)

---

<br/>

## 📜 Licentie

Bindu is open-source onder de [Apache License 2.0](https://choosealicense.com/licenses/apache-2.0/).

---

<br/>

## 💬 Community

We 💛 bijdragen! Of je nu bugs fixt, documentatie verbetert of demo's bouwt – jouw bijdragen maken Bindu beter.

- 💬 [Sluit je aan bij Discord](https://discord.gg/3w5zuYUuwt) voor discussies en ondersteuning
- ⭐ [Geef de repository een ster](https://github.com/getbindu/Bindu) als je het nuttig vindt!

---

<br/>

## 👥 Actieve Moderators

Onze toegewijde moderators helpen een gastvrije en productieve community te onderhouden:

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
      <a href="https://github.com/Gaurika-Sethi">
        <img src="https://avatars.githubusercontent.com/u/178935569?v=4" width="100px;" alt="Gaurika Sethi"/>
        <br />
        <sub><b>Gaurika Sethi</b></sub>
      </a>
      <br />
    </td>
    <td align="center">
      <a href="https://github.com/Avngrstark62">
        <img src="https://avatars.githubusercontent.com/u/133889196?v=4" width="100px;" alt="Abhijeet Singh Thakur"/>
        <br />
        <sub><b>Abhijeet Singh Thakur</b></sub>
      </a>
      <br />
    </td>
  </tr>
</table>

> Wil je moderator worden? Neem contact op via [Discord](https://discord.gg/3w5zuYUuwt)!

---

<br/>

## 🙏 Dankbetuigingen

Dankbaar aan deze projecten:

- [FastA2A](https://github.com/pydantic/fasta2a)
- [12 Factor Agents](https://github.com/humanlayer/12-factor-agents/blob/main/content/factor-11-trigger-from-anywhere.md)
- [A2A](https://github.com/a2aproject/A2A)
- [AP2](https://github.com/google-agentic-commerce/AP2)
- [X402](https://github.com/coinbase/x402)
- [Bindu Logo](https://openmoji.org/library/emoji-1F33B/)
- [ASCII Space Art](https://www.asciiart.eu/space/other)

---

<br/>

## 🗺️ Roadmap

- [ ] GRPC transport ondersteuning
- [x] Sentry error tracking
- [x] Ag-UI integratie
- [x] Retry mechanisme
- [ ] Test coverage verhogen naar 80% - In ontwikkeling
- [x] Redis scheduler implementatie
- [x] Postgres database voor memory storage
- [x] Negotiation ondersteuning
- [ ] AP2 end-to-end ondersteuning
- [ ] DSPy integratie - In ontwikkeling
- [ ] MLTS ondersteuning
- [ ] X402 ondersteuning met andere facilitators

> 💡 [Stel features voor op Discord](https://discord.gg/3w5zuYUuwt)!

---

<br/>

## 🎓 Workshops

- [AI Native in Action: Agent Symphony](https://www.meetup.com/ai-native-amsterdam/events/311066899/) - [Slides](https://docs.google.com/presentation/d/1SqGXI0Gv_KCWZ1Mw2SOx_kI0u-LLxwZq7lMSONdl8oQ/edit)

---

<br/>

## ⭐ Star Geschiedenis

[![Star History Chart](https://api.star-history.com/svg?repos=getbindu/Bindu&type=Date)](https://www.star-history.com/#getbindu/Bindu&Date)

---

<p align="center">
  <strong>Gebouwd met 💛 door het team uit Amsterdam</strong><br/>
  <em>Happy Bindu! 🌻🚀✨</em>
</p>

<p align="center">
  <strong>Van idee tot Internet of Agents in 2 minuten.</strong><br/>
  <em>Jouw agent. Jouw framework. Universele protocollen.</em>
</p>

<p align="center">
  <a href="https://github.com/getbindu/Bindu">⭐ Geef ons een ster op GitHub</a> •
  <a href="https://discord.gg/3w5zuYUuwt">💬 Sluit je aan bij Discord</a> •
  <a href="https://docs.getbindu.com">🌻 Lees de Docs</a>
</p>
