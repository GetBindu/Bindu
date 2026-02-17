"""
MedResearch Agent v4.0 - RAG POWERED (FREE)
Uses Google Gemini + text-embedding-004 + ChromaDB for precise answers.

RAG Flow:
  PDF Upload → chunk text → embed with Google text-embedding-004 → store in ChromaDB
  User Question → embed question → retrieve top-K chunks → Gemini answers with real context

Setup:
  pip install google-generativeai fastapi uvicorn python-multipart pdfplumber chromadb
"""

import json
import logging
import os
import re
import hashlib
import time
from typing import Any, Dict, List, Optional
from pathlib import Path
import sys

# ─────────────────────────────────────────────
# FASTAPI
# ─────────────────────────────────────────────
try:
    from fastapi import FastAPI, Request, UploadFile, File
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import JSONResponse
    import uvicorn
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False

# ─────────────────────────────────────────────
# GEMINI SDK (try new SDK first, fall back to old)
# ─────────────────────────────────────────────
GEMINI_AVAILABLE = False
GEMINI_SDK = None

try:
    from google import genai as genai_new
    GEMINI_AVAILABLE = True
    GEMINI_SDK = "new"
except ImportError:
    try:
        import google.generativeai as genai_old
        GEMINI_AVAILABLE = True
        GEMINI_SDK = "old"
    except ImportError:
        print("⚠️  Run: pip install google-generativeai")

# ─────────────────────────────────────────────
# CHROMADB (local vector store — free, no server)
# ─────────────────────────────────────────────
CHROMA_AVAILABLE = False
try:
    import chromadb
    CHROMA_AVAILABLE = True
except ImportError:
    print("⚠️  RAG disabled. Run: pip install chromadb")

from bindu.penguin.bindufy import bindufy

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'tools'))
try:
    from tools.pdf_processor import PDFProcessor
    from tools.medical_nlp import MedicalNLP
    from tools.evidence_scorer import EvidenceScorer
    from tools.synthesizer import PaperSynthesizer
except ImportError:
    from pdf_processor import PDFProcessor
    from medical_nlp import MedicalNLP
    from evidence_scorer import EvidenceScorer
    from synthesizer import PaperSynthesizer

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

