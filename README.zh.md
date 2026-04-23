<div align="center" id="top">
  <a href="https://getbindu.com">
    <picture>
      <img src="assets/bindu.png" alt="Bindu" width="300">
    </picture>
  </a>
</div>

<p align="center">
  <em>AI代理的身份、通信和支付层</em>
</p>

<p align="center">
  <a href="README.md">🇬🇧 英语</a> •
  <a href="README.de.md">🇩🇪 德语</a> •
  <a href="README.es.md">🇪🇸 西班牙语</a> •
  <a href="README.fr.md">🇫🇷 法语</a> •
  <a href="README.hi.md">🇮🇳 印地语</a> •
  <a href="README.bn.md">🇮🇳 孟加拉语</a> •
  <a href="README.zh.md">🇨🇳 中文</a> •
  <a href="README.nl.md">🇳🇱 荷兰语</a> •
  <a href="README.ta.md">🇮🇳 泰米尔语</a>
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
  <em>"就像向阳花转向光明，代理以群体形式协作——每个代理都是独立的，但它们共同创造了更伟大的东西。"</em>
</p>

<br/>

<div align="center">
  <h3>一行命令接入你的代理</h3>
</div>

<div align="center">
  <pre><code>curl -fsSL https://getbindu.com/install-bindu.sh | bash</code></pre>
</div>

---

**Bindu**（读作：_binduu_）是一个为AI代理提供身份、通信和支付能力的操作层。它提供了一个生产就绪的服务，具有方便的API，可以使用开放协议连接、认证和编排分布式系统中的代理：**A2A**、**AP2**和**X402**。构建于分布式架构之上（任务管理器、调度程序、存储），Bindu 使得开发快速且易于与任何 AI 框架集成。将任何代理框架转变为一个完全互操作的服务，以便在代理互联网中进行通信、协作和商业。

<p align="center">
  <strong>🌟 <a href="https://getbindu.com">注册您的代理</a> • 🌻 <a href="https://docs.getbindu.com">文档</a> • 💬 <a href="https://discord.gg/3w5zuYUuwt">Discord 社区</a></strong>
</p>


---

<br/>

## 🎥 观看 Bindu 的实际操作

<div align="center">
  <a href="https://www.youtube.com/watch?v=qppafMuw_KI" target="_blank">
    <img src="https://img.youtube.com/vi/qppafMuw_KI/maxresdefault.jpg" alt="Bindu Demo" width="640" style="border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);" />
  </a>
</div>

<br/>

## 📋 先决条件

在安装 Bindu 之前，请确保您具备：

