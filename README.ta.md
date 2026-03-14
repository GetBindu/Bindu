<div align="center" id="top">
  <a href="https://getbindu.com">
    <picture>
      <img src="assets/bindu.png" alt="Bindu" width="300">
    </picture>
  </a>
</div>

<p align="center">
  <em>AI ஏஜென்ட்களுக்கான அடையாளம், தொடர்பு மற்றும் பணம் செலுத்தும் அடுக்கு</em>
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

**Bindu** (உச்சரிப்பு: _பிந்து_) என்பது AI ஏஜென்ட்களுக்கான ஒரு இயக்க அடுக்கு ஆகும், இது அடையாளம், தொடர்பு மற்றும் பணம் செலுத்தும் திறன்களை வழங்குகிறது. இது ஒரு உற்பத்தி-தயார் சேவையாகும், இது வசதியான API களுடன் விநியோகிக்கப்பட்ட அமைப்புகளில் ஏஜென்ட்களை இணைக்கிறது, அங்கீகரிக்கிறது மற்றும் ஒருங்கிணைக்கிறது – திறந்த நெறிமுறைகளைப் பயன்படுத்தி: **A2A**, **AP2**, மற்றும் **X402**.

விநியோகிக்கப்பட்ட கட்டமைப்புடன் (Task Manager, scheduler, storage) கட்டமைக்கப்பட்ட Bindu, விரைவாக உருவாக்குவதையும் எந்த AI framework உடனும் ஒருங்கிணைப்பதையும் எளிதாக்குகிறது. எந்த ஏஜென்ட் framework ஐயும் Internet of Agents இல் தொடர்பு, ஒத்துழைப்பு மற்றும் வர்த்தகத்திற்கான முழுமையாக இயங்கக்கூடிய சேவையாக மாற்றுங்கள்.

<p align="center">
  <strong>🌟 <a href="https://bindus.directory">உங்கள் ஏஜென்ட்டைப் பதிவு செய்யுங்கள்</a> • 🌻 <a href="https://docs.getbindu.com">ஆவணங்கள்</a> • 💬 <a href="https://discord.gg/3w5zuYUuwt">Discord சமூகம்</a></strong>
</p>

---

<br/>

## 🎥 Bindu ஐ செயலில் பாருங்கள்

<div align="center">
  <a href="https://www.youtube.com/watch?v=qppafMuw_KI" target="_blank">
    <img src="https://img.youtube.com/vi/qppafMuw_KI/maxresdefault.jpg" alt="Bindu Demo" width="640" style="border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);" />
  </a>
</div>

## 📋 தேவைகள்

Bindu ஐ நிறுவுவதற்கு முன், உங்களிடம் இருப்பதை உறுதிப்படுத்திக் கொள்ளுங்கள்:

