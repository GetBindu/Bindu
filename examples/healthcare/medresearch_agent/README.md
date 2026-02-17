# 🏥 MedResearch Agent

> Medical research paper analyzer powered by **Google Gemini AI (free tier)** — built on [Bindu](https://github.com/getbindu/bindu).

Upload PDF research papers and get plain-language summaries, evidence quality scores, multi-paper synthesis, and AI-powered Q&A — all backed by citations from your own documents.

---

## ✨ Features

### 📄 Single Paper Analysis
- Extracts title, authors, year, study type, and sample size automatically
- Generates plain-English summaries using Gemini AI
- Scores evidence quality from **0–100** based on study design, sample size, recency, methodology, and peer review signals
- Identifies key findings, limitations, and clinical relevance

### 🔬 Multi-Paper Synthesis
- Compares 2+ papers to find **consensus findings** and **contradictions**
- Produces structured synthesis with methodology comparison and research gap analysis
- Calculates overall evidence strength across the paper set

### 💬 AI-Powered Q&A
- Ask any question in plain English — Gemini answers using only your uploaded papers
- Responses include citations (paper title + authors) and relevant statistics
- Falls back to rule-based extraction if Gemini is unavailable

### 🧬 Medical NLP
- Extracts conditions, medications, procedures, and lab values
- Detects selection, publication, and funding bias
- Supports multi-library PDF extraction: `pdfplumber` → `PyPDF2` → `pymupdf` (auto-fallback)

---

## 🗂️ Project Structure

```
medresearch_agent/
├── medresearch_agent.py      # Main agent + FastAPI server
├── pdf_processor.py          # PDF text extraction & section parsing
├── medical_nlp.py            # Medical entity recognition
├── evidence_scorer.py        # Evidence quality scoring (0–100)
├── synthesizer.py            # Multi-paper synthesis engine
├── config.json               # Bindu agent configuration
├── requirements.txt          # Dependencies
├── demo.py                   # Demo / quick-start script
├── test_medresearch_agent.py # Test suite
├── setup.sh                  # One-command setup
└── ui/
    └── index.html            # Web UI (drag-and-drop PDF upload + chat)
```

---

## ⚡ Quick Start

### 1. Prerequisites

- Python 3.12+
- A **free** Google Gemini API key → [Get one here](https://aistudio.google.com/apikey)

### 2. Install dependencies

```bash
pip install google-generativeai fastapi uvicorn python-multipart pdfplumber
pip install bindu>=0.3.18
```

Or use the setup script:

```bash
bash setup.sh
```

### 3. Set your API key

```bash
# Option A: environment variable (recommended)
export GEMINI_API_KEY=your_key_here

# Option B: edit medresearch_agent.py line ~45
GEMINI_API_KEY = "your_key_here"
```

### 4. Run the agent

```bash
python medresearch_agent.py
```

Server starts at **http://localhost:3773**

Open `ui/index.html` in your browser to use the web interface.

---

## 🖥️ API Reference

### Upload a paper
```bash
curl -X POST http://localhost:3773/upload \
  -F "file=@your_paper.pdf"
```

**Response:**
```json
{
  "success": true,
  "paper_id": "paper_abc123",
  "title": "Associations of Free Triiodothyronine...",
  "authors": ["Zhao", "Wang"],
  "year": 2026,
  "study_type": "Observational Study",
  "sample_size": "312",
  "evidence_score": 61
}
```

### Ask a question
```bash
curl -X POST http://localhost:3773/messages \
  -H "Content-Type: application/json" \
  -d '[{"role": "user", "content": "What were the main findings?"}]'
```

### Synthesize across papers
```bash
curl -X POST http://localhost:3773/synthesize \
  -H "Content-Type: application/json" \
  -d '{"topic": "diabetes and metabolic outcomes"}'
```

### Check status
```bash
curl http://localhost:3773/status
```

### A2A / JSON-RPC (Bindu protocol)
```bash
curl -X POST http://localhost:3773/ \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "message/send",
    "params": {
      "message": {
        "role": "user",
        "parts": [{"kind": "text", "text": "Summarize all papers"}],
        "kind": "message",
        "messageId": "550e8400-e29b-41d4-a716-446655440038",
        "contextId": "550e8400-e29b-41d4-a716-446655440038",
        "taskId": "550e8400-e29b-41d4-a716-446655440300"
      },
      "configuration": {"acceptedOutputModes": ["application/json"]}
    },
    "id": "550e8400-e29b-41d4-a716-446655440024"
  }'
```

---

## 🤖 How the LLM Integration Works

The agent uses **Google Gemini** (free tier) as its reasoning engine. On startup it auto-selects the best available model in this order:

1. `gemini-2.0-flash`
2. `gemini-2.0-flash-lite`
3. `gemini-1.5-flash-latest`
4. `gemini-1.5-flash`
5. `gemini-pro`

If no Gemini key is set, the agent falls back to rule-based keyword extraction and pattern matching — it still works, just without the AI-quality responses.

All prompts are engineered to:
- Answer **only from uploaded papers** (no hallucination of external facts)
- Cite paper titles and authors explicitly
- End every response with the medical disclaimer

---

## 📊 Evidence Scoring

Papers are scored 0–100 using a weighted formula:

| Component | Weight | Description |
|-----------|--------|-------------|
| Study design | 35% | RCT=85, Meta-analysis=90, Observational=50, etc. |
| Sample size | 25% | n≥5000→100, n≥1000→85, n≥100→40 |
| Methodology | 20% | Bonus for double-blind, randomized, multi-center |
| Recency | 10% | Papers from current year→100, 10yr old→25 |
| Peer review | 10% | Top journal mentions boost score |

**Grade scale:** A (85–100) · B (70–84) · C (55–69) · D (40–54) · F (<40)

---

## 🧪 Running Tests

```bash
pytest test_medresearch_agent.py -v
pytest test_medresearch_agent.py --cov=. --cov-report=term-missing
```

---

## 🔧 Configuration (`config.json`)

Key settings you may want to change:

```json
{
  "author": "your.email@example.com",
  "deployment": {
    "url": "http://localhost:3773",
    "expose": true
  },
  "auth": {
    "enabled": false
  },
  "storage": {
    "type": "memory"
  }
}
```

Set `auth.enabled: true` to require DID authentication. Change `storage.type` to `"redis"` for persistent paper cache across restarts.

---

## 🗺️ Roadmap

- [ ] PubMed API integration for auto-fetching papers by DOI/PMID
- [ ] Semantic search using sentence embeddings
- [ ] Drug interaction database integration
- [ ] Support for `.docx` and `.txt` input formats
- [ ] X402 payment integration for premium synthesis features
- [ ] Redis-backed persistent storage

---

## ⚠️ Medical Disclaimer

**This tool is for educational and research purposes only.** It does not provide medical advice and must not be used for diagnosis or treatment decisions. Always consult qualified healthcare professionals for medical guidance.

---

## 📄 License

See [LICENSE](LICENSE) for details.

---

## 🙏 Acknowledgements

Built with [Bindu](https://github.com/getbindu/bindu) · Powered by [Google Gemini](https://aistudio.google.com) (free tier) · PDF parsing by [pdfplumber](https://github.com/jsvine/pdfplumber)