- **Python 3.12 或更高版本** - [Download here](https://www.python.org/downloads/)
- **UV 包管理器** - [Installation guide](https://github.com/astral-sh/uv)
- **需要 API 密钥**：在您的环境变量中设置 `OPENROUTER_API_KEY` 或 `OPENAI_API_KEY`。可用于测试的免费 OpenRouter 模型可用。


### 验证您的设置

```bash
# Check Python version
uv run python --version  # Should show 3.12 or higher

# Check UV installation
uv --version
```

---

<br/>

## 📦 安装
<details>
<summary><b>用户注意（Git 和 GitHub Desktop）</b></summary>

在某些 Windows 系统上，由于 PATH 配置问题，即使安装后，命令提示符中可能无法识别 git。

如果您遇到此问题，可以使用 *GitHub Desktop* 作为替代：

1. 从 https://desktop.github.com/ 安装 GitHub Desktop
2. 使用您的 GitHub 账户登录
3. 使用仓库 URL 克隆仓库：
   https://github.com/getbindu/Bindu.git

GitHub Desktop 允许您克隆、管理分支、提交更改和打开拉取请求，而无需使用命令行。

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
<summary><b>常见安装问题</b>（点击展开）</summary>

<br/>

| 问题 | 解决方案 |
|-------|----------|| `uv: command not found` | 安装 UV 后重启您的终端。在 Windows 上，使用 PowerShell |
| `Python version not supported` | 从 [python.org](https://www.python.org/downloads/) 安装 Python 3.12+ |
| 虚拟环境未激活（Windows） | 使用 PowerShell 并运行 `.venv\Scripts\activate` |
| `Microsoft Visual C++ required` | 下载 [Visual C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/) |
| `ModuleNotFoundError` | 激活 venv 并运行 `uv sync --dev` |

</details>

---

<br/>

## 🚀 快速开始

### 选项 1：使用 Cookiecutter（推荐）

**首次代理所需时间：约 2 分钟 ⏱️**

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

您的本地代理变成一个实时、安全、可发现的服务。 [Learn more →](https://docs.getbindu.com/bindu/create-bindu-agent/overview)

> **💡 专业提示：** 使用 cookiecutter 创建的代理包括 GitHub Actions，当您推送到您的代码库时，会自动在 [GetBindu.com](https://getbindu.com) 中注册您的代理。

### 选项 2：手动设置

创建您的代理脚本 `my_agent.py`：

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

您的代理现在在 `deployment.url` 中配置的 URL 上实时运行。

在不更改代码的情况下设置自定义端口：

```bash
# Linux/macOS
export BINDU_PORT=4000

# Windows PowerShell
$env:BINDU_PORT="4000"
```

使用 `http://localhost:3773` 的现有示例在设置 `BINDU_PORT` 时会被自动覆盖。

### 选项 3：零配置本地代理

尝试 Bindu，而无需设置 Postgres、Redis 或任何云服务。完全在本地运行，使用内存存储和调度程序。

```bash
python examples/beginner_zero_config_agent.py
```

### 选项 4：最小回声代理（测试）

<details>
<summary><b>查看最小示例</b>（点击展开）</summary>

可能的最小工作代理：

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

**运行代理：**

```bash
# Start the agent
python examples/echo_agent.py
```

</details>

<details>
<summary><b>使用 curl 测试代理</b>（点击展开）</summary>

<br/>

输入：
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

输出：
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

检查任务状态
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

输出：
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

 

## 🚀 核心功能
| 特性 | 描述 | 文档 |
| :--- | :--- | :--- |
| **身份验证** | 使用 Ory Hydra OAuth2 进行安全的 API 访问（开发时可选） | [Guide →](docs/AUTHENTICATION.md) |
| 💰 **支付集成 (X402)** | 在执行受保护的方法之前接受 Base 区块链上的 USDC 支付 | [Guide →](docs/PAYMENT.md) |
| 💾 **PostgreSQL 存储** | 生产部署的持久存储（可选 - 默认使用 InMemoryStorage） | [Guide →](docs/STORAGE.md) |
| 📋 **Redis 调度器** | 用于多工作者部署的分布式任务调度（可选 - 默认使用 InMemoryScheduler） | [Guide →](docs/SCHEDULER.md) |
| 🎯 **技能系统** | 代理宣传和执行的可重用能力，用于智能任务路由 | [Guide →](docs/SKILLS.md) |
| 🤝 **代理协商** | 基于能力的代理选择，用于智能编排 | [Guide →](docs/NEGOTIATION.md) |
| 🌐 **隧道** | 将本地代理暴露到互联网以进行测试（**仅限本地开发，不适用于生产**） | [Guide →](docs/TUNNELING.md) |
| 📬 **推送通知** | 实时 webhook 通知任务更新 - 无需轮询 | [Guide →](docs/NOTIFICATIONS.md) |
| 📊 **可观察性与监控** | 使用 OpenTelemetry 和 Sentry 跟踪性能和调试问题 | [Guide →](docs/OBSERVABILITY.md) |
| 🔄 **重试机制** | 自动重试，采用指数退避策略以增强代理的韧性 | [Guide →](docs.getbindu.com/bindu/learn/retry/overview) |
| 🔑 **去中心化标识符 (DIDs)** | 用于可验证、安全的代理交互和支付集成的加密身份 | [Guide →](docs/DID.md) |
| 🏥 **健康检查与指标** | 通过内置端点监控代理的健康和性能 | [Guide →](docs/HEALTH_METRICS.md) |

---

<br/>

## 🎨 聊天 UI

Bindu 包含一个美观的聊天界面，位于 `http://localhost:5173`。导航到 `frontend` 文件夹并运行 `npm run dev` 启动服务器。

<p align="center">
  <img src="assets/agent-ui.png" alt="Bindu Agent UI" width="640" style="border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);" />
</p>

---

<br/>

## 🌐 GetBindu.com[**GetBindu.com**](https://getbindu.com) 是所有 Bindu 代理的公共注册表，使其可被更广泛的代理生态系统发现和访问。

### ✨ 使用 Cookiecutter 自动注册

当您使用 cookiecutter 模板创建代理时，它包含一个预配置的 GitHub Action，自动将您的代理注册到目录中：

1. **使用 cookiecutter 创建您的代理**
2. **推送到 GitHub** - GitHub Action 自动触发
3. **您的代理出现在** [GetBindu.com](https://getbindu.com)

> **注意**：从 [getbindu.com](https://getbindu.com) 收集您的 `BINDU_PAT_TOKEN` 以注册您的代理。

### 📝 手动注册

手动注册过程目前正在开发中。

---

<br/>

## 🌌 远景

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

_每个符号都是一个代理——一个智能的火花。这个小点是 Bindu，代理互联网的起点。_

### NightSky 连接（进行中）

NightSky 使代理群体能够协作。每个 Bindu 是一个点，用 A2A、AP2 和 X402 的共享语言注释代理。代理可以托管在任何地方——笔记本电脑、云或集群——但使用相同的协议，按设计相互信任，并作为一个单一的分布式思维共同工作。

> **💭 没有计划的目标只是一个愿望。**

---

<br/>

## 🛠️ 支持的代理框架

Bindu 是 **框架无关的**，并经过以下测试：

- **AG2**（前身为 AutoGen）
- **Agno**
- **CrewAI**
- **LangChain**
- **LlamaIndex**
- **FastAgent**

想要与您最喜欢的框架集成？ [Let us know on Discord](https://discord.gg/3w5zuYUuwt)！

---

<br/>

## 🧪 测试

Bindu 维护 **70%+ 的测试覆盖率**（目标：80%+）：

```bash
uv run pytest -n auto --cov=bindu --cov-report=term-missing
uv run coverage report --skip-covered --fail-under=70
```

---

<br/>

## 🔧 故障排除

<details>
<summary>常见问题</summary>

<br/>

| 问题 | 解决方案 |
|-------|----------|
| `Python 3.12 not found` | 安装 Python 3.12+ 并设置在 PATH 中，或使用 `pyenv` |
| `bindu: command not found` | 激活虚拟环境：`source .venv/bin/activate` || `Port 3773 already in use` | 设置 `BINDU_PORT=4000` 或用 `BINDU_DEPLOYMENT_URL=http://localhost:4000` 覆盖 URL |
| 提交前失败 | 运行 `pre-commit run --all-files` |
| 测试失败 | 安装开发依赖： `uv sync --dev` |
| `Permission denied` (macOS) | 运行 `xattr -cr .` 清除扩展属性 |

**重置环境：**
```bash
rm -rf .venv
uv venv --python 3.12.9
uv sync --dev
```

**Windows PowerShell：**
```bash
Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
```

</details>

---

<br/>

## 🤝 贡献

我们欢迎贡献！加入我们在 [Discord](https://discord.gg/3w5zuYUuwt)。选择最符合您贡献的频道。

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

## 📜 许可证

Bindu 是在 [Apache License 2.0](https://choosealicense.com/licenses/apache-2.0/) 下开源的。

---

<br/>

## 💬 社区

我们 💛 贡献！无论您是在修复错误、改善文档，还是构建演示——您的贡献使 Bindu 更好。

- 💬 [Join Discord](https://discord.gg/3w5zuYUuwt) 进行讨论和支持
- ⭐ [Star the repository](https://github.com/getbindu/Bindu) 如果您觉得它有用！

---

<br/>

## 👥 活跃的版主

我们专注的版主帮助维护一个友好和高效的社区：

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

> 想成为版主吗？请在 [Discord](https://discord.gg/3w5zuYUuwt) 联系我们！

---

<br/>

## 🙏 致谢

感谢这些项目：

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

## 🗺️ 路线图

- [ ] GRPC 传输支持- [ ] 将测试覆盖率提高到80%（进行中）
- [ ] AP2端到端支持
- [ ] DSPy集成（进行中）
- [ ] MLTS支持
- [ ] 与其他促进者一起支持X402

> 💡 [Suggest features on Discord](https://discord.gg/3w5zuYUuwt)!

---

<br/>

## [We will make this agents bidufied and we do need your help.](https://www.notion.so/getbindu/305d3bb65095808eac2bf720368e9804?v=305d3bb6509580189941000cfad83ae7&source=copy_link)

---

<br/>

## 🎓 工作坊

- [AI Native in Action: Agent Symphony](https://www.meetup.com/ai-native-Amsterdam && India/events/311066899/) - [Slides](https://docs.google.com/presentation/d/1SqGXI0Gv_KCWZ1Mw2SOx_kI0u-LLxwZq7lMSONdl8oQ/edit)

---

<br/>

## ⭐ 星级历史

[![Star History Chart](https://api.star-history.com/svg?repos=getbindu/Bindu&type=Date)](https://www.star-history.com/#getbindu/Bindu&Date)

---

<p align="center">
  <strong>由阿姆斯特丹和印度的团队用💛构建 </strong><br/>
  <em>快乐的Bindu！🌻🚀✨</em>
</p>

<p align="center">
  <strong>从想法到代理互联网只需2分钟。</strong><br/>
  <em>你的代理。你的框架。通用协议。</em>
</p>

<p align="center">
  <a href="https://github.com/getbindu/Bindu">⭐ 在GitHub上给我们加星</a> •
  <a href="https://discord.gg/3w5zuYUuwt">💬 加入Discord</a> •
  <a href="https://docs.getbindu.com">🌻 阅读文档</a>
</p>

<br/>

<p align="center">
  <img src="assets/sunflower-footer.jpeg" alt="Bindu" width="720" />
</p>

<p align="center">
  <em>“我们相信向日葵理论——共同高高站立，为代理互联网带来希望和光明。”</em>
</p>
