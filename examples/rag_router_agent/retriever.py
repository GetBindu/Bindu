def retrieve_docs(db_path: str, query: str, k: int = 2):
    try:
        with open(db_path, "r") as f:
            docs = f.readlines()
    except FileNotFoundError:
        return []

    # Simple retrieval (keyword match)
    scored = []
    for doc in docs:
        score = sum(1 for word in query.split() if word in doc.lower())
        scored.append((score, doc))

    scored.sort(reverse=True)
    return [doc for _, doc in scored[:k]]