UPLOAD_DIR = Path("./uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

CHROMA_DIR = Path("./chroma_db")
CHROMA_DIR.mkdir(exist_ok=True)

# Models — newest first (all FREE tier)
MODEL_CANDIDATES = [
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
    "gemini-1.5-flash-latest",
    "gemini-1.5-flash",
    "gemini-1.0-pro",
]
EMBED_MODEL = "text-embedding-004"   # FREE Google embedding model

CHUNK_SIZE    = 600    # characters per chunk
CHUNK_OVERLAP = 100    # overlap between chunks
TOP_K_CHUNKS  = 6      # chunks to retrieve per question

# ─────────────────────────────────────────────
# GEMINI SETUP
# ─────────────────────────────────────────────
gemini_model      = None
gemini_model_name = None

if GEMINI_AVAILABLE and GEMINI_API_KEY not in ("", "YOUR_GEMINI_API_KEY_HERE"):
    if GEMINI_SDK == "new":
        try:
            _client = genai_new.Client(api_key=GEMINI_API_KEY)
            gemini_model      = _client
            gemini_model_name = MODEL_CANDIDATES[0]
            logger.info(f"✅ Gemini ready [new SDK] — {gemini_model_name}")
        except Exception as e:
            logger.error(f"❌ Gemini new-SDK setup error: {e}")
    else:
        try:
            genai_old.configure(api_key=GEMINI_API_KEY)
            gemini_model      = genai_old.GenerativeModel(MODEL_CANDIDATES[0])
            gemini_model_name = MODEL_CANDIDATES[0]
            logger.info(f"✅ Gemini ready [old SDK] — {gemini_model_name}")
        except Exception as e:
            logger.error(f"❌ Gemini old-SDK setup error: {e}")
else:
    logger.warning("⚠️  Gemini API key not set. Using rule-based fallback.")

MEDICAL_DISCLAIMER = "\n⚠️ MEDICAL DISCLAIMER: For educational purposes only. Not medical advice. Always consult qualified healthcare professionals."

# ─────────────────────────────────────────────
# CHROMADB SETUP
# ─────────────────────────────────────────────
chroma_client     = None
chroma_collection = None

if CHROMA_AVAILABLE:
    try:
        chroma_client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        chroma_collection = chroma_client.get_or_create_collection(
            name="medresearch_papers",
            metadata={"hnsw:space": "cosine"}
        )
        logger.info(f"✅ ChromaDB ready — {chroma_collection.count()} chunks stored")
    except Exception as e:
        logger.error(f"❌ ChromaDB setup error: {e}")

# ─────────────────────────────────────────────
# EMBEDDING (Google text-embedding-004 — FREE)
# ─────────────────────────────────────────────
def get_embedding(text: str) -> Optional[List[float]]:
    """
    Get embedding from Google text-embedding-004.
    100% FREE — same API key as Gemini, generous quota.
    Returns list of 768 floats, or None on failure.
    """
    if not GEMINI_AVAILABLE or not GEMINI_API_KEY:
        return None
    try:
        if GEMINI_SDK == "new":
            result = gemini_model.models.embed_content(
                model=f"models/{EMBED_MODEL}",
                contents=text,
            )
            return result.embeddings[0].values
        else:
            result = genai_old.embed_content(
                model=f"models/{EMBED_MODEL}",
                content=text,
                task_type="retrieval_document",
            )
            return result["embedding"]
    except Exception as e:
        logger.warning(f"⚠️ Embedding failed: {e}")
        return None


def get_query_embedding(text: str) -> Optional[List[float]]:
    """Embedding for queries (slightly different task_type for old SDK)."""
    if not GEMINI_AVAILABLE or not GEMINI_API_KEY:
        return None
    try:
        if GEMINI_SDK == "new":
            result = gemini_model.models.embed_content(
                model=f"models/{EMBED_MODEL}",
                contents=text,
            )
            return result.embeddings[0].values
        else:
            result = genai_old.embed_content(
                model=f"models/{EMBED_MODEL}",
                content=text,
                task_type="retrieval_query",
            )
            return result["embedding"]
    except Exception as e:
        logger.warning(f"⚠️ Query embedding failed: {e}")
        return None

# ─────────────────────────────────────────────
# TEXT CHUNKING
# ─────────────────────────────────────────────
def chunk_text(text: str, paper_id: str, paper_title: str) -> List[Dict]:
    """
    Split paper text into overlapping chunks for embedding.
    Tries to split on sentence boundaries for better coherence.
    """
    # Split into sentences first
    sentences = re.split(r'(?<=[.!?])\s+', text)

    chunks     = []
    current    = ""
    chunk_idx  = 0

    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue

        # If adding this sentence exceeds chunk size, save current chunk
        if len(current) + len(sentence) > CHUNK_SIZE and len(current) > 100:
            chunk_text_val = current.strip()
            if chunk_text_val:
                chunks.append({
                    "id":    f"{paper_id}_chunk_{chunk_idx}",
                    "text":  chunk_text_val,
                    "paper_id":    paper_id,
                    "paper_title": paper_title,
                    "chunk_index": chunk_idx,
                })
                chunk_idx += 1
                # Overlap: keep last CHUNK_OVERLAP chars as start of next chunk
                current = current[-CHUNK_OVERLAP:] + " " + sentence
        else:
            current = (current + " " + sentence).strip()

    # Don't forget the last chunk
    if current.strip():
        chunks.append({
            "id":    f"{paper_id}_chunk_{chunk_idx}",
            "text":  current.strip(),
            "paper_id":    paper_id,
            "paper_title": paper_title,
            "chunk_index": chunk_idx,
        })

    logger.info(f"✂️  '{paper_title[:40]}' → {len(chunks)} chunks")
    return chunks


# ─────────────────────────────────────────────
# RAG: INDEX PAPER
# ─────────────────────────────────────────────
def index_paper_in_rag(paper_data: Dict[str, Any]) -> bool:
    """
    Chunk paper text, embed each chunk with text-embedding-004,
    and store in ChromaDB. Returns True on success.
    """
    if not chroma_collection:
        logger.warning("⚠️ ChromaDB not available — RAG indexing skipped")
        return False

    paper_id    = paper_data["id"]
    paper_title = paper_data["title"]
    full_text   = paper_data.get("full_text", "")

    if not full_text.strip():
        logger.warning(f"⚠️ No text to index for {paper_title}")
        return False

    # Delete old chunks for this paper (in case of re-upload)
    try:
        existing = chroma_collection.get(where={"paper_id": paper_id})
        if existing["ids"]:
            chroma_collection.delete(ids=existing["ids"])
            logger.info(f"🗑️  Deleted {len(existing['ids'])} old chunks for {paper_id}")
    except Exception:
        pass

    chunks = chunk_text(full_text, paper_id, paper_title)
    if not chunks:
        return False

    # Embed and store in batches of 10 (avoids rate limits)
    batch_size = 10
    total_indexed = 0

    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i+batch_size]
        ids        = []
        embeddings = []
        documents  = []
        metadatas  = []

        for chunk in batch:
            emb = get_embedding(chunk["text"])
            if emb is None:
                logger.warning(f"⚠️ Could not embed chunk {chunk['id']} — skipping")
                continue
            ids.append(chunk["id"])
            embeddings.append(emb)
            documents.append(chunk["text"])
            metadatas.append({
                "paper_id":    chunk["paper_id"],
                "paper_title": chunk["paper_title"],
                "chunk_index": chunk["chunk_index"],
            })

        if ids:
            try:
                chroma_collection.add(
                    ids=ids,
                    embeddings=embeddings,
                    documents=documents,
                    metadatas=metadatas,
                )
                total_indexed += len(ids)
            except Exception as e:
                logger.error(f"❌ ChromaDB add error: {e}")

        # Small pause between batches to respect free tier rate limits
        if i + batch_size < len(chunks):
            time.sleep(0.5)

    logger.info(f"✅ RAG indexed: {total_indexed}/{len(chunks)} chunks for '{paper_title[:50]}'")
    return total_indexed > 0


