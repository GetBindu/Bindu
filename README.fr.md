<div align="center" id="top">
  <a href="https://getbindu.com">
    <picture>
      <img src="assets/bindu.png" alt="Bindu" width="300">
    </picture>
  </a>
</div>

<p align="center">
  <em>Couche d'identité, de communication et de paiement pour les agents IA</em>
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

**Bindu** (prononciation : _bin-dou_) est une couche opérationnelle pour les agents IA qui fournit des capacités d'identité, de communication et de paiement. C'est un service prêt pour la production qui connecte, authentifie et orchestre les agents à travers des systèmes distribués avec des API pratiques – en utilisant des protocoles ouverts : **A2A**, **AP2**, et **X402**.

Construit avec une architecture distribuée (Task Manager, scheduler, storage), Bindu facilite le développement rapide et l'intégration avec n'importe quel framework IA. Transformez n'importe quel framework d'agents en un service entièrement interopérable pour la communication, la collaboration et le commerce dans l'Internet of Agents.

<p align="center">
  <strong>🌟 <a href="https://bindus.directory">Enregistrez votre agent</a> • 🌻 <a href="https://docs.getbindu.com">Documentation</a> • 💬 <a href="https://discord.gg/3w5zuYUuwt">Communauté Discord</a></strong>
</p>

---

<br/>

## 🎥 Voir Bindu en action

<div align="center">
  <a href="https://www.youtube.com/watch?v=qppafMuw_KI" target="_blank">
    <img src="https://img.youtube.com/vi/qppafMuw_KI/maxresdefault.jpg" alt="Bindu Demo" width="640" style="border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);" />
  </a>
</div>

## 📋 Prérequis

Avant d'installer Bindu, assurez-vous d'avoir :

