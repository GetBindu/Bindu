<div align="center" id="top">
  <a href="https://getbindu.com">
    <picture>
      <img src="assets/bindu.png" alt="Bindu" width="300">
    </picture>
  </a>
</div>

<p align="center">
  <em>AI 代理的身份、通信和支付层</em>
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

**Bindu**（发音：_宾度_）是 AI 代理的操作层，提供身份、通信和支付能力。它是一个生产就绪的服务，通过便捷的 API 在分布式系统中连接、认证和编排代理——使用开放协议：**A2A**、**AP2** 和 **X402**。

采用分布式架构（Task Manager、scheduler、storage）构建，Bindu 使快速开发和与任何 AI 框架集成变得简单。将任何代理框架转变为完全可互操作的服务，用于 Internet of Agents 中的通信、协作和商务。

<p align="center">
  <strong>🌟 <a href="https://bindus.directory">注册您的代理</a> • 🌻 <a href="https://docs.getbindu.com">文档</a> • 💬 <a href="https://discord.gg/3w5zuYUuwt">Discord 社区</a></strong>
</p>

---

<br/>

## 🎥 观看 Bindu 实战

<div align="center">
  <a href="https://www.youtube.com/watch?v=qppafMuw_KI" target="_blank">
    <img src="https://img.youtube.com/vi/qppafMuw_KI/maxresdefault.jpg" alt="Bindu Demo" width="640" style="border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);" />
  </a>
</div>

## 📋 前置要求

在安装 Bindu 之前，请确保您拥有：

