# 🚀 Quick Start Guide - MedResearch Agent

Get up and running in 5 minutes!

---

## ⚡ 1-Minute Setup

```bash
# Install dependencies
pip install bindu agno pytest

# Run the agent
python medresearch_agent.py
```

That's it! Agent is live at `http://localhost:3773`

---

## 📝 Basic Usage

### Test 1: Welcome Message
```bash
curl -X POST http://localhost:3773/messages \
  -H "Content-Type: application/json" \
  -d '[{"role": "user", "content": "Hello"}]'
```

Expected: Welcome message with feature list

### Test 2: Ask a Question
```bash
curl -X POST http://localhost:3773/messages \
  -H "Content-Type: application/json" \
  -d '[{"role": "user", "content": "How does this agent work?"}]'
```

### Test 3: Multi-Paper Synthesis Request
```bash
curl -X POST http://localhost:3773/messages \
  -H "Content-Type: application/json" \
  -d '[{"role": "user", "content": "Compare papers on diabetes treatment"}]'
```

Expected: Message about needing papers uploaded first

---

## 🧪 Run Tests

```bash
# Quick test
pytest tests/ -v

# With coverage
pytest tests/ --cov=tools --cov-report=term

# Specific test
pytest tests/test_medresearch_agent.py::TestPDFProcessor -v
```

---

## 🎯 Key Features to Demonstrate

### 1. Evidence Quality Scoring
The agent scores papers 0-100 based on:
- Study design (RCT = highest)
- Sample size (larger = better)
- Methodology (double-blind, randomized)
- Recency (newer = better)
- Peer review status

### 2. Multi-Paper Synthesis (⭐ Surprise!)
Upload 3+ papers and the agent will:
- Find consensus across studies
- Identify contradictions
- Calculate overall evidence strength
- Detect research gaps
- Analyze temporal trends

### 3. Medical Entity Extraction
Automatically detects:
- Conditions (diabetes, hypertension, etc.)
- Medications (metformin, aspirin, etc.)
- Procedures (surgery, MRI, etc.)
- Lab values (HbA1c, cholesterol, etc.)
- Dosages (500mg twice daily)
- Statistics (p<0.001, 95% CI)

---

## 📊 Expected Output Examples

### Single Paper Summary:
```
📄 **Effect of Metformin on Type 2 Diabetes**

⭐ **Evidence Quality Score:** 82/100

**Plain-Language Summary:**
This study examined 500 patients with type 2 diabetes...

**Key Findings:**
1. Significant HbA1c reduction (1.2%)
2. Well-tolerated with minimal side effects

⚠️ MEDICAL DISCLAIMER
This is for educational purposes only...
```

### Multi-Paper Synthesis:
```
🔬 **Multi-Paper Synthesis: Diabetes Treatment**

📚 **Papers Analyzed:** 5

**Consensus Findings:**
• HbA1c reduction consistently reported (4/5 studies)
• Treatment well-tolerated (5/5 studies)

**Contradictions:**
• Optimal dosing varies across studies

**Overall Evidence Strength:** 78/100
**Confidence Level:** Moderate confidence
```

---

## ⚠️ Troubleshooting

### Port Already in Use
```bash
# Change port in config.json
"deployment": {"url": "http://localhost:4000"}
```

### Import Errors
```bash
# Ensure virtual environment is activated
source .venv/bin/activate  # macOS/Linux
.venv\Scripts\activate     # Windows
```

### Tests Failing
```bash
# Reinstall dependencies
pip install --upgrade -r requirements.txt
```

---

## 🎓 Learn More

- **Full README**: [README.md](README.md)
- **Architecture**: See "Architecture" section in README
- **Contributing**: [CONTRIBUTING.md](CONTRIBUTING.md)
- **Bindu Docs**: https://docs.getbindu.com

---

## 💬 Get Help

- **Discord**: https://discord.gg/3w5zuYUuwt
- **Issues**: Open a GitHub issue
- **Email**: Contact maintainers

---

**Happy analyzing! 🏥📚**
