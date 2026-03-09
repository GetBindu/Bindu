<div align="center" id="top">
  <a href="https://getbindu.com">
    <picture>
      <img src="assets/bindu.png" alt="Bindu" width="300">
    </picture>
  </a>
</div>

<p align="center">
  <em>Die Identitäts-, Kommunikations- und Zahlungsschicht für KI-Agenten</em>
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

**Bindu** (ausgesprochen: _binduu_) ist eine Betriebsschicht für KI-Agenten, die Identität, Kommunikation und Zahlungsfunktionen bereitstellt. Es liefert einen produktionsreifen Service mit einer komfortablen API, um Agenten über verteilte Systeme hinweg zu verbinden, zu authentifizieren und zu orchestrieren – basierend auf offenen Protokollen: **A2A**, **AP2** und **X402**.

Mit einer verteilten Architektur (Task Manager, Scheduler, Storage) macht es Bindu schnell, zu entwickeln und einfach, in jedes KI-Framework zu integrieren. Verwandeln Sie jedes Agenten-Framework in einen vollständig interoperablen Service für Kommunikation, Zusammenarbeit und Commerce im Internet of Agents.

<p align="center">
  <strong>🌟 <a href="https://bindus.directory">Registriere deinen Agenten</a> • 🌻 <a href="https://docs.getbindu.com">Dokumentation</a> • 💬 <a href="https://discord.gg/3w5zuYUuwt">Discord Community</a></strong>
</p>


---

<br/>

## 🎥 Bindu in Aktion

<div align="center">
  <a href="https://www.youtube.com/watch?v=qppafMuw_KI" target="_blank">
    <img src="https://img.youtube.com/vi/qppafMuw_KI/maxresdefault.jpg" alt="Bindu Demo" width="640" style="border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);" />
  </a>
</div>


## 📋 Voraussetzungen

Bevor du Bindu installierst, stelle sicher, dass du Folgendes hast:

- **Python 3.12 oder höher** - [Hier herunterladen](https://www.python.org/downloads/)
- **UV Package Manager** - [Installationsanleitung](https://github.com/astral-sh/uv)

### Überprüfe dein Setup

```bash
# Python-Version prüfen
uv run python --version  # Sollte 3.12 oder höher anzeigen

# UV-Installation prüfen
uv --version
```

---

<br/>

## 📦 Installation
<details>
<summary><b>Hinweis für Windows-Nutzer (Git & GitHub Desktop)</b></summary>

Auf manchen Windows-Systemen wird Git möglicherweise nicht in der Eingabeaufforderung erkannt, selbst nach der Installation – aufgrund von PATH-Konfigurationsproblemen.

Falls du auf dieses Problem stößt, kannst du *GitHub Desktop* als Alternative verwenden:

1. Installiere GitHub Desktop von https://desktop.github.com/
2. Melde dich mit deinem GitHub-Konto an
3. Klone das Repository mit der Repository-URL:
   https://github.com/getbindu/Bindu.git

GitHub Desktop ermöglicht es dir, Repositories zu klonen, Branches zu verwalten, Änderungen zu committen und Pull Requests zu öffnen – ohne die Kommandozeile.

</details>

```bash
# Bindu installieren
uv add bindu

# Für die Entwicklung (wenn du zu Bindu beiträgst)
# Virtuelle Umgebung erstellen und aktivieren
uv venv --python 3.12.9
source .venv/bin/activate  # Auf macOS/Linux
# .venv\Scripts\activate  # Auf Windows

uv sync --dev
```

<details>
<summary><b>Häufige Installationsprobleme</b> (zum Erweitern klicken)</summary>

<br/>

| Problem | Lösung |
|---------|----------|
| `uv: command not found` | Starte dein Terminal nach der UV-Installation neu. Auf Windows verwende PowerShell |
| `Python version not supported` | Installiere Python 3.12+ von [python.org](https://www.python.org/downloads/) |
| Virtuelle Umgebung aktiviert nicht (Windows) | Verwende PowerShell und führe `.venv\Scripts\activate` aus |
| `Microsoft Visual C++ required` | Lade [Visual C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/) herunter |
| `ModuleNotFoundError` | Aktiviere venv und führe `uv sync --dev` aus |

</details>

---

<br/>

## 🚀 Schnellstart

### Option 1: Cookiecutter verwenden (Empfohlen)

**Zeit bis zum ersten Agenten: ~2 Minuten ⏱️**

```bash
# Cookiecutter installieren
uv add cookiecutter

# Erstelle deinen Bindu-Agenten
uvx cookiecutter https://github.com/getbindu/create-bindu-agent.git
```

## 🎥 Produktionsreife Agenten in Minuten erstellen

<div align="center">
  <a href="https://youtu.be/obY1bGOoWG8?si=uEeDb0XWrtYOQTL7" target="_blank">
    <img src="https://img.youtube.com/vi/obY1bGOoWG8/maxresdefault.jpg" alt="Bindu Demo" width="640" style="border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);" />
  </a>
</div>

Das war's! Dein lokaler Agent wird zu einem live, sicheren und entdeckbaren Service. [Mehr erfahren →](https://docs.getbindu.com/bindu/create-bindu-agent/overview)

> **💡 Profi-Tipp:** Agenten, die mit Cookiecutter erstellt wurden, enthalten GitHub Actions, die deinen Agenten automatisch im [Bindu Directory](https://bindus.directory) registrieren, wenn du zu deinem Repository pushst. Keine manuelle Registrierung erforderlich!

### Option 2: Manuelle Einrichtung

Erstelle dein Agenten-Skript `my_agent.py`:

```python
from bindu.penguin.bindufy import bindufy
from agno.agent import Agent
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.models.openai import OpenAIChat

# Definiere deinen Agenten
agent = Agent(
    instructions="Du bist ein Recherche-Assistent, der Informationen findet und zusammenfasst.",
    model=OpenAIChat(id="gpt-4o"),
    tools=[DuckDuckGoTools()],
)

# Konfiguration
config = {
    "author": "deine.email@beispiel.de",
    "name": "research_agent",
    "description": "Ein Recherche-Assistenten-Agent",
    "deployment": {"url": "http://localhost:3773", "expose": True},
    "skills": ["skills/question-answering", "skills/pdf-processing"]
}

# Handler-Funktion
def handler(messages: list[dict[str, str]]):
    """Verarbeitet Nachrichten und gibt die Antwort des Agenten zurück.

    Args:
        messages: Liste von Nachrichten-Dictionaries mit Gesprächsverlauf

    Returns:
        Ergebnis der Agenten-Antwort
    """
    result = agent.run(input=messages)
    return result

# Bindu-fiziere es
bindufy(config, handler)
```

![Sample Agent](assets/agno-simple.png)

Dein Agent ist jetzt live unter `http://localhost:3773` und bereit, mit anderen Agenten zu kommunizieren.

---

### Option 3: Minimaler Echo-Agent (Testing)

<details>
<summary><b>Minimales Beispiel anzeigen</b> (zum Erweitern klicken)</summary>

Kleinstmöglicher funktionierender Agent:

```python
from bindu.penguin.bindufy import bindufy

def handler(messages):
    return [{"role": "assistant", "content": messages[-1]["content"]}]

config = {
    "author": "deine.email@beispiel.de",
    "name": "echo_agent",
    "description": "Ein einfacher Echo-Agent zum schnellen Testen.",
    "deployment": {"url": "http://localhost:3773", "expose": True},
    "skills": []
}

bindufy(config, handler)
```

**Ausführen und testen:**

```bash
# Starte den Agenten
python examples/echo_agent.py
```

</details>

<details>
<summary><b>Teste den Agenten mit curl</b> (zum Erweitern klicken)</summary>

<br/>

Eingabe:
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

Ausgabe:
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

Überprüfe den Status der Aufgabe
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

Ausgabe:
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

Bindu verwendet PostgreSQL als persistentes Storage-Backend für Produktions-Deployments. Die Storage-Schicht ist mit SQLAlchemy's async Engine gebaut und verwendet imperative Mappings mit Protocol TypedDicts.

Es ist optional – InMemoryStorage wird standardmäßig verwendet.

### 📊 Storage-Struktur

Die Storage-Schicht verwendet drei Haupttabellen:

1. **tasks_table**: Speichert alle Tasks mit JSONB-History und Artifacts
2. **contexts_table**: Verwaltet Context-Metadaten und Nachrichtenverlauf
3. **task_feedback_table**: Optionaler Feedback-Speicher für Tasks

### ⚙️ Konfiguration

<details>
<summary><b>Konfigurationsbeispiel anzeigen</b> (zum Erweitern klicken)</summary>

Konfiguriere die PostgreSQL-Verbindung in deiner Umgebung oder Einstellungen:
Gib die Verbindungszeichenfolge in der Konfiguration des Agenten an.

```json
config = {
    "author": "deine.email@beispiel.de",
    "name": "research_agent",
    "description": "Ein Recherche-Assistenten-Agent",
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

 **💡 Task-First-Pattern**: Der Storage unterstützt Bindus Task-First-Ansatz, bei dem Tasks durch Anhängen von Nachrichten an nicht-terminale Tasks fortgesetzt werden können, was inkrementelle Verfeinerungen und Multi-Turn-Konversationen ermöglicht.

---

<br/>

## [Redis Scheduler](https://docs.getbindu.com/bindu/learn/scheduler/overview)

Bindu verwendet Redis als verteilten Task-Scheduler zur Koordination von Arbeit über mehrere Worker und Prozesse hinweg. Der Scheduler verwendet Redis-Listen mit blockierenden Operationen für eine effiziente Task-Verteilung.

Es ist optional – InMemoryScheduler wird standardmäßig verwendet.

### ⚙️ Konfiguration

<details>
<summary><b>Konfigurationsbeispiel anzeigen</b> (zum Erweitern klicken)</summary>

Konfiguriere die Redis-Verbindung in deiner Agenten-Konfiguration:

```json
config = {
    "author": "deine.email@beispiel.de",
    "name": "research_agent",
    "description": "Ein Recherche-Assistenten-Agent",
    "deployment": {"url": "http://localhost:3773", "expose": True},
    "skills": ["skills/question-answering", "skills/pdf-processing"],
     "scheduler": {
        "type": "redis",
        "redis_url": "redis://localhost:6379/0",
    },
}
```

</details>

Alle Operationen werden in Redis in die Warteschlange gestellt und von verfügbaren Workern mit einem blockierenden Pop-Mechanismus verarbeitet, was eine effiziente Verteilung ohne Polling-Overhead gewährleistet.

---

<br/>

## [Retry-Mechanismus](https://docs.getbindu.com/bindu/learn/retry/overview)

> Automatische Retry-Logik mit exponentiellem Backoff für resiliente Bindu-Agenten

Bindu enthält einen integrierten Tenacity-basierten Retry-Mechanismus, um vorübergehende Fehler elegant über Worker, Storage, Scheduler und API-Aufrufe hinweg zu behandeln. Dies stellt sicher, dass deine Agenten in Produktionsumgebungen resilient bleiben.


### ⚙️ Standardeinstellungen

Falls nicht konfiguriert, verwendet Bindu diese Standards:

| Operationstyp | Max. Versuche | Min. Wartezeit | Max. Wartezeit |
| -------------- | ------------ | -------- | -------- |
| Worker         | 3            | 1.0s     | 10.0s    |
| Storage        | 5            | 0.5s     | 5.0s     |
| Scheduler      | 3            | 1.0s     | 8.0s     |
| API            | 4            | 1.0s     | 15.0s    |

---

<br/>

## [Sentry-Integration](https://docs.getbindu.com/bindu/learn/sentry/overview)

> Echtzeit-Fehler-Tracking und Performance-Monitoring für Bindu-Agenten

Sentry ist eine Echtzeit-Plattform für Fehler-Tracking und Performance-Monitoring, die dir hilft, Probleme in der Produktion zu identifizieren, zu diagnostizieren und zu beheben. Bindu enthält eine integrierte Sentry-Integration, um umfassende Observability für deine KI-Agenten bereitzustellen.

### ⚙️ Konfiguration

<details>
<summary><b>Konfigurationsbeispiel anzeigen</b> (zum Erweitern klicken)</summary>

Konfiguriere Sentry direkt in deiner `bindufy()`-Konfiguration:

```python
config = {
    "author": "gaurikasethi88@gmail.com",
    "name": "echo_agent",
    "description": "Ein einfacher Echo-Agent zum schnellen Testen.",
    "deployment": {"url": "http://localhost:3773", "expose": True},
    "skills": [],
    "storage": {
        "type": "postgres",
        "database_url": "postgresql+asyncpg://bindu:bindu@localhost:5432/bindu",  # pragma: allowlist secret
        "run_migrations_on_startup": False,
    },
    # Scheduler-Konfiguration (optional)
    # Verwende "memory" für Single-Process (Standard) oder "redis" für verteilte Multi-Process
    "scheduler": {
        "type": "redis",
        "redis_url": "redis://localhost:6379/0",
    },
    # Sentry-Fehler-Tracking (optional)
    # Konfiguriere Sentry direkt im Code statt über Umgebungsvariablen
    "sentry": {
        "enabled": True,
        "dsn": "https://252c0197ddeafb621f91abdbb59fa819@o4510504294612992.ingest.de.sentry.io/4510504299069520",
        "environment": "development",
        "traces_sample_rate": 1.0,
        "profiles_sample_rate": 0.1,
    },
}

def handler(messages):
    # Deine Agenten-Logik
    pass

bindufy(config, handler)
```

</details>

### 🚀 Erste Schritte

1. **Sentry-Konto erstellen**: Registriere dich bei [sentry.io](https://sentry.io)
2. **Hol dir deinen DSN**: Kopiere ihn aus den Projekteinstellungen
3. **Konfiguriere Bindu**: Füge die `sentry`-Konfiguration hinzu (siehe oben)
4. **Führe deinen Agenten aus**: Sentry initialisiert sich automatisch

> 📚 Siehe die [vollständige Sentry-Dokumentation](https://docs.getbindu.com/bindu/learn/sentry/overview) für alle Details.

---

<br/>

## [Skills-System](https://docs.getbindu.com/bindu/skills/introduction/overview)

> Umfassende Fähigkeits-Werbung für intelligente Agenten-Orchestrierung

Das Bindu Skills-System bietet umfassende Agenten-Fähigkeits-Werbung für intelligente Orchestrierung und Agenten-Discovery. Inspiriert von Claudes Skills-Architektur ermöglicht es Agenten, detaillierte Dokumentation über ihre Fähigkeiten bereitzustellen, damit Orchestratoren informierte Routing-Entscheidungen treffen können.

### 💡 Was sind Skills?

Skills in Bindu dienen als **umfassende Werbe-Metadaten**, die Orchestratoren helfen:

* 🔍 **Entdecken** des richtigen Agenten für eine Aufgabe
* 📖 **Verstehen** detaillierter Fähigkeiten und Einschränkungen
* ✅ **Validieren** von Anforderungen vor der Ausführung
* 📊 **Schätzen** von Performance und Ressourcenbedarf
* 🔗 **Verketten** mehrerer Agenten intelligent

> **Hinweis**: Skills sind kein ausführbarer Code – sie sind strukturierte Metadaten, die beschreiben, was dein Agent kann.

### 📋 Vollständige Skill-Struktur

<details>
<summary><b>Vollständige skill.yaml-Struktur anzeigen</b> (zum Erweitern klicken)</summary>

Eine skill.yaml-Datei enthält alle Metadaten, die für intelligente Orchestrierung benötigt werden:

```yaml
# Basis-Metadaten
id: pdf-processing-v1
name: pdf-processing
version: 1.0.0
author: raahul@getbindu.com

# Beschreibung
description: |
  Extrahiere Text, fülle Formulare aus und extrahiere Tabellen aus PDF-Dokumenten.
  Verarbeitet sowohl standardmäßige textbasierte PDFs als auch gescannte Dokumente mit OCR.

# Tags und Modi
tags:
  - pdf
  - documents
  - extraction

input_modes:
  - application/pdf

output_modes:
  - text/plain
  - application/json
  - application/pdf

# Beispiel-Anfragen
examples:
  - "Extrahiere Text aus diesem PDF-Dokument"
  - "Fülle dieses PDF-Formular mit den bereitgestellten Daten aus"
  - "Extrahiere Tabellen aus dieser Rechnungs-PDF"

# Detaillierte Fähigkeiten
capabilities_detail:
  text_extraction:
    supported: true
    types:
      - standard
      - scanned_with_ocr
    languages:
      - eng
      - spa
    limitations: "OCR erfordert pytesseract und tesseract-ocr"
    preserves_formatting: true

  form_filling:
    supported: true
    field_types:
      - text
      - checkbox
      - dropdown
    validation: true

  table_extraction:
    supported: true
    table_types:
      - simple
      - complex_multi_column
    output_formats:
      - json
      - csv

# Anforderungen
requirements:
  packages:
    - pypdf>=3.0.0
    - pdfplumber>=0.9.0
    - pytesseract>=0.3.10
  system:
    - tesseract-ocr
  min_memory_mb: 512

# Performance-Metriken
performance:
  avg_processing_time_ms: 2000
  avg_time_per_page_ms: 200
  max_file_size_mb: 50
  max_pages: 500
  concurrent_requests: 5
  memory_per_request_mb: 500
  timeout_per_page_seconds: 30

# Umfassende Dokumentation
documentation:
  overview: |
    Dieser Agent ist spezialisiert auf PDF-Dokumentenverarbeitung mit Unterstützung für Textextraktion,
    Formularausfüllung und Tabellenextraktion. Verarbeitet sowohl standardmäßige textbasierte PDFs als auch
    gescannte Dokumente (mit OCR).

  use_cases:
    when_to_use:
      - Benutzer lädt eine PDF hoch und bittet um Textextraktion
      - Benutzer muss PDF-Formulare programmatisch ausfüllen
      - Benutzer möchte Tabellen aus Berichten/Rechnungen extrahieren
    when_not_to_use:
      - PDF-Bearbeitung oder -Modifikation
      - PDF-Erstellung von Grund auf
      - Bildextraktion aus PDFs

  input_structure: |
    {
      "file": "base64_encoded_pdf_or_url",
      "operation": "extract_text|fill_form|extract_tables",
      "options": {
        "ocr": true,
        "language": "eng"
      }
    }

  output_format: |
    {
      "success": true,
      "pages": [{"page_number": 1, "text": "...", "confidence": 0.98}],
      "metadata": {"total_pages": 10, "processing_time_ms": 1500}
    }

  error_handling:
    - "Verschlüsselte PDFs: Gibt Fehler zurück, der nach Passwort fragt"
    - "Beschädigte Dateien: Gibt Validierungsfehler mit Details zurück"
    - "Timeout: 30s pro Seite, gibt Teilergebnisse zurück"

  examples:
    - title: "Text aus PDF extrahieren"
      input:
        file: "https://example.com/document.pdf"
        operation: "extract_text"
      output:
        success: true
        pages:
          - page_number: 1
            text: "Extrahierter Text..."
            confidence: 0.99

  best_practices:
    for_developers:
      - "Prüfe Dateigröße vor der Verarbeitung (max 50MB)"
      - "Verwende OCR nur bei Bedarf (3-5x langsamer)"
      - "Behandle Fehler elegant mit benutzerfreundlichen Nachrichten"
    for_orchestrators:
      - "Route basierend auf Operationstyp (extract/fill/parse)"
      - "Berücksichtige Dateigröße für Performance-Schätzung"
      - "Verkette mit Text-Analyse für Inhaltsverständnis"

# Assessment-Felder für Skill-Negotiation
assessment:
  keywords:
    - pdf
    - extract
    - document
    - form
    - table

  specializations:
    - domain: invoice_processing
      confidence_boost: 0.3
    - domain: form_filling
      confidence_boost: 0.3

  anti_patterns:
    - "pdf editing"
    - "pdf creation"
    - "merge pdf"

  complexity_indicators:
    simple:
      - "single page"
      - "extract text"
    medium:
      - "multiple pages"
      - "fill form"
    complex:
      - "scanned document"
      - "ocr"
      - "batch processing"
```

</details>

### 🔌 API-Endpunkte

**Alle Skills auflisten**:
```bash
GET /agent/skills
```

**Skill-Details abrufen**:
```bash
GET /agent/skills/{skill_id}
```

**Skill-Dokumentation abrufen**:
```bash
GET /agent/skills/{skill_id}/documentation
```

> 📚 Siehe die [Skills-Dokumentation](https://github.com/getbindu/Bindu/tree/main/examples/skills) für vollständige Beispiele.

---

<br/>

## Negotiation

> Fähigkeitsbasierte Agenten-Auswahl für intelligente Orchestrierung

Bindus Negotiation-System ermöglicht es Orchestratoren, mehrere Agenten abzufragen und intelligent den besten für eine Aufgabe basierend auf Skills, Performance, Last und Kosten auszuwählen.

### 🔄 Wie es funktioniert

1. **Orchestrator sendet** Assessment-Anfrage an mehrere Agenten
2. **Agenten bewerten sich selbst** mit Skill-Matching und Last-Analyse
3. **Orchestrator rankt** Antworten mit Multi-Faktor-Scoring
4. **Bester Agent ausgewählt** und Task ausgeführt

### 🔌 Assessment-Endpunkt

<details>
<summary><b>API-Details anzeigen</b> (zum Erweitern klicken)</summary>

```bash
POST /agent/negotiation
```

**Anfrage:**
```json
{
  "task_summary": "Extrahiere Tabellen aus PDF-Rechnungen",
  "task_details": "Verarbeite Rechnungs-PDFs und extrahiere strukturierte Daten",
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

**Antwort:**
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

### 📊 Scoring-Algorithmus

Agenten berechnen einen Confidence-Score basierend auf mehreren Faktoren:

```python
score = (
    skill_match * 0.6 +        # Primär: Skill-Matching
    io_compatibility * 0.2 +   # Input/Output-Format-Unterstützung
    performance * 0.1 +        # Geschwindigkeit und Zuverlässigkeit
    load * 0.05 +              # Aktuelle Verfügbarkeit
    cost * 0.05                # Preisgestaltung
)
```

### 🎯 Skill-Assessment

<details>
<summary><b>Assessment-Metadaten-Beispiel anzeigen</b> (zum Erweitern klicken)</summary>

Skills enthalten Assessment-Metadaten für intelligentes Matching:

```yaml
assessment:
  keywords:
    - pdf
    - extract
    - table
    - invoice

  specializations:
    - domain: invoice_processing
      confidence_boost: 0.3
    - domain: table_extraction
      confidence_boost: 0.2

  anti_patterns:
    - "pdf editing"
    - "pdf creation"

  complexity_indicators:
    simple:
      - "single page"
      - "extract text"
    complex:
      - "scanned document"
      - "batch processing"
```

</details>

### 💡 Beispiel: Multi-Agenten-Auswahl

```bash
# Frage 10 Übersetzungs-Agenten ab
for agent in translation-agents:
  curl http://$agent:3773/agent/negotiation \
    -d '{"task_summary": "Übersetze technisches Handbuch ins Spanische"}'

# Antworten vom Orchestrator gerankt
# Agent 1: score=0.98 (technischer Spezialist, queue=2)
# Agent 2: score=0.82 (allgemeiner Übersetzer, queue=0)
# Agent 3: score=0.65 (keine technische Spezialisierung)
```

### ⚙️ Konfiguration

<details>
<summary><b>Konfigurationsbeispiel anzeigen</b> (zum Erweitern klicken)</summary>

Aktiviere Negotiation in deiner Agenten-Konfiguration:

```json
config = {
    "author": "deine.email@beispiel.de",
    "name": "research_agent",
    "description": "Ein Recherche-Assistenten-Agent",
    "deployment": {"url": "http://localhost:3773", "expose": True},
    "skills": ["skills/question-answering", "skills/pdf-processing"],
    "storage": {
        "type": "postgres",
        "database_url": "postgresql+asyncpg://bindu:bindu@localhost:5432/bindu",  # pragma: allowlist secret
        "run_migrations_on_startup": False,
    },
    "negotiation": {
        "embedding_api_key": os.getenv("OPENROUTER_API_KEY"),  # Aus Umgebung laden
    },
}
```

</details>

> 📚 Siehe die [Negotiation-Dokumentation](https://docs.getbindu.com/bindu/negotiation/overview) für alle Details.

---

<br/>

## Task-Feedback und DSPy

Bindu sammelt Benutzer-Feedback zu Task-Ausführungen, um kontinuierliche Verbesserung durch DSPy-Optimierung zu ermöglichen. Durch das Speichern von Feedback mit Bewertungen und Metadaten kannst du Golden Datasets aus echten Interaktionen erstellen und DSPy verwenden, um die Prompts und das Verhalten deines Agenten automatisch zu optimieren.

### Feedback einreichen

Gib Feedback zu jedem Task mit der `tasks/feedback`-Methode:

```bash
curl --location 'http://localhost:3773/' \
--header 'Content-Type: application/json' \
--header 'Authorization: Bearer <dein-token>' \
--data '{
    "jsonrpc": "2.0",
    "method": "tasks/feedback",
    "params": {
        "taskId": "550e8400-e29b-41d4-a716-446655440200",
        "feedback": "Großartige Arbeit! Die Antwort war sehr hilfreich und präzise.",
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

Feedback wird in der `task_feedback`-Tabelle gespeichert und kann verwendet werden, um:
- Hochwertige Task-Interaktionen für Trainingsdaten zu filtern
- Muster in erfolgreichen vs. erfolglosen Abschlüssen zu identifizieren
- Agenten-Anweisungen und Few-Shot-Beispiele mit DSPy zu optimieren
- Wir arbeiten an der DSPy-Integration – wird bald veröffentlicht.

---

<br/>

## 📬 Push-Benachrichtigungen

Bindu unterstützt **Echtzeit-Webhook-Benachrichtigungen** für lang laufende Tasks, gemäß der [A2A-Protokoll-Spezifikation](https://a2a-protocol.org/latest/specification/). Dies ermöglicht es Clients, Push-Benachrichtigungen über Task-Statusänderungen und Artifact-Generierung zu erhalten, ohne zu pollen.

### Schnellstart

1. **Webhook-Empfänger starten:** `python examples/webhook_client_example.py`
2. **Agent konfigurieren** in `examples/echo_agent_with_webhooks.py`:
   ```python
   manifest = {
       "capabilities": {"push_notifications": True},
       "global_webhook_url": "http://localhost:8000/webhooks/task-updates",
       "global_webhook_token": "secret_abc123",
   }
   ```
3. **Agent ausführen:** `python examples/echo_agent_with_webhooks.py`
4. **Tasks senden** - Webhook-Benachrichtigungen kommen automatisch an

<details>
<summary><b>Webhook-Empfänger-Implementierung anzeigen</b> (zum Erweitern klicken)</summary>

```python
from fastapi import FastAPI, Request, Header, HTTPException

@app.post("/webhooks/task-updates")
async def handle_task_update(request: Request, authorization: str = Header(None)):
    if authorization != "Bearer secret_abc123":
        raise HTTPException(status_code=401)

    event = await request.json()

    if event["kind"] == "status-update":
        print(f"Task {event['task_id']} Status: {event['status']['state']}")
    elif event["kind"] == "artifact-update":
        print(f"Artifact generiert: {event['artifact']['name']}")

    return {"status": "received"}
```

</details>

<details>
<summary><b>Benachrichtigungs-Event-Typen anzeigen</b> (zum Erweitern klicken)</summary>

<br/>

**Status-Update-Event** - Gesendet, wenn sich der Task-Status ändert:
```json
{
  "kind": "status-update",
  "task_id": "123e4567-...",
  "status": {"state": "working"},
  "final": false
}
```

**Artifact-Update-Event** - Gesendet, wenn Artifacts generiert werden:
```json
{
  "kind": "artifact-update",
  "task_id": "123e4567-...",
  "artifact": {
    "artifact_id": "456e7890-...",
    "name": "results.json",
    "parts": [...]
  }
}
```

</details>

### ⚙️ Konfiguration

<details>
<summary><b>Konfigurationsbeispiel anzeigen</b> (zum Erweitern klicken)</summary>

**Mit `bindufy`:**

```python
from bindu.penguin.bindufy import bindufy

def handler(messages):
    return [{"role": "assistant", "content": messages[-1]["content"]}]

config = {
    "author": "du@beispiel.de",
    "name": "my_agent",
    "description": "Agent mit Push-Benachrichtigungen",
    "deployment": {"url": "http://localhost:3773"},
    "capabilities": {"push_notifications": True},
    "global_webhook_url": "https://myapp.com/webhooks/global",
    "global_webhook_token": "global_secret"
}

bindufy(config, handler)
```

**Per-Task-Webhook-Override:**

```python
"configuration": {
    "long_running": True,  # Webhook in Datenbank persistieren
    "push_notification_config": {
        "id": str(uuid4()),
        "url": "https://custom-endpoint.com/webhooks",
        "token": "custom_token_123"
    }
}
```

**Lang laufende Tasks:**

Für Tasks, die länger als typische Request-Timeouts laufen (Minuten, Stunden oder Tage), setze `long_running=True`, um Webhook-Konfigurationen über Server-Neustarts hinweg zu persistieren. Die Webhook-Konfiguration wird in der Datenbank gespeichert (`webhook_configs`-Tabelle).

</details>

📖 **[Vollständige Dokumentation](docs/NOTIFICATIONS.md)** - Detaillierter Leitfaden mit Architektur, Sicherheit, Beispielen und Troubleshooting.

---

<br/>

## 🎨 Chat-UI

Bindu enthält eine wunderschöne Chat-Oberfläche unter `http://localhost:3773/docs`

<p align="center">
  <img src="assets/agent-ui.png" alt="Bindu Agent UI" width="640" style="border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);" />
</p>

---

<br/>

## 🌐 Bindu Directory

Das [**Bindu Directory**](https://bindus.directory) ist ein öffentliches Verzeichnis aller Bindu-Agenten, das sie für das breitere Agenten-Ökosystem entdeckbar und zugänglich macht.

### ✨ Automatische Registrierung mit Cookiecutter

Wenn du einen Agenten mit dem Cookiecutter-Template erstellst, enthält er eine vorkonfigurierte GitHub Action, die deinen Agenten automatisch im Verzeichnis registriert:

1. **Erstelle deinen Agenten** mit Cookiecutter
2. **Push zu GitHub** - Die GitHub Action wird automatisch ausgelöst
3. **Dein Agent erscheint** im [Bindu Directory](https://bindus.directory)

> **🔑 Hinweis**: Du musst das BINDU_PAT_TOKEN von bindus.directory sammeln und es verwenden, um deinen Agenten zu registrieren.

### 📝 Manuelle Registrierung

Wir arbeiten an einem manuellen Registrierungsprozess.

---

<br/>

## 🌌 Die Vision

```
ein Blick in den Nachthimmel
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

_Jedes Symbol ist ein Agent – ein Funke von Intelligenz. Der winzige Punkt ist Bindu, der Ursprungspunkt im Internet of Agents._

### NightSky-Verbindung [In Arbeit]

NightSky ermöglicht Schwärme von Agenten. Jeder Bindu ist ein Punkt, der Agenten mit der gemeinsamen Sprache von A2A, AP2 und X402 annotiert. Agenten können überall gehostet werden – auf Laptops, in Clouds oder Clustern – sprechen aber dasselbe Protokoll, vertrauen einander by Design und arbeiten zusammen als ein einziger, verteilter Geist.

> **💭 Ein Ziel ohne Plan ist nur ein Wunsch.**

---


<br/>

## 🛠️ Unterstützte Agenten-Frameworks

Bindu ist **framework-agnostisch** und getestet mit:

- **Agno**
- **CrewAI**
- **LangChain**
- **LlamaIndex**
- **FastAgent**

Möchtest du Integration mit deinem Lieblings-Framework? [Lass es uns auf Discord wissen](https://discord.gg/3w5zuYUuwt)!

---

<br/>

## 🧪 Testing

Bindu hält **70%+ Test-Coverage**:

```bash
uv run pytest -n auto --cov=bindu --cov-report= && coverage report --skip-covered --fail-under=70
```

---

<br/>

## Troubleshooting
<details>
<summary>Häufige Probleme</summary>

<br/>

| Problem | Lösung |
|---------|----------|
| `Python 3.12 not found` | Installiere Python 3.12+ und setze es in PATH, oder verwende `pyenv` |
| `bindu: command not found` | Aktiviere virtuelle Umgebung: `source .venv/bin/activate` |
| `Port 3773 already in use` | Ändere Port in Konfiguration: `"url": "http://localhost:4000"` |
| Pre-commit schlägt fehl | Führe `pre-commit run --all-files` aus |
| Tests schlagen fehl | Installiere Dev-Abhängigkeiten: `uv sync --dev` |
| `Permission denied` (macOS) | Führe `xattr -cr .` aus, um erweiterte Attribute zu löschen |

**Umgebung zurücksetzen:**
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

## 🤝 Beitragen

Wir freuen uns über Beiträge! Tritt uns auf [Discord](https://discord.gg/3w5zuYUuwt) bei. Wähle den Kanal, der am besten zu deinem Beitrag passt.

```bash
git clone https://github.com/getbindu/Bindu.git
cd Bindu
uv venv --python 3.12.9
source .venv/bin/activate
uv sync --dev
pre-commit run --all-files
```

> 📖 [Beitrags-Richtlinien](.github/contributing.md)

---

<br/>

## 📜 Lizenz

Bindu ist Open-Source unter der [Apache License 2.0](https://choosealicense.com/licenses/apache-2.0/).

---

<br/>

## 💬 Community

Wir 💛 Beiträge! Ob du Bugs behebst, Dokumentation verbesserst oder Demos baust – deine Beiträge machen Bindu besser.

- 💬 [Tritt Discord bei](https://discord.gg/3w5zuYUuwt) für Diskussionen und Support
- ⭐ [Markiere das Repository mit einem Stern](https://github.com/getbindu/Bindu), wenn du es nützlich findest!

---

<br/>

## 👥 Aktive Moderatoren

Unsere engagierten Moderatoren helfen dabei, eine einladende und produktive Community zu pflegen:

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

> Möchtest du Moderator werden? Melde dich auf [Discord](https://discord.gg/3w5zuYUuwt)!

---

<br/>

## 🙏 Danksagungen

Dankbar für diese Projekte:

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

- [ ] GRPC-Transport-Unterstützung
- [x] Sentry-Fehler-Tracking
- [x] Ag-UI-Integration
- [x] Retry-Mechanismus
- [ ] Test-Coverage auf 80% erhöhen - In Arbeit
- [x] Redis-Scheduler-Implementierung
- [x] Postgres-Datenbank für Memory-Storage
- [x] Negotiation-Unterstützung
- [ ] AP2-End-to-End-Unterstützung
- [ ] DSPy-Integration - In Arbeit
- [ ] MLTS-Unterstützung
- [ ] X402-Unterstützung mit anderen Facilitators

> 💡 [Schlage Features auf Discord vor](https://discord.gg/3w5zuYUuwt)!

---

<br/>

## 🎓 Workshops

- [AI Native in Action: Agent Symphony](https://www.meetup.com/ai-native-amsterdam/events/311066899/) - [Folien](https://docs.google.com/presentation/d/1SqGXI0Gv_KCWZ1Mw2SOx_kI0u-LLxwZq7lMSONdl8oQ/edit)

---

<br/>

## ⭐ Star-Historie

[![Star History Chart](https://api.star-history.com/svg?repos=getbindu/Bindu&type=Date)](https://www.star-history.com/#getbindu/Bindu&Date)

---

<p align="center">
  <strong>Mit 💛 gebaut vom Team aus Amsterdam</strong><br/>
  <em>Happy Bindu! 🌻🚀✨</em>
</p>

<p align="center">
  <strong>Von der Idee zum Internet of Agents in 2 Minuten.</strong><br/>
  <em>Dein Agent. Dein Framework. Universelle Protokolle.</em>
</p>

<p align="center">
  <a href="https://github.com/getbindu/Bindu">⭐ Markiere uns auf GitHub mit einem Stern</a> •
  <a href="https://discord.gg/3w5zuYUuwt">💬 Tritt Discord bei</a> •
  <a href="https://docs.getbindu.com">🌻 Lies die Docs</a>
</p>
