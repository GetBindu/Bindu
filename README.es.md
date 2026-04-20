<div align="center" id="top">
  <a href="https://getbindu.com">
    <picture>
      <img src="assets/bindu.png" alt="Bindu" width="300">
    </picture>
  </a>
</div>

<p align="center">
  <em>La capa de identidad, comunicación y pagos para agentes de IA</em>
</p>

<p align="center">
  <a href="README.md">🇬🇧 Inglés</a> •
  <a href="README.de.md">🇩🇪 Alemán</a> •
  <a href="README.es.md">🇪🇸 Español</a> •
  <a href="README.fr.md">🇫🇷 Francés</a> •
  <a href="README.hi.md">🇮🇳 हिंदी</a> •
  <a href="README.bn.md">🇮🇳 বাংলা</a> •
  <a href="README.zh.md">🇨🇳 中文</a> •
  <a href="README.nl.md">🇳🇱 Neerlandés</a> •
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
  <em>"Como girasoles que se orientan hacia la luz, los agentes colaboran en enjambres - cada uno independiente, pero juntos crean algo más grande."</em>
</p>

<br/>

<div align="center">
  <h3>Incorpora tu agente en una sola línea</h3>
</div>

<div align="center">
  <pre><code>curl -fsSL https://getbindu.com/install-bindu.sh | bash</code></pre>
</div>

---

**Bindu** (se lee: _binduu_) es una capa operativa para agentes de IA que proporciona capacidades de identidad, comunicación y pago. Ofrece un servicio listo para producción con una API conveniente para conectar, autenticar y orquestar agentes a través de sistemas distribuidos utilizando protocolos abiertos: **A2A**, **AP2** y **X402**.Construido con una arquitectura distribuida (Gestor de Tareas, programador, almacenamiento), Bindu facilita el desarrollo rápido y la integración con cualquier marco de IA. Transforma cualquier marco de agente en un servicio completamente interoperable para comunicación, colaboración y comercio en el Internet de los Agentes.

<p align="center">
  <strong>🌟 <a href="https://getbindu.com">Registra tu agente</a> • 🌻 <a href="https://docs.getbindu.com">Documentación</a> • 💬 <a href="https://discord.gg/3w5zuYUuwt">Comunidad de Discord</a></strong>
</p>


---

<br/>

## 🎥 Mira Bindu en Acción

<div align="center">
  <a href="https://www.youtube.com/watch?v=qppafMuw_KI" target="_blank">
    <img src="https://img.youtube.com/vi/qppafMuw_KI/maxresdefault.jpg" alt="Bindu Demo" width="640" style="border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);" />
  </a>
</div>

<br/>

## 📋 Requisitos Previos

Antes de instalar Bindu, asegúrate de tener:

- **Python 3.12 o superior** - [Download here](https://www.python.org/downloads/)
- **Gestor de paquetes UV** - [Installation guide](https://github.com/astral-sh/uv)
- **Se requiere clave API**: Establece `OPENROUTER_API_KEY` o `OPENAI_API_KEY` en tus variables de entorno. Modelos gratuitos de OpenRouter están disponibles para pruebas.


### Verifica tu Configuración

```bash
# Check Python version
uv run python --version  # Should show 3.12 or higher

# Check UV installation
uv --version
```

---

<br/>

## 📦 Instalación
<details>
<summary><b>Nota para usuarios (Git y GitHub Desktop)</b></summary>

En algunos sistemas Windows, git puede no ser reconocido en el Símbolo del sistema incluso después de la instalación debido a problemas de configuración de PATH.

Si enfrentas este problema, puedes usar *GitHub Desktop* como alternativa:

1. Instala GitHub Desktop desde https://desktop.github.com/
2. Inicia sesión con tu cuenta de GitHub
3. Clona el repositorio usando la URL del repositorio:
   https://github.com/getbindu/Bindu.git

GitHub Desktop te permite clonar, gestionar ramas, confirmar cambios y abrir solicitudes de extracción sin usar la línea de comandos.

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
<summary><b>Problemas Comunes de Instalación</b> (haz clic para expandir)</summary>

<br/>

| Problema | Solución |
|-------|----------|| `uv: command not found` | Reinicie su terminal después de instalar UV. En Windows, use PowerShell |
| `Python version not supported` | Instale Python 3.12+ desde [python.org](https://www.python.org/downloads/) |
| Virtual environment not activating (Windows) | Use PowerShell y ejecute `.venv\Scripts\activate` |
| `Microsoft Visual C++ required` | Descargue [Visual C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/) |
| `ModuleNotFoundError` | Active venv y ejecute `uv sync --dev` |

</details>

---

<br/>

## 🚀 Inicio Rápido

### Opción 1: Usando Cookiecutter (Recomendado)

**Tiempo hasta el primer agente: ~2 minutos ⏱️**

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

Su agente local se convierte en un servicio en vivo, seguro y descubrible. [Learn more →](https://docs.getbindu.com/bindu/create-bindu-agent/overview)

> **💡 Consejo Profesional:** Los agentes creados con cookiecutter incluyen GitHub Actions que registran automáticamente su agente en el [GetBindu.com](https://getbindu.com) cuando hace push a su repositorio.

### Opción 2: Configuración Manual

Cree su script de agente `my_agent.py`:

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

Su agente ahora está activo en la URL configurada en `deployment.url`.

Establezca un puerto personalizado sin cambios en el código:

```bash
# Linux/macOS
export BINDU_PORT=4000

# Windows PowerShell
$env:BINDU_PORT="4000"
```

Los ejemplos existentes que utilizan `http://localhost:3773` se sobrescriben automáticamente cuando se establece `BINDU_PORT`.

### Opción 3: Agente Local Sin Configuración

Pruebe Bindu sin configurar Postgres, Redis o cualquier servicio en la nube. Funciona completamente de forma local utilizando almacenamiento en memoria y programador.

```bash
python examples/beginner_zero_config_agent.py
```

### Opción 4: Agente Echo Mínimo (Pruebas)

<details>
<summary><b>Ver ejemplo mínimo</b> (haga clic para expandir)</summary>

Agente funcional más pequeño posible:

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

**Ejecute el agente:**

```bash
# Start the agent
python examples/echo_agent.py
```

</details>

<details>
<summary><b>Pruebe el agente con curl</b> (haga clic para expandir)</summary>

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

Verifique el estado de la tarea
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

 

## 🚀 Características
| Feature                                    | Description                                                                                                                               | Documentation                                                   |
|--------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------|
| **Autenticación**                          | Acceso seguro a la API con Ory Hydra OAuth2 (opcional para desarrollo)                                                                   | [Guide →](docs/AUTHENTICATION.md)                              |
| 💰 **Integración de Pagos (X402)**         | Aceptar pagos en USDC en la blockchain Base antes de ejecutar métodos protegidos                                                         | [Guide →](docs/PAYMENT.md)                                     |
| 💾 **Almacenamiento PostgreSQL**           | Almacenamiento persistente para implementaciones en producción (opcional - Almacenamiento en memoria por defecto)                        | [Guide →](docs/STORAGE.md)                                     |
| 📋 **Programador Redis**                   | Programación de tareas distribuidas para implementaciones con múltiples trabajadores (opcional - Programador en memoria por defecto)     | [Guide →](docs/SCHEDULER.md)                                   |
| 🎯 **Sistema de Habilidades**              | Capacidades reutilizables que los agentes publicitan y ejecutan para el enrutamiento inteligente de tareas                              | [Guide →](docs/SKILLS.md)                                      |
| 🤝 **Negociación de Agentes**              | Selección de agentes basada en capacidades para una orquestación inteligente                                                            | [Guide →](docs/NEGOTIATION.md)                                 |
| 🌐 **Túnel**                               | Exponer agentes locales a Internet para pruebas (**solo desarrollo local, no para producción**)                                         | [Guide →](docs/TUNNELING.md)                                   |
| 📬 **Notificaciones Push**                 | Notificaciones de webhook en tiempo real para actualizaciones de tareas - no se requiere polling                                        | [Guide →](docs/NOTIFICATIONS.md)                               |
| 📊 **Observabilidad y Monitoreo**          | Rastrear el rendimiento y depurar problemas con OpenTelemetry y Sentry                                                                  | [Guide →](docs/OBSERVABILITY.md)                               |
| 🔄 **Mecanismo de Reintento**              | Reintento automático con retroceso exponencial para agentes resilientes                                                                 | [Guide →](https://docs.getbindu.com/bindu/learn/retry/overview)|
| 🔑 **Identificadores Descentralizados (DIDs)** | Identidad criptográfica para interacciones de agentes verificables y seguras e integración de pagos                                      | [Guide →](docs/DID.md)                                         |
| 🏥 **Verificación de Salud y Métricas**    | Monitorear la salud y el rendimiento de los agentes con puntos finales integrados                                                       | [Guide →](docs/HEALTH_METRICS.md)                              |
---

<br/>

## 🎨 Interfaz de Chat

Bindu incluye una hermosa interfaz de chat en `http://localhost:5173`. Navega a la carpeta `frontend` y ejecuta `npm run dev` para iniciar el servidor.

<p align="center">
  <img src="assets/agent-ui.png" alt="Bindu Agent UI" width="640" style="border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);" />
</p>

---

<br/>

## 🌐 GetBindu.comEl [**GetBindu.com**](https://getbindu.com) es un registro público de todos los agentes Bindu, haciéndolos descubribles y accesibles para el ecosistema de agentes más amplio.

### ✨ Registro Automático con Cookiecutter

Cuando creas un agente utilizando la plantilla de cookiecutter, incluye una acción de GitHub preconfigurada que registra automáticamente tu agente en el directorio:

1. **Crea tu agente** usando cookiecutter
2. **Envía a GitHub** - La acción de GitHub se activa automáticamente
3. **Tu agente aparece** en el [GetBindu.com](https://getbindu.com)

> **Nota**: Recoge tu `BINDU_PAT_TOKEN` de [getbindu.com](https://getbindu.com) para registrar tu agente.

### 📝 Registro Manual

El proceso de registro manual está actualmente en desarrollo.

---

<br/>

## 🌌 La Visión

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

_Cada símbolo es un agente — una chispa de inteligencia. El pequeño punto es Bindu, el punto de origen en el Internet de los Agentes._

### Conexión NightSky (En Progreso)

NightSky permite enjambres de agentes. Cada Bindu es un punto que anota agentes con el lenguaje compartido de A2A, AP2 y X402. Los agentes pueden ser alojados en cualquier lugar—portátiles, nubes o clústeres—y aún así hablan el mismo protocolo, confían entre sí por diseño y trabajan juntos como una sola mente distribuida.

> **💭 Un Objetivo Sin un Plan Es Solo un Deseo.**

---

<br/>

## 🛠️ Marcos de Agentes Soportados

Bindu es **agnóstico al marco** y ha sido probado con:

- **AG2** (anteriormente AutoGen)
- **Agno**
- **CrewAI**
- **LangChain**
- **LlamaIndex**
- **FastAgent**

¿Quieres integración con tu marco favorito? [Let us know on Discord](https://discord.gg/3w5zuYUuwt)!

---

<br/>

## 🧪 Pruebas

Bindu mantiene **más del 70% de cobertura de pruebas** (objetivo: más del 80%):

```bash
uv run pytest -n auto --cov=bindu --cov-report=term-missing
uv run coverage report --skip-covered --fail-under=70
```

---

<br/>

## 🔧 Solución de Problemas

<details>
<summary>Problemas Comunes</summary>

<br/>

| Problema | Solución |
|----------|----------|
| `Python 3.12 not found` | Instala Python 3.12+ y configúralo en PATH, o usa `pyenv` |
| `bindu: command not found` | Activa el entorno virtual: `source .venv/bin/activate` || `Port 3773 already in use` | Establecer `BINDU_PORT=4000` o sobrescribir URL con `BINDU_DEPLOYMENT_URL=http://localhost:4000` |
| Fallos en pre-commit | Ejecutar `pre-commit run --all-files` |
| Fallos en pruebas | Instalar dependencias de desarrollo: `uv sync --dev` |
| `Permission denied` (macOS) | Ejecutar `xattr -cr .` para limpiar atributos extendidos |

**Restablecer entorno:**
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

## 🤝 Contribuyendo

¡Damos la bienvenida a las contribuciones! Únete a nosotros en [Discord](https://discord.gg/3w5zuYUuwt). Elige el canal que mejor se adapte a tu contribución.

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

## 📜 Licencia

Bindu es de código abierto bajo la [Apache License 2.0](https://choosealicense.com/licenses/apache-2.0/).

---

<br/>

## 💬 Comunidad

¡Nos 💛 las contribuciones! Ya sea que estés corrigiendo errores, mejorando la documentación o construyendo demostraciones, tus contribuciones hacen que Bindu sea mejor.

- 💬 [Join Discord](https://discord.gg/3w5zuYUuwt) para discusiones y soporte
- ⭐ [Star the repository](https://github.com/getbindu/Bindu) si lo encuentras útil!

---

<br/>

## 👥 Moderadores Activos

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
      <a href="https://github.com/chandan-1427">
        <img src="https://avatars.githubusercontent.com/u/202320492?v=4" width="100px;" alt="Chandan"/>
        <br />
        <sub><b>Chandan</b></sub>
      </a>
      <br />
    </td>
    </tr>
</table>

> ¿Quieres convertirte en moderador? ¡Contacta en [Discord](https://discord.gg/3w5zuYUuwt)!

---

<br/>

## 🙏 Agradecimientos

Agradecido a estos proyectos:

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

## 🗺️ Hoja de Ruta

- [ ] Soporte para transporte GRPC- [ ] Aumentar la cobertura de pruebas al 80% (en progreso)
- [ ] Soporte de extremo a extremo de AP2
- [ ] Integración de DSPy (en progreso)
- [ ] Soporte de MLTS
- [ ] Soporte de X402 con otros facilitadores

> 💡 [Suggest features on Discord](https://discord.gg/3w5zuYUuwt)!

---

<br/>

## [We will make this agents bidufied and we do need your help.](https://www.notion.so/getbindu/305d3bb65095808eac2bf720368e9804?v=305d3bb6509580189941000cfad83ae7&source=copy_link)

---

<br/>

## 🎓 Talleres

- [AI Native in Action: Agent Symphony](https://www.meetup.com/ai-native-Amsterdam && India/events/311066899/) - [Slides](https://docs.google.com/presentation/d/1SqGXI0Gv_KCWZ1Mw2SOx_kI0u-LLxwZq7lMSONdl8oQ/edit)

---

<br/>

## ⭐ Historia de Estrellas

[![Star History Chart](https://api.star-history.com/svg?repos=getbindu/Bindu&type=Date)](https://www.star-history.com/#getbindu/Bindu&Date)

---

<p align="center">
  <strong>Construido con 💛 por el equipo de Ámsterdam && India </strong><br/>
  <em>¡Feliz Bindu! 🌻🚀✨</em>
</p>

<p align="center">
  <strong>De la idea a Internet de Agentes en 2 minutos.</strong><br/>
  <em>Tu agente. Tu marco. Protocolos universales.</em>
</p>

<p align="center">
  <a href="https://github.com/getbindu/Bindu">⭐ Danos una estrella en GitHub</a> •
  <a href="https://discord.gg/3w5zuYUuwt">💬 Únete a Discord</a> •
  <a href="https://docs.getbindu.com">🌻 Lee la Documentación</a>
</p>

<br/>

<p align="center">
  <img src="assets/sunflower-footer.jpeg" alt="Bindu" width="720" />
</p>

<p align="center">
  <em>"Creemos en la teoría del girasol - de pie juntos, trayendo esperanza y luz al Internet de Agentes."</em>
</p>
