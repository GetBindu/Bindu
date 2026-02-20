from ddgs import DDGS


def search_agent(query: str) -> str:
    print("Searching the web...\n")

    for attempt in range(2):
        try:
            results = []

            with DDGS() as ddgs:
                for r in ddgs.text(query, max_results=5):
                    title = r.get("title", "No title")
                    body = r.get("body", "No description")
                    link = r.get("href", "No link")

                    results.append(
                        f"Title: {title}\n"
                        f"Snippet: {body}\n"
                        f"Link: {link}"
                    )

            if not results:
                return "No results found."

            return "\n\n".join(results)

        except Exception as e:
            print(f"Retry {attempt+1} failed: {e}")

    return "Search failed after retries."