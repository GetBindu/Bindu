<div align="center" id="top">
  <a href="https://getbindu.com">
    <picture>
      <img src="assets/bindu.png" alt="Bindu" width="300">
    </picture>
  </a>
</div>

<p align="center">
  <em>De identiteit, communicatie & betalingslaag voor AI-agenten</em>
</p>

<p align="center">
  <a href="README.md">🇬🇧 Engels</a> •
  <a href="README.de.md">🇩🇪 Duits</a> •
  <a href="README.es.md">🇪🇸 Spaans</a> •
  <a href="README.fr.md">🇫🇷 Frans</a> •
  <a href="README.hi.md">🇮🇳 Hindi</a> •
  <a href="README.bn.md">🇮🇳 Bengaals</a> •
  <a href="README.zh.md">🇨🇳 Chinees</a> •
  <a href="README.nl.md">🇳🇱 Nederlands</a> •
  <a href="README.ta.md">🇮🇳 Tamil</a>
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
  <img src="assets/sunflower-mountains.jpeg" alt="Bindu — The Internet of Agents" width="720" />
</p>

<p align="center">
  <em>"Zoals zonnebloemen die naar het licht draaien, werken agenten samen in zwermen - elk onafhankelijk, maar samen creëren ze iets groters."</em>
</p>

<br/>

<div align="center">
  <h3>Onboard je agent in één regel</h3>
</div>

<div align="center">
  <pre><code>curl -fsSL https://getbindu.com/install-bindu.sh | bash</code></pre>
</div>

---

**Bindu** (uitgesproken als _binduu_) is een operationele laag voor AI-agenten die identiteit, communicatie en betalingsmogelijkheden biedt. Het levert een productieklare service met een handige API om agenten te verbinden, te authenticeren en te orkestreren over gedistribueerde systemen met behulp van open protocollen: **A2A**, **AP2** en **X402**.Gebouwd met een gedistribueerde architectuur (Taakbeheerder, planner, opslag), maakt Bindu het snel om te ontwikkelen en eenvoudig om te integreren met elk AI-framework. Transformeer elk agentframework in een volledig interoperabele service voor communicatie, samenwerking en handel in het Internet van Agents.

<p align="center">
  <strong>🌟 <a href="https://getbindu.com">Registreer uw agent</a> • 🌻 <a href="https://docs.getbindu.com">Documentatie</a> • 💬 <a href="https://discord.gg/3w5zuYUuwt">Discord Gemeenschap</a></strong>
</p>


---

<br/>

## 🎥 Bekijk Bindu in Actie

<div align="center">
  <a href="https://www.youtube.com/watch?v=qppafMuw_KI" target="_blank">
    <img src="https://img.youtube.com/vi/qppafMuw_KI/maxresdefault.jpg" alt="Bindu Demo" width="640" style="border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);" />
  </a>
</div>

<br/>

## 📋 Vereisten

Voordat u Bindu installeert, zorg ervoor dat u heeft:

