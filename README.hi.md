<div align="center" id="top">
  <a href="https://getbindu.com">
    <picture>
      <img src="assets/bindu.png" alt="Bindu" width="300">
    </picture>
  </a>
</div>

<p align="center">
  <em>AI एजेंटों के लिए पहचान, संचार और भुगतान परत</em>
</p>

<p align="center">
  <a href="README.md">🇬🇧 English</a> •
  <a href="README.de.md">🇩🇪 Deutsch</a> •
  <a href="README.es.md">🇪🇸 Español</a> •
  <a href="README.fr.md">🇫🇷 Français</a> •
  <a href="README.hi.md">🇮🇳 हिंदी</a> •
  <a href="README.bn.md">🇮🇳 বাংলা</a> •
  <a href="README.zh.md">🇨🇳 中文</a> •
  <a href="README.nl.md">🇳🇱 Nederlands</a> •
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
  <em>"सूरजमुखी की तरह जो प्रकाश की ओर मुड़ते हैं, एजेंट झुंड में सहयोग करते हैं - प्रत्येक स्वतंत्र, फिर भी मिलकर वे कुछ बड़ा बनाते हैं।"</em>
</p>

<br/>

<div align="center">
  <h3>एक लाइन में अपने एजेंट को ऑनबोर्ड करें</h3>
</div>

<div align="center">
  <pre><code>curl -fsSL https://getbindu.com/install-bindu.sh | bash</code></pre>
</div>

---

**Bindu** (पढ़ें: _binduu_) AI एजेंटों के लिए एक संचालन परत है जो पहचान, संचार और भुगतान क्षमताएँ प्रदान करती है। यह एक उत्पादन-तैयार सेवा प्रदान करती है जिसमें एजेंटों को कनेक्ट, प्रमाणित और व्यवस्थित करने के लिए एक सुविधाजनक API है, जो ओपन प्रोटोकॉल का उपयोग करते हुए वितरित प्रणालियों में काम करती है: **A2A**, **AP2**, और **X402**।बंटा हुआ आर्किटेक्चर (कार्य प्रबंधक, शेड्यूलर, भंडारण) के साथ निर्मित, बिंदु को विकसित करना तेज़ बनाता है और किसी भी एआई ढांचे के साथ एकीकृत करना आसान बनाता है। किसी भी एजेंट ढांचे को संचार, सहयोग और वाणिज्य के लिए एक पूरी तरह से इंटरऑपरेबल सेवा में बदलें, जो एजेंटों के इंटरनेट में है।

<p align="center">
  <strong>🌟 <a href="https://getbindu.com">अपने एजेंट को पंजीकृत करें</a> • 🌻 <a href="https://docs.getbindu.com">दस्तावेज़ीकरण</a> • 💬 <a href="https://discord.gg/3w5zuYUuwt">डिस्कॉर्ड समुदाय</a></strong>
</p>


---

<br/>

## 🎥 बिंदु को क्रियान्वित होते हुए देखें

<div align="center">
  <a href="https://www.youtube.com/watch?v=qppafMuw_KI" target="_blank">
    <img src="https://img.youtube.com/vi/qppafMuw_KI/maxresdefault.jpg" alt="Bindu Demo" width="640" style="border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);" />
  </a>
</div>

<br/>

## 📋 पूर्वापेक्षाएँ

बिंदु को स्थापित करने से पहले, सुनिश्चित करें कि आपके पास है:

