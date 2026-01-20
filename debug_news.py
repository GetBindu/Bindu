from ddgs import DDGS
import json

def test_news(query):
    print(f"--- Testing News for: {query} ---")
    try:
        # Mimic the agent's logic
        news_query = f"{query} stock news"
        print(f"Querying DDGS().news('{news_query}')...")
        
        # Try positional argument first based on error message
        results = DDGS().news(news_query, max_results=3)
        print(f"Raw Type: {type(results)}")
        
        # DDGS sometimes returns a generator or list. Let's force list.
        results_list = list(results)
        print(f"Count: {len(results_list)}")
        
        if results_list:
            print("First Item Keys:", results_list[0].keys())
            print(json.dumps(results_list, indent=2))
        else:
            print("❌ No news found via .news()")
            
            # Fallback test: Text search for news
            print("\nTrying Fallback: Text search...")
            text_results = DDGS().text(f"{query} latest financial news", max_results=3)
            print(json.dumps(list(text_results), indent=2))

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_news("Tata Elxsi")
    test_news("Tesla")
