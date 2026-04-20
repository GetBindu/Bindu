<div align="center" id="top">
  <a href="https://getbindu.com">
    <picture>
      <img src="assets/bindu.png" alt="Bindu" width="300">
    </picture>
  </a>
</div>

<p align="center">
  <em>La couche d'identité, de communication et de paiements pour les agents IA</em>
</p>

<p align="center">
  <a href="README.md">🇬🇧 Anglais</a> •
  <a href="README.de.md">🇩🇪 Allemand</a> •
  <a href="README.es.md">🇪🇸 Espagnol</a> •
  <a href="README.fr.md">🇫🇷 Français</a> •
  <a href="README.hi.md">🇮🇳 हिंदी</a> •
  <a href="README.bn.md">🇮🇳 বাংলা</a> •
  <a href="README.zh.md">🇨🇳 中文</a> •
  <a href="README.nl.md">🇳🇱 Néerlandais</a> •
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
  <img src="assets/sunflower-mountains.jpeg" alt="Bindu — The Internet of Agents" width="720" />
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

![Sample Agent](assets/agno-simple.png)

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
| **Authentification** | Accès API sécurisé avec Ory Hydra OAuth2 (optionnel pour le développement) | [Guide →](docs/AUTHENTICATION.md) |
| 💰 **Intégration de Paiement (X402)** | Accepter les paiements USDC sur la blockchain Base avant d'exécuter des méthodes protégées | [Guide →](docs/PAYMENT.md) |
| 💾 **Stockage PostgreSQL** | Stockage persistant pour les déploiements en production (optionnel - InMemoryStorage par défaut) | [Guide →](docs/STORAGE.md) |
| 📋 **Planificateur Redis** | Planification de tâches distribuées pour des déploiements multi-travailleurs (optionnel - InMemoryScheduler par défaut) | [Guide →](docs/SCHEDULER.md) |
| 🎯 **Système de Compétences** | Capacités réutilisables que les agents annoncent et exécutent pour un routage intelligent des tâches | [Guide →](docs/SKILLS.md) |
| 🤝 **Négociation d'Agent** | Sélection d'agent basée sur les capacités pour une orchestration intelligente | [Guide →](docs/NEGOTIATION.md) |
| 🌐 **Tunneling** | Exposer des agents locaux à Internet pour des tests (**développement local uniquement, pas pour la production**) | [Guide →](docs/TUNNELING.md) |
| 📬 **Notifications Push** | Notifications webhook en temps réel pour les mises à jour de tâches - aucun sondage requis | [Guide →](docs/NOTIFICATIONS.md) |
| 📊 **Observabilité & Surveillance** | Suivre les performances et déboguer les problèmes avec OpenTelemetry et Sentry | [Guide →](docs/OBSERVABILITY.md) |
| 🔄 **Mécanisme de Réessai** | Réessai automatique avec un backoff exponentiel pour des agents résilients | [Guide →](docs.getbindu.com/bindu/learn/retry/overview) |
| 🔑 **Identifiants Décentralisés (DIDs)** | Identité cryptographique pour des interactions d'agent vérifiables et sécurisées et intégration de paiement | [Guide →](docs/DID.md) |
| 🏥 **Vérification de Santé & Métriques** | Surveiller la santé et les performances des agents avec des points de terminaison intégrés | [Guide →](docs/HEALTH_METRICS.md) |

---

<br/>

## 🎨 Interface de Chat

Bindu comprend une belle interface de chat à `http://localhost:5173`. Accédez au dossier `frontend` et exécutez `npm run dev` pour démarrer le serveur.

<p align="center">
  <img src="assets/agent-ui.png" alt="Bindu Agent UI" width="640" style="border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);" />
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

> 📖 [Contributing Guidelines](.github/contributing.md)

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
  <img src="assets/sunflower-footer.jpeg" alt="Bindu" width="720" />
</p>

<p align="center">
  <em>"Nous croyons en la théorie du tournesol - se tenir debout ensemble, apportant espoir et lumière à l'Internet des Agents."</em>
</p>