# ─────────────────────────────────────────────
# RAG: RETRIEVE RELEVANT CHUNKS
# ─────────────────────────────────────────────
def retrieve_relevant_chunks(question: str, paper_ids: Optional[List[str]] = None, k: int = TOP_K_CHUNKS) -> List[Dict]:
    """
    Embed the question and find the most similar chunks in ChromaDB.
    Optionally filter by specific paper IDs.
    Returns list of {text, paper_title, paper_id, score} dicts.
    """
    if not chroma_collection or chroma_collection.count() == 0:
        return []

    query_emb = get_query_embedding(question)
    if query_emb is None:
        return []

    try:
        where_filter = {"paper_id": {"$in": paper_ids}} if paper_ids else None
        results = chroma_collection.query(
            query_embeddings=[query_emb],
            n_results=min(k, chroma_collection.count()),
            where=where_filter,
            include=["documents", "metadatas", "distances"],
        )

        chunks = []
        for doc, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            chunks.append({
                "text":        doc,
                "paper_title": meta.get("paper_title", "Unknown"),
                "paper_id":    meta.get("paper_id", ""),
                "score":       round(1 - dist, 3),   # cosine similarity
            })

        logger.info(f"🔍 Retrieved {len(chunks)} chunks for: '{question[:60]}'")
        return chunks

    except Exception as e:
        logger.error(f"❌ ChromaDB query error: {e}")
        return []


# ─────────────────────────────────────────────
# LLM CALL
# ─────────────────────────────────────────────
def ask_gemini(prompt: str, max_tokens: int = 1500) -> Optional[str]:
    """Ask Gemini. Auto-switches model on 404. Retries on 429."""
    global gemini_model, gemini_model_name

    if not gemini_model:
        logger.warning("⚠️ Gemini not initialised — using fallback")
        return None

    max_retries = 3
    for attempt in range(max_retries):
        try:
            if GEMINI_SDK == "new":
                response = gemini_model.models.generate_content(
                    model=gemini_model_name,
                    contents=prompt,
                    config={"max_output_tokens": max_tokens, "temperature": 0.3},
                )
                return response.text
            else:
                response = gemini_model.generate_content(
                    prompt,
                    generation_config=genai_old.types.GenerationConfig(
                        max_output_tokens=max_tokens,
                        temperature=0.3,
                    )
                )
                return response.text
        except Exception as e:
            err = str(e)
            # 404 model not found → try next model automatically
            if "404" in err or "not found" in err.lower():
                logger.warning(f"⚠️ {gemini_model_name} returned 404. Switching model...")
                idx = MODEL_CANDIDATES.index(gemini_model_name) if gemini_model_name in MODEL_CANDIDATES else -1
                for next_m in MODEL_CANDIDATES[idx+1:]:
                    try:
                        if GEMINI_SDK == "new":
                            gemini_model_name = next_m
                        else:
                            gemini_model = genai_old.GenerativeModel(next_m)
                            gemini_model_name = next_m
                        logger.info(f"✅ Switched to: {next_m}")
                        break
                    except Exception:
                        continue
                else:
                    logger.error("❌ All Gemini models failed")
                    return None
                continue
            # 429 rate limit → wait and retry
            elif "429" in err or "quota" in err.lower():
                wait = (attempt + 1) * 10
                logger.warning(f"⚠️ Rate limit. Waiting {wait}s... (attempt {attempt+1}/{max_retries})")
                if attempt < max_retries - 1:
                    time.sleep(wait)
                    continue
                return None
            else:
                logger.error(f"❌ Gemini error: {err[:150]}")
                return None
    return None


