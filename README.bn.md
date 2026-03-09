<div align="center" id="top">
  <a href="https://getbindu.com">
    <picture>
      <img src="assets/bindu.png" alt="Bindu" width="300">
    </picture>
  </a>
</div>

<p align="center">
  <em>AI এজেন্টদের জন্য পরিচয়, যোগাযোগ এবং পেমেন্ট লেয়ার</em>
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

**Bindu** (উচ্চারণ: _বিন্দু_) হলো AI এজেন্টদের জন্য একটি অপারেটিং লেয়ার যা পরিচয়, যোগাযোগ এবং পেমেন্ট সুবিধা প্রদান করে। এটি একটি প্রোডাকশন-রেডি সার্ভিস যা সুবিধাজনক API দিয়ে ডিস্ট্রিবিউটেড সিস্টেম জুড়ে এজেন্টদের সংযুক্ত, প্রমাণীকৃত এবং অর্কেস্ট্রেট করে – ওপেন প্রোটোকল ব্যবহার করে: **A2A**, **AP2**, এবং **X402**।

ডিস্ট্রিবিউটেড আর্কিটেকচার (Task Manager, scheduler, storage) দিয়ে তৈরি, Bindu দ্রুত ডেভেলপ করা এবং যেকোনো AI ফ্রেমওয়ার্কের সাথে ইন্টিগ্রেট করা সহজ করে তোলে। যেকোনো এজেন্ট ফ্রেমওয়ার্ককে Internet of Agents-এ যোগাযোগ, সহযোগিতা এবং কমার্সের জন্য সম্পূর্ণ ইন্টারঅপারেবল সার্ভিসে রূপান্তরিত করুন।

<p align="center">
  <strong>🌟 <a href="https://bindus.directory">আপনার এজেন্ট রেজিস্টার করুন</a> • 🌻 <a href="https://docs.getbindu.com">ডকুমেন্টেশন</a> • 💬 <a href="https://discord.gg/3w5zuYUuwt">Discord কমিউনিটি</a></strong>
</p>

---

<br/>

## 🎥 Bindu-কে কাজ করতে দেখুন

<div align="center">
  <a href="https://www.youtube.com/watch?v=qppafMuw_KI" target="_blank">
    <img src="https://img.youtube.com/vi/qppafMuw_KI/maxresdefault.jpg" alt="Bindu Demo" width="640" style="border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);" />
  </a>
</div>

## 📋 প্রয়োজনীয়তা

Bindu ইনস্টল করার আগে নিশ্চিত করুন যে আপনার কাছে আছে:

- **Python 3.12 বা তার উপরে** - [এখানে ডাউনলোড করুন](https://www.python.org/downloads/)
- **UV Package Manager** - [ইনস্টলেশন গাইড](https://github.com/astral-sh/uv)

### আপনার সেটআপ যাচাই করুন

```bash
# Python ভার্সন চেক করুন
uv run python --version  # 3.12 বা তার উপরে দেখাবে

# UV ইনস্টলেশন চেক করুন
uv --version
```

---

<br/>

## 📦 ইনস্টলেশন

<details>
<summary><b>Windows ইউজারদের জন্য নোট (Git & GitHub Desktop)</b></summary>

কিছু Windows সিস্টেমে, ইনস্টলেশনের পরেও Command Prompt-এ git চিনতে পারে না – PATH কনফিগারেশন সমস্যার কারণে।

যদি এই সমস্যায় পড়েন, আপনি বিকল্প হিসেবে *GitHub Desktop* ব্যবহার করতে পারেন:

1. https://desktop.github.com/ থেকে GitHub Desktop ইনস্টল করুন
2. আপনার GitHub অ্যাকাউন্ট দিয়ে সাইন ইন করুন
3. রিপোজিটরি URL ব্যবহার করে ক্লোন করুন:
   https://github.com/getbindu/Bindu.git

GitHub Desktop আপনাকে কমান্ড লাইন ছাড়াই রিপোজিটরি ক্লোন, ব্রাঞ্চ ম্যানেজ, পরিবর্তন কমিট এবং pull request খুলতে দেয়।

</details>

```bash
# Bindu ইনস্টল করুন
uv add bindu

# ডেভেলপমেন্টের জন্য (যদি Bindu-তে কন্ট্রিবিউট করেন)
# ভার্চুয়াল এনভায়রনমেন্ট তৈরি এবং অ্যাক্টিভেট করুন
uv venv --python 3.12.9
source .venv/bin/activate  # macOS/Linux-এ
# .venv\Scripts\activate  # Windows-এ

uv sync --dev
```

<details>
<summary><b>সাধারণ ইনস্টলেশন সমস্যা</b> (প্রসারিত করতে ক্লিক করুন)</summary>

<br/>

| সমস্যা | সমাধান |
|-------|----------|
| `uv: command not found` | UV ইনস্টল করার পর টার্মিনাল রিস্টার্ট করুন। Windows-এ PowerShell ব্যবহার করুন |
| `Python version not supported` | [python.org](https://www.python.org/downloads/) থেকে Python 3.12+ ইনস্টল করুন |
| ভার্চুয়াল এনভায়রনমেন্ট অ্যাক্টিভেট হচ্ছে না (Windows) | PowerShell ব্যবহার করুন এবং `.venv\Scripts\activate` রান করুন |
| `Microsoft Visual C++ required` | [Visual C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/) ডাউনলোড করুন |
| `ModuleNotFoundError` | venv অ্যাক্টিভেট করুন এবং `uv sync --dev` রান করুন |

</details>

---

<br/>

## 🚀 দ্রুত শুরু

### অপশন ১: Cookiecutter ব্যবহার করুন (সুপারিশকৃত)

**প্রথম এজেন্ট পর্যন্ত সময়: ~২ মিনিট ⏱️**

```bash
# Cookiecutter ইনস্টল করুন
uv add cookiecutter

# আপনার Bindu এজেন্ট তৈরি করুন
uvx cookiecutter https://github.com/getbindu/create-bindu-agent.git
```

## 🎥 মিনিটেই প্রোডাকশন-রেডি এজেন্ট তৈরি করুন

<div align="center">
  <a href="https://youtu.be/obY1bGOoWG8?si=uEeDb0XWrtYOQTL7" target="_blank">
    <img src="https://img.youtube.com/vi/obY1bGOoWG8/maxresdefault.jpg" alt="Bindu Demo" width="640" style="border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);" />
  </a>
</div>

ব্যস হয়ে গেল! আপনার লোকাল এজেন্ট এখন একটি লাইভ, সিকিউর এবং আবিষ্কারযোগ্য সার্ভিস। [আরো জানুন →](https://docs.getbindu.com/bindu/create-bindu-agent/overview)

> **💡 প্রো টিপ:** Cookiecutter দিয়ে তৈরি এজেন্টে GitHub Actions থাকে যা আপনার রিপোজিটরিতে push করলে স্বয়ংক্রিয়ভাবে [Bindu Directory](https://bindus.directory)-তে এজেন্ট রেজিস্টার করে। ম্যানুয়াল রেজিস্ট্রেশনের দরকার নেই!

### অপশন ২: ম্যানুয়াল সেটআপ

আপনার এজেন্ট স্ক্রিপ্ট `my_agent.py` তৈরি করুন:

```python
from bindu.penguin.bindufy import bindufy
from agno.agent import Agent
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.models.openai import OpenAIChat

# আপনার এজেন্ট ডিফাইন করুন
agent = Agent(
    instructions="আপনি একজন রিসার্চ অ্যাসিস্ট্যান্ট যে তথ্য খুঁজে বের করে এবং সংক্ষিপ্ত করে।",
    model=OpenAIChat(id="gpt-4o"),
    tools=[DuckDuckGoTools()],
)

# কনফিগারেশন
config = {
    "author": "your.email@example.com",
    "name": "research_agent",
    "description": "একটি রিসার্চ অ্যাসিস্ট্যান্ট এজেন্ট",
    "deployment": {"url": "http://localhost:3773", "expose": True},
    "skills": ["skills/question-answering", "skills/pdf-processing"]
}

# Handler ফাংশন
def handler(messages: list[dict[str, str]]):
    """মেসেজ প্রসেস করে এবং এজেন্টের রেসপন্স রিটার্ন করে।

    Args:
        messages: কথোপকথনের ইতিহাস সহ মেসেজ ডিকশনারির লিস্ট

    Returns:
        এজেন্ট রেসপন্স রেজাল্ট
    """
    result = agent.run(input=messages)
    return result

# Bindu-ফাই করুন
bindufy(config, handler)
```

![Sample Agent](assets/agno-simple.png)

আপনার এজেন্ট এখন `http://localhost:3773`-এ লাইভ এবং অন্য এজেন্টদের সাথে যোগাযোগ করতে প্রস্তুত।

---

### অপশন ৩: মিনিমাল Echo এজেন্ট (টেস্টিং)

<details>
<summary><b>মিনিমাল উদাহরণ দেখুন</b> (প্রসারিত করতে ক্লিক করুন)</summary>

সবচেয়ে ছোট কার্যকর এজেন্ট:

```python
from bindu.penguin.bindufy import bindufy

def handler(messages):
    return [{"role": "assistant", "content": messages[-1]["content"]}]

config = {
    "author": "your.email@example.com",
    "name": "echo_agent",
    "description": "দ্রুত টেস্টিংয়ের জন্য একটি বেসিক echo এজেন্ট।",
    "deployment": {"url": "http://localhost:3773", "expose": True},
    "skills": []
}

bindufy(config, handler)
```

**রান এবং টেস্ট করুন:**

```bash
# এজেন্ট স্টার্ট করুন
python examples/echo_agent.py
```

</details>


<details>
<summary><b>curl দিয়ে এজেন্ট টেস্ট করুন</b> (প্রসারিত করতে ক্লিক করুন)</summary>

<br/>

ইনপুট:
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

আউটপুট:
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

Task-এর স্ট্যাটাস চেক করুন
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

আউটপুট:
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

Bindu প্রোডাকশন ডিপ্লয়মেন্টের জন্য PostgreSQL-কে তার persistent storage backend হিসেবে ব্যবহার করে। Storage লেয়ার SQLAlchemy-র async engine দিয়ে তৈরি এবং protocol TypedDicts-এর সাথে imperative mapping ব্যবহার করে।

এটি ঐচ্ছিক - ডিফল্টভাবে InMemoryStorage ব্যবহার করা হয়।

### 📊 Storage স্ট্রাকচার

Storage লেয়ার তিনটি প্রধান টেবিল ব্যবহার করে:

1. **tasks_table**: JSONB history এবং artifacts সহ সব task স্টোর করে
2. **contexts_table**: Context metadata এবং message history বজায় রাখে
3. **task_feedback_table**: Task-এর জন্য ঐচ্ছিক feedback storage

### ⚙️ কনফিগারেশন

<details>
<summary><b>কনফিগারেশন উদাহরণ দেখুন</b> (প্রসারিত করতে ক্লিক করুন)</summary>

আপনার environment বা settings-এ PostgreSQL connection কনফিগার করুন:
এজেন্টের config-এ connection string প্রদান করুন।

```json
config = {
    "author": "your.email@example.com",
    "name": "research_agent",
    "description": "একটি রিসার্চ অ্যাসিস্ট্যান্ট এজেন্ট",
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

**💡 Task-First Pattern**: Storage Bindu-র task-first approach সাপোর্ট করে যেখানে non-terminal task-এ message যোগ করে task চালিয়ে যাওয়া যায়, যা incremental refinements এবং multi-turn conversations সক্ষম করে।

---

<br/>

## [Redis Scheduler](https://docs.getbindu.com/bindu/learn/scheduler/overview)

Bindu একাধিক worker এবং process জুড়ে কাজ সমন্বয় করার জন্য Redis-কে তার distributed task scheduler হিসেবে ব্যবহার করে। Scheduler দক্ষ task distribution-এর জন্য blocking operations সহ Redis lists ব্যবহার করে।

এটি ঐচ্ছিক - ডিফল্টভাবে InMemoryScheduler ব্যবহার করা হয়।

### ⚙️ কনফিগারেশন

<details>
<summary><b>কনফিগারেশন উদাহরণ দেখুন</b> (প্রসারিত করতে ক্লিক করুন)</summary>

আপনার এজেন্ট config-এ Redis connection কনফিগার করুন:

```json
config = {
    "author": "your.email@example.com",
    "name": "research_agent",
    "description": "একটি রিসার্চ অ্যাসিস্ট্যান্ট এজেন্ট",
    "deployment": {"url": "http://localhost:3773", "expose": True},
    "skills": ["skills/question-answering", "skills/pdf-processing"],
     "scheduler": {
        "type": "redis",
        "redis_url": "redis://localhost:6379/0",
    },
}
```

</details>

সব operation Redis-এ queue করা হয় এবং উপলব্ধ worker দ্বারা blocking pop mechanism ব্যবহার করে প্রসেস করা হয়, যা polling overhead ছাড়াই দক্ষ distribution নিশ্চিত করে।

---

<br/>

## [Retry Mechanism](https://docs.getbindu.com/bindu/learn/retry/overview)

> স্থিতিস্থাপক Bindu এজেন্টদের জন্য exponential backoff সহ স্বয়ংক্রিয় retry logic

Bindu-তে একটি built-in Tenacity-based retry mechanism আছে যা worker, storage, scheduler এবং API call জুড়ে transient failure সুন্দরভাবে হ্যান্ডেল করে। এটি নিশ্চিত করে যে আপনার এজেন্ট প্রোডাকশন environment-এ স্থিতিস্থাপক থাকে।

### ⚙️ ডিফল্ট সেটিংস

যদি কনফিগার না করা হয়, Bindu এই defaults ব্যবহার করে:

| Operation Type | Max Attempts | Min Wait | Max Wait |
| -------------- | ------------ | -------- | -------- |
| Worker         | 3            | 1.0s     | 10.0s    |
| Storage        | 5            | 0.5s     | 5.0s     |
| Scheduler      | 3            | 1.0s     | 8.0s     |
| API            | 4            | 1.0s     | 15.0s    |

---

<br/>

## [Sentry Integration](https://docs.getbindu.com/bindu/learn/sentry/overview)

> Bindu এজেন্টদের জন্য রিয়েল-টাইম error tracking এবং performance monitoring

Sentry একটি রিয়েল-টাইম error tracking এবং performance monitoring platform যা আপনাকে প্রোডাকশনে সমস্যা চিহ্নিত, নির্ণয় এবং সমাধান করতে সাহায্য করে। Bindu-তে আপনার AI এজেন্টদের জন্য comprehensive observability প্রদান করতে built-in Sentry integration আছে।

### ⚙️ কনফিগারেশন

<details>
<summary><b>কনফিগারেশন উদাহরণ দেখুন</b> (প্রসারিত করতে ক্লিক করুন)</summary>

আপনার `bindufy()` config-এ সরাসরি Sentry কনফিগার করুন:

```python
config = {
    "author": "gaurikasethi88@gmail.com",
    "name": "echo_agent",
    "description": "দ্রুত টেস্টিংয়ের জন্য একটি বেসিক echo এজেন্ট।",
    "deployment": {"url": "http://localhost:3773", "expose": True},
    "skills": [],
    "storage": {
        "type": "postgres",
        "database_url": "postgresql+asyncpg://bindu:bindu@localhost:5432/bindu",  # pragma: allowlist secret
        "run_migrations_on_startup": False,
    },
    # Scheduler কনফিগারেশন (ঐচ্ছিক)
    # Single-process-এর জন্য "memory" (default) বা distributed multi-process-এর জন্য "redis" ব্যবহার করুন
    "scheduler": {
        "type": "redis",
        "redis_url": "redis://localhost:6379/0",
    },
    # Sentry error tracking (ঐচ্ছিক)
    # Environment variable-এর পরিবর্তে code-এ সরাসরি Sentry কনফিগার করুন
    "sentry": {
        "enabled": True,
        "dsn": "https://252c0197ddeafb621f91abdbb59fa819@o4510504294612992.ingest.de.sentry.io/4510504299069520",
        "environment": "development",
        "traces_sample_rate": 1.0,
        "profiles_sample_rate": 0.1,
    },
}

def handler(messages):
    # আপনার এজেন্ট logic
    pass

bindufy(config, handler)
```

</details>

### 🚀 শুরু করা

1. **Sentry Account তৈরি করুন**: [sentry.io](https://sentry.io)-তে সাইন আপ করুন
2. **আপনার DSN পান**: Project settings থেকে কপি করুন
3. **Bindu কনফিগার করুন**: `sentry` config যোগ করুন (উপরে দেখুন)
4. **আপনার এজেন্ট রান করুন**: Sentry স্বয়ংক্রিয়ভাবে initialize হয়

> 📚 সম্পূর্ণ বিবরণের জন্য [সম্পূর্ণ Sentry ডকুমেন্টেশন](https://docs.getbindu.com/bindu/learn/sentry/overview) দেখুন।

---

<br/>

## [Skills System](https://docs.getbindu.com/bindu/skills/introduction/overview)

> বুদ্ধিমান এজেন্ট orchestration-এর জন্য সমৃদ্ধ capability advertisement

Bindu Skills System বুদ্ধিমান orchestration এবং এজেন্ট discovery-র জন্য সমৃদ্ধ এজেন্ট capability advertisement প্রদান করে। Claude-এর skills architecture দ্বারা অনুপ্রাণিত, এটি এজেন্টদের তাদের ক্ষমতা সম্পর্কে বিস্তারিত ডকুমেন্টেশন প্রদান করতে সক্ষম করে যাতে orchestrator-রা সচেতন routing সিদ্ধান্ত নিতে পারে।

### 💡 Skills কী?

Bindu-তে Skills **সমৃদ্ধ advertisement metadata** হিসেবে কাজ করে যা orchestrator-দের সাহায্য করে:

* 🔍 **আবিষ্কার করতে** একটি task-এর জন্য সঠিক এজেন্ট
* 📖 **বুঝতে** বিস্তারিত ক্ষমতা এবং সীমাবদ্ধতা
* ✅ **যাচাই করতে** execution-এর আগে requirements
* 📊 **অনুমান করতে** performance এবং resource needs
* 🔗 **Chain করতে** একাধিক এজেন্ট বুদ্ধিমানভাবে

> **নোট**: Skills executable code নয়—এগুলো structured metadata যা বর্ণনা করে আপনার এজেন্ট কী করতে পারে।

### 🔌 API Endpoints

**সব Skills তালিকা করুন**:
```bash
GET /agent/skills
```

**Skill বিবরণ পান**:
```bash
GET /agent/skills/{skill_id}
```

**Skill ডকুমেন্টেশন পান**:
```bash
GET /agent/skills/{skill_id}/documentation
```

> 📚 সম্পূর্ণ উদাহরণের জন্য [Skills ডকুমেন্টেশন](https://github.com/getbindu/Bindu/tree/main/examples/skills) দেখুন।

---

<br/>

## Negotiation

> বুদ্ধিমান orchestration-এর জন্য capability-based এজেন্ট selection

Bindu-র negotiation system orchestrator-দের একাধিক এজেন্ট query করতে এবং skills, performance, load এবং cost-এর ভিত্তিতে বুদ্ধিমানভাবে একটি task-এর জন্য সেরা এজেন্ট নির্বাচন করতে সক্ষম করে।

### 🔄 এটি কীভাবে কাজ করে

1. **Orchestrator broadcasts** একাধিক এজেন্টে assessment request
2. **এজেন্ট self-assess** skill matching এবং load analysis ব্যবহার করে capability
3. **Orchestrator ranks** multi-factor scoring ব্যবহার করে responses
4. **সেরা এজেন্ট নির্বাচিত** এবং task execute করা হয়

### 🔌 Assessment Endpoint

<details>
<summary><b>API বিবরণ দেখুন</b> (প্রসারিত করতে ক্লিক করুন)</summary>

```bash
POST /agent/negotiation
```

**Request:**
```json
{
  "task_summary": "PDF invoice থেকে table extract করুন",
  "task_details": "Invoice PDF প্রসেস করুন এবং structured data extract করুন",
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

### 📊 Scoring Algorithm

এজেন্ট একাধিক factor-এর ভিত্তিতে একটি confidence score গণনা করে:

```python
score = (
    skill_match * 0.6 +        # Primary: skill matching
    io_compatibility * 0.2 +   # Input/output format support
    performance * 0.1 +        # Speed এবং reliability
    load * 0.05 +              # বর্তমান availability
    cost * 0.05                # Pricing
)
```

> 📚 সম্পূর্ণ বিবরণের জন্য [Negotiation ডকুমেন্টেশন](https://docs.getbindu.com/bindu/negotiation/overview) দেখুন।

---

<br/>

## Task Feedback এবং DSPy

Bindu DSPy optimization-এর মাধ্যমে ক্রমাগত উন্নতি সক্ষম করতে task execution-এ user feedback সংগ্রহ করে। Rating এবং metadata সহ feedback স্টোর করে, আপনি বাস্তব interaction থেকে golden dataset তৈরি করতে পারেন এবং আপনার এজেন্টের prompt এবং behavior স্বয়ংক্রিয়ভাবে optimize করতে DSPy ব্যবহার করতে পারেন।

### Feedback জমা দেওয়া

`tasks/feedback` method ব্যবহার করে যেকোনো task-এ feedback প্রদান করুন:

```bash
curl --location 'http://localhost:3773/' \
--header 'Content-Type: application/json' \
--header 'Authorization: Bearer <your-token>' \
--data '{
    "jsonrpc": "2.0",
    "method": "tasks/feedback",
    "params": {
        "taskId": "550e8400-e29b-41d4-a716-446655440200",
        "feedback": "দুর্দান্ত কাজ! রেসপন্স খুবই সহায়ক এবং সঠিক ছিল।",
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

Feedback `task_feedback` table-এ স্টোর করা হয় এবং ব্যবহার করা যেতে পারে:
- Training data-র জন্য উচ্চ-মানের task interaction ফিল্টার করতে
- সফল বনাম ব্যর্থ completion-এ pattern চিহ্নিত করতে
- DSPy দিয়ে এজেন্ট instruction এবং few-shot example optimize করতে
- আমরা DsPY-তে কাজ করছি - শীঘ্রই রিলিজ করব।

---

<br/>

## 📬 Push Notifications

Bindu দীর্ঘ-চলমান task-এর জন্য **রিয়েল-টাইম webhook notification** সাপোর্ট করে, [A2A Protocol specification](https://a2a-protocol.org/latest/specification/) অনুসরণ করে। এটি client-দের polling ছাড়াই task state change এবং artifact generation সম্পর্কে push notification পেতে সক্ষম করে।

### দ্রুত শুরু

1. **Webhook receiver স্টার্ট করুন:** `python examples/webhook_client_example.py`
2. **এজেন্ট কনফিগার করুন** `examples/echo_agent_with_webhooks.py`-তে:
   ```python
   manifest = {
       "capabilities": {"push_notifications": True},
       "global_webhook_url": "http://localhost:8000/webhooks/task-updates",
       "global_webhook_token": "secret_abc123",
   }
   ```
3. **এজেন্ট রান করুন:** `python examples/echo_agent_with_webhooks.py`
4. **Task পাঠান** - webhook notification স্বয়ংক্রিয়ভাবে আসে

📖 **[সম্পূর্ণ ডকুমেন্টেশন](docs/NOTIFICATIONS.md)** - Architecture, security, example এবং troubleshooting সহ বিস্তারিত গাইড।

---

<br/>

## 🎨 Chat UI

Bindu `http://localhost:3773/docs`-এ একটি সুন্দর chat interface অন্তর্ভুক্ত করে

<p align="center">
  <img src="assets/agent-ui.png" alt="Bindu Agent UI" width="640" style="border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);" />
</p>

---

<br/>

## 🌐 Bindu Directory

[**Bindu Directory**](https://bindus.directory) হলো সব Bindu এজেন্টের একটি পাবলিক রেজিস্ট্রি, যা তাদের বৃহত্তর এজেন্ট ইকোসিস্টেমে আবিষ্কারযোগ্য এবং অ্যাক্সেসযোগ্য করে তোলে।

### ✨ Cookiecutter দিয়ে স্বয়ংক্রিয় রেজিস্ট্রেশন

যখন আপনি cookiecutter টেমপ্লেট ব্যবহার করে একটি এজেন্ট তৈরি করেন, এতে একটি প্রি-কনফিগার্ড GitHub Action থাকে যা স্বয়ংক্রিয়ভাবে আপনার এজেন্ট ডিরেক্টরিতে রেজিস্টার করে:

1. **আপনার এজেন্ট তৈরি করুন** cookiecutter ব্যবহার করে
2. **GitHub-এ Push করুন** - GitHub Action স্বয়ংক্রিয়ভাবে ট্রিগার হয়
3. **আপনার এজেন্ট দেখা যায়** [Bindu Directory](https://bindus.directory)-তে

> **🔑 নোট**: আপনাকে bindus.directory থেকে BINDU_PAT_TOKEN সংগ্রহ করতে হবে এবং আপনার এজেন্ট রেজিস্টার করতে এটি ব্যবহার করতে হবে।

### 📝 ম্যানুয়াল রেজিস্ট্রেশন

আমরা একটি ম্যানুয়াল রেজিস্ট্রেশন প্রক্রিয়ায় কাজ করছি।

---

<br/>

## 🌌 ভিশন

```
রাতের আকাশে এক ঝলক
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

_প্রতিটি চিহ্ন একটি এজেন্ট – বুদ্ধিমত্তার একটি স্ফুলিঙ্গ। ক্ষুদ্র বিন্দুটি হলো Bindu, Internet of Agents-এর উৎপত্তি বিন্দু।_

### NightSky সংযোগ [চলমান]

NightSky এজেন্টদের ঝাঁক সক্ষম করে। প্রতিটি Bindu একটি বিন্দু যা A2A, AP2, এবং X402-এর ভাগ করা ভাষা দিয়ে এজেন্টদের টীকা করে। এজেন্ট যেকোনো জায়গায় হোস্ট করা যেতে পারে – ল্যাপটপ, ক্লাউড বা ক্লাস্টারে – তবুও একই প্রোটোকল বলে, ডিজাইন অনুযায়ী একে অপরকে বিশ্বাস করে এবং একক, ডিস্ট্রিবিউটেড মন হিসেবে একসাথে কাজ করে।

> **💭 পরিকল্পনা ছাড়া লক্ষ্য শুধুই একটি ইচ্ছা।**

---

<br/>

## 🛠️ সমর্থিত এজেন্ট ফ্রেমওয়ার্ক

Bindu **ফ্রেমওয়ার্ক-অজ্ঞেয়বাদী** এবং টেস্ট করা হয়েছে:

- **Agno**
- **CrewAI**
- **LangChain**
- **LlamaIndex**
- **FastAgent**

আপনার প্রিয় ফ্রেমওয়ার্কের সাথে ইন্টিগ্রেশন চান? [Discord-এ আমাদের জানান](https://discord.gg/3w5zuYUuwt)!

---

<br/>

## 🧪 টেস্টিং

Bindu **70%+ টেস্ট কভারেজ** বজায় রাখে:

```bash
pytest -n auto --cov=bindu --cov-report= && coverage report --skip-covered --fail-under=70
```

---

<br/>

## সমস্যা সমাধান

<details>
<summary>সাধারণ সমস্যা</summary>

<br/>

| সমস্যা | সমাধান |
|---------|----------|
| `Python 3.12 not found` | Python 3.12+ ইনস্টল করুন এবং PATH-এ সেট করুন, অথবা `pyenv` ব্যবহার করুন |
| `bindu: command not found` | ভার্চুয়াল এনভায়রনমেন্ট অ্যাক্টিভেট করুন: `source .venv/bin/activate` |
| `Port 3773 already in use` | কনফিগে পোর্ট পরিবর্তন করুন: `"url": "http://localhost:4000"` |
| Pre-commit ব্যর্থ হয় | `pre-commit run --all-files` রান করুন |
| টেস্ট ব্যর্থ হয় | Dev ডিপেন্ডেন্সি ইনস্টল করুন: `uv sync --dev` |
| `Permission denied` (macOS) | এক্সটেন্ডেড অ্যাট্রিবিউট মুছতে `xattr -cr .` রান করুন |

**এনভায়রনমেন্ট রিসেট করুন:**
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

## 🤝 অবদান রাখুন

আমরা অবদানকে স্বাগত জানাই! [Discord](https://discord.gg/3w5zuYUuwt)-এ আমাদের সাথে যোগ দিন। আপনার অবদানের সাথে সবচেয়ে ভালো মেলে এমন চ্যানেল বেছে নিন।

```bash
git clone https://github.com/getbindu/Bindu.git
cd Bindu
uv venv --python 3.12.9
source .venv/bin/activate
uv sync --dev
pre-commit run --all-files
```

> 📖 [অবদান গাইডলাইন](.github/contributing.md)

---

<br/>

## 📜 লাইসেন্স

Bindu [Apache License 2.0](https://choosealicense.com/licenses/apache-2.0/)-এর অধীনে ওপেন-সোর্স।

---

<br/>

## 💬 কমিউনিটি

আমরা 💛 অবদান! আপনি বাগ ঠিক করুন, ডকুমেন্টেশন উন্নত করুন বা ডেমো তৈরি করুন – আপনার অবদান Bindu-কে আরও ভালো করে তোলে।

- 💬 আলোচনা এবং সাপোর্টের জন্য [Discord-এ যোগ দিন](https://discord.gg/3w5zuYUuwt)
- ⭐ যদি এটি উপযোগী মনে হয় তাহলে [রিপোজিটরিতে স্টার দিন](https://github.com/getbindu/Bindu)!

---

<br/>

## 👥 সক্রিয় মডারেটর

আমাদের নিবেদিত মডারেটররা একটি স্বাগতমূলক এবং উৎপাদনশীল কমিউনিটি বজায় রাখতে সাহায্য করে:

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

> মডারেটর হতে চান? [Discord](https://discord.gg/3w5zuYUuwt)-এ যোগাযোগ করুন!

---

<br/>

## 🙏 কৃতজ্ঞতা

এই প্রজেক্টগুলির প্রতি কৃতজ্ঞ:

- [FastA2A](https://github.com/pydantic/fasta2a)
- [12 Factor Agents](https://github.com/humanlayer/12-factor-agents/blob/main/content/factor-11-trigger-from-anywhere.md)
- [A2A](https://github.com/a2aproject/A2A)
- [AP2](https://github.com/google-agentic-commerce/AP2)
- [X402](https://github.com/coinbase/x402)
- [Bindu Logo](https://openmoji.org/library/emoji-1F33B/)
- [ASCII Space Art](https://www.asciiart.eu/space/other)

---

<br/>

## 🗺️ রোডম্যাপ

- [ ] GRPC ট্রান্সপোর্ট সাপোর্ট
- [x] Sentry এরর ট্র্যাকিং
- [x] Ag-UI ইন্টিগ্রেশন
- [x] Retry মেকানিজম
- [ ] টেস্ট কভারেজ 80%-এ বৃদ্ধি করা - চলমান
- [x] Redis scheduler ইমপ্লিমেন্টেশন
- [x] মেমরি স্টোরেজের জন্য Postgres ডাটাবেস
- [x] Negotiation সাপোর্ট
- [ ] AP2 end-to-end সাপোর্ট
- [ ] DSPy ইন্টিগ্রেশন - চলমান
- [ ] MLTS সাপোর্ট
- [ ] অন্যান্য facilitator-দের সাথে X402 সাপোর্ট

> 💡 [Discord-এ ফিচার সাজেস্ট করুন](https://discord.gg/3w5zuYUuwt)!

---

<br/>

## 🎓 ওয়ার্কশপ

- [AI Native in Action: Agent Symphony](https://www.meetup.com/ai-native-amsterdam/events/311066899/) - [স্লাইড](https://docs.google.com/presentation/d/1SqGXI0Gv_KCWZ1Mw2SOx_kI0u-LLxwZq7lMSONdl8oQ/edit)

---

<br/>

## ⭐ স্টার হিস্ট্রি

[![Star History Chart](https://api.star-history.com/svg?repos=getbindu/Bindu&type=Date)](https://www.star-history.com/#getbindu/Bindu&Date)

---

<p align="center">
  <strong>Amsterdam থেকে টিম দ্বারা 💛 দিয়ে তৈরি</strong><br/>
  <em>Happy Bindu! 🌻🚀✨</em>
</p>

<p align="center">
  <strong>আইডিয়া থেকে Internet of Agents পর্যন্ত ২ মিনিটে।</strong><br/>
  <em>আপনার এজেন্ট। আপনার ফ্রেমওয়ার্ক। সার্বজনীন প্রোটোকল।</em>
</p>

<p align="center">
  <a href="https://github.com/getbindu/Bindu">⭐ GitHub-এ আমাদের স্টার দিন</a> •
  <a href="https://discord.gg/3w5zuYUuwt">💬 Discord-এ যোগ দিন</a> •
  <a href="https://docs.getbindu.com">🌻 ডক্স পড়ুন</a>
</p>
