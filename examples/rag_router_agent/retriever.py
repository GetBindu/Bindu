import re


def retrieve_docs(db_path: str, query: str, k: int = 2):
    try:
        # ✅ Explicit encoding (fix cross-platform issues)
        with open(db_path, "r", encoding="utf-8") as f:
            docs = f.readlines()
    except FileNotFoundError:
        return []

    # 🔤 Normalize query into tokens (true token-based)
    query_words = set(re.findall(r"\w+", query.lower()))

    scored = []

    for doc in docs:
        # 🔤 Tokenize document
        doc_words = set(re.findall(r"\w+", doc.lower()))

        # 📊 True token-based score (intersection)
        score = len(query_words & doc_words)

        # ❗ Keep only relevant docs
        if score > 0:
            scored.append((score, doc))

    # 📈 Sort by relevance (highest score first)
    scored.sort(key=lambda x: x[0], reverse=True)

    # 📦 Return top-k results
    return [doc for _, doc in scored[:k]]