- **Python 3.12 या उच्चतर** - [Download here](https://www.python.org/downloads/)
- **UV पैकेज प्रबंधक** - [Installation guide](https://github.com/astral-sh/uv)
- **API कुंजी आवश्यक**: अपने पर्यावरण चर में `OPENROUTER_API_KEY` या `OPENAI_API_KEY` सेट करें। परीक्षण के लिए मुफ्त OpenRouter मॉडल उपलब्ध हैं।


### अपने सेटअप की पुष्टि करें

```bash
# Check Python version
uv run python --version  # Should show 3.12 or higher

# Check UV installation
uv --version
```

---

<br/>

## 📦 स्थापना
<details>
<summary><b>उपयोगकर्ताओं का नोट (Git & GitHub डेस्कटॉप)</b></summary>

कुछ विंडोज सिस्टम पर, PATH कॉन्फ़िगरेशन समस्याओं के कारण कमांड प्रॉम्प्ट में git को मान्यता नहीं मिल सकती है, भले ही इसे स्थापित किया गया हो।

यदि आप इस समस्या का सामना करते हैं, तो आप *GitHub डेस्कटॉप* का विकल्प के रूप में उपयोग कर सकते हैं:

1. https://desktop.github.com/ से GitHub डेस्कटॉप स्थापित करें
2. अपने GitHub खाते से साइन इन करें
3. रिपॉजिटरी URL का उपयोग करके रिपॉजिटरी को क्लोन करें:
   https://github.com/getbindu/Bindu.git

GitHub डेस्कटॉप आपको कमांड लाइन का उपयोग किए बिना क्लोन, शाखाओं का प्रबंधन, परिवर्तनों को कमिट करने और पुल अनुरोध खोलने की अनुमति देता है।

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
<summary><b>सामान्य स्थापना समस्याएँ</b> (विस्तार के लिए क्लिक करें)</summary>

<br/>

| समस्या | समाधान |
|-------|----------|| `uv: command not found` | UV स्थापित करने के बाद अपने टर्मिनल को पुनः प्रारंभ करें। Windows पर, PowerShell का उपयोग करें |
| `Python version not supported` | [python.org](https://www.python.org/downloads/) से Python 3.12+ स्थापित करें |
| वर्चुअल वातावरण सक्रिय नहीं हो रहा (Windows) | PowerShell का उपयोग करें और `.venv\Scripts\activate` चलाएँ |
| `Microsoft Visual C++ required` | [Visual C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/) डाउनलोड करें |
| `ModuleNotFoundError` | venv सक्रिय करें और `uv sync --dev` चलाएँ |

</details>

---

<br/>

## 🚀 त्वरित प्रारंभ

### विकल्प 1: कूकीकटर का उपयोग करना (सिफारिश की गई)

**पहले एजेंट के लिए समय: ~2 मिनट ⏱️**

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

आपका स्थानीय एजेंट एक लाइव, सुरक्षित, खोजने योग्य सेवा बन जाता है। [Learn more →](https://docs.getbindu.com/bindu/create-bindu-agent/overview)

> **💡 प्रो टिप:** कूकीकटर के साथ बनाए गए एजेंट GitHub Actions शामिल करते हैं जो आपके एजेंट को [GetBindu.com](https://getbindu.com) में स्वचालित रूप से पंजीकृत करते हैं जब आप अपने रिपॉजिटरी में पुश करते हैं।

### विकल्प 2: मैनुअल सेटअप

अपने एजेंट स्क्रिप्ट `my_agent.py` बनाएं:

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

आपका एजेंट अब `deployment.url` में कॉन्फ़िगर किए गए URL पर लाइव है।

कोड परिवर्तनों के बिना एक कस्टम पोर्ट सेट करें:

```bash
# Linux/macOS
export BINDU_PORT=4000

# Windows PowerShell
$env:BINDU_PORT="4000"
```

जो मौजूदा उदाहरण `http://localhost:3773` का उपयोग करते हैं, उन्हें `BINDU_PORT` सेट होने पर स्वचालित रूप से ओवरराइड किया जाता है।

### विकल्प 3: जीरो-कॉन्फ़िग स्थानीय एजेंट

Postgres, Redis, या किसी भी क्लाउड सेवाओं को सेटअप किए बिना Bindu का प्रयास करें। पूरी तरह से स्थानीय रूप से इन-मेमोरी स्टोरेज और शेड्यूलर का उपयोग करके चलता है।

```bash
python examples/beginner_zero_config_agent.py
```

### विकल्प 4: न्यूनतम इको एजेंट (परीक्षण)

<details>
<summary><b>न्यूनतम उदाहरण देखें</b> (विस्तार के लिए क्लिक करें)</summary>

संभवतः सबसे छोटा कार्यशील एजेंट:

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

**एजेंट चलाएँ:**

```bash
# Start the agent
python examples/echo_agent.py
```

</details>

<details>
<summary><b>curl के साथ एजेंट का परीक्षण करें</b> (विस्तार के लिए क्लिक करें)</summary>

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

कार्य की स्थिति की जांच करें
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

 

## 🚀 मुख्य विशेषताएँ

| Feature | Description | Documentation |
| :--- | :--- | :--- |
| **Authentication** | Ory Hydra OAuth2 के साथ सुरक्षित API पहुंच (विकास के लिए वैकल्पिक) | [Guide →](docs/AUTHENTICATION.md) |
| 💰 **Payment Integration (X402)** | सुरक्षित विधियों को निष्पादित करने से पहले बेस ब्लॉकचेन पर USDC भुगतान स्वीकार करें | [Guide →](docs/PAYMENT.md) |
| 💾 **PostgreSQL Storage** | उत्पादन तैनाती के लिए स्थायी भंडारण (वैकल्पिक - डिफ़ॉल्ट रूप से InMemoryStorage) | [Guide →](docs/STORAGE.md) |
| 📋 **Redis Scheduler** | मल्टी-वर्कर तैनाती के लिए वितरित कार्य अनुसूची (वैकल्पिक - डिफ़ॉल्ट रूप से InMemoryScheduler) | [Guide →](docs/SCHEDULER.md) |
| 🎯 **Skills System** | पुन: प्रयोज्य क्षमताएँ जो एजेंट विज्ञापन करते हैं और बुद्धिमान कार्य रूटिंग के लिए निष्पादित करते हैं | [Guide →](docs/SKILLS.md) |
| 🤝 **Agent Negotiation** | बुद्धिमान समन्वय के लिए क्षमता-आधारित एजेंट चयन | [Guide →](docs/NEGOTIATION.md) |
| 🌐 **Tunneling** | परीक्षण के लिए स्थानीय एजेंटों को इंटरनेट पर उजागर करें (**स्थानीय विकास के लिए ही, उत्पादन के लिए नहीं**) | [Guide →](docs/TUNNELING.md) |
| 📬 **Push Notifications** | कार्य अपडेट के लिए वास्तविक समय वेबहुक सूचनाएँ - कोई पोलिंग आवश्यक नहीं | [Guide →](docs/NOTIFICATIONS.md) |
| 📊 **Observability & Monitoring** | OpenTelemetry और Sentry के साथ प्रदर्शन को ट्रैक करें और समस्याओं को डिबग करें | [Guide →](docs/OBSERVABILITY.md) |
| 🔄 **Retry Mechanism** | लचीले एजेंटों के लिए स्वचालित पुनः प्रयास के साथ गुणात्मक बैकऑफ | [Guide →](docs.getbindu.com/bindu/learn/retry/overview) |
| 🔑 **Decentralized Identifiers (DIDs)** | सत्यापन योग्य, सुरक्षित एजेंट इंटरैक्शन और भुगतान एकीकरण के लिए क्रिप्टोग्राफिक पहचान | [Guide →](docs/DID.md) |
| 🏥 **Health Check & Metrics** | अंतर्निर्मित एंडपॉइंट्स के साथ एजेंट के स्वास्थ्य और प्रदर्शन की निगरानी करें | [Guide →](docs/HEALTH_METRICS.md) |

---

<br/>

## 🎨 Chat UI

Bindu में `http://localhost:5173` पर एक सुंदर चैट इंटरफेस शामिल है। `frontend` फ़ोल्डर पर जाएं और सर्वर शुरू करने के लिए `npm run dev` चलाएं।

<p align="center">
  <img src="assets/agent-ui.png" alt="Bindu Agent UI" width="640" style="border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);" />
</p>

---

<br/>

## 🌐 GetBindu.com[**GetBindu.com**](https://getbindu.com) सभी बिंदु एजेंटों का एक सार्वजनिक रजिस्ट्रि है, जो उन्हें खोजने योग्य और व्यापक एजेंट पारिस्थितिकी तंत्र के लिए सुलभ बनाता है।

### ✨ कुकीकट्टर के साथ स्वचालित पंजीकरण

जब आप कुकीकट्टर टेम्पलेट का उपयोग करके एक एजेंट बनाते हैं, तो इसमें एक पूर्व-कॉन्फ़िगर किया गया गिटहब क्रिया शामिल होता है जो स्वचालित रूप से आपके एजेंट को निर्देशिका में पंजीकृत करता है:

1. **कुकीकट्टर का उपयोग करके अपना एजेंट बनाएं**
2. **गिटहब पर पुश करें** - गिटहब क्रिया स्वचालित रूप से ट्रिगर होती है
3. **आपका एजेंट [GetBindu.com](https://getbindu.com) में दिखाई देता है**

> **नोट**: अपने एजेंट को पंजीकृत करने के लिए `BINDU_PAT_TOKEN` को [getbindu.com](https://getbindu.com) से एकत्र करें।

### 📝 मैनुअल पंजीकरण

मैनुअल पंजीकरण प्रक्रिया वर्तमान में विकास में है।

---

<br/>

## 🌌 दृष्टि

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

_प्रत्येक प्रतीक एक एजेंट है - बुद्धिमत्ता की एक चिंगारी। छोटा बिंदु बिंदु है, एजेंटों के इंटरनेट में उत्पत्ति बिंदु।_

### नाइटस्काई कनेक्शन (प्रगति में)

नाइटस्काई एजेंटों के झुंडों को सक्षम बनाता है। प्रत्येक बिंदु एक बिंदु है जो एजेंटों को A2A, AP2, और X402 की साझा भाषा के साथ एनोटेट करता है। एजेंट कहीं भी होस्ट किए जा सकते हैं—लैपटॉप, बादल, या क्लस्टर—फिर भी एक ही प्रोटोकॉल बोलते हैं, डिज़ाइन द्वारा एक-दूसरे पर भरोसा करते हैं, और एक एकल, वितरित मन के रूप में एक साथ काम करते हैं।

> **💭 बिना योजना के एक लक्ष्य केवल एक इच्छा है।**

---

<br/>

## 🛠️ समर्थित एजेंट ढांचे

बिंदु **ढांचे-निषेधात्मक** है और के साथ परीक्षण किया गया है:

- **AG2** (पूर्व में ऑटोजन)
- **अग्नो**
- **क्रूएआई**
- **लैंगचेन**
- **लामा इंडेक्स**
- **फास्टएजेंट**

क्या आप अपने पसंदीदा ढांचे के साथ एकीकरण चाहते हैं? [Let us know on Discord](https://discord.gg/3w5zuYUuwt)!

---

<br/>

## 🧪 परीक्षण

बिंदु **70%+ परीक्षण कवरेज** बनाए रखता है (लक्ष्य: 80%+):

```bash
uv run pytest -n auto --cov=bindu --cov-report=term-missing
uv run coverage report --skip-covered --fail-under=70
```

---

<br/>

## 🔧 समस्या निवारण

<details>
<summary>सामान्य समस्याएँ</summary>

<br/>

| समस्या | समाधान |
|-------|----------|
| `Python 3.12 not found` | Python 3.12+ स्थापित करें और PATH में सेट करें, या `pyenv` का उपयोग करें |
| `bindu: command not found` | वर्चुअल वातावरण सक्रिय करें: `source .venv/bin/activate` || `Port 3773 already in use` | `BINDU_PORT=4000` सेट करें या `BINDU_DEPLOYMENT_URL=http://localhost:4000` के साथ URL को ओवरराइड करें |
| प्री-कमिट विफल | `pre-commit run --all-files` चलाएँ |
| परीक्षण विफल | डेवलप निर्भरताएँ स्थापित करें: `uv sync --dev` |
| `Permission denied` (macOS) | विस्तारित विशेषताओं को साफ़ करने के लिए `xattr -cr .` चलाएँ |

**पर्यावरण रीसेट करें:**
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

## 🤝 योगदान

हम योगदान का स्वागत करते हैं! [Discord](https://discord.gg/3w5zuYUuwt) पर हमारे साथ जुड़ें। उस चैनल का चयन करें जो आपके योगदान से सबसे अच्छा मेल खाता है।

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

## 📜 लाइसेंस

Bindu [Apache License 2.0](https://choosealicense.com/licenses/apache-2.0/) के तहत ओपन-सोर्स है।

---

<br/>

## 💬 समुदाय

हम योगदान को 💛 करते हैं! चाहे आप बग ठीक कर रहे हों, दस्तावेज़ीकरण में सुधार कर रहे हों, या डेमो बना रहे हों—आपका योगदान Bindu को बेहतर बनाता है।

- 💬 चर्चा और समर्थन के लिए [Join Discord](https://discord.gg/3w5zuYUuwt)
- ⭐ यदि आपको यह उपयोगी लगे तो [Star the repository](https://github.com/getbindu/Bindu)!

---

<br/>

## 👥 सक्रिय मॉडरेटर

हमारे समर्पित मॉडरेटर एक स्वागत योग्य और उत्पादक समुदाय बनाए रखने में मदद करते हैं:

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

> क्या आप मॉडरेटर बनना चाहते हैं? [Discord](https://discord.gg/3w5zuYUuwt) पर संपर्क करें!

---

<br/>

## 🙏 आभार

इन परियोजनाओं के लिए आभारी:

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

## 🗺️ रोडमैप

- [ ] GRPC परिवहन समर्थन- [ ] परीक्षण कवरेज को 80% तक बढ़ाएं (प्रगति पर)
- [ ] AP2 एंड-टू-एंड समर्थन
- [ ] DSPy एकीकरण (प्रगति पर)
- [ ] MLTS समर्थन
- [ ] अन्य सुविधाकर्ताओं के साथ X402 समर्थन

> 💡 [Suggest features on Discord](https://discord.gg/3w5zuYUuwt)!

---

<br/>

## [We will make this agents bidufied and we do need your help.](https://www.notion.so/getbindu/305d3bb65095808eac2bf720368e9804?v=305d3bb6509580189941000cfad83ae7&source=copy_link)

---

<br/>

## 🎓 कार्यशालाएँ

- [AI Native in Action: Agent Symphony](https://www.meetup.com/ai-native-Amsterdam && India/events/311066899/) - [Slides](https://docs.google.com/presentation/d/1SqGXI0Gv_KCWZ1Mw2SOx_kI0u-LLxwZq7lMSONdl8oQ/edit)

---

<br/>

## ⭐ स्टार इतिहास

[![Star History Chart](https://api.star-history.com/svg?repos=getbindu/Bindu&type=Date)](https://www.star-history.com/#getbindu/Bindu&Date)

---

<p align="center">
  <strong>💛 द्वारा एम्स्टर्डम && भारत की टीम द्वारा निर्मित </strong><br/>
  <em>खुश बिंदु! 🌻🚀✨</em>
</p>

<p align="center">
  <strong>विचार से एजेंटों के इंटरनेट तक 2 मिनट में.</strong><br/>
  <em>आपका एजेंट। आपका ढांचा। सार्वभौमिक प्रोटोकॉल।</em>
</p>

<p align="center">
  <a href="https://github.com/getbindu/Bindu">⭐ हमें GitHub पर स्टार करें</a> •
  <a href="https://discord.gg/3w5zuYUuwt">💬 Discord में शामिल हों</a> •
  <a href="https://docs.getbindu.com">🌻 दस्तावेज़ पढ़ें</a>
</p>

<br/>

<p align="center">
  <img src="assets/sunflower-footer.jpeg" alt="Bindu" width="720" />
</p>

<p align="center">
  <em>"हम सूरजमुखी सिद्धांत में विश्वास करते हैं - एक साथ ऊँचा खड़े होना, एजेंटों के इंटरनेट में आशा और प्रकाश लाना।"</em>
</p>