# ─────────────────────────────────────────────
# AGENT CLASS
# ─────────────────────────────────────────────
class MedResearchAgent:
    def __init__(self):
        self.pdf_processor = PDFProcessor()
        self.medical_nlp   = MedicalNLP()
        self.evidence_scorer = EvidenceScorer()
        self.synthesizer   = PaperSynthesizer()
        self.paper_cache: Dict[str, Dict[str, Any]] = {}
        rag_status = "✅ RAG active" if (CHROMA_AVAILABLE and chroma_collection is not None) else "⚠️ RAG disabled (install chromadb)"
        logger.info(f"✅ MedResearch Agent v4.0 initialized — {rag_status}")

    def add_paper(self, pdf_path: str) -> Dict[str, Any]:
        logger.info(f"📄 Processing: {pdf_path}")
        paper_data = self.pdf_processor.process_paper(pdf_path)
        self.paper_cache[paper_data["id"]] = paper_data

        # Index into RAG vector store
        if CHROMA_AVAILABLE and chroma_collection:
            success = index_paper_in_rag(paper_data)
            if success:
                logger.info(f"✅ RAG indexed: {paper_data['title'][:50]}")
            else:
                logger.warning(f"⚠️ RAG indexing failed for: {paper_data['title'][:50]}")

        return paper_data

    def get_papers_context(self) -> str:
        """Build metadata context for LLM (used when RAG chunks aren't enough)."""
        if not self.paper_cache:
            return ""
        parts = []
        for i, (pid, paper) in enumerate(self.paper_cache.items(), 1):
            parts.append(f"""=== PAPER {i} ===
Title: {paper['title']}
Authors: {', '.join(paper['authors'])}
Year: {paper['year']} | Study Type: {paper['study_type']} | Sample: n={paper['sample_size']}
Summary: {paper.get('abstract_summary', 'N/A')[:400]}
Key Findings: {' | '.join(paper.get('key_findings', [])[:3])}
Limitations: {' | '.join(paper.get('limitations', [])[:2])}""")
        return "\n\n".join(parts)

    # ── RAG-powered Q&A ──────────────────────────────────────────────────────
    def answer_with_llm(self, question: str) -> str:
        """
        RAG-powered answer:
        1. Retrieve most relevant chunks from ChromaDB using semantic search
        2. Send ONLY those chunks to Gemini (precise, no truncation)
        3. Fall back to full context if RAG unavailable
        """
        num_papers  = len(self.paper_cache)
        paper_ids   = list(self.paper_cache.keys())

        # ── RAG path ──
        chunks = retrieve_relevant_chunks(question, paper_ids=paper_ids, k=TOP_K_CHUNKS)

        if chunks:
            # Build context from retrieved chunks
            rag_context = ""
            for i, chunk in enumerate(chunks, 1):
                rag_context += f"\n--- Excerpt {i} from '{chunk['paper_title']}' (relevance: {chunk['score']}) ---\n"
                rag_context += chunk["text"] + "\n"

            prompt = f"""You are MedResearch Agent, an expert medical research analyst.

You have retrieved the most relevant excerpts from {num_papers} uploaded paper(s) to answer the user's question.

RETRIEVED CONTEXT (most relevant passages):
{rag_context}

USER QUESTION: {question}

Instructions:
- Answer PRECISELY based on the retrieved excerpts above
- Quote specific numbers, statistics, and findings from the text
- Cite which paper each piece of information comes from
- Use clear headings and bullet points
- If the excerpts don't contain enough info, say so clearly

End with exactly:
⚠️ MEDICAL DISCLAIMER: For educational purposes only. Not medical advice. Always consult qualified healthcare professionals."""

        else:
            # Fallback: use full metadata context
            logger.info("ℹ️ RAG unavailable — using metadata context")
            context = self.get_papers_context()
            prompt = f"""You are MedResearch Agent, an expert medical research paper analyst.

You have {num_papers} medical research paper(s):

{context}

USER QUESTION: {question}

Answer specifically, cite paper titles and authors, use bullet points.

End with: ⚠️ MEDICAL DISCLAIMER: For educational purposes only. Not medical advice. Always consult qualified healthcare professionals."""

        response = ask_gemini(prompt, max_tokens=1500)
        if response:
            rag_badge = " 🔍 *Answer powered by RAG semantic search*" if chunks else ""
            logger.info(f"✅ Answered with {'RAG' if chunks else 'metadata'} context")
            return response + rag_badge
        return self._fallback_answer(question)

    # ── RAG-powered Synthesis ─────────────────────────────────────────────────
    def synthesize_with_llm(self, topic: str) -> str:
        """Synthesis using RAG to pull the best cross-paper evidence."""
        papers = list(self.paper_cache.values())
        if len(papers) < 2:
            return "⚠️ Need at least 2 papers for synthesis."

        paper_ids = list(self.paper_cache.keys())

        # Retrieve broad chunks covering key synthesis topics
        synthesis_queries = [
            f"{topic} main findings results",
            f"{topic} methodology study design sample size",
            f"{topic} limitations conclusions",
            f"{topic} statistical significance outcomes",
        ]

        all_chunks = {}
        for q in synthesis_queries:
            for chunk in retrieve_relevant_chunks(q, paper_ids=paper_ids, k=4):
                cid = chunk["paper_id"] + chunk["text"][:30]
                if cid not in all_chunks:
                    all_chunks[cid] = chunk

        rag_context = ""
        if all_chunks:
            for i, chunk in enumerate(list(all_chunks.values())[:16], 1):
                rag_context += f"\n--- Excerpt {i} | Paper: '{chunk['paper_title']}' ---\n"
                rag_context += chunk["text"] + "\n"
        else:
            rag_context = self.get_papers_context()

        prompt = f"""You are MedResearch Agent, an expert at synthesizing medical research.

Retrieved evidence from {len(papers)} papers on: "{topic}"

{rag_context}

Paper Metadata:
{self.get_papers_context()}

Create a comprehensive synthesis report with EXACTLY these sections:

📊 **OVERVIEW**
[What these papers collectively study — 2-3 sentences]

✅ **CONSENSUS FINDINGS**
[Numbered list — what ALL papers agree on, with specific numbers/stats from the excerpts]

⚔️ **CONTRADICTIONS & DEBATES**
[Where papers disagree — cite specific paper titles]

🔬 **METHODOLOGY COMPARISON**
[Compare: study design, sample sizes, duration, populations, outcome measures]

📈 **OVERALL EVIDENCE STRENGTH**
[Score 0-100 with justification based on study types and sample sizes]

🔍 **RESEARCH GAPS**
[What remains unknown, what future research should address]

💡 **KEY TAKEAWAYS**
[3-5 bullet points — the most clinically important findings]

Be thorough and specific. Cite paper titles when comparing.

End with: ⚠️ MEDICAL DISCLAIMER: For educational purposes only. Not medical advice. Always consult qualified healthcare professionals."""

        response = ask_gemini(prompt, max_tokens=2500)
        if response:
            rag_badge = "\n\n🔍 *Synthesis powered by RAG semantic search*" if all_chunks else ""
            return response + rag_badge
        return self._fallback_synthesis(topic)

    # ── Paper Summary ─────────────────────────────────────────────────────────
    def generate_summary_with_llm(self, paper_data: Dict[str, Any]) -> str:
        """Individual paper summary using RAG chunks for accuracy."""
        quality_score = self.evidence_scorer.score_paper(paper_data)

        # Pull the most informative chunks from this specific paper
        chunks = retrieve_relevant_chunks(
            "main findings results methods conclusions sample size",
            paper_ids=[paper_data["id"]],
            k=5
        )

        chunk_context = ""
        if chunks:
            for i, c in enumerate(chunks, 1):
                chunk_context += f"\n[Excerpt {i}]\n{c['text']}\n"
        else:
            chunk_context = f"""
Abstract: {paper_data.get('abstract_summary', '')}
Methods: {paper_data.get('methods', '')[:400]}
Results: {paper_data.get('results', '')[:400]}
Conclusions: {paper_data.get('conclusions', '')[:300]}
Key Findings: {', '.join(paper_data.get('key_findings', []))}"""

        prompt = f"""You are MedResearch Agent. Summarize this paper in plain English.

PAPER:
Title: {paper_data['title']}
Authors: {', '.join(paper_data['authors'])}
Year: {paper_data['year']} | Type: {paper_data['study_type']} | n={paper_data['sample_size']}
Evidence Score: {quality_score}/100

RELEVANT EXCERPTS:
{chunk_context}

Write in this EXACT format:

📄 **{paper_data['title']}**
👥 **Authors:** {', '.join(paper_data['authors'][:3])}{'et al.' if len(paper_data['authors']) > 3 else ''} | 📅 **Year:** {paper_data['year']}
⭐ **Evidence Quality:** {quality_score}/100

**🔍 What This Study Is About:**
[2-3 plain English sentences anyone can understand]

**🎯 Key Findings:**
[4-5 bullet points with SPECIFIC numbers and statistics from the excerpts]

**🧪 Study Design:**
[Study type, participants, duration, what was measured — in simple terms]

**⚠️ Limitations:**
[2-3 main weaknesses]

**💊 Clinical Relevance:**
[Why this matters for patients and doctors]

End with: ⚠️ MEDICAL DISCLAIMER: For educational purposes only. Not medical advice."""

        response = ask_gemini(prompt)
        if response:
            return response
        return f"""📄 **{paper_data['title']}**
👥 Authors: {', '.join(paper_data['authors'])} | 📅 Year: {paper_data['year']}
⭐ Evidence Quality: {quality_score}/100

**Summary:** {paper_data.get('abstract_summary', 'No summary available')}

**Key Findings:**
{chr(10).join(f"• {f}" for f in paper_data.get('key_findings', []))}

**Study Design:** {paper_data['study_type']} | Sample: n={paper_data['sample_size']}
{MEDICAL_DISCLAIMER}"""

    # ── Status ────────────────────────────────────────────────────────────────
    def get_status(self) -> Dict[str, Any]:
        rag_chunks = chroma_collection.count() if chroma_collection else 0
        return {
            "papers_count":   len(self.paper_cache),
            "llm_powered":    gemini_model is not None,
            "llm_provider":   f"Google Gemini ({gemini_model_name})" if gemini_model else "Rule-based fallback",
            "rag_enabled":    CHROMA_AVAILABLE and chroma_collection is not None,
            "rag_chunks":     rag_chunks,
            "embed_model":    EMBED_MODEL if CHROMA_AVAILABLE else "N/A",
            "upload_dir":     str(UPLOAD_DIR.absolute()),
            "papers": [
                {"id": pid, "title": p["title"], "authors": p["authors"],
                 "year": p["year"], "study_type": p["study_type"]}
                for pid, p in self.paper_cache.items()
            ]
        }

    # ── Fallback: Rule-based answer ───────────────────────────────────────────
    def _fallback_answer(self, question: str) -> str:
        papers = list(self.paper_cache.values())
        if not papers:
            return f"No papers loaded.{MEDICAL_DISCLAIMER}"

        q = question.lower()
        asking_sample   = any(w in q for w in ["sample", "participant", "patient", "size", "n=", "how many"])
        asking_authors  = any(w in q for w in ["author", "who wrote", "researcher", "written by"])
        asking_method   = any(w in q for w in ["method", "design", "study type", "how was", "protocol"])
        asking_result   = any(w in q for w in ["result", "finding", "outcome", "show", "found", "significant"])
        asking_limit    = any(w in q for w in ["limit", "weakness", "shortcoming"])
        asking_conclude = any(w in q for w in ["conclusion", "conclude", "summary", "takeaway"])

        answer_parts = []
        for i, paper in enumerate(papers, 1):
            lines = [f"**Paper {i}: {paper.get('title','?')} ({paper.get('year','')})**"]
            if asking_sample:
                lines.append(f"- Sample size: **n = {paper.get('sample_size','?')}**")
                lines.append(f"- Study type: {paper.get('study_type','?')}")
            elif asking_authors:
                lines.append(f"- Authors: **{', '.join(paper.get('authors',['?']))}**")
            elif asking_method:
                m = paper.get('methods','')[:300]
                lines.append(f"- Type: **{paper.get('study_type','?')}** | n={paper.get('sample_size','?')}")
                if m: lines.append(f"- {m}...")
            elif asking_limit:
                for l in paper.get('limitations',['Not stated'])[:3]:
                    lines.append(f"- {l}")
            elif asking_conclude:
                c = paper.get('conclusions','')[:300]
                if c: lines.append(f"- {c}...")
            else:
                for f in paper.get('key_findings',[])[:3]:
                    lines.append(f"- {f}")
                lines.append(f"- Study: {paper.get('study_type','?')} | n={paper.get('sample_size','?')}")
            answer_parts.append("\n".join(lines))

        return f"## Based on {len(papers)} Paper(s)\n\n" + "\n\n".join(answer_parts) + MEDICAL_DISCLAIMER

    # ── Fallback: Rule-based synthesis ───────────────────────────────────────
    def _fallback_synthesis(self, topic: str) -> str:
        papers = list(self.paper_cache.values())
        if not papers:
            return "No papers loaded."
        s = self.synthesizer.synthesize(papers, topic)

        rows = []
        for i, p in enumerate(papers, 1):
            auth = ", ".join(p.get("authors", ["?"])[:2])
            if len(p.get("authors",[])) > 2: auth += " et al."
            rows.append(f"| {i} | {p.get('title','?')[:50]} | {auth} | {p.get('year','')} | {p.get('study_type','?')} | n={p.get('sample_size','?')} |")

        table = ("| # | Title | Authors | Year | Study Type | Sample |\n"
                 "|---|-------|---------|------|------------|--------|\n" + "\n".join(rows))

        findings_blocks = []
        for i, p in enumerate(papers, 1):
            good = [f for f in p.get("key_findings",[]) if 30 < len(f) < 400][:3]
            block = f"**Paper {i} — {p.get('title','?')[:50]}:**\n"
            block += ("\n".join(f"- {f}" for f in good) if good else "- Key findings not extracted.")
            findings_blocks.append(block)

        return f"""## 🔬 Multi-Paper Synthesis: {topic}

### 📋 Papers Overview
{table}

### ✅ Consensus Findings
{chr(10).join(f"{i+1}. {f}" for i, f in enumerate(s.get('consensus_findings',[])))}

### 📊 Evidence Strength: {s.get('overall_evidence_strength','?')}/100
**Confidence:** {s.get('confidence_level','?')}

### 🔑 Key Findings Per Paper
{chr(10+chr(10).join(findings_blocks))}

### 🔍 Research Gaps
{chr(10).join(f"- {g}" for g in s.get('research_gaps',[]))}

{MEDICAL_DISCLAIMER}"""