- **Python 3.12 அல்லது அதற்கு மேல்** - [இங்கே பதிவிறக்கவும்](https://www.python.org/downloads/)
- **UV Package Manager** - [நிறுவல் வழிகாட்டி](https://github.com/astral-sh/uv)

### உங்கள் அமைப்பை சரிபார்க்கவும்

```bash
# Python பதிப்பை சரிபார்க்கவும்
uv run python --version  # 3.12 அல்லது அதற்கு மேல் காட்ட வேண்டும்

# UV நிறுவலை சரிபார்க்கவும்
uv --version
```

---

<br/>

## 📦 நிறுவல்

```bash
# Bindu ஐ நிறுவவும்
uv add bindu

# மேம்பாட்டிற்கு (நீங்கள் Bindu க்கு பங்களிக்கிறீர்கள் என்றால்)
# மெய்நிகர் சூழலை உருவாக்கி செயல்படுத்தவும்
uv venv --python 3.12.9
source .venv/bin/activate  # macOS/Linux இல்
# .venv\Scripts\activate  # Windows இல்

uv sync --dev
```

---

<br/>

## 🚀 விரைவான தொடக்கம்

### விருப்பம் 1: Cookiecutter ஐப் பயன்படுத்தவும் (பரிந்துரைக்கப்படுகிறது)

**முதல் ஏஜென்ட் வரை நேரம்: ~2 நிமிடங்கள் ⏱️**

```bash
# Cookiecutter ஐ நிறுவவும்
uv add cookiecutter

# உங்கள் Bindu ஏஜென்ட்டை உருவாக்கவும்
uvx cookiecutter https://github.com/getbindu/create-bindu-agent.git
```

அவ்வளவுதான்! உங்கள் உள்ளூர் ஏஜென்ட் இப்போது நேரடி, பாதுகாப்பான மற்றும் கண்டுபிடிக்கக்கூடிய சேவையாகும். [மேலும் அறிக →](https://docs.getbindu.com/bindu/create-bindu-agent/overview)

### விருப்பம் 2: கைமுறை அமைப்பு

உங்கள் ஏஜென்ட் ஸ்கிரிப்ட் `my_agent.py` ஐ உருவாக்கவும்:

```python
from bindu.penguin.bindufy import bindufy
from agno.agent import Agent
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.models.openai import OpenAIChat

# உங்கள் ஏஜென்ட்டை வரையறுக்கவும்
agent = Agent(
    instructions="நீங்கள் ஒரு ஆராய்ச்சி உதவியாளர், தகவல்களைக் கண்டுபிடித்து சுருக்கமாகக் கூறுபவர்.",
    model=OpenAIChat(id="gpt-4o"),
    tools=[DuckDuckGoTools()],
)

# கட்டமைப்பு
config = {
    "author": "your.email@example.com",
    "name": "research_agent",
    "description": "ஒரு ஆராய்ச்சி உதவியாளர் ஏஜென்ட்",
    "deployment": {"url": "http://localhost:3773", "expose": True},
    "skills": ["skills/question-answering", "skills/pdf-processing"]
}

# Handler செயல்பாடு
def handler(messages: list[dict[str, str]]):
    """செய்திகளைச் செயலாக்கி ஏஜென்ட் பதிலை வழங்குகிறது.

    Args:
        messages: உரையாடல் வரலாற்றுடன் செய்தி அகராதிகளின் பட்டியல்

    Returns:
        ஏஜென்ட் பதில் முடிவு
    """
    result = agent.run(input=messages)
    return result

# Bindu-fy
bindufy(config, handler)
```

உங்கள் ஏஜென்ட் இப்போது `http://localhost:3773` இல் நேரடியாக இயங்குகிறது மற்றும் பிற ஏஜென்ட்களுடன் தொடர்பு கொள்ள தயாராக உள்ளது.

---

<br/>

## [Postgres Storage](https://docs.getbindu.com/bindu/learn/storage/overview)

Bindu உற்பத்தி வரிசைப்படுத்தல்களுக்கு PostgreSQL ஐ அதன் நிரந்தர சேமிப்பக பின்தளமாகப் பயன்படுத்துகிறது. சேமிப்பக அடுக்கு SQLAlchemy இன் async engine உடன் கட்டமைக்கப்பட்டுள்ளது.

இது விருப்பமானது – இயல்புநிலையாக InMemoryStorage பயன்படுத்தப்படுகிறது.

---

<br/>

## [Redis Scheduler](https://docs.getbindu.com/bindu/learn/scheduler/overview)

Bindu பல workers மற்றும் செயல்முறைகள் முழுவதும் வேலையை ஒருங்கிணைக்க Redis ஐ அதன் விநியோகிக்கப்பட்ட பணி திட்டமிடுபவராகப் பயன்படுத்துகிறது.

இது விருப்பமானது – இயல்புநிலையாக InMemoryScheduler பயன்படுத்தப்படுகிறது.

---

<br/>

## [Retry Mechanism](https://docs.getbindu.com/bindu/learn/retry/overview)

> நெகிழ்வான Bindu ஏஜென்ட்களுக்கான exponential backoff உடன் தானியங்கு retry logic

Bindu இல் Tenacity-அடிப்படையிலான retry பொறிமுறை உள்ளது, இது workers, storage, schedulers மற்றும் API அழைப்புகளில் தற்காலிக தோல்விகளை நேர்த்தியாகக் கையாளுகிறது.

---

<br/>

## [Sentry Integration](https://docs.getbindu.com/bindu/learn/sentry/overview)

> Bindu ஏஜென்ட்களுக்கான நிகழ்நேர பிழை கண்காணிப்பு மற்றும் செயல்திறன் கண்காணிப்பு

Sentry என்பது நிகழ்நேர பிழை கண்காணிப்பு மற்றும் செயல்திறன் கண்காணிப்பு தளமாகும், இது உற்பத்தியில் சிக்கல்களை அடையாளம் காண, கண்டறிய மற்றும் சரிசெய்ய உதவுகிறது.

---

<br/>

## [Skills System](https://docs.getbindu.com/bindu/skills/introduction/overview)

> புத்திசாலித்தனமான ஏஜென்ட் ஒருங்கிணைப்புக்கான வளமான திறன் விளம்பரம்

Bindu Skills System புத்திசாலித்தனமான ஒருங்கிணைப்பு மற்றும் ஏஜென்ட் கண்டுபிடிப்புக்கு வளமான ஏஜென்ட் திறன் விளம்பரத்தை வழங்குகிறது.

---

<br/>

## Negotiation

> புத்திசாலித்தனமான ஒருங்கிணைப்புக்கான திறன்-அடிப்படையிலான ஏஜென்ட் தேர்வு

Bindu இன் பேச்சுவார்த்தை அமைப்பு orchestrators க்கு பல ஏஜென்ட்களை வினவ மற்றும் skills, செயல்திறன், சுமை மற்றும் செலவின் அடிப்படையில் ஒரு பணிக்கு சிறந்த ஏஜென்ட்டை புத்திசாலித்தனமாக தேர்ந்தெடுக்க உதவுகிறது.

---

<br/>

## Task Feedback மற்றும் DSPy

Bindu DSPy மேம்படுத்தல் மூலம் தொடர்ச்சியான மேம்பாட்டை செயல்படுத்த பணி செயல்படுத்தல்களில் பயனர் கருத்துக்களை சேகரிக்கிறது.

---

<br/>

## 📬 Push Notifications

Bindu நீண்ட கால பணிகளுக்கு **நிகழ்நேர webhook அறிவிப்புகளை** ஆதரிக்கிறது, [A2A Protocol specification](https://a2a-protocol.org/latest/specification/) ஐப் பின்பற்றுகிறது.

---

<br/>

## 🎨 Chat UI

Bindu `http://localhost:3773/docs` இல் அழகான chat இடைமுகத்தை உள்ளடக்கியுள்ளது

<p align="center">
  <img src="assets/agent-ui.png" alt="Bindu Agent UI" width="640" style="border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);" />
</p>

---

<br/>

## 🌐 Bindu Directory

[**Bindu Directory**](https://bindus.directory) என்பது அனைத்து Bindu ஏஜென்ட்களின் பொது பதிவேடு ஆகும், இது அவற்றை பரந்த ஏஜென்ட் சூழலியலில் கண்டுபிடிக்கக்கூடியதாகவும் அணுகக்கூடியதாகவும் ஆக்குகிறது.

---

<br/>

## 🌌 தொலைநோக்கு

```
இரவு வானத்தின் ஒரு பார்வை
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

_ஒவ்வொரு குறியீடும் ஒரு ஏஜென்ட் – நுண்ணறிவின் ஒரு தீப்பொறி. சிறிய புள்ளி Bindu ஆகும், Internet of Agents இல் தோற்ற புள்ளி._

> **💭 திட்டமில்லாத இலக்கு வெறும் விருப்பம் மட்டுமே.**

---

<br/>

## 🛠️ ஆதரிக்கப்படும் ஏஜென்ட் Frameworks

Bindu **framework-agnostic** மற்றும் சோதிக்கப்பட்டது:

- **Agno**
- **CrewAI**
- **LangChain**
- **LlamaIndex**
- **FastAgent**

உங்களுக்கு பிடித்த framework உடன் ஒருங்கிணைப்பு வேண்டுமா? [Discord இல் எங்களுக்குத் தெரியப்படுத்துங்கள்](https://discord.gg/3w5zuYUuwt)!

---

<br/>

## � DSPy வினை உச்চரிப்பு

Bindu **DSPy** ஐ ஒருங்கிணைக்கிறது, LLM வினைகளை நிரல்படியாக உச்சரிப்பு செய்ய ஏஜென்ட் செயல்திறனை மேம்படுத்த ஒரு கাঠামோ ஆகும். வினைகளை கைப்பணியாக உருவாக்குவதற்கு பதிலாக, DSPy உண்மையான ஏஜென்ட் கருத்துகளைப் பயன்படுத்தி தேர்ந்தெடுக்கப்பட்ட வெளிப்படுத்துதல்களை স্বயங்கிரியமாக உற்பத்தி செய்து மற்றும் சரிபார்க்கிறது।

### இது எவ்வாறு செயல்படுகிறது

DSPy மூன்று முக்கிய திறன்களை வழங்குகிறது:

1. **🎯 உச்சரிப்பு செய்யப்பட்ட வினைகளை பயிற்றுவிக்கவும்** - ஏஜென்ட் இயக்கவ்யவகளை பகுப்பாய்வு செய்யவும் மற்றும் முன்னிலை வினைகளை உற்பத்தி செய்யவும்
   ```bash
   bindu train --did agent_did
   ```
   இது A/B சோதனை மாறிகளை உருவாக்குகிறது: ஒரு "செயல்படும்" வினை (உங்கள் தற்போதைய பதிப்பு) மற்றும் ஒரு "விண்ணப்পம்" (உச்சரிப்பு செய்யப்பட்ட பதிப்பு) அமைக்கப்பட்ட போக்கு பிரிப்புடன்.

2. **📊 Canary Rollout** - முன்னிலை செய்யப்பட்ட வினைக்கு தனிப்பட்ட முறையில் போக்கை மாற்றவும்
   ```bash
   bindu canary --did agent_did
   ```

3. **🔄 நேரடி வினை மக்களாக்கம்** - ஒவ்வொரு வேண்டுகோளுக்கும் சரியான வினை பதிப்பை இயங்கியாக பரிமாற்றவும்
   ```python
   from bindu.dspy.prompt_router import route_prompt
   
   async def handler(messages: list[dict[str, str]]):
       agent.instructions = await route_prompt(initial_prompt=agent.instructions)
       return agent.run(input=messages)
   ```

### வேகமான தொடக்கம் உதாரணம்

Agno ஏஜென்ட்டுடன் முழுமையான செயல்படும் உதாரணத்திற்கு [examples/agno_dspy_example.py](examples/agno_dspy_example.py) ஐ பார்க்கவும்.

### DSPy பயிற்சிக்கான முன்நிபந்தனைகள்

- உங்கள் `.env` கோப்பில் `OPENAI_API_KEY` ஐ அமைக்கவும்
- ஏஜென்ட் பணி வரலாற்று மற்றும் கருத்து மதிப்பீடுகளுடன் PostgreSQL ஐ கட்டமைக்கவும்
- ஏஜென்ட்கள் கருத்து மதிப்பெண்கள் (0-1 அல்லது 1-5 மதிப்பீட்டு அளவுக்கோல்) உடன் ஒத்துயர்க்கையை பதிவு செய்கிறதா என்பதை உறுதிப்படுத்திக் கொள்ளுங்கள்

---

<br/>

## �🧪 சோதனை

Bindu **70%+ சோதனை கவரேஜை** பராமரிக்கிறது:

```bash
pytest -n auto --cov=bindu --cov-report= && coverage report --skip-covered --fail-under=70
```

---

<br/>

## சிக்கல் தீர்வு

<details>
<summary>பொதுவான சிக்கல்கள்</summary>

<br/>

| சிக்கல் | தீர்வு |
|---------|----------|
| `Python 3.12 not found` | Python 3.12+ ஐ நிறுவவும் மற்றும் PATH இல் அமைக்கவும், அல்லது `pyenv` ஐப் பயன்படுத்தவும் |
| `bindu: command not found` | மெய்நிகர் சூழலை செயல்படுத்தவும்: `source .venv/bin/activate` |
| `Port 3773 already in use` | config இல் port ஐ மாற்றவும்: `"url": "http://localhost:4000"` |

</details>

<br/>

## 🤝 பங்களிப்பு

நாங்கள் பங்களிப்புகளை வரவேற்கிறோம்! [Discord](https://discord.gg/3w5zuYUuwt) இல் எங்களுடன் சேருங்கள்.

```bash
git clone https://github.com/getbindu/Bindu.git
cd Bindu
uv venv --python 3.12.9
source .venv/bin/activate
uv sync --dev
pre-commit run --all-files
```

> 📖 [பங்களிப்பு வழிகாட்டுதல்கள்](.github/contributing.md)

---

<br/>

## 📜 உரிமம்

Bindu [Apache License 2.0](https://choosealicense.com/licenses/apache-2.0/) இன் கீழ் திறந்த மூலமாகும்.

---

<br/>

## 💬 சமூகம்

நாங்கள் 💛 பங்களிப்புகள்! நீங்கள் பிழைகளை சரிசெய்தாலும், ஆவணங்களை மேம்படுத்தினாலும் அல்லது demos ஐ உருவாக்கினாலும் – உங்கள் பங்களிப்புகள் Bindu ஐ சிறப்பாக்குகின்றன.

- 💬 விவாதங்கள் மற்றும் ஆதரவுக்கு [Discord இல் சேருங்கள்](https://discord.gg/3w5zuYUuwt)
- ⭐ பயனுள்ளதாக இருந்தால் [repository க்கு star கொடுங்கள்](https://github.com/getbindu/Bindu)!

---

<br/>

## 👥 செயலில் உள்ள மதிப்பீட்டாளர்கள்

எங்கள் அர்ப்பணிப்புள்ள மதிப்பீட்டாளர்கள் வரவேற்பு மற்றும் உற்பத்தி சமூகத்தை பராமரிக்க உதவுகிறார்கள்.

---

<br/>

## 🙏 நன்றி

இந்த திட்டங்களுக்கு நன்றி:

- [FastA2A](https://github.com/pydantic/fasta2a)
- [12 Factor Agents](https://github.com/humanlayer/12-factor-agents)
- [A2A](https://github.com/a2aproject/A2A)
- [AP2](https://github.com/google-agentic-commerce/AP2)
- [X402](https://github.com/coinbase/x402)

---

<br/>

## 🗺️ வழித்திட்டம்

- [ ] GRPC transport ஆதரவு
- [x] Sentry பிழை கண்காணிப்பு
- [x] Ag-UI ஒருங்கிணைப்பு
- [x] Retry பொறிமுறை
- [ ] சோதனை கவரேஜை 80% ஆக அதிகரிக்க - முன்னேற்றத்தில்
- [x] Redis scheduler செயல்படுத்தல்
- [x] நினைவக சேமிப்பிற்கான Postgres database
- [x] Negotiation ஆதரவு
- [ ] AP2 end-to-end ஆதரவு
- [ ] DSPy ஒருங்கிணைப்பு - முன்னேற்றத்தில்

> 💡 [Discord இல் அம்சங்களை பரிந்துரைக்கவும்](https://discord.gg/3w5zuYUuwt)!

---

<br/>

## ⭐ Star வரலாறு

[![Star History Chart](https://api.star-history.com/svg?repos=getbindu/Bindu&type=Date)](https://www.star-history.com/#getbindu/Bindu&Date)

---

<p align="center">
  <strong>Amsterdam அணியால் 💛 உடன் கட்டமைக்கப்பட்டது</strong><br/>
  <em>Happy Bindu! 🌻🚀✨</em>
</p>

<p align="center">
  <strong>யோசனையிலிருந்து Internet of Agents வரை 2 நிமிடங்களில்.</strong><br/>
  <em>உங்கள் ஏஜென்ட். உங்கள் framework. உலகளாவிய நெறிமுறைகள்.</em>
</p>

<p align="center">
  <a href="https://github.com/getbindu/Bindu">⭐ GitHub இல் எங்களுக்கு star கொடுங்கள்</a> •
  <a href="https://discord.gg/3w5zuYUuwt">💬 Discord இல் சேருங்கள்</a> •
  <a href="https://docs.getbindu.com">🌻 Docs ஐ படியுங்கள்</a>
</p>