- **Python 3.12 of hoger** - [Download here](https://www.python.org/downloads/)
- **UV pakketbeheerder** - [Installation guide](https://github.com/astral-sh/uv)
- **API-sleutel vereist**: Stel `OPENROUTER_API_KEY` of `OPENAI_API_KEY` in uw omgevingsvariabelen in. Gratis OpenRouter-modellen zijn beschikbaar voor testen.


### Verifieer uw Setup

```bash
# Check Python version
uv run python --version  # Should show 3.12 or higher

# Check UV installation
uv --version
```

---

<br/>

## 📦 Installatie
<details>
<summary><b>Gebruikersopmerking (Git & GitHub Desktop)</b></summary>

Op sommige Windows-systemen wordt git mogelijk niet herkend in de Opdrachtprompt, zelfs na installatie, vanwege problemen met de PATH-configuratie.

Als u dit probleem ondervindt, kunt u *GitHub Desktop* als alternatief gebruiken:

1. Installeer GitHub Desktop van https://desktop.github.com/
2. Meld u aan met uw GitHub-account
3. Clone de repository met de repository-URL:
   https://github.com/getbindu/Bindu.git

GitHub Desktop stelt u in staat om te clonen, takken te beheren, wijzigingen vast te leggen en pull-verzoeken te openen zonder de opdrachtregel te gebruiken.

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
<summary><b>Veelvoorkomende Installatieproblemen</b> (klik om uit te vouwen)</summary>

<br/>

| Probleem | Oplossing |
|-------|----------|| `uv: command not found` | Herstart je terminal na het installeren van UV. Gebruik PowerShell op Windows |
| `Python version not supported` | Installeer Python 3.12+ van [python.org](https://www.python.org/downloads/) |
| Virtuele omgeving wordt niet geactiveerd (Windows) | Gebruik PowerShell en voer `.venv\Scripts\activate` uit |
| `Microsoft Visual C++ required` | Download [Visual C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/) |
| `ModuleNotFoundError` | Activeer venv en voer `uv sync --dev` uit |

</details>

---

<br/>

## 🚀 Snelle Start

### Optie 1: Gebruik Cookiecutter (Aanbevolen)

**Tijd tot de eerste agent: ~2 minuten ⏱️**

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

Je lokale agent wordt een live, veilige, vindbare service. [Learn more →](https://docs.getbindu.com/bindu/create-bindu-agent/overview)

> **💡 Pro Tip:** Agents die met cookiecutter zijn gemaakt, bevatten GitHub Actions die je agent automatisch registreren in de [GetBindu.com](https://getbindu.com) wanneer je naar je repository pusht.

### Optie 2: Handmatige Setup

Maak je agent-script `my_agent.py`:

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

![Sample Agent](assets/agno-simple.png)

Je agent is nu live op de URL die is geconfigureerd in `deployment.url`.

Stel een aangepaste poort in zonder codewijzigingen:

```bash
# Linux/macOS
export BINDU_PORT=4000

# Windows PowerShell
$env:BINDU_PORT="4000"
```

Bestaande voorbeelden die `http://localhost:3773` gebruiken, worden automatisch overschreven wanneer `BINDU_PORT` is ingesteld.

### Optie 3: Zero-Config Lokale Agent

Probeer Bindu zonder Postgres, Redis of andere cloudservices in te stellen. Draait volledig lokaal met behulp van in-memory opslag en planner.

```bash
python examples/beginner_zero_config_agent.py
```

### Optie 4: Minimale Echo Agent (Testen)

<details>
<summary><b>Bekijk minimaal voorbeeld</b> (klik om uit te vouwen)</summary>

Kleinste mogelijke werkende agent:

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

**Voer de agent uit:**

```bash
# Start the agent
python examples/echo_agent.py
```

</details>

<details>
<summary><b>Test de agent met curl</b> (klik om uit te vouwen)</summary>

<br/>

Invoer:
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

Uitvoer:
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

Controleer de status van de taak
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

Uitvoer:
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

 

## 🚀 Kernfuncties
| Kenmerk | Beschrijving | Documentatie |
| :--- | :--- | :--- |
| **Authenticatie** | Veilige API-toegang met Ory Hydra OAuth2 (optioneel voor ontwikkeling) | [Guide →](docs/AUTHENTICATION.md) |
| 💰 **Betalingsintegratie (X402)** | Accepteer USDC-betalingen op de Base-blockchain voordat beschermde methoden worden uitgevoerd | [Guide →](docs/PAYMENT.md) |
| 💾 **PostgreSQL Opslag** | Persistente opslag voor productie-implementaties (optioneel - InMemoryStorage standaard) | [Guide →](docs/STORAGE.md) |
| 📋 **Redis Scheduler** | Gedistribueerde taakplanning voor multi-werknemersimplementaties (optioneel - InMemoryScheduler standaard) | [Guide →](docs/SCHEDULER.md) |
| 🎯 **Vaardigheden Systeem** | Herbruikbare mogelijkheden die agenten adverteren en uitvoeren voor intelligente taakroutering | [Guide →](docs/SKILLS.md) |
| 🤝 **Agentonderhandeling** | Capaciteitsgebaseerde agentselectie voor intelligente orkestratie | [Guide →](docs/NEGOTIATION.md) |
| 🌐 **Tunneling** | Lokale agenten blootstellen aan het internet voor testen (**alleen lokale ontwikkeling, niet voor productie**) | [Guide →](docs/TUNNELING.md) |
| 📬 **Pushmeldingen** | Real-time webhookmeldingen voor taakupdates - geen polling vereist | [Guide →](docs/NOTIFICATIONS.md) |
| 📊 **Observability & Monitoring** | Volg prestaties en debugproblemen met OpenTelemetry en Sentry | [Guide →](docs/OBSERVABILITY.md) |
| 🔄 **Retry Mechanisme** | Automatische herhaling met exponentiële backoff voor veerkrachtige agenten | [Guide →](docs.getbindu.com/bindu/learn/retry/overview) |
| 🔑 **Gedecentraliseerde Identifiers (DIDs)** | Cryptografische identiteit voor verifieerbare, veilige agentinteracties en betalingsintegratie | [Guide →](docs/DID.md) |
| 🏥 **Gezondheidscontrole & Statistieken** | Monitor agentgezondheid en prestaties met ingebouwde eindpunten | [Guide →](docs/HEALTH_METRICS.md) |

---

<br/>

## 🎨 Chat UI

Bindu bevat een mooie chatinterface op `http://localhost:5173`. Navigeer naar de `frontend` map en voer `npm run dev` uit om de server te starten.

<p align="center">
  <img src="assets/agent-ui.png" alt="Bindu Agent UI" width="640" style="border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);" />
</p>

---

<br/>

## 🌐 GetBindu.comDe [**GetBindu.com**](https://getbindu.com) is een openbaar register van alle Bindu-agenten, waardoor ze ontdekbaar en toegankelijk zijn voor het bredere agentecosysteem.

### ✨ Automatische Registratie met Cookiecutter

Wanneer je een agent maakt met de cookiecutter-sjabloon, bevat deze een vooraf geconfigureerde GitHub Actie die je agent automatisch registreert in de directory:

1. **Maak je agent** met cookiecutter
2. **Push naar GitHub** - De GitHub Actie wordt automatisch geactiveerd
3. **Je agent verschijnt** in de [GetBindu.com](https://getbindu.com)

> **Opmerking**: Verzamel je `BINDU_PAT_TOKEN` van [getbindu.com](https://getbindu.com) om je agent te registreren.

### 📝 Handmatige Registratie

Het handmatige registratieproces is momenteel in ontwikkeling.

---

<br/>

## 🌌 De Visie

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

_Each symbol is an agent — a spark of intelligence. The tiny dot is Bindu, the origin point in the Internet of Agents._

### NightSky Verbinding (In Behandeling)

NightSky maakt zwermen van agenten mogelijk. Elke Bindu is een stip die agenten annotaties geeft met de gedeelde taal van A2A, AP2 en X402. Agenten kunnen overal worden gehost—laptops, clouds of clusters—maar spreken dezelfde protocol, vertrouwen elkaar per ontwerp en werken samen als een enkele, gedistribueerde geest.

> **💭 Een Doel Zonder Plan Is Gewoon Een Wens.**

---

<br/>

## 🛠️ Ondersteunde Agent Frameworks

Bindu is **framework-onafhankelijk** en getest met:

- **AG2** (voorheen AutoGen)
- **Agno**
- **CrewAI**
- **LangChain**
- **LlamaIndex**
- **FastAgent**

Wil je integratie met je favoriete framework? [Let us know on Discord](https://discord.gg/3w5zuYUuwt)!

---

<br/>

## 🧪 Testen

Bindu onderhoudt **70%+ testdekking** (doel: 80%+):

```bash
uv run pytest -n auto --cov=bindu --cov-report=term-missing
uv run coverage report --skip-covered --fail-under=70
```

---

<br/>

## 🔧 Probleemoplossing

<details>
<summary>Veelvoorkomende Problemen</summary>

<br/>

| Probleem | Oplossing |
|----------|-----------|
| `Python 3.12 not found` | Installeer Python 3.12+ en stel in PATH in, of gebruik `pyenv` |
| `bindu: command not found` | Activeer virtuele omgeving: `source .venv/bin/activate` || `Port 3773 already in use` | Stel `BINDU_PORT=4000` in of overschrijf URL met `BINDU_DEPLOYMENT_URL=http://localhost:4000` |
| Pre-commit mislukt | Voer `pre-commit run --all-files` uit |
| Tests mislukt | Installeer dev-afhankelijkheden: `uv sync --dev` |
| `Permission denied` (macOS) | Voer `xattr -cr .` uit om uitgebreide attributen te wissen |

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

---

<br/>

## 🤝 Bijdragen

We verwelkomen bijdragen! Sluit je bij ons aan op [Discord](https://discord.gg/3w5zuYUuwt). Kies het kanaal dat het beste past bij jouw bijdrage.

```bash
git clone https://github.com/getbindu/Bindu.git
cd Bindu
uv venv --python 3.12.9
source .venv/bin/activate
uv sync --dev
pre-commit run --all-files
```

> 📖 [Contributing Guidelines](.github/contributing.md)

---

<br/>

## 📜 Licentie

Bindu is open-source onder de [Apache License 2.0](https://choosealicense.com/licenses/apache-2.0/).

---

<br/>

## 💬 Gemeenschap

We 💛 bijdragen! Of je nu bugs oplost, documentatie verbetert of demo's bouwt—jouw bijdragen maken Bindu beter.

- 💬 [Join Discord](https://discord.gg/3w5zuYUuwt) voor discussies en ondersteuning
- ⭐ [Star the repository](https://github.com/getbindu/Bindu) als je het nuttig vindt!

---

<br/>

## 👥 Actieve Moderators

Onze toegewijde moderators helpen een gastvrije en productieve gemeenschap te behouden:

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

> Wil je moderator worden? Neem contact op via [Discord](https://discord.gg/3w5zuYUuwt)!

---

<br/>

## 🙏 Erkenningen

Dankbaar voor deze projecten:

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

## 🗺️ Roadmap

- [ ] GRPC transportondersteuning- [ ] Verhoog de testdekking tot 80% (in uitvoering)
- [ ] AP2 end-to-end ondersteuning
- [ ] DSPy integratie (in uitvoering)
- [ ] MLTS ondersteuning
- [ ] X402 ondersteuning met andere facilitators

> 💡 [Suggest features on Discord](https://discord.gg/3w5zuYUuwt)!

---

<br/>

## [We will make this agents bidufied and we do need your help.](https://www.notion.so/getbindu/305d3bb65095808eac2bf720368e9804?v=305d3bb6509580189941000cfad83ae7&source=copy_link)

---

<br/>

## 🎓 Workshops

- [AI Native in Action: Agent Symphony](https://www.meetup.com/ai-native-Amsterdam && India/events/311066899/) - [Slides](https://docs.google.com/presentation/d/1SqGXI0Gv_KCWZ1Mw2SOx_kI0u-LLxwZq7lMSONdl8oQ/edit)

---

<br/>

## ⭐ Sterren Geschiedenis

[![Star History Chart](https://api.star-history.com/svg?repos=getbindu/Bindu&type=Date)](https://www.star-history.com/#getbindu/Bindu&Date)

---

<p align="center">
  <strong>Gebouwd met 💛 door het team uit Amsterdam && India </strong><br/>
  <em>Gelukkige Bindu! 🌻🚀✨</em>
</p>

<p align="center">
  <strong>Van idee naar Internet of Agents in 2 minuten.</strong><br/>
  <em>Jouw agent. Jouw framework. Universele protocollen.</em>
</p>

<p align="center">
  <a href="https://github.com/getbindu/Bindu">⭐ Geef ons een ster op GitHub</a> •
  <a href="https://discord.gg/3w5zuYUuwt">💬 Sluit je aan bij Discord</a> •
  <a href="https://docs.getbindu.com">🌻 Lees de Docs</a>
</p>

<br/>

<p align="center">
  <img src="assets/sunflower-footer.jpeg" alt="Bindu" width="720" />
</p>

<p align="center">
  <em>"We geloven in de zonnebloemtheorie - samen rechtop staan, hoop en licht brengen naar het Internet of Agents."</em>
</p>
