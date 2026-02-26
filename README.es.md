<div align="center" id="top">
  <a href="https://getbindu.com">
    <picture>
      <img src="assets/bindu.png" alt="Bindu" width="300">
    </picture>
  </a>
</div>

<p align="center">
  <em>Capa de identidad, comunicación y pagos para agentes de IA</em>
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

**Bindu** (pronunciación: _bin-du_) es una capa operativa para agentes de IA que proporciona capacidades de identidad, comunicación y pagos. Es un servicio listo para producción que conecta, autentica y orquesta agentes a través de sistemas distribuidos con APIs convenientes – utilizando protocolos abiertos: **A2A**, **AP2**, y **X402**.

Construido con una arquitectura distribuida (Task Manager, scheduler, storage), Bindu hace que sea sencillo desarrollar rápidamente e integrarse con cualquier framework de IA. Transforma cualquier framework de agentes en un servicio completamente interoperable para comunicación, colaboración y comercio en el Internet of Agents.

<p align="center">
  <strong>🌟 <a href="https://bindus.directory">Registra tu agente</a> • 🌻 <a href="https://docs.getbindu.com">Documentación</a> • 💬 <a href="https://discord.gg/3w5zuYUuwt">Comunidad Discord</a></strong>
</p>

---

<br/>

## 🎥 Ve Bindu en acción

<div align="center">
  <a href="https://www.youtube.com/watch?v=qppafMuw_KI" target="_blank">
    <img src="https://img.youtube.com/vi/qppafMuw_KI/maxresdefault.jpg" alt="Bindu Demo" width="640" style="border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);" />
  </a>
</div>

## 📋 Requisitos

Antes de instalar Bindu, asegúrate de tener:

- **Python 3.12 o superior** - [Descarga aquí](https://www.python.org/downloads/)
- **UV Package Manager** - [Guía de instalación](https://github.com/astral-sh/uv)
- **Se requiere API Key**: configura `OPENROUTER_API_KEY` o `OPENAI_API_KEY` en tus variables de entorno. Hay modelos gratuitos de OpenRouter disponibles para pruebas.

### Verifica tu configuración

```bash
# Verifica la versión de Python
uv run python --version  # Debe mostrar 3.12 o superior

# Verifica la instalación de UV
uv --version
```

---

<br/>

## 📦 Instalación

<details>
<summary><b>Nota para usuarios de Windows (Git & GitHub Desktop)</b></summary>

En algunos sistemas Windows, git puede no ser reconocido en el Command Prompt incluso después de la instalación – debido a problemas de configuración de PATH.

Si encuentras este problema, puedes usar *GitHub Desktop* como alternativa:

1. Instala GitHub Desktop desde https://desktop.github.com/
2. Inicia sesión con tu cuenta de GitHub
3. Clona usando la URL del repositorio:
   https://github.com/getbindu/Bindu.git

GitHub Desktop te permite clonar repositorios, gestionar ramas, hacer commits de cambios y abrir pull requests sin la línea de comandos.

</details>

```bash
# Instala Bindu
uv add bindu

# Para desarrollo (si estás contribuyendo a Bindu)
# Crea y activa un entorno virtual
uv venv --python 3.12.9
source .venv/bin/activate  # En macOS/Linux
# .venv\Scripts\activate  # En Windows

uv sync --dev
```

<details>
<summary><b>Problemas comunes de instalación</b> (Haz clic para expandir)</summary>

<br/>

| Problema | Solución |
|-------|----------|
| `uv: command not found` | Reinicia la terminal después de instalar UV. Usa PowerShell en Windows |
| `Python version not supported` | Instala Python 3.12+ desde [python.org](https://www.python.org/downloads/) |
| El entorno virtual no se activa (Windows) | Usa PowerShell y ejecuta `.venv\Scripts\activate` |
| `Microsoft Visual C++ required` | Descarga [Visual C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/) |
| `ModuleNotFoundError` | Activa venv y ejecuta `uv sync --dev` |

</details>

---

<br/>

## 🚀 Inicio rápido

### Opción 1: Usa Cookiecutter (Recomendado)

**Tiempo hasta el primer agente: ~2 minutos ⏱️**

```bash
# Instala Cookiecutter
uv add cookiecutter

# Crea tu agente Bindu
uvx cookiecutter https://github.com/getbindu/create-bindu-agent.git
```

## 🎥 Construye agentes listos para producción en minutos

<div align="center">
  <a href="https://youtu.be/obY1bGOoWG8?si=uEeDb0XWrtYOQTL7" target="_blank">
    <img src="https://img.youtube.com/vi/obY1bGOoWG8/maxresdefault.jpg" alt="Bindu Demo" width="640" style="border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);" />
  </a>
</div>

¡Eso es todo! Tu agente local ahora es un servicio en vivo, seguro y descubrible. [Aprende más →](https://docs.getbindu.com/bindu/create-bindu-agent/overview)

> **💡 Consejo profesional:** Los agentes creados con Cookiecutter incluyen GitHub Actions que registran automáticamente tu agente en el [Bindu Directory](https://bindus.directory) cuando haces push a tu repositorio. ¡No se necesita registro manual!

### Opción 2: Configuración manual

Crea tu script de agente `my_agent.py`:

```python
from bindu.penguin.bindufy import bindufy
from agno.agent import Agent
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.models.openai import OpenAIChat

# Define tu agente
agent = Agent(
    instructions="Eres un asistente de investigación que encuentra y resume información.",
    model=OpenAIChat(id="gpt-4o"),
    tools=[DuckDuckGoTools()],
)

# Configuración
config = {
    "author": "your.email@example.com",
    "name": "research_agent",
    "description": "Un agente asistente de investigación",
    "deployment": {"url": "http://localhost:3773", "expose": True},
    "skills": ["skills/question-answering", "skills/pdf-processing"]
}

# Función handler
def handler(messages: list[dict[str, str]]):
    """Procesa mensajes y devuelve la respuesta del agente.

    Args:
        messages: Lista de diccionarios de mensajes con historial de conversación

    Returns:
        Resultado de la respuesta del agente
    """
    result = agent.run(input=messages)
    return result

# Bindu-fy
bindufy(config, handler)
```

![Sample Agent](assets/agno-simple.png)

Tu agente ahora está en vivo en `http://localhost:3773` y listo para comunicarse con otros agentes.

---

### Opción 3: Agente Echo mínimo (Pruebas)

<details>
<summary><b>Ver ejemplo mínimo</b> (Haz clic para expandir)</summary>

El agente funcional más pequeño:

```python
from bindu.penguin.bindufy import bindufy

def handler(messages):
    return [{"role": "assistant", "content": messages[-1]["content"]}]

config = {
    "author": "your.email@example.com",
    "name": "echo_agent",
    "description": "Un agente echo básico para pruebas rápidas.",
    "deployment": {"url": "http://localhost:3773", "expose": True},
    "skills": []
}

bindufy(config, handler)
```

**Ejecutar y probar:**

```bash
# Inicia el agente
python examples/echo_agent.py
```

</details>

<details>
<summary><b>Prueba el agente con curl</b> (Haz clic para expandir)</summary>

<br/>

Entrada:
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

Salida:
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

Verifica el estado de la tarea
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

Salida:
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

Bindu utiliza PostgreSQL como su backend de almacenamiento persistente para implementaciones en producción. La capa de almacenamiento está construida con el motor asíncrono de SQLAlchemy y utiliza mapeo imperativo con protocol TypeDicts.

Esto es opcional – por defecto se usa InMemoryStorage.

### 📊 Estructura de almacenamiento

La capa de almacenamiento utiliza tres tablas principales:

1. **tasks_table**: Almacena todas las tareas con historial JSONB y artefactos
2. **contexts_table**: Mantiene metadatos de contexto e historial de mensajes
3. **task_feedback_table**: Almacenamiento opcional de feedback para tareas

### ⚙️ Configuración

<details>
<summary><b>Ver ejemplo de configuración</b> (Haz clic para expandir)</summary>

Configura la conexión PostgreSQL en tu entorno o configuración:
Proporciona la cadena de conexión en la configuración del agente.

```json
config = {
    "author": "your.email@example.com",
    "name": "research_agent",
    "description": "Un agente asistente de investigación",
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

**💡 Patrón Task-First**: El almacenamiento soporta el enfoque task-first de Bindu donde las tareas pueden continuar agregando mensajes a tareas no terminales, permitiendo refinamientos incrementales y conversaciones de múltiples turnos.

---

<br/>

## [Redis Scheduler](https://docs.getbindu.com/bindu/learn/scheduler/overview)

Bindu utiliza Redis como su planificador de tareas distribuido para coordinar el trabajo entre múltiples workers y procesos. El planificador usa listas de Redis con operaciones de bloqueo para una distribución eficiente de tareas.

Esto es opcional – por defecto se usa InMemoryScheduler.

### ⚙️ Configuración

<details>
<summary><b>Ver ejemplo de configuración</b> (Haz clic para expandir)</summary>

Configura la conexión Redis en tu configuración de agente:

```json
config = {
    "author": "your.email@example.com",
    "name": "research_agent",
    "description": "Un agente asistente de investigación",
    "deployment": {"url": "http://localhost:3773", "expose": True},
    "skills": ["skills/question-answering", "skills/pdf-processing"],
     "scheduler": {
        "type": "redis",
        "redis_url": "redis://localhost:6379/0",
    },
}
```

</details>

Todas las operaciones se ponen en cola en Redis y son procesadas por workers disponibles usando un mecanismo de pop bloqueante, garantizando una distribución eficiente sin sobrecarga de polling.

---

<br/>

## [Retry Mechanism](https://docs.getbindu.com/bindu/learn/retry/overview)

> Lógica de reintento automática con retroceso exponencial para agentes Bindu resilientes

Bindu tiene un mecanismo de reintento integrado basado en Tenacity que maneja elegantemente fallos transitorios en workers, storage, schedulers y llamadas API. Esto asegura que tus agentes permanezcan resilientes en entornos de producción.

### ⚙️ Configuración predeterminada

Si no está configurado, Bindu usa estos valores predeterminados:

| Tipo de operación | Intentos máx. | Espera mín. | Espera máx. |
| -------------- | ------------ | -------- | -------- |
| Worker         | 3            | 1.0s     | 10.0s    |
| Storage        | 5            | 0.5s     | 5.0s     |
| Scheduler      | 3            | 1.0s     | 8.0s     |
| API            | 4            | 1.0s     | 15.0s    |

---

<br/>

## [Sentry Integration](https://docs.getbindu.com/bindu/learn/sentry/overview)

> Seguimiento de errores en tiempo real y monitoreo de rendimiento para agentes Bindu

Sentry es una plataforma de seguimiento de errores y monitoreo de rendimiento en tiempo real que te ayuda a identificar, diagnosticar y corregir problemas en producción. Bindu tiene integración Sentry incorporada para proporcionar observabilidad completa para tus agentes de IA.

### ⚙️ Configuración

<details>
<summary><b>Ver ejemplo de configuración</b> (Haz clic para expandir)</summary>

Configura Sentry directamente en tu configuración de `bindufy()`:

```python
config = {
    "author": "gaurikasethi88@gmail.com",
    "name": "echo_agent",
    "description": "Un agente echo básico para pruebas rápidas.",
    "deployment": {"url": "http://localhost:3773", "expose": True},
    "skills": [],
    "storage": {
        "type": "postgres",
        "database_url": "postgresql+asyncpg://bindu:bindu@localhost:5432/bindu",  # pragma: allowlist secret
        "run_migrations_on_startup": False,
    },
    # Configuración del Scheduler (opcional)
    # Usa "memory" (predeterminado) para proceso único o "redis" para multi-proceso distribuido
    "scheduler": {
        "type": "redis",
        "redis_url": "redis://localhost:6379/0",
    },
    # Seguimiento de errores Sentry (opcional)
    # Configura Sentry directamente en el código en lugar de variables de entorno
    "sentry": {
        "enabled": True,
        "dsn": "https://252c0197ddeafb621f91abdbb59fa819@o4510504294612992.ingest.de.sentry.io/4510504299069520",
        "environment": "development",
        "traces_sample_rate": 1.0,
        "profiles_sample_rate": 0.1,
    },
}

def handler(messages):
    # Tu lógica de agente
    pass

bindufy(config, handler)
```

</details>

### 🚀 Comenzando

1. **Crea una cuenta Sentry**: Regístrate en [sentry.io](https://sentry.io)
2. **Obtén tu DSN**: Copia desde la configuración del proyecto
3. **Configura Bindu**: Agrega la configuración `sentry` (ver arriba)
4. **Ejecuta tu agente**: Sentry se inicializa automáticamente

> 📚 Consulta la [documentación completa de Sentry](https://docs.getbindu.com/bindu/learn/sentry/overview) para detalles completos.

---

<br/>

## [Skills System](https://docs.getbindu.com/bindu/skills/introduction/overview)

> Publicidad rica de capacidades para orquestación inteligente de agentes

El Bindu Skills System proporciona publicidad rica de capacidades de agentes para orquestación inteligente y descubrimiento de agentes. Inspirado en la arquitectura de skills de Claude, permite a los agentes proporcionar documentación detallada sobre sus capacidades para que los orquestadores puedan tomar decisiones de enrutamiento informadas.

### 💡 ¿Qué son las Skills?

En Bindu, las Skills actúan como **metadatos de publicidad ricos** que ayudan a los orquestadores a:

* 🔍 **Descubrir** el agente correcto para una tarea
* 📖 **Entender** capacidades y limitaciones detalladas
* ✅ **Verificar** requisitos antes de la ejecución
* 📊 **Estimar** rendimiento y necesidades de recursos
* 🔗 **Encadenar** múltiples agentes inteligentemente

> **Nota**: Las Skills no son código ejecutable—son metadatos estructurados que describen lo que tu agente puede hacer.

### 🔌 Endpoints API

**Listar todas las Skills**:
```bash
GET /agent/skills
```

**Obtener detalles de Skill**:
```bash
GET /agent/skills/{skill_id}
```

**Obtener documentación de Skill**:
```bash
GET /agent/skills/{skill_id}/documentation
```

> 📚 Consulta la [documentación de Skills](https://github.com/getbindu/Bindu/tree/main/examples/skills) para ejemplos completos.

---

<br/>

## Negotiation

> Selección de agentes basada en capacidades para orquestación inteligente

El sistema de negociación de Bindu permite a los orquestadores consultar múltiples agentes y seleccionar inteligentemente el mejor agente para una tarea basándose en skills, rendimiento, carga y costo.

### 🔄 Cómo funciona

1. **El orquestador transmite** solicitud de evaluación a múltiples agentes
2. **Los agentes se autoevalúan** la capacidad usando coincidencia de skills y análisis de carga
3. **El orquestador clasifica** las respuestas usando puntuación multifactorial
4. **Se selecciona el mejor agente** y se ejecuta la tarea

### 🔌 Endpoint de evaluación

<details>
<summary><b>Ver detalles de API</b> (Haz clic para expandir)</summary>

```bash
POST /agent/negotiation
```

**Solicitud:**
```json
{
  "task_summary": "Extraer tablas de facturas PDF",
  "task_details": "Procesar PDFs de facturas y extraer datos estructurados",
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

**Respuesta:**
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

### 📊 Algoritmo de puntuación

Los agentes calculan una puntuación de confianza basada en múltiples factores:

```python
score = (
    skill_match * 0.6 +        # Primario: coincidencia de skills
    io_compatibility * 0.2 +   # Soporte de formato entrada/salida
    performance * 0.1 +        # Velocidad y confiabilidad
    load * 0.05 +              # Disponibilidad actual
    cost * 0.05                # Precio
)
```

> 📚 Consulta la [documentación de Negotiation](https://docs.getbindu.com/bindu/negotiation/overview) para detalles completos.

---

<br/>

## Task Feedback y DSPy

Bindu recopila feedback de usuarios en ejecuciones de tareas para permitir mejora continua a través de optimización DSPy. Al almacenar feedback con calificaciones y metadatos, puedes construir conjuntos de datos dorados a partir de interacciones reales y usar DSPy para optimizar automáticamente los prompts y el comportamiento de tu agente.

### Enviar feedback

Proporciona feedback sobre cualquier tarea usando el método `tasks/feedback`:

```bash
curl --location 'http://localhost:3773/' \
--header 'Content-Type: application/json' \
--header 'Authorization: Bearer <your-token>' \
--data '{
    "jsonrpc": "2.0",
    "method": "tasks/feedback",
    "params": {
        "taskId": "550e8400-e29b-41d4-a716-446655440200",
        "feedback": "¡Excelente trabajo! La respuesta fue muy útil y precisa.",
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

El feedback se almacena en la tabla `task_feedback` y puede usarse para:
- Filtrar interacciones de tareas de alta calidad para datos de entrenamiento
- Identificar patrones en completaciones exitosas vs. fallidas
- Optimizar instrucciones de agentes y ejemplos few-shot con DSPy
- Estamos trabajando en DsPY - próximamente disponible.

---

<br/>

## 📬 Push Notifications

Bindu soporta **notificaciones webhook en tiempo real** para tareas de larga duración, siguiendo la [especificación del Protocolo A2A](https://a2a-protocol.org/latest/specification/). Esto permite a los clientes recibir notificaciones push sobre cambios de estado de tareas y generación de artefactos sin polling.

### Inicio rápido

1. **Inicia el receptor webhook:** `python examples/webhook_client_example.py`
2. **Configura el agente** en `examples/echo_agent_with_webhooks.py`:
   ```python
   manifest = {
       "capabilities": {"push_notifications": True},
       "global_webhook_url": "http://localhost:8000/webhooks/task-updates",
       "global_webhook_token": "secret_abc123",
   }
   ```
3. **Ejecuta el agente:** `python examples/echo_agent_with_webhooks.py`
4. **Envía tareas** - las notificaciones webhook llegan automáticamente

📖 **[Documentación completa](docs/long-running-task-notifications.md)** - Guía detallada con arquitectura, seguridad, ejemplos y solución de problemas.

---

<br/>

## 🎨 Chat UI

Bindu incluye una hermosa interfaz de chat en `http://localhost:3773/docs`

<p align="center">
  <img src="assets/agent-ui.png" alt="Bindu Agent UI" width="640" style="border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);" />
</p>

---

<br/>

## 🌐 Bindu Directory

El [**Bindu Directory**](https://bindus.directory) es un registro público de todos los agentes Bindu, haciéndolos descubribles y accesibles para el ecosistema de agentes más amplio.

### ✨ Registro automático con Cookiecutter

Cuando creas un agente usando la plantilla cookiecutter, incluye una GitHub Action preconfigurada que registra automáticamente tu agente en el directorio:

1. **Crea tu agente** usando cookiecutter
2. **Haz push a GitHub** - La GitHub Action se activa automáticamente
3. **Tu agente aparece** en el [Bindu Directory](https://bindus.directory)

> **🔑 Nota**: Necesitas recopilar el BINDU_PAT_TOKEN de bindus.directory y usarlo para registrar tu agente.

### 📝 Registro manual

Estamos trabajando en un proceso de registro manual.

---

<br/>

## 🌌 La Visión

```
una mirada al cielo nocturno
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

_Cada símbolo es un agente – una chispa de inteligencia. El pequeño punto es Bindu, el punto de origen en el Internet of Agents._

### Conexión NightSky [En progreso]

NightSky habilita enjambres de agentes. Cada Bindu es un punto que anota agentes con el lenguaje compartido de A2A, AP2 y X402. Los agentes pueden alojarse en cualquier lugar – laptops, nubes o clusters – pero hablan el mismo protocolo, confían entre sí por diseño y trabajan juntos como una única mente distribuida.

> **💭 Un objetivo sin plan es solo un deseo.**

---

<br/>

## 🛠️ Frameworks de agentes soportados

Bindu es **agnóstico al framework** y está probado con:

- **Agno**
- **CrewAI**
- **LangChain**
- **LlamaIndex**
- **FastAgent**

¿Quieres integración con tu framework favorito? [¡Háznoslo saber en Discord](https://discord.gg/3w5zuYUuwt)!

---

<br/>

## 🧪 Pruebas

Bindu mantiene **70%+ de cobertura de pruebas**:

```bash
pytest -n auto --cov=bindu --cov-report= && coverage report --skip-covered --fail-under=70
```

---

<br/>

## Solución de problemas

<details>
<summary>Problemas comunes</summary>

<br/>

| Problema | Solución |
|---------|----------|
| `Python 3.12 not found` | Instala Python 3.12+ y configúralo en PATH, o usa `pyenv` |
| `bindu: command not found` | Activa el entorno virtual: `source .venv/bin/activate` |
| `Port 3773 already in use` | Cambia el puerto en la configuración: `"url": "http://localhost:4000"` |
| Pre-commit falla | Ejecuta `pre-commit run --all-files` |
| Las pruebas fallan | Instala dependencias de desarrollo: `uv sync --dev` |
| `Permission denied` (macOS) | Ejecuta `xattr -cr .` para limpiar atributos extendidos |

**Reiniciar entorno:**
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

## 🤝 Contribuir

¡Damos la bienvenida a las contribuciones! Únete a nosotros en [Discord](https://discord.gg/3w5zuYUuwt). Elige el canal que mejor se adapte a tu contribución.

```bash
git clone https://github.com/getbindu/Bindu.git
cd Bindu
uv venv --python 3.12.9
source .venv/bin/activate
uv sync --dev
pre-commit run --all-files
```

> 📖 [Guías de contribución](.github/contributing.md)

---

<br/>

## 📜 Licencia

Bindu es de código abierto bajo la [Apache License 2.0](https://choosealicense.com/licenses/apache-2.0/).

---

<br/>

## 💬 Comunidad

¡Nos 💛 las contribuciones! Ya sea que estés corrigiendo bugs, mejorando documentación o construyendo demos – tus contribuciones hacen que Bindu sea mejor.

- 💬 [Únete a Discord](https://discord.gg/3w5zuYUuwt) para discusiones y soporte
- ⭐ [Dale una estrella al repositorio](https://github.com/getbindu/Bindu) si lo encuentras útil!

---

<br/>

## 👥 Moderadores activos

Nuestros moderadores dedicados ayudan a mantener una comunidad acogedora y productiva:

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

> ¿Quieres convertirte en moderador? ¡Contáctanos en [Discord](https://discord.gg/3w5zuYUuwt)!

---

<br/>

## 🙏 Agradecimientos

Agradecidos a estos proyectos:

- [FastA2A](https://github.com/pydantic/fasta2a)
- [12 Factor Agents](https://github.com/humanlayer/12-factor-agents/blob/main/content/factor-11-trigger-from-anywhere.md)
- [A2A](https://github.com/a2aproject/A2A)
- [AP2](https://github.com/google-agentic-commerce/AP2)
- [X402](https://github.com/coinbase/x402)
- [Bindu Logo](https://openmoji.org/library/emoji-1F33B/)
- [ASCII Space Art](https://www.asciiart.eu/space/other)

---

<br/>

## 🗺️ Hoja de ruta

- [ ] Soporte de transporte GRPC
- [x] Seguimiento de errores Sentry
- [x] Integración Ag-UI
- [x] Mecanismo de reintento
- [ ] Aumentar cobertura de pruebas al 80% - En progreso
- [x] Implementación del planificador Redis
- [x] Base de datos Postgres para almacenamiento de memoria
- [x] Soporte de negociación
- [ ] Soporte AP2 de extremo a extremo
- [ ] Integración DSPy - En progreso
- [ ] Soporte MLTS
- [ ] Soporte X402 con otros facilitadores

> 💡 [¡Sugiere características en Discord](https://discord.gg/3w5zuYUuwt)!

---

<br/>

## 🎓 Talleres

- [AI Native in Action: Agent Symphony](https://www.meetup.com/ai-native-amsterdam/events/311066899/) - [Diapositivas](https://docs.google.com/presentation/d/1SqGXI0Gv_KCWZ1Mw2SOx_kI0u-LLxwZq7lMSONdl8oQ/edit)

---

<br/>

## ⭐ Historial de estrellas

[![Star History Chart](https://api.star-history.com/svg?repos=getbindu/Bindu&type=Date)](https://www.star-history.com/#getbindu/Bindu&Date)

---

<p align="center">
  <strong>Construido con 💛 por el equipo de Ámsterdam</strong><br/>
  <em>¡Happy Bindu! 🌻🚀✨</em>
</p>

<p align="center">
  <strong>De la idea al Internet of Agents en 2 minutos.</strong><br/>
  <em>Tu agente. Tu framework. Protocolos universales.</em>
</p>

<p align="center">
  <a href="https://github.com/getbindu/Bindu">⭐ Danos una estrella en GitHub</a> •
  <a href="https://discord.gg/3w5zuYUuwt">💬 Únete a Discord</a> •
  <a href="https://docs.getbindu.com">🌻 Lee los Docs</a>
</p>
