<div align="center" id="top">
  <a href="https://getbindu.com">
    <picture>
      <img src="assets/bindu.png" alt="Bindu" width="300">
    </picture>
  </a>
</div>

<p align="center">
  <em>AI एजेंट्स के लिए पहचान, संचार और भुगतान लेयर</em>
</p>

<p align="center">
  <a href="https://opensource.org/licenses/Apache-2.0"><img src="https://img.shields.io/badge/license-Apache%202.0-blue.svg" alt="License"></a>
  <a href="https://hits.sh/github.com/getbindu/Bindu.svg"><img src="https://hits.sh/github.com/getbindu/Bindu.svg" alt="Hits"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.12+-blue.svg" alt="Python Version"></a>
  <a href="https://pepy.tech/projects/bindu"><img src="https://static.pepy.tech/personalized-badge/bindu?period=total&units=INTERNATIONAL_SYSTEM&left_color=BLACK&right_color=GREEN&left_text=downloads" alt="PyPI Downloads"></a>
  <a href="https://pypi.org/project/bindu/"><img src="https://img.shields.io/pypi/v/bindu.svg" alt="PyPI version"></a>
  <a href="https://pypi.org/project/bindu/"><img src="https://img.shields.io/pypi/dm/bindu" alt="PyPI Downloads"></a>
  <a href="https://coveralls.io/github/getbindu/Bindu?branch=v0.3.18"><img src="https://coveralls.io/repos/github/getbindu/Bindu/badge.svg?branch=v0.3.18" alt="Coverage"></a>
  <a href="https://github.com/getbindu/Bindu/actions/workflows/release.yml"><img src="https://github.com/getbindu/Bindu/actions/workflows/release.yml/badge.svg" alt="Tests"></a>
  <a href="https://discord.gg/3w5zuYUuwt"><img src="https://img.shields.io/badge/Join%20Discord-7289DA?logo=discord&logoColor=white" alt="Discord"></a>
  <a href="https://github.com/getbindu/Bindu/graphs/contributors"><img src="https://img.shields.io/github/contributors/getbindu/Bindu" alt="Contributors"></a>
</p>

---

**Bindu** (उच्चारण: _बिंदु_) AI एजेंट्स के लिए एक ऑपरेटिंग लेयर है जो पहचान, संचार और भुगतान क्षमताएं प्रदान करता है। यह एक प्रोडक्शन-रेडी सर्विस है जो सुविधाजनक API के साथ डिस्ट्रिब्यूटेड सिस्टम्स में एजेंट्स को कनेक्ट, ऑथेंटिकेट और ऑर्केस्ट्रेट करती है – ओपन प्रोटोकॉल का उपयोग करते हुए: **A2A**, **AP2**, और **X402**।

डिस्ट्रिब्यूटेड आर्किटेक्चर (Task Manager, scheduler, storage) के साथ बनाया गया, Bindu तेज़ी से डेवलप करना और किसी भी AI फ्रेमवर्क के साथ इंटीग्रेट करना आसान बनाता है। किसी भी एजेंट फ्रेमवर्क को Internet of Agents में संचार, सहयोग और कॉमर्स के लिए पूरी तरह से इंटरऑपरेबल सर्विस में बदल दें।

<p align="center">
  <strong>🌟 <a href="https://bindus.directory">अपना एजेंट रजिस्टर करें</a> • 🌻 <a href="https://docs.getbindu.com">डॉक्यूमेंटेशन</a> • 💬 <a href="https://discord.gg/3w5zuYUuwt">Discord कम्युनिटी</a></strong>
</p>

---

<br/>

## 🎥 Bindu को एक्शन में देखें

<div align="center">
  <a href="https://www.youtube.com/watch?v=qppafMuw_KI" target="_blank">
    <img src="https://img.youtube.com/vi/qppafMuw_KI/maxresdefault.jpg" alt="Bindu Demo" width="640" style="border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);" />
  </a>
</div>

## 📋 आवश्यकताएं

Bindu इंस्टॉल करने से पहले सुनिश्चित करें कि आपके पास है:

- **Python 3.12 या उससे ऊपर** - [यहां डाउनलोड करें](https://www.python.org/downloads/)
- **UV Package Manager** - [इंस्टॉलेशन गाइड](https://github.com/astral-sh/uv)
- **API Key आवश्यक**: अपने environment variables में `OPENROUTER_API_KEY` या `OPENAI_API_KEY` सेट करें। टेस्टिंग के लिए फ्री OpenRouter models उपलब्ध हैं।

### अपना सेटअप वेरिफाई करें

```bash
# Python वर्जन चेक करें
uv run python --version  # 3.12 या उससे ऊपर दिखाना चाहिए

# UV इंस्टॉलेशन चेक करें
uv --version
```

---

<br/>

## 📦 इंस्टॉलेशन

<details>
<summary><b>Windows यूजर्स के लिए नोट (Git & GitHub Desktop)</b></summary>

कुछ Windows सिस्टम्स पर, इंस्टॉलेशन के बाद भी Command Prompt में git को पहचाना नहीं जा सकता – PATH कॉन्फ़िगरेशन समस्याओं के कारण।

यदि आप इस समस्या का सामना करते हैं, तो आप विकल्प के रूप में *GitHub Desktop* का उपयोग कर सकते हैं:

1. https://desktop.github.com/ से GitHub Desktop इंस्टॉल करें
2. अपने GitHub अकाउंट से साइन इन करें
3. रिपॉजिटरी URL का उपयोग करके क्लोन करें:
   https://github.com/getbindu/Bindu.git

GitHub Desktop आपको कमांड लाइन के बिना रिपॉजिटरी क्लोन करने, ब्रांच मैनेज करने, चेंजेस कमिट करने और pull request खोलने की सुविधा देता है।

</details>

```bash
# Bindu इंस्टॉल करें
uv add bindu

# डेवलपमेंट के लिए (यदि आप Bindu में कंट्रिब्यूट कर रहे हैं)
# वर्चुअल एनवायरनमेंट बनाएं और एक्टिवेट करें
uv venv --python 3.12.9
source .venv/bin/activate  # macOS/Linux पर
# .venv\Scripts\activate  # Windows पर

uv sync --dev
```

<details>
<summary><b>सामान्य इंस्टॉलेशन समस्याएं</b> (विस्तार के लिए क्लिक करें)</summary>

<br/>

| समस्या | समाधान |
|-------|----------|
| `uv: command not found` | UV इंस्टॉल करने के बाद टर्मिनल रीस्टार्ट करें। Windows पर PowerShell का उपयोग करें |
| `Python version not supported` | [python.org](https://www.python.org/downloads/) से Python 3.12+ इंस्टॉल करें |
| वर्चुअल एनवायरनमेंट एक्टिवेट नहीं हो रहा (Windows) | PowerShell का उपयोग करें और `.venv\Scripts\activate` रन करें |
| `Microsoft Visual C++ required` | [Visual C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/) डाउनलोड करें |
| `ModuleNotFoundError` | venv एक्टिवेट करें और `uv sync --dev` रन करें |

</details>

---

<br/>

## 🚀 त्वरित शुरुआत

### विकल्प 1: Cookiecutter का उपयोग करें (अनुशंसित)

**पहले एजेंट तक का समय: ~2 मिनट ⏱️**

```bash
# Cookiecutter इंस्टॉल करें
uv add cookiecutter

# अपना Bindu एजेंट बनाएं
uvx cookiecutter https://github.com/getbindu/create-bindu-agent.git
```

## 🎥 मिनटों में प्रोडक्शन-रेडी एजेंट बनाएं

<div align="center">
  <a href="https://youtu.be/obY1bGOoWG8?si=uEeDb0XWrtYOQTL7" target="_blank">
    <img src="https://img.youtube.com/vi/obY1bGOoWG8/maxresdefault.jpg" alt="Bindu Demo" width="640" style="border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);" />
  </a>
</div>

बस हो गया! आपका लोकल एजेंट अब एक लाइव, सिक्योर और डिस्कवरेबल सर्विस है। [और जानें →](https://docs.getbindu.com/bindu/create-bindu-agent/overview)

> **💡 प्रो टिप:** Cookiecutter से बनाए गए एजेंट्स में GitHub Actions होते हैं जो आपके रिपॉजिटरी में push करने पर स्वचालित रूप से [Bindu Directory](https://bindus.directory) में एजेंट को रजिस्टर कर देते हैं। मैनुअल रजिस्ट्रेशन की जरूरत नहीं!

### विकल्प 2: मैनुअल सेटअप

अपनी एजेंट स्क्रिप्ट `my_agent.py` बनाएं:

```python
from bindu.penguin.bindufy import bindufy
from agno.agent import Agent
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.models.openai import OpenAIChat

# अपना एजेंट डिफाइन करें
agent = Agent(
    instructions="आप एक रिसर्च असिस्टेंट हैं जो जानकारी खोजते और सारांशित करते हैं।",
    model=OpenAIChat(id="gpt-4o"),
    tools=[DuckDuckGoTools()],
)

# कॉन्फ़िगरेशन
config = {
    "author": "your.email@example.com",
    "name": "research_agent",
    "description": "एक रिसर्च असिस्टेंट एजेंट",
    "deployment": {"url": "http://localhost:3773", "expose": True},
    "skills": ["skills/question-answering", "skills/pdf-processing"]
}

# Handler फंक्शन
def handler(messages: list[dict[str, str]]):
    """मैसेज प्रोसेस करता है और एजेंट का रिस्पॉन्स रिटर्न करता है।

    Args:
        messages: बातचीत के इतिहास के साथ मैसेज डिक्शनरी की लिस्ट

    Returns:
        एजेंट रिस्पॉन्स रिजल्ट
    """
    result = agent.run(input=messages)
    return result

# Bindu-फाई करें
bindufy(config, handler)
```

![Sample Agent](assets/agno-simple.png)

आपका एजेंट अब `http://localhost:3773` पर लाइव है और दूसरे एजेंट्स के साथ कम्युनिकेट करने के लिए तैयार है।

---

### विकल्प 3: मिनिमल Echo एजेंट (टेस्टिंग)

<details>
<summary><b>मिनिमल उदाहरण देखें</b> (विस्तार के लिए क्लिक करें)</summary>

सबसे छोटा काम करने वाला एजेंट:

```python
from bindu.penguin.bindufy import bindufy

def handler(messages):
    return [{"role": "assistant", "content": messages[-1]["content"]}]

config = {
    "author": "your.email@example.com",
    "name": "echo_agent",
    "description": "त्वरित टेस्टिंग के लिए एक बेसिक echo एजेंट।",
    "deployment": {"url": "http://localhost:3773", "expose": True},
    "skills": []
}

bindufy(config, handler)
```

**रन और टेस्ट करें:**

```bash
# एजेंट स्टार्ट करें
python examples/echo_agent.py
```

</details>

<details>
<summary><b>curl के साथ एजेंट टेस्ट करें</b> (विस्तार के लिए क्लिक करें)</summary>

<br/>

इनपुट:
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

आउटपुट:
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

Task का स्टेटस चेक करें
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

आउटपुट:
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

Bindu प्रोडक्शन डिप्लॉयमेंट के लिए PostgreSQL को अपने persistent storage backend के रूप में उपयोग करता है। Storage लेयर SQLAlchemy के async engine के साथ बनाई गई है और protocol TypedDicts के साथ imperative mapping का उपयोग करती है।

यह वैकल्पिक है - डिफ़ॉल्ट रूप से InMemoryStorage का उपयोग किया जाता है।

### 📊 Storage स्ट्रक्चर

Storage लेयर तीन मुख्य टेबल्स का उपयोग करती है:

1. **tasks_table**: JSONB history और artifacts के साथ सभी tasks को स्टोर करता है
2. **contexts_table**: Context metadata और message history को बनाए रखता है
3. **task_feedback_table**: Tasks के लिए वैकल्पिक feedback storage

### ⚙️ कॉन्फ़िगरेशन

<details>
<summary><b>कॉन्फ़िगरेशन उदाहरण देखें</b> (विस्तार के लिए क्लिक करें)</summary>

अपने environment या settings में PostgreSQL connection कॉन्फ़िगर करें:
एजेंट के config में connection string प्रदान करें।

```json
config = {
    "author": "your.email@example.com",
    "name": "research_agent",
    "description": "एक रिसर्च असिस्टेंट एजेंट",
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

**💡 Task-First Pattern**: Storage Bindu के task-first approach को सपोर्ट करता है जहां non-terminal tasks में messages जोड़कर tasks को जारी रखा जा सकता है, जो incremental refinements और multi-turn conversations को सक्षम बनाता है।

---

<br/>

## [Redis Scheduler](https://docs.getbindu.com/bindu/learn/scheduler/overview)

Bindu कई workers और processes में काम को समन्वित करने के लिए Redis को अपने distributed task scheduler के रूप में उपयोग करता है। Scheduler कुशल task distribution के लिए blocking operations के साथ Redis lists का उपयोग करता है।

यह वैकल्पिक है - डिफ़ॉल्ट रूप से InMemoryScheduler का उपयोग किया जाता है।

### ⚙️ कॉन्फ़िगरेशन

<details>
<summary><b>कॉन्फ़िगरेशन उदाहरण देखें</b> (विस्तार के लिए क्लिक करें)</summary>

अपने एजेंट config में Redis connection कॉन्फ़िगर करें:

```json
config = {
    "author": "your.email@example.com",
    "name": "research_agent",
    "description": "एक रिसर्च असिस्टेंट एजेंट",
    "deployment": {"url": "http://localhost:3773", "expose": True},
    "skills": ["skills/question-answering", "skills/pdf-processing"],
     "scheduler": {
        "type": "redis",
        "redis_url": "redis://localhost:6379/0",
    },
}
```

</details>

सभी operations Redis में queue किए जाते हैं और उपलब्ध workers द्वारा blocking pop mechanism का उपयोग करके प्रोसेस किए जाते हैं, जो polling overhead के बिना कुशल distribution सुनिश्चित करता है।

---

<br/>

## [Retry Mechanism](https://docs.getbindu.com/bindu/learn/retry/overview)

> लचीले Bindu एजेंट्स के लिए exponential backoff के साथ स्वचालित retry logic

Bindu में एक built-in Tenacity-based retry mechanism है जो workers, storage, schedulers और API calls में transient failures को सुचारू रूप से संभालता है। यह सुनिश्चित करता है कि आपके एजेंट्स प्रोडक्शन environments में लचीले रहें।

### ⚙️ डिफ़ॉल्ट सेटिंग्स

यदि कॉन्फ़िगर नहीं किया गया है, तो Bindu इन defaults का उपयोग करता है:

| Operation Type | Max Attempts | Min Wait | Max Wait |
| -------------- | ------------ | -------- | -------- |
| Worker         | 3            | 1.0s     | 10.0s    |
| Storage        | 5            | 0.5s     | 5.0s     |
| Scheduler      | 3            | 1.0s     | 8.0s     |
| API            | 4            | 1.0s     | 15.0s    |

---

<br/>

## [Sentry Integration](https://docs.getbindu.com/bindu/learn/sentry/overview)

> Bindu एजेंट्स के लिए रियल-टाइम error tracking और performance monitoring

Sentry एक रियल-टाइम error tracking और performance monitoring platform है जो आपको प्रोडक्शन में समस्याओं की पहचान करने, निदान करने और ठीक करने में मदद करता है। Bindu में आपके AI एजेंट्स के लिए व्यापक observability प्रदान करने के लिए built-in Sentry integration है।

### ⚙️ कॉन्फ़िगरेशन

<details>
<summary><b>कॉन्फ़िगरेशन उदाहरण देखें</b> (विस्तार के लिए क्लिक करें)</summary>

अपने `bindufy()` config में सीधे Sentry कॉन्फ़िगर करें:

```python
config = {
    "author": "gaurikasethi88@gmail.com",
    "name": "echo_agent",
    "description": "त्वरित टेस्टिंग के लिए एक बेसिक echo एजेंट।",
    "deployment": {"url": "http://localhost:3773", "expose": True},
    "skills": [],
    "storage": {
        "type": "postgres",
        "database_url": "postgresql+asyncpg://bindu:bindu@localhost:5432/bindu",  # pragma: allowlist secret
        "run_migrations_on_startup": False,
    },
    # Scheduler कॉन्फ़िगरेशन (वैकल्पिक)
    # Single-process के लिए "memory" (default) या distributed multi-process के लिए "redis" का उपयोग करें
    "scheduler": {
        "type": "redis",
        "redis_url": "redis://localhost:6379/0",
    },
    # Sentry error tracking (वैकल्पिक)
    # Environment variables के बजाय code में सीधे Sentry कॉन्फ़िगर करें
    "sentry": {
        "enabled": True,
        "dsn": "https://252c0197ddeafb621f91abdbb59fa819@o4510504294612992.ingest.de.sentry.io/4510504299069520",
        "environment": "development",
        "traces_sample_rate": 1.0,
        "profiles_sample_rate": 0.1,
    },
}

def handler(messages):
    # आपका एजेंट logic
    pass

bindufy(config, handler)
```

</details>

### 🚀 शुरुआत करना

1. **Sentry Account बनाएं**: [sentry.io](https://sentry.io) पर साइन अप करें
2. **अपना DSN प्राप्त करें**: Project settings से कॉपी करें
3. **Bindu कॉन्फ़िगर करें**: `sentry` config जोड़ें (ऊपर देखें)
4. **अपना एजेंट रन करें**: Sentry स्वचालित रूप से initialize होता है

> 📚 पूर्ण विवरण के लिए [पूर्ण Sentry डॉक्यूमेंटेशन](https://docs.getbindu.com/bindu/learn/sentry/overview) देखें।

---

<br/>

## [Skills System](https://docs.getbindu.com/bindu/skills/introduction/overview)

> बुद्धिमान एजेंट orchestration के लिए समृद्ध capability advertisement

Bindu Skills System बुद्धिमान orchestration और एजेंट discovery के लिए समृद्ध एजेंट capability advertisement प्रदान करता है। Claude की skills architecture से प्रेरित, यह एजेंट्स को उनकी क्षमताओं के बारे में विस्तृत documentation प्रदान करने में सक्षम बनाता है ताकि orchestrators सूचित routing निर्णय ले सकें।

### 💡 Skills क्या हैं?

Bindu में Skills **समृद्ध advertisement metadata** के रूप में कार्य करते हैं जो orchestrators की मदद करते हैं:

* 🔍 **खोजने** में एक task के लिए सही एजेंट
* 📖 **समझने** में विस्तृत क्षमताएं और सीमाएं
* ✅ **सत्यापित करने** में execution से पहले requirements
* 📊 **अनुमान लगाने** में performance और resource needs
* 🔗 **Chain करने** में कई एजेंट्स को बुद्धिमानी से

> **नोट**: Skills executable code नहीं हैं—वे structured metadata हैं जो वर्णन करते हैं कि आपका एजेंट क्या कर सकता है।

### 🔌 API Endpoints

**सभी Skills की सूची बनाएं**:
```bash
GET /agent/skills
```

**Skill विवरण प्राप्त करें**:
```bash
GET /agent/skills/{skill_id}
```

**Skill डॉक्यूमेंटेशन प्राप्त करें**:
```bash
GET /agent/skills/{skill_id}/documentation
```

> 📚 पूर्ण उदाहरणों के लिए [Skills डॉक्यूमेंटेशन](https://github.com/getbindu/Bindu/tree/main/examples/skills) देखें।

---

<br/>

## Negotiation

> बुद्धिमान orchestration के लिए capability-based एजेंट selection

Bindu का negotiation system orchestrators को कई एजेंट्स को query करने और skills, performance, load और cost के आधार पर बुद्धिमानी से एक task के लिए सबसे अच्छा एजेंट चुनने में सक्षम बनाता है।

### 🔄 यह कैसे काम करता है

1. **Orchestrator broadcasts** कई एजेंट्स को assessment request
2. **एजेंट्स self-assess** skill matching और load analysis का उपयोग करके capability
3. **Orchestrator ranks** multi-factor scoring का उपयोग करके responses
4. **सबसे अच्छा एजेंट चुना जाता है** और task execute किया जाता है

### 🔌 Assessment Endpoint

<details>
<summary><b>API विवरण देखें</b> (विस्तार के लिए क्लिक करें)</summary>

```bash
POST /agent/negotiation
```

**Request:**
```json
{
  "task_summary": "PDF invoices से tables extract करें",
  "task_details": "Invoice PDFs को process करें और structured data extract करें",
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

एजेंट्स कई factors के आधार पर एक confidence score की गणना करते हैं:

```python
score = (
    skill_match * 0.6 +        # Primary: skill matching
    io_compatibility * 0.2 +   # Input/output format support
    performance * 0.1 +        # Speed और reliability
    load * 0.05 +              # वर्तमान availability
    cost * 0.05                # Pricing
)
```

> 📚 पूर्ण विवरण के लिए [Negotiation डॉक्यूमेंटेशन](https://docs.getbindu.com/bindu/negotiation/overview) देखें।

---

<br/>

## Task Feedback और DSPy

Bindu DSPy optimization के माध्यम से निरंतर सुधार को सक्षम करने के लिए task executions पर user feedback एकत्र करता है। Ratings और metadata के साथ feedback स्टोर करके, आप वास्तविक interactions से golden datasets बना सकते हैं और अपने एजेंट के prompts और behavior को स्वचालित रूप से optimize करने के लिए DSPy का उपयोग कर सकते हैं।

### Feedback सबमिट करना

`tasks/feedback` method का उपयोग करके किसी भी task पर feedback प्रदान करें:

```bash
curl --location 'http://localhost:3773/' \
--header 'Content-Type: application/json' \
--header 'Authorization: Bearer <your-token>' \
--data '{
    "jsonrpc": "2.0",
    "method": "tasks/feedback",
    "params": {
        "taskId": "550e8400-e29b-41d4-a716-446655440200",
        "feedback": "बढ़िया काम! रिस्पॉन्स बहुत मददगार और सटीक था।",
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

Feedback `task_feedback` table में स्टोर किया जाता है और इसका उपयोग किया जा सकता है:
- Training data के लिए उच्च-गुणवत्ता वाले task interactions को फ़िल्टर करने के लिए
- सफल बनाम असफल completions में patterns की पहचान करने के लिए
- DSPy के साथ एजेंट instructions और few-shot examples को optimize करने के लिए
- हम DsPY पर काम कर रहे हैं - जल्द ही रिलीज़ करेंगे।

---

<br/>

## 📬 Push Notifications

Bindu लंबे समय तक चलने वाले tasks के लिए **रियल-टाइम webhook notifications** का समर्थन करता है, [A2A Protocol specification](https://a2a-protocol.org/latest/specification/) का पालन करते हुए। यह clients को polling के बिना task state changes और artifact generation के बारे में push notifications प्राप्त करने में सक्षम बनाता है।

### त्वरित शुरुआत

1. **Webhook receiver स्टार्ट करें:** `python examples/webhook_client_example.py`
2. **एजेंट कॉन्फ़िगर करें** `examples/echo_agent_with_webhooks.py` में:
   ```python
   manifest = {
       "capabilities": {"push_notifications": True},
       "global_webhook_url": "http://localhost:8000/webhooks/task-updates",
       "global_webhook_token": "secret_abc123",
   }
   ```
3. **एजेंट रन करें:** `python examples/echo_agent_with_webhooks.py`
4. **Tasks भेजें** - webhook notifications स्वचालित रूप से आते हैं

📖 **[पूर्ण डॉक्यूमेंटेशन](docs/NOTIFICATIONS.md)** - Architecture, security, examples और troubleshooting के साथ विस्तृत गाइड।

---

<br/>

## 🎨 Chat UI

Bindu `http://localhost:3773/docs` पर एक सुंदर chat interface शामिल करता है

<p align="center">
  <img src="assets/agent-ui.png" alt="Bindu Agent UI" width="640" style="border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);" />
</p>

---

<br/>

## 🌐 Bindu Directory

[**Bindu Directory**](https://bindus.directory) सभी Bindu एजेंट्स की एक पब्लिक रजिस्ट्री है, जो उन्हें व्यापक एजेंट इकोसिस्टम में डिस्कवरेबल और एक्सेसिबल बनाती है।

### ✨ Cookiecutter के साथ ऑटोमैटिक रजिस्ट्रेशन

जब आप cookiecutter टेम्पलेट का उपयोग करके एक एजेंट बनाते हैं, तो इसमें एक प्री-कॉन्फ़िगर्ड GitHub Action होता है जो स्वचालित रूप से आपके एजेंट को डायरेक्टरी में रजिस्टर करता है:

1. **अपना एजेंट बनाएं** cookiecutter का उपयोग करके
2. **GitHub पर Push करें** - GitHub Action स्वचालित रूप से ट्रिगर होता है
3. **आपका एजेंट दिखाई देता है** [Bindu Directory](https://bindus.directory) में

> **🔑 नोट**: आपको bindus.directory से BINDU_PAT_TOKEN एकत्र करना होगा और अपने एजेंट को रजिस्टर करने के लिए इसका उपयोग करना होगा।

### 📝 मैनुअल रजिस्ट्रेशन

हम एक मैनुअल रजिस्ट्रेशन प्रक्रिया पर काम कर रहे हैं।

---

<br/>

## 🌌 विजन

```
रात के आकाश में एक झलक
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

_हर प्रतीक एक एजेंट है – बुद्धिमत्ता की एक चिंगारी। छोटा बिंदु Bindu है, Internet of Agents में उत्पत्ति का बिंदु।_

### NightSky कनेक्शन [प्रगति में]

NightSky एजेंट्स के झुंड को सक्षम बनाता है। प्रत्येक Bindu एक बिंदु है जो A2A, AP2, और X402 की साझा भाषा के साथ एजेंट्स को एनोटेट करता है। एजेंट्स कहीं भी होस्ट किए जा सकते हैं – लैपटॉप, क्लाउड या क्लस्टर में – फिर भी एक ही प्रोटोकॉल बोलते हैं, डिज़ाइन द्वारा एक-दूसरे पर भरोसा करते हैं, और एक एकल, डिस्ट्रिब्यूटेड माइंड के रूप में एक साथ काम करते हैं।

> **💭 प्लान के बिना लक्ष्य सिर्फ एक इच्छा है।**

---

<br/>

## 🛠️ समर्थित एजेंट फ्रेमवर्क्स

Bindu **फ्रेमवर्क-एग्नोस्टिक** है और टेस्ट किया गया है:

- **Agno**
- **CrewAI**
- **LangChain**
- **LlamaIndex**
- **FastAgent**

अपने पसंदीदा फ्रेमवर्क के साथ इंटीग्रेशन चाहते हैं? [Discord पर हमें बताएं](https://discord.gg/3w5zuYUuwt)!

---

<br/>

## 🧪 टेस्टिंग

Bindu **70%+ टेस्ट कवरेज** बनाए रखता है:

```bash
pytest -n auto --cov=bindu --cov-report= && coverage report --skip-covered --fail-under=70
```

---

<br/>

## समस्या निवारण

<details>
<summary>सामान्य समस्याएं</summary>

<br/>

| समस्या | समाधान |
|---------|----------|
| `Python 3.12 not found` | Python 3.12+ इंस्टॉल करें और PATH में सेट करें, या `pyenv` का उपयोग करें |
| `bindu: command not found` | वर्चुअल एनवायरनमेंट एक्टिवेट करें: `source .venv/bin/activate` |
| `Port 3773 already in use` | कॉन्फ़िग में पोर्ट बदलें: `"url": "http://localhost:4000"` |
| Pre-commit फेल होता है | `pre-commit run --all-files` रन करें |
| टेस्ट फेल होते हैं | Dev डिपेंडेंसी इंस्टॉल करें: `uv sync --dev` |
| `Permission denied` (macOS) | एक्सटेंडेड एट्रिब्यूट्स क्लियर करने के लिए `xattr -cr .` रन करें |

**एनवायरनमेंट रीसेट करें:**
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

## 🤝 योगदान करें

हम योगदान का स्वागत करते हैं! [Discord](https://discord.gg/3w5zuYUuwt) पर हमसे जुड़ें। वह चैनल चुनें जो आपके योगदान से सबसे अच्छा मेल खाता हो।

```bash
git clone https://github.com/getbindu/Bindu.git
cd Bindu
uv venv --python 3.12.9
source .venv/bin/activate
uv sync --dev
pre-commit run --all-files
```

> 📖 [योगदान दिशानिर्देश](.github/contributing.md)

---

<br/>

## 📜 लाइसेंस

Bindu [Apache License 2.0](https://choosealicense.com/licenses/apache-2.0/) के तहत ओपन-सोर्स है।

---

<br/>

## 💬 कम्युनिटी

हम 💛 योगदान! चाहे आप बग्स फिक्स कर रहे हों, डॉक्यूमेंटेशन सुधार रहे हों, या डेमो बना रहे हों – आपका योगदान Bindu को बेहतर बनाता है।

- 💬 चर्चा और सपोर्ट के लिए [Discord जॉइन करें](https://discord.gg/3w5zuYUuwt)
- ⭐ यदि आपको यह उपयोगी लगे तो [रिपॉजिटरी को स्टार करें](https://github.com/getbindu/Bindu)!

---

<br/>

## 👥 सक्रिय मॉडरेटर्स

हमारे समर्पित मॉडरेटर्स एक स्वागत योग्य और उत्पादक कम्युनिटी बनाए रखने में मदद करते हैं:

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

> मॉडरेटर बनना चाहते हैं? [Discord](https://discord.gg/3w5zuYUuwt) पर संपर्क करें!

---

<br/>

## 🙏 आभार

इन प्रोजेक्ट्स के लिए आभारी:

- [FastA2A](https://github.com/pydantic/fasta2a)
- [12 Factor Agents](https://github.com/humanlayer/12-factor-agents/blob/main/content/factor-11-trigger-from-anywhere.md)
- [A2A](https://github.com/a2aproject/A2A)
- [AP2](https://github.com/google-agentic-commerce/AP2)
- [X402](https://github.com/coinbase/x402)
- [Bindu Logo](https://openmoji.org/library/emoji-1F33B/)
- [ASCII Space Art](https://www.asciiart.eu/space/other)

---

<br/>

## 🗺️ रोडमैप

- [ ] GRPC ट्रांसपोर्ट सपोर्ट
- [x] Sentry एरर ट्रैकिंग
- [x] Ag-UI इंटीग्रेशन
- [x] Retry मैकेनिज्म
- [ ] टेस्ट कवरेज को 80% तक बढ़ाना - प्रगति में
- [x] Redis scheduler इम्प्लीमेंटेशन
- [x] मेमोरी स्टोरेज के लिए Postgres डेटाबेस
- [x] Negotiation सपोर्ट
- [ ] AP2 end-to-end सपोर्ट
- [ ] DSPy इंटीग्रेशन - प्रगति में
- [ ] MLTS सपोर्ट
- [ ] अन्य facilitators के साथ X402 सपोर्ट

> 💡 [Discord पर फीचर्स सुझाएं](https://discord.gg/3w5zuYUuwt)!

---

<br/>

## 🎓 वर्कशॉप्स

- [AI Native in Action: Agent Symphony](https://www.meetup.com/ai-native-amsterdam/events/311066899/) - [स्लाइड्स](https://docs.google.com/presentation/d/1SqGXI0Gv_KCWZ1Mw2SOx_kI0u-LLxwZq7lMSONdl8oQ/edit)

---

<br/>

## ⭐ स्टार हिस्ट्री

[![Star History Chart](https://api.star-history.com/svg?repos=getbindu/Bindu&type=Date)](https://www.star-history.com/#getbindu/Bindu&Date)

---

<p align="center">
  <strong>Amsterdam से टीम द्वारा 💛 के साथ बनाया गया</strong><br/>
  <em>Happy Bindu! 🌻🚀✨</em>
</p>

<p align="center">
  <strong>आइडिया से Internet of Agents तक 2 मिनट में।</strong><br/>
  <em>आपका एजेंट। आपका फ्रेमवर्क। यूनिवर्सल प्रोटोकॉल्स।</em>
</p>

<p align="center">
  <a href="https://github.com/getbindu/Bindu">⭐ GitHub पर हमें स्टार करें</a> •
  <a href="https://discord.gg/3w5zuYUuwt">💬 Discord जॉइन करें</a> •
  <a href="https://docs.getbindu.com">🌻 डॉक्स पढ़ें</a>
</p>