- **Python 3.12 ou supérieur** - [Télécharger ici](https://www.python.org/downloads/)
- **UV Package Manager** - [Guide d'installation](https://github.com/astral-sh/uv)
- **Clé API requise** : définissez `OPENROUTER_API_KEY` ou `OPENAI_API_KEY` dans vos variables d'environnement. Des modèles OpenRouter gratuits sont disponibles pour les tests.

### Vérifiez votre configuration

```bash
# Vérifier la version de Python
uv run python --version  # Doit afficher 3.12 ou supérieur

# Vérifier l'installation d'UV
uv --version
```

---

<br/>

## 📦 Installation

<details>
<summary><b>Note pour les utilisateurs Windows (Git & GitHub Desktop)</b></summary>

Sur certains systèmes Windows, git peut ne pas être reconnu dans l'invite de commande même après l'installation – en raison de problèmes de configuration PATH.

Si vous rencontrez ce problème, vous pouvez utiliser *GitHub Desktop* comme alternative :

1. Installez GitHub Desktop depuis https://desktop.github.com/
2. Connectez-vous avec votre compte GitHub
3. Clonez en utilisant l'URL du dépôt :
   https://github.com/getbindu/Bindu.git

GitHub Desktop vous permet de cloner des dépôts, gérer des branches, valider des modifications et ouvrir des pull requests sans la ligne de commande.

</details>

```bash
# Installer Bindu
uv add bindu

# Pour le développement (si vous contribuez à Bindu)
# Créer et activer un environnement virtuel
uv venv --python 3.12.9
source .venv/bin/activate  # Sur macOS/Linux
# .venv\Scripts\activate  # Sur Windows

uv sync --dev
```

<details>
<summary><b>Problèmes d'installation courants</b> (Cliquez pour développer)</summary>

<br/>

| Problème | Solution |
|-------|----------|
| `uv: command not found` | Redémarrez le terminal après avoir installé UV. Utilisez PowerShell sur Windows |
| `Python version not supported` | Installez Python 3.12+ depuis [python.org](https://www.python.org/downloads/) |
| L'environnement virtuel ne s'active pas (Windows) | Utilisez PowerShell et exécutez `.venv\Scripts\activate` |
| `Microsoft Visual C++ required` | Téléchargez [Visual C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/) |
| `ModuleNotFoundError` | Activez venv et exécutez `uv sync --dev` |

</details>

---

<br/>

## 🚀 Démarrage rapide

### Option 1 : Utilisez Cookiecutter (Recommandé)

**Temps jusqu'au premier agent : ~2 minutes ⏱️**

```bash
# Installer Cookiecutter
uv add cookiecutter

# Créer votre agent Bindu
uvx cookiecutter https://github.com/getbindu/create-bindu-agent.git
```

## 🎥 Construisez des agents prêts pour la production en quelques minutes

<div align="center">
  <a href="https://youtu.be/obY1bGOoWG8?si=uEeDb0XWrtYOQTL7" target="_blank">
    <img src="https://img.youtube.com/vi/obY1bGOoWG8/maxresdefault.jpg" alt="Bindu Demo" width="640" style="border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);" />
  </a>
</div>

C'est tout ! Votre agent local est maintenant un service en direct, sécurisé et découvrable. [En savoir plus →](https://docs.getbindu.com/bindu/create-bindu-agent/overview)

> **💡 Conseil pro :** Les agents créés avec Cookiecutter incluent des GitHub Actions qui enregistrent automatiquement votre agent dans le [Bindu Directory](https://bindus.directory) lorsque vous poussez vers votre dépôt. Pas besoin d'enregistrement manuel !

### Option 2 : Configuration manuelle

Créez votre script d'agent `my_agent.py` :

```python
from bindu.penguin.bindufy import bindufy
from agno.agent import Agent
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.models.openai import OpenAIChat

# Définir votre agent
agent = Agent(
    instructions="Vous êtes un assistant de recherche qui trouve et résume des informations.",
    model=OpenAIChat(id="gpt-4o"),
    tools=[DuckDuckGoTools()],
)

# Configuration
config = {
    "author": "your.email@example.com",
    "name": "research_agent",
    "description": "Un agent assistant de recherche",
    "deployment": {"url": "http://localhost:3773", "expose": True},
    "skills": ["skills/question-answering", "skills/pdf-processing"]
}

# Fonction handler
def handler(messages: list[dict[str, str]]):
    """Traite les messages et retourne la réponse de l'agent.

    Args:
        messages: Liste de dictionnaires de messages avec l'historique de conversation

    Returns:
        Résultat de la réponse de l'agent
    """
    result = agent.run(input=messages)
    return result

# Bindu-fy
bindufy(config, handler)
```

![Sample Agent](assets/agno-simple.png)

Votre agent est maintenant en direct sur `http://localhost:3773` et prêt à communiquer avec d'autres agents.

---

### Option 3 : Agent Echo minimal (Tests)

<details>
<summary><b>Voir l'exemple minimal</b> (Cliquez pour développer)</summary>

L'agent fonctionnel le plus petit :

```python
from bindu.penguin.bindufy import bindufy

def handler(messages):
    return [{"role": "assistant", "content": messages[-1]["content"]}]

config = {
    "author": "your.email@example.com",
    "name": "echo_agent",
    "description": "Un agent echo de base pour des tests rapides.",
    "deployment": {"url": "http://localhost:3773", "expose": True},
    "skills": []
}

bindufy(config, handler)
```

**Exécuter et tester :**

```bash
# Démarrer l'agent
python examples/echo_agent.py
```

</details>

<details>
<summary><b>Tester l'agent avec curl</b> (Cliquez pour développer)</summary>

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

Vérifier l'état de la tâche
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

<br/>

## [Postgres Storage](https://docs.getbindu.com/bindu/learn/storage/overview)

Bindu utilise PostgreSQL comme backend de stockage persistant pour les déploiements en production. La couche de stockage est construite avec le moteur asynchrone de SQLAlchemy et utilise un mappage impératif avec des protocol TypeDicts.

Ceci est optionnel – par défaut, InMemoryStorage est utilisé.

### 📊 Structure de stockage

La couche de stockage utilise trois tables principales :

1. **tasks_table** : Stocke toutes les tâches avec l'historique JSONB et les artefacts
2. **contexts_table** : Maintient les métadonnées de contexte et l'historique des messages
3. **task_feedback_table** : Stockage optionnel de feedback pour les tâches

### ⚙️ Configuration

<details>
<summary><b>Voir l'exemple de configuration</b> (Cliquez pour développer)</summary>

Configurez la connexion PostgreSQL dans votre environnement ou paramètres :
Fournissez la chaîne de connexion dans la configuration de l'agent.

```json
config = {
    "author": "your.email@example.com",
    "name": "research_agent",
    "description": "Un agent assistant de recherche",
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

**💡 Modèle Task-First** : Le stockage prend en charge l'approche task-first de Bindu où les tâches peuvent continuer en ajoutant des messages aux tâches non terminales, permettant des raffinements incrémentaux et des conversations multi-tours.

---

<br/>

## [Redis Scheduler](https://docs.getbindu.com/bindu/learn/scheduler/overview)

Bindu utilise Redis comme planificateur de tâches distribué pour coordonner le travail entre plusieurs workers et processus. Le planificateur utilise des listes Redis avec des opérations de blocage pour une distribution efficace des tâches.

Ceci est optionnel – par défaut, InMemoryScheduler est utilisé.

### ⚙️ Configuration

<details>
<summary><b>Voir l'exemple de configuration</b> (Cliquez pour développer)</summary>

Configurez la connexion Redis dans votre configuration d'agent :

```json
config = {
    "author": "your.email@example.com",
    "name": "research_agent",
    "description": "Un agent assistant de recherche",
    "deployment": {"url": "http://localhost:3773", "expose": True},
    "skills": ["skills/question-answering", "skills/pdf-processing"],
     "scheduler": {
        "type": "redis",
        "redis_url": "redis://localhost:6379/0",
    },
}
```

</details>

Toutes les opérations sont mises en file d'attente dans Redis et traitées par les workers disponibles en utilisant un mécanisme de pop bloquant, garantissant une distribution efficace sans surcharge de polling.

---

<br/>

## [Retry Mechanism](https://docs.getbindu.com/bindu/learn/retry/overview)

> Logique de réessai automatique avec backoff exponentiel pour des agents Bindu résilients

Bindu dispose d'un mécanisme de réessai intégré basé sur Tenacity qui gère élégamment les échecs transitoires dans les workers, le stockage, les planificateurs et les appels API. Cela garantit que vos agents restent résilients dans les environnements de production.

### ⚙️ Paramètres par défaut

Si non configuré, Bindu utilise ces valeurs par défaut :

| Type d'opération | Tentatives max | Attente min | Attente max |
| -------------- | ------------ | -------- | -------- |
| Worker         | 3            | 1.0s     | 10.0s    |
| Storage        | 5            | 0.5s     | 5.0s     |
| Scheduler      | 3            | 1.0s     | 8.0s     |
| API            | 4            | 1.0s     | 15.0s    |

---

<br/>

## [Sentry Integration](https://docs.getbindu.com/bindu/learn/sentry/overview)

> Suivi des erreurs en temps réel et surveillance des performances pour les agents Bindu

Sentry est une plateforme de suivi des erreurs et de surveillance des performances en temps réel qui vous aide à identifier, diagnostiquer et corriger les problèmes en production. Bindu dispose d'une intégration Sentry intégrée pour fournir une observabilité complète pour vos agents IA.

### ⚙️ Configuration

<details>
<summary><b>Voir l'exemple de configuration</b> (Cliquez pour développer)</summary>

Configurez Sentry directement dans votre configuration `bindufy()` :

```python
config = {
    "author": "gaurikasethi88@gmail.com",
    "name": "echo_agent",
    "description": "Un agent echo de base pour des tests rapides.",
    "deployment": {"url": "http://localhost:3773", "expose": True},
    "skills": [],
    "storage": {
        "type": "postgres",
        "database_url": "postgresql+asyncpg://bindu:bindu@localhost:5432/bindu",  # pragma: allowlist secret
        "run_migrations_on_startup": False,
    },
    # Configuration du Scheduler (optionnel)
    # Utilisez "memory" (par défaut) pour un processus unique ou "redis" pour multi-processus distribué
    "scheduler": {
        "type": "redis",
        "redis_url": "redis://localhost:6379/0",
    },
    # Suivi des erreurs Sentry (optionnel)
    # Configurez Sentry directement dans le code au lieu de variables d'environnement
    "sentry": {
        "enabled": True,
        "dsn": "https://252c0197ddeafb621f91abdbb59fa819@o4510504294612992.ingest.de.sentry.io/4510504299069520",
        "environment": "development",
        "traces_sample_rate": 1.0,
        "profiles_sample_rate": 0.1,
    },
}

def handler(messages):
    # Votre logique d'agent
    pass

bindufy(config, handler)
```

</details>

### 🚀 Démarrage

1. **Créez un compte Sentry** : Inscrivez-vous sur [sentry.io](https://sentry.io)
2. **Obtenez votre DSN** : Copiez depuis les paramètres du projet
3. **Configurez Bindu** : Ajoutez la configuration `sentry` (voir ci-dessus)
4. **Exécutez votre agent** : Sentry s'initialise automatiquement

> 📚 Consultez la [documentation complète de Sentry](https://docs.getbindu.com/bindu/learn/sentry/overview) pour tous les détails.

---

<br/>

## [Skills System](https://docs.getbindu.com/bindu/skills/introduction/overview)

> Publicité riche de capacités pour l'orchestration intelligente d'agents

Le Bindu Skills System fournit une publicité riche des capacités d'agents pour l'orchestration intelligente et la découverte d'agents. Inspiré par l'architecture des skills de Claude, il permet aux agents de fournir une documentation détaillée sur leurs capacités afin que les orchestrateurs puissent prendre des décisions de routage éclairées.

### 💡 Que sont les Skills ?

Dans Bindu, les Skills agissent comme des **métadonnées de publicité riches** qui aident les orchestrateurs à :

* 🔍 **Découvrir** le bon agent pour une tâche
* 📖 **Comprendre** les capacités et limitations détaillées
* ✅ **Vérifier** les exigences avant l'exécution
* 📊 **Estimer** les performances et les besoins en ressources
* 🔗 **Enchaîner** plusieurs agents intelligemment

> **Note** : Les Skills ne sont pas du code exécutable—ce sont des métadonnées structurées qui décrivent ce que votre agent peut faire.

### 🔌 Endpoints API

**Lister toutes les Skills** :
```bash
GET /agent/skills
```

**Obtenir les détails d'une Skill** :
```bash
GET /agent/skills/{skill_id}
```

**Obtenir la documentation d'une Skill** :
```bash
GET /agent/skills/{skill_id}/documentation
```

> 📚 Consultez la [documentation des Skills](https://github.com/getbindu/Bindu/tree/main/examples/skills) pour des exemples complets.

---

<br/>

## Negotiation

> Sélection d'agents basée sur les capacités pour une orchestration intelligente

Le système de négociation de Bindu permet aux orchestrateurs d'interroger plusieurs agents et de sélectionner intelligemment le meilleur agent pour une tâche en fonction des skills, des performances, de la charge et du coût.

### 🔄 Comment ça marche

1. **L'orchestrateur diffuse** une demande d'évaluation à plusieurs agents
2. **Les agents s'auto-évaluent** la capacité en utilisant la correspondance des skills et l'analyse de charge
3. **L'orchestrateur classe** les réponses en utilisant un score multi-facteurs
4. **Le meilleur agent est sélectionné** et la tâche est exécutée

### 🔌 Endpoint d'évaluation

<details>
<summary><b>Voir les détails de l'API</b> (Cliquez pour développer)</summary>

```bash
POST /agent/negotiation
```

**Requête :**
```json
{
  "task_summary": "Extraire des tableaux de factures PDF",
  "task_details": "Traiter les PDF de factures et extraire des données structurées",
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

**Réponse :**
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

### 📊 Algorithme de notation

Les agents calculent un score de confiance basé sur plusieurs facteurs :

```python
score = (
    skill_match * 0.6 +        # Primaire : correspondance des skills
    io_compatibility * 0.2 +   # Support du format entrée/sortie
    performance * 0.1 +        # Vitesse et fiabilité
    load * 0.05 +              # Disponibilité actuelle
    cost * 0.05                # Prix
)
```

> 📚 Consultez la [documentation Negotiation](https://docs.getbindu.com/bindu/negotiation/overview) pour tous les détails.

---

<br/>

## Task Feedback et DSPy

Bindu collecte les retours des utilisateurs sur les exécutions de tâches pour permettre une amélioration continue via l'optimisation DSPy. En stockant les retours avec des notes et des métadonnées, vous pouvez construire des ensembles de données de référence à partir d'interactions réelles et utiliser DSPy pour optimiser automatiquement les prompts et le comportement de votre agent.

### Soumettre un feedback

Fournissez un feedback sur n'importe quelle tâche en utilisant la méthode `tasks/feedback` :

```bash
curl --location 'http://localhost:3773/' \
--header 'Content-Type: application/json' \
--header 'Authorization: Bearer <your-token>' \
--data '{
    "jsonrpc": "2.0",
    "method": "tasks/feedback",
    "params": {
        "taskId": "550e8400-e29b-41d4-a716-446655440200",
        "feedback": "Excellent travail ! La réponse était très utile et précise.",
        "rating": 5,
        "metadata": {
            "category": "quality",
            "source": "user",
            "helpful": true
        }
    },
    "id": "550e8400-e29b-41d4-a716-446655440024"
}'
```

Le feedback est stocké dans la table `task_feedback` et peut être utilisé pour :
- Filtrer les interactions de tâches de haute qualité pour les données d'entraînement
- Identifier les modèles dans les complétions réussies vs échouées
- Optimiser les instructions d'agents et les exemples few-shot avec DSPy
- Nous travaillons sur DsPY - bientôt disponible.

---

<br/>

## 📬 Push Notifications

Bindu prend en charge les **notifications webhook en temps réel** pour les tâches de longue durée, suivant la [spécification du protocole A2A](https://a2a-protocol.org/latest/specification/). Cela permet aux clients de recevoir des notifications push sur les changements d'état des tâches et la génération d'artefacts sans polling.

### Démarrage rapide

1. **Démarrez le récepteur webhook :** `python examples/webhook_client_example.py`
2. **Configurez l'agent** dans `examples/echo_agent_with_webhooks.py` :
   ```python
   manifest = {
       "capabilities": {"push_notifications": True},
       "global_webhook_url": "http://localhost:8000/webhooks/task-updates",
       "global_webhook_token": "secret_abc123",
   }
   ```
3. **Exécutez l'agent :** `python examples/echo_agent_with_webhooks.py`
4. **Envoyez des tâches** - les notifications webhook arrivent automatiquement

📖 **[Documentation complète](docs/long-running-task-notifications.md)** - Guide détaillé avec architecture, sécurité, exemples et dépannage.

---

<br/>

## 🎨 Chat UI

Bindu inclut une belle interface de chat sur `http://localhost:3773/docs`

<p align="center">
  <img src="assets/agent-ui.png" alt="Bindu Agent UI" width="640" style="border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);" />
</p>

---

<br/>

## 🌐 Bindu Directory

Le [**Bindu Directory**](https://bindus.directory) est un registre public de tous les agents Bindu, les rendant découvrables et accessibles pour l'écosystème d'agents plus large.

### ✨ Enregistrement automatique avec Cookiecutter

Lorsque vous créez un agent en utilisant le modèle cookiecutter, il inclut une GitHub Action préconfigurée qui enregistre automatiquement votre agent dans le répertoire :

1. **Créez votre agent** en utilisant cookiecutter
2. **Poussez vers GitHub** - La GitHub Action se déclenche automatiquement
3. **Votre agent apparaît** dans le [Bindu Directory](https://bindus.directory)

> **🔑 Note** : Vous devez collecter le BINDU_PAT_TOKEN depuis bindus.directory et l'utiliser pour enregistrer votre agent.

### 📝 Enregistrement manuel

Nous travaillons sur un processus d'enregistrement manuel.

---

<br/>

## 🌌 La Vision

```
un aperçu du ciel nocturne
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

_Chaque symbole est un agent – une étincelle d'intelligence. Le petit point est Bindu, le point d'origine dans l'Internet of Agents._

### Connexion NightSky [En cours]

NightSky permet des essaims d'agents. Chaque Bindu est un point qui annote les agents avec le langage partagé d'A2A, AP2 et X402. Les agents peuvent être hébergés n'importe où – ordinateurs portables, clouds ou clusters – mais parlent le même protocole, se font confiance par conception et travaillent ensemble comme un seul esprit distribué.

> **💭 Un objectif sans plan n'est qu'un souhait.**

---

<br/>

## 🛠️ Frameworks d'agents pris en charge

Bindu est **agnostique au framework** et testé avec :

- **Agno**
- **CrewAI**
- **LangChain**
- **LlamaIndex**
- **FastAgent**

Vous voulez une intégration avec votre framework préféré ? [Faites-le nous savoir sur Discord](https://discord.gg/3w5zuYUuwt) !

---

<br/>

## 🧪 Tests

Bindu maintient **70%+ de couverture de tests** :

```bash
pytest -n auto --cov=bindu --cov-report= && coverage report --skip-covered --fail-under=70
```

---

<br/>

## Dépannage

<details>
<summary>Problèmes courants</summary>

<br/>

| Problème | Solution |
|---------|----------|
| `Python 3.12 not found` | Installez Python 3.12+ et configurez-le dans PATH, ou utilisez `pyenv` |
| `bindu: command not found` | Activez l'environnement virtuel : `source .venv/bin/activate` |
| `Port 3773 already in use` | Changez le port dans la config : `"url": "http://localhost:4000"` |
| Pre-commit échoue | Exécutez `pre-commit run --all-files` |
| Les tests échouent | Installez les dépendances de dev : `uv sync --dev` |
| `Permission denied` (macOS) | Exécutez `xattr -cr .` pour effacer les attributs étendus |

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

> 📖 [Directives de contribution](.github/contributing.md)

---

<br/>

## 📜 Licence

Bindu est open-source sous la [Apache License 2.0](https://choosealicense.com/licenses/apache-2.0/).

---

<br/>

## 💬 Communauté

Nous 💛 les contributions ! Que vous corrigiez des bugs, amélioriez la documentation ou construisiez des démos – vos contributions rendent Bindu meilleur.

- 💬 [Rejoignez Discord](https://discord.gg/3w5zuYUuwt) pour les discussions et le support
- ⭐ [Donnez une étoile au dépôt](https://github.com/getbindu/Bindu) si vous le trouvez utile !

---

<br/>

## 👥 Modérateurs actifs

Nos modérateurs dévoués aident à maintenir une communauté accueillante et productive :

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

> Vous voulez devenir modérateur ? Contactez-nous sur [Discord](https://discord.gg/3w5zuYUuwt) !

---

<br/>

## 🙏 Remerciements

Reconnaissants envers ces projets :

- [FastA2A](https://github.com/pydantic/fasta2a)
- [12 Factor Agents](https://github.com/humanlayer/12-factor-agents/blob/main/content/factor-11-trigger-from-anywhere.md)
- [A2A](https://github.com/a2aproject/A2A)
- [AP2](https://github.com/google-agentic-commerce/AP2)
- [X402](https://github.com/coinbase/x402)
- [Bindu Logo](https://openmoji.org/library/emoji-1F33B/)
- [ASCII Space Art](https://www.asciiart.eu/space/other)

---

<br/>

## 🗺️ Feuille de route

- [ ] Support du transport GRPC
- [x] Suivi des erreurs Sentry
- [x] Intégration Ag-UI
- [x] Mécanisme de réessai
- [ ] Augmenter la couverture de tests à 80% - En cours
- [x] Implémentation du planificateur Redis
- [x] Base de données Postgres pour le stockage de mémoire
- [x] Support de négociation
- [ ] Support AP2 de bout en bout
- [ ] Intégration DSPy - En cours
- [ ] Support MLTS
- [ ] Support X402 avec d'autres facilitateurs

> 💡 [Suggérez des fonctionnalités sur Discord](https://discord.gg/3w5zuYUuwt) !

---

<br/>

## 🎓 Ateliers

- [AI Native in Action: Agent Symphony](https://www.meetup.com/ai-native-amsterdam/events/311066899/) - [Slides](https://docs.google.com/presentation/d/1SqGXI0Gv_KCWZ1Mw2SOx_kI0u-LLxwZq7lMSONdl8oQ/edit)

---

<br/>

## ⭐ Historique des étoiles

[![Star History Chart](https://api.star-history.com/svg?repos=getbindu/Bindu&type=Date)](https://www.star-history.com/#getbindu/Bindu&Date)

---

<p align="center">
  <strong>Construit avec 💛 par l'équipe d'Amsterdam</strong><br/>
  <em>Happy Bindu! 🌻🚀✨</em>
</p>

<p align="center">
  <strong>De l'idée à l'Internet of Agents en 2 minutes.</strong><br/>
  <em>Votre agent. Votre framework. Protocoles universels.</em>
</p>

<p align="center">
  <a href="https://github.com/getbindu/Bindu">⭐ Donnez-nous une étoile sur GitHub</a> •
  <a href="https://discord.gg/3w5zuYUuwt">💬 Rejoignez Discord</a> •
  <a href="https://docs.getbindu.com">🌻 Lisez les Docs</a>
</p>
