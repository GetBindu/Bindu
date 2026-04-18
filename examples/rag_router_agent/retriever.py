import re


def retrieve_docs(db_path: str, query: str, k: int = 2):
    try:
        with open(db_path, "r") as f:
            docs = f.readlines()
    except FileNotFoundError:
        return []

    # 🔤 Normalize query (fix punctuation + case issues)
    query_words = re.findall(r"\w+", query.lower())

    scored = []

    for doc in docs:
        doc_lower = doc.lower()

        # 📊 Compute score (token-based match)
        score = sum(1 for word in query_words if word in doc_lower)

        # ❗ Filter irrelevant docs (IMPORTANT FIX)
        if score > 0:
            scored.append((score, doc))

    # 📈 Sort by relevance
    scored.sort(key=lambda x: x[0], reverse=True)

    # 📦 Return top-k docs
    return [doc for _, doc in scored[:k]]