# ─────────────────────────────────────────────
# INITIALIZE AGENT
# ─────────────────────────────────────────────
med_agent = MedResearchAgent()


# ─────────────────────────────────────────────
# MESSAGE HANDLER
# ─────────────────────────────────────────────
def handler(messages: List[Dict[str, str]]) -> str:
    try:
        user_message = messages[-1]["content"] if messages else ""
        if not user_message:
            return "⚠️ No message received."

        logger.info(f"📩 Received: '{user_message[:100]}'")
        user_lower  = user_message.lower()
        num_papers  = len(med_agent.paper_cache)
        llm_on      = gemini_model is not None
        rag_on      = CHROMA_AVAILABLE and chroma_collection is not None
        rag_chunks  = chroma_collection.count() if chroma_collection else 0

        rag_status  = f"🔍 RAG Active ({rag_chunks} chunks)" if (rag_on and rag_chunks > 0) else "⚠️ RAG offline"

        # GREETINGS
        if any(w in user_lower for w in ["hi", "hello", "hey", "greetings"]):
            paper_status = f"📚 {num_papers} paper(s) loaded!" if num_papers > 0 else "💡 Upload papers to get started!"
            return f"""👋 **Hello! I'm MedResearch Agent v4.0**

I analyze medical research papers using **RAG + Google Gemini AI**.

**What I can do:**
• 📄 Summarize papers in plain English
• 🔬 Synthesize & compare multiple papers
• 💬 Answer questions with **precise citations** from paper text
• 📊 Score evidence quality (0-100)
• 🔍 Semantic search across all uploaded papers

**Status:** {paper_status}
**AI:** {'✅ Google Gemini Active' if llm_on else '⚙️ Set GEMINI_API_KEY'}
**RAG:** {rag_status}

Upload papers and ask me anything!{MEDICAL_DISCLAIMER}"""

        # STATUS
        elif any(w in user_lower for w in ["status", "how many paper", "list paper"]):
            if num_papers > 0:
                paper_list = "\n".join(
                    f"  {i+1}. **{med_agent.paper_cache[pid]['title'][:60]}** ({med_agent.paper_cache[pid]['year']}) — Authors: {', '.join(med_agent.paper_cache[pid]['authors'][:2])}"
                    for i, pid in enumerate(med_agent.paper_cache.keys())
                )
                return f"""📊 **Agent Status**

**Papers Loaded:** {num_papers}
**AI:** {'✅ Google Gemini (' + gemini_model_name + ')' if llm_on else '⚙️ Rule-based'}
**RAG:** {rag_status}
**Embeddings:** {'✅ text-embedding-004 (FREE)' if rag_on else '⚠️ Disabled'}

**Loaded Papers:**
{paper_list}{MEDICAL_DISCLAIMER}"""
            else:
                return f"📊 No papers loaded yet. Upload PDFs in the Upload tab!{MEDICAL_DISCLAIMER}"

        # SYNTHESIS / COMPARE
        elif any(w in user_lower for w in ["compare", "synthesize", "synthesis", "contrast", "differences", "similarities", "consensus"]):
            if num_papers >= 2:
                return med_agent.synthesize_with_llm(user_message)
            elif num_papers == 1:
                return f"📚 Upload at least 1 more paper to compare.{MEDICAL_DISCLAIMER}"
            else:
                return f"📚 No papers loaded. Upload 2+ papers to synthesize.{MEDICAL_DISCLAIMER}"

        # SUMMARY
        elif any(w in user_lower for w in ["summarize", "summary", "summarise", "overview"]) and num_papers > 0:
            if num_papers == 1:
                return med_agent.generate_summary_with_llm(list(med_agent.paper_cache.values())[0])
            else:
                return med_agent.synthesize_with_llm("comprehensive summary of all papers")

        # HELP
        elif "help" in user_lower:
            return f"""📖 **How to Use MedResearch Agent v4.0**

**Step 1:** Upload Papers tab → drag & drop PDFs
**Step 2:** Papers are auto-indexed into RAG vector store
**Step 3:** Ask any question — answers cite exact paper text!

**Example Questions:**
• "What were the main findings?"
• "What was the sample size of each study?"
• "Compare the methodologies"
• "What are the limitations?"
• "Were results statistically significant?"
• "Synthesize the findings"
• "Which paper had the larger sample size?"

**RAG:** {rag_status}
**AI:** {'✅ Google Gemini Active' if llm_on else '⚙️ Get FREE key at aistudio.google.com'}{MEDICAL_DISCLAIMER}"""

        # ALL OTHER QUESTIONS → RAG + Gemini
        else:
            if num_papers > 0:
                return med_agent.answer_with_llm(user_message)
            else:
                return f"""❓ Upload research papers first!

1. Go to **Upload Papers** tab
2. Upload your PDF files
3. Come back and ask anything!{MEDICAL_DISCLAIMER}"""

    except Exception as e:
        logger.error(f"❌ Handler error: {e}", exc_info=True)
        return f"⚠️ Error: {str(e)}\n\nPlease try again.{MEDICAL_DISCLAIMER}"