- **Python 3.12 或更高版本** - [在此下载](https://www.python.org/downloads/)
- **UV Package Manager** - [安装指南](https://github.com/astral-sh/uv)

### 验证您的设置

```bash
# 检查 Python 版本
uv run python --version  # 应显示 3.12 或更高

# 检查 UV 安装
uv --version
```

---

<br/>

## 📦 安装

<details>
<summary><b>Windows 用户注意事项（Git & GitHub Desktop）</b></summary>

在某些 Windows 系统上，即使安装后，命令提示符也可能无法识别 git——这是由于 PATH 配置问题。

如果遇到此问题，您可以使用 *GitHub Desktop* 作为替代方案：

1. 从 https://desktop.github.com/ 安装 GitHub Desktop
2. 使用您的 GitHub 账户登录
3. 使用仓库 URL 克隆：
   https://github.com/getbindu/Bindu.git

GitHub Desktop 允许您在不使用命令行的情况下克隆仓库、管理分支、提交更改和打开 pull request。

</details>

```bash
# 安装 Bindu
uv add bindu

# 用于开发（如果您正在为 Bindu 做贡献）
# 创建并激活虚拟环境
uv venv --python 3.12.9
source .venv/bin/activate  # 在 macOS/Linux 上
# .venv\Scripts\activate  # 在 Windows 上

uv sync --dev
```

<details>
<summary><b>常见安装问题</b>（点击展开）</summary>

<br/>

| 问题 | 解决方案 |
|-------|----------|
| `uv: command not found` | 安装 UV 后重启终端。在 Windows 上使用 PowerShell |
| `Python version not supported` | 从 [python.org](https://www.python.org/downloads/) 安装 Python 3.12+ |
| 虚拟环境无法激活（Windows） | 使用 PowerShell 并运行 `.venv\Scripts\activate` |
| `Microsoft Visual C++ required` | 下载 [Visual C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/) |
| `ModuleNotFoundError` | 激活 venv 并运行 `uv sync --dev` |

</details>

---

<br/>

## 🚀 快速开始

### 选项 1：使用 Cookiecutter（推荐）

**首个代理所需时间：约 2 分钟 ⏱️**

```bash
# 安装 Cookiecutter
uv add cookiecutter

# 创建您的 Bindu 代理
uvx cookiecutter https://github.com/getbindu/create-bindu-agent.git
```

## 🎥 几分钟内构建生产就绪的代理

<div align="center">
  <a href="https://youtu.be/obY1bGOoWG8?si=uEeDb0XWrtYOQTL7" target="_blank">
    <img src="https://img.youtube.com/vi/obY1bGOoWG8/maxresdefault.jpg" alt="Bindu Demo" width="640" style="border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);" />
  </a>
</div>

就这样！您的本地代理现在是一个实时、安全且可发现的服务。[了解更多 →](https://docs.getbindu.com/bindu/create-bindu-agent/overview)

> **💡 专业提示：** 使用 Cookiecutter 创建的代理包含 GitHub Actions，当您推送到仓库时会自动将代理注册到 [Bindu Directory](https://bindus.directory)。无需手动注册！

### 选项 2：手动设置

创建您的代理脚本 `my_agent.py`：

```python
from bindu.penguin.bindufy import bindufy
from agno.agent import Agent
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.models.openai import OpenAIChat

# 定义您的代理
agent = Agent(
    instructions="您是一个研究助手，可以查找和总结信息。",
    model=OpenAIChat(id="gpt-4o"),
    tools=[DuckDuckGoTools()],
)

# 配置
config = {
    "author": "your.email@example.com",
    "name": "research_agent",
    "description": "一个研究助手代理",
    "deployment": {"url": "http://localhost:3773", "expose": True},
    "skills": ["skills/question-answering", "skills/pdf-processing"]
}

# Handler 函数
def handler(messages: list[dict[str, str]]):
    """处理消息并返回代理响应。

    Args:
        messages: 包含对话历史的消息字典列表

    Returns:
        代理响应结果
    """
    result = agent.run(input=messages)
    return result

# Bindu 化
bindufy(config, handler)
```

![Sample Agent](assets/agno-simple.png)

您的代理现在在 `http://localhost:3773` 上运行，准备与其他代理通信。

---

### 选项 3：最小 Echo 代理（测试）

<details>
<summary><b>查看最小示例</b>（点击展开）</summary>

最小的可工作代理：

```python
from bindu.penguin.bindufy import bindufy

def handler(messages):
    return [{"role": "assistant", "content": messages[-1]["content"]}]

config = {
    "author": "your.email@example.com",
    "name": "echo_agent",
    "description": "用于快速测试的基本 echo 代理。",
    "deployment": {"url": "http://localhost:3773", "expose": True},
    "skills": []
}

bindufy(config, handler)
```

**运行和测试：**

```bash
# 启动代理
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

<br/>

## [Postgres Storage](https://docs.getbindu.com/bindu/learn/storage/overview)

Bindu 使用 PostgreSQL 作为生产部署的持久存储后端。存储层使用 SQLAlchemy 的异步引擎构建，并使用 protocol TypedDicts 的命令式映射。

这是可选的——默认使用 InMemoryStorage。

### 📊 存储结构

存储层使用三个主要表：

1. **tasks_table**：存储所有任务及其 JSONB history 和 artifacts
2. **contexts_table**：维护 context metadata 和 message history
3. **task_feedback_table**：任务的可选 feedback 存储

### ⚙️ 配置

<details>
<summary><b>查看配置示例</b>（点击展开）</summary>

在您的环境或设置中配置 PostgreSQL 连接：
在代理配置中提供连接字符串。

```json
config = {
    "author": "your.email@example.com",
    "name": "research_agent",
    "description": "一个研究助手代理",
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

**💡 任务优先模式**：存储支持 Bindu 的任务优先方法，其中可以通过向非终端任务添加消息来继续任务，从而实现增量改进和多轮对话。

---

<br/>

## [Redis Scheduler](https://docs.getbindu.com/bindu/learn/scheduler/overview)

Bindu 使用 Redis 作为其分布式任务调度器，以协调多个 worker 和进程之间的工作。调度器使用带有阻塞操作的 Redis 列表来实现高效的任务分发。

这是可选的——默认使用 InMemoryScheduler。

### ⚙️ 配置

<details>
<summary><b>查看配置示例</b>（点击展开）</summary>

在您的代理配置中配置 Redis 连接：

```json
config = {
    "author": "your.email@example.com",
    "name": "research_agent",
    "description": "一个研究助手代理",
    "deployment": {"url": "http://localhost:3773", "expose": True},
    "skills": ["skills/question-answering", "skills/pdf-processing"],
     "scheduler": {
        "type": "redis",
        "redis_url": "redis://localhost:6379/0",
    },
}
```

</details>

所有操作都在 Redis 中排队，并由可用的 worker 使用阻塞 pop 机制处理，确保高效分发而无需轮询开销。

---

<br/>

## [Retry Mechanism](https://docs.getbindu.com/bindu/learn/retry/overview)

> 具有指数退避的自动重试逻辑，用于弹性 Bindu 代理

Bindu 具有基于 Tenacity 的内置重试机制，可优雅地处理 worker、storage、scheduler 和 API 调用中的瞬态故障。这确保您的代理在生产环境中保持弹性。

### ⚙️ 默认设置

如果未配置，Bindu 使用这些默认值：

| 操作类型 | 最大尝试次数 | 最小等待 | 最大等待 |
| -------------- | ------------ | -------- | -------- |
| Worker         | 3            | 1.0s     | 10.0s    |
| Storage        | 5            | 0.5s     | 5.0s     |
| Scheduler      | 3            | 1.0s     | 8.0s     |
| API            | 4            | 1.0s     | 15.0s    |

---

<br/>

## [Sentry Integration](https://docs.getbindu.com/bindu/learn/sentry/overview)

> Bindu 代理的实时错误跟踪和性能监控

Sentry 是一个实时错误跟踪和性能监控平台，可帮助您在生产中识别、诊断和修复问题。Bindu 具有内置的 Sentry 集成，为您的 AI 代理提供全面的可观察性。

### ⚙️ 配置

<details>
<summary><b>查看配置示例</b>（点击展开）</summary>

直接在您的 `bindufy()` 配置中配置 Sentry：

```python
config = {
    "author": "gaurikasethi88@gmail.com",
    "name": "echo_agent",
    "description": "用于快速测试的基本 echo 代理。",
    "deployment": {"url": "http://localhost:3773", "expose": True},
    "skills": [],
    "storage": {
        "type": "postgres",
        "database_url": "postgresql+asyncpg://bindu:bindu@localhost:5432/bindu",  # pragma: allowlist secret
        "run_migrations_on_startup": False,
    },
    # Scheduler 配置（可选）
    # 对于单进程使用 "memory"（默认），对于分布式多进程使用 "redis"
    "scheduler": {
        "type": "redis",
        "redis_url": "redis://localhost:6379/0",
    },
    # Sentry 错误跟踪（可选）
    # 直接在代码中配置 Sentry，而不是环境变量
    "sentry": {
        "enabled": True,
        "dsn": "https://252c0197ddeafb621f91abdbb59fa819@o4510504294612992.ingest.de.sentry.io/4510504299069520",
        "environment": "development",
        "traces_sample_rate": 1.0,
        "profiles_sample_rate": 0.1,
    },
}

def handler(messages):
    # 您的代理逻辑
    pass

bindufy(config, handler)
```

</details>

### 🚀 入门

1. **创建 Sentry 账户**：在 [sentry.io](https://sentry.io) 注册
2. **获取您的 DSN**：从项目设置中复制
3. **配置 Bindu**：添加 `sentry` 配置（见上文）
4. **运行您的代理**：Sentry 会自动初始化

> 📚 查看 [完整 Sentry 文档](https://docs.getbindu.com/bindu/learn/sentry/overview) 了解完整详情。

---

<br/>

## [Skills System](https://docs.getbindu.com/bindu/skills/introduction/overview)

> 用于智能代理编排的丰富能力广告

Bindu Skills System 为智能编排和代理发现提供丰富的代理能力广告。受 Claude 的 skills 架构启发，它使代理能够提供有关其能力的详细文档，以便编排器做出明智的路由决策。

### 💡 什么是 Skills？

在 Bindu 中，Skills 充当**丰富的广告元数据**，帮助编排器：

* 🔍 **发现**任务的正确代理
* 📖 **理解**详细的能力和限制
* ✅ **验证**执行前的要求
* 📊 **估计**性能和资源需求
* 🔗 **智能链接**多个代理

> **注意**：Skills 不是可执行代码——它们是描述您的代理能做什么的结构化元数据。

### 🔌 API 端点

**列出所有 Skills**：
```bash
GET /agent/skills
```

**获取 Skill 详情**：
```bash
GET /agent/skills/{skill_id}
```

**获取 Skill 文档**：
```bash
GET /agent/skills/{skill_id}/documentation
```

> 📚 查看 [Skills 文档](https://github.com/getbindu/Bindu/tree/main/examples/skills) 获取完整示例。

---

<br/>

## Negotiation

> 基于能力的代理选择，用于智能编排

Bindu 的协商系统使编排器能够查询多个代理，并根据 skills、performance、load 和 cost 智能选择最佳代理来执行任务。

### 🔄 工作原理

1. **编排器广播**评估请求到多个代理
2. **代理自我评估**使用 skill matching 和 load analysis 评估能力
3. **编排器排名**使用多因素评分对响应进行排名
4. **选择最佳代理**并执行任务

### 🔌 评估端点

<details>
<summary><b>查看 API 详情</b>（点击展开）</summary>

```bash
POST /agent/negotiation
```

**请求：**
```json
{
  "task_summary": "从 PDF 发票中提取表格",
  "task_details": "处理发票 PDF 并提取结构化数据",
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

**响应：**
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

### 📊 评分算法

代理根据多个因素计算置信度分数：

```python
score = (
    skill_match * 0.6 +        # 主要：skill matching
    io_compatibility * 0.2 +   # 输入/输出格式支持
    performance * 0.1 +        # 速度和可靠性
    load * 0.05 +              # 当前可用性
    cost * 0.05                # 定价
)
```

> 📚 查看 [Negotiation 文档](https://docs.getbindu.com/bindu/negotiation/overview) 了解完整详情。

---

<br/>

## Task Feedback 和 DSPy

Bindu 在任务执行时收集用户反馈，以通过 DSPy 优化实现持续改进。通过存储带有评分和元数据的反馈，您可以从真实交互中构建黄金数据集，并使用 DSPy 自动优化代理的提示和行为。

### 提交反馈

使用 `tasks/feedback` 方法为任何任务提供反馈：

```bash
curl --location 'http://localhost:3773/' \
--header 'Content-Type: application/json' \
--header 'Authorization: Bearer <your-token>' \
--data '{
    "jsonrpc": "2.0",
    "method": "tasks/feedback",
    "params": {
        "taskId": "550e8400-e29b-41d4-a716-446655440200",
        "feedback": "做得很好！响应非常有帮助且准确。",
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

反馈存储在 `task_feedback` 表中，可用于：
- 过滤高质量的任务交互以用于训练数据
- 识别成功与失败完成中的模式
- 使用 DSPy 优化代理指令和少样本示例
- 我们正在开发 DsPY——即将发布。

---

<br/>

## 📬 Push Notifications

Bindu 支持长时间运行任务的**实时 webhook 通知**，遵循 [A2A Protocol specification](https://a2a-protocol.org/latest/specification/)。这使客户端能够在不轮询的情况下接收有关任务状态更改和 artifact 生成的推送通知。

### 快速开始

1. **启动 webhook 接收器：** `python examples/webhook_client_example.py`
2. **配置代理**在 `examples/echo_agent_with_webhooks.py` 中：
   ```python
   manifest = {
       "capabilities": {"push_notifications": True},
       "global_webhook_url": "http://localhost:8000/webhooks/task-updates",
       "global_webhook_token": "secret_abc123",
   }
   ```
3. **运行代理：** `python examples/echo_agent_with_webhooks.py`
4. **发送任务** - webhook 通知会自动到达

📖 **[完整文档](docs/NOTIFICATIONS.md)** - 包含架构、安全性、示例和故障排除的详细指南。

---

<br/>

## 🎨 Chat UI

Bindu 在 `http://localhost:3773/docs` 包含一个漂亮的聊天界面

<p align="center">
  <img src="assets/agent-ui.png" alt="Bindu Agent UI" width="640" style="border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);" />
</p>

---

<br/>

## 🌐 Bindu Directory

[**Bindu Directory**](https://bindus.directory) 是所有 Bindu 代理的公共注册表，使它们在更广泛的代理生态系统中可被发现和访问。

### ✨ 使用 Cookiecutter 自动注册

当您使用 cookiecutter 模板创建代理时，它包含一个预配置的 GitHub Action，当您推送到仓库时会自动将您的代理注册到目录中：

1. **使用 cookiecutter 创建您的代理**
2. **推送到 GitHub** - GitHub Action 自动触发
3. **您的代理出现**在 [Bindu Directory](https://bindus.directory) 中

> **🔑 注意**：您需要从 bindus.directory 收集 BINDU_PAT_TOKEN 并使用它来注册您的代理。

### 📝 手动注册

我们正在开发手动注册流程。

---

<br/>

## 🌌 愿景

```
夜空一瞥
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

_每个符号都是一个代理——智能的火花。微小的点是 Bindu，Internet of Agents 中的起源点。_

### NightSky 连接 [进行中]

NightSky 实现代理群。每个 Bindu 都是一个点，用 A2A、AP2 和 X402 的共享语言注释代理。代理可以托管在任何地方——笔记本电脑、云或集群中——但说同一种协议，设计上相互信任，并作为单一的分布式思维一起工作。

> **💭 没有计划的目标只是一个愿望。**

---

<br/>

## 🛠️ 支持的代理框架

Bindu 是**框架无关的**，并已测试：

- **Agno**
- **CrewAI**
- **LangChain**
- **LlamaIndex**
- **FastAgent**

想要与您喜欢的框架集成？[在 Discord 上告诉我们](https://discord.gg/3w5zuYUuwt)！

---

<br/>

## 🧪 测试

Bindu 维持 **70%+ 测试覆盖率**：

```bash
pytest -n auto --cov=bindu --cov-report= && coverage report --skip-covered --fail-under=70
```

---

<br/>

## 故障排除

<details>
<summary>常见问题</summary>

<br/>

| 问题 | 解决方案 |
|---------|----------|
| `Python 3.12 not found` | 安装 Python 3.12+ 并在 PATH 中设置，或使用 `pyenv` |
| `bindu: command not found` | 激活虚拟环境：`source .venv/bin/activate` |
| `Port 3773 already in use` | 在配置中更改端口：`"url": "http://localhost:4000"` |
| Pre-commit 失败 | 运行 `pre-commit run --all-files` |
| 测试失败 | 安装开发依赖：`uv sync --dev` |
| `Permission denied`（macOS） | 运行 `xattr -cr .` 清除扩展属性 |

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

<br/>

## 🤝 贡献

我们欢迎贡献！在 [Discord](https://discord.gg/3w5zuYUuwt) 上加入我们。选择最适合您贡献的频道。

```bash
git clone https://github.com/getbindu/Bindu.git
cd Bindu
uv venv --python 3.12.9
source .venv/bin/activate
uv sync --dev
pre-commit run --all-files
```

> 📖 [贡献指南](.github/contributing.md)

---

<br/>

## 📜 许可证

Bindu 在 [Apache License 2.0](https://choosealicense.com/licenses/apache-2.0/) 下开源。

---

<br/>

## 💬 社区

我们 💛 贡献！无论您是修复错误、改进文档还是构建演示——您的贡献都会让 Bindu 变得更好。

- 💬 [加入 Discord](https://discord.gg/3w5zuYUuwt) 进行讨论和支持
- ⭐ 如果您觉得有用，请[给仓库加星](https://github.com/getbindu/Bindu)！

---

<br/>

## 👥 活跃版主

我们敬业的版主帮助维护一个热情和富有成效的社区：

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

> 想成为版主？在 [Discord](https://discord.gg/3w5zuYUuwt) 上联系我们！

---

<br/>

## 🙏 致谢

感谢这些项目：

- [FastA2A](https://github.com/pydantic/fasta2a)
- [12 Factor Agents](https://github.com/humanlayer/12-factor-agents/blob/main/content/factor-11-trigger-from-anywhere.md)
- [A2A](https://github.com/a2aproject/A2A)
- [AP2](https://github.com/google-agentic-commerce/AP2)
- [X402](https://github.com/coinbase/x402)
- [Bindu Logo](https://openmoji.org/library/emoji-1F33B/)
- [ASCII Space Art](https://www.asciiart.eu/space/other)

---

<br/>

## 🗺️ 路线图

- [ ] GRPC 传输支持
- [x] Sentry 错误跟踪
- [x] Ag-UI 集成
- [x] 重试机制
- [ ] 将测试覆盖率提高到 80% - 进行中
- [x] Redis scheduler 实现
- [x] 用于内存存储的 Postgres 数据库
- [x] Negotiation 支持
- [ ] AP2 端到端支持
- [ ] DSPy 集成 - 进行中
- [ ] MLTS 支持
- [ ] 与其他 facilitator 的 X402 支持

> 💡 [在 Discord 上建议功能](https://discord.gg/3w5zuYUuwt)！

---

<br/>

## 🎓 研讨会

- [AI Native in Action: Agent Symphony](https://www.meetup.com/ai-native-amsterdam/events/311066899/) - [幻灯片](https://docs.google.com/presentation/d/1SqGXI0Gv_KCWZ1Mw2SOx_kI0u-LLxwZq7lMSONdl8oQ/edit)

---

<br/>

## ⭐ Star 历史

[![Star History Chart](https://api.star-history.com/svg?repos=getbindu/Bindu&type=Date)](https://www.star-history.com/#getbindu/Bindu&Date)

---

<p align="center">
  <strong>由来自阿姆斯特丹的团队用 💛 打造</strong><br/>
  <em>Happy Bindu! 🌻🚀✨</em>
</p>

<p align="center">
  <strong>从想法到 Internet of Agents 只需 2 分钟。</strong><br/>
  <em>您的代理。您的框架。通用协议。</em>
</p>

<p align="center">
  <a href="https://github.com/getbindu/Bindu">⭐ 在 GitHub 上给我们加星</a> •
  <a href="https://discord.gg/3w5zuYUuwt">💬 加入 Discord</a> •
  <a href="https://docs.getbindu.com">🌻 阅读文档</a>
</p>