# ─────────────────────────────────────────────
# FASTAPI ROUTES
# ─────────────────────────────────────────────
def create_fastapi_app():
    app = FastAPI(title="MedResearch Agent v4.0 — RAG + Gemini (FREE)")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/")
    async def root():
        return {
            "name":          "MedResearch Agent",
            "version":       "4.0.0 - RAG + Gemini (FREE)",
            "papers_loaded": len(med_agent.paper_cache),
            "llm_active":    gemini_model is not None,
            "llm_model":     gemini_model_name,
            "rag_enabled":   CHROMA_AVAILABLE and chroma_collection is not None,
            "rag_chunks":    chroma_collection.count() if chroma_collection else 0,
            "embed_model":   EMBED_MODEL,
        }

    @app.post("/messages")
    async def messages(request: Request):
        try:
            body = await request.body()
            messages_data = json.loads(body)
            return handler(messages_data)
        except Exception as e:
            logger.error(f"Error: {e}", exc_info=True)
            return JSONResponse({"error": str(e)}, status_code=500)

    @app.post("/upload")
    async def upload_paper(file: UploadFile = File(...)):
        try:
            logger.info(f"📤 Uploading: {file.filename}")
            safe_name = re.sub(r'[<>:"/\\|?*]', '_', file.filename)
            if not safe_name.lower().endswith('.pdf'):
                raise ValueError("Only PDF files are supported")

            file_path = UPLOAD_DIR / safe_name
            content   = await file.read()
            with open(file_path, "wb") as f:
                f.write(content)
            logger.info(f"💾 Saved: {file_path} ({len(content):,} bytes)")

            paper_data     = med_agent.add_paper(str(file_path))
            evidence_score = med_agent.evidence_scorer.score_paper(paper_data)
            rag_chunks     = chroma_collection.count() if chroma_collection else 0

            return JSONResponse({
                "success":       True,
                "paper_id":      paper_data["id"],
                "title":         paper_data["title"],
                "authors":       paper_data["authors"],
                "year":          paper_data["year"],
                "study_type":    paper_data["study_type"],
                "sample_size":   paper_data["sample_size"],
                "evidence_score": evidence_score,
                "rag_indexed":   CHROMA_AVAILABLE and chroma_collection is not None,
                "rag_chunks":    rag_chunks,
                "message":       f"✅ Processed & RAG indexed: {paper_data['title']}"
            })

        except Exception as e:
            logger.error(f"❌ Upload error: {e}", exc_info=True)
            return JSONResponse({"error": str(e)}, status_code=500)

    @app.get("/status")
    async def get_status():
        return med_agent.get_status()

    @app.post("/synthesize")
    async def synthesize(request: Request):
        try:
            body  = await request.json()
            topic = body.get("topic", "medical research")
            if len(med_agent.paper_cache) < 2:
                return JSONResponse({"error": "Need at least 2 papers"}, status_code=400)
            synthesis = med_agent.synthesize_with_llm(topic)
            return {"synthesis": synthesis}
        except Exception as e:
            logger.error(f"Synthesis error: {e}", exc_info=True)
            return JSONResponse({"error": str(e)}, status_code=500)

    return app


config = {
    "author":      "medresearch@example.com",
    "name":        "medresearch_agent_rag",
    "description": "Medical research analyzer — RAG + Google Gemini (FREE)",
    "version":     "4.0.0",
}

if __name__ == "__main__":
    logger.info("🚀 MedResearch Agent v4.0 — RAG + Gemini (FREE)")
    logger.info(f"📁 Uploads:  {UPLOAD_DIR.absolute()}")
    logger.info(f"🗄️  ChromaDB: {CHROMA_DIR.absolute()}")
    logger.info(f"🤖 Gemini:  {'✅ ' + gemini_model_name if gemini_model else '⚠️  Set GEMINI_API_KEY'}")
    logger.info(f"🔍 RAG:     {'✅ Active' if (CHROMA_AVAILABLE and chroma_collection) else '⚠️  Install chromadb'}")
    logger.info(f"📐 Embed:   {EMBED_MODEL} (FREE)")

    if FASTAPI_AVAILABLE:
        app = create_fastapi_app()
        logger.info("✅ Server starting at http://localhost:3773")
        uvicorn.run(app, host="localhost", port=3773, log_level="info")
    else:
        logger.error("❌ Install: pip install fastapi uvicorn python-multipart")
        sys.exit(1)
