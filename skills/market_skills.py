import yfinance as yf
from duckduckgo_search import DDGS
from datetime import datetime

class MarketSkills:
    """
    Core logic for the Financial Analyst.
    
    This class handles:
    1. Identifying (mapping names like "Tesla" to "TSLA").
    2. Fetching (getting raw data from yfinance).
    3. Synthesizing (creating a summary for the agent).
    """

    # Static mapping for commonly requested stocks.
    # This acts as a "Fast Path" cache to avoid network calls for obvious things.
    COMMON_TICKERS = {
        "TESLA": "TSLA",
        "GOOGLE": "GOOGL", 
        "APPLE": "AAPL",
        "MICROSOFT": "MSFT",
        "AMAZON": "AMZN",
        "NVIDIA": "NVDA",
        "FACEBOOK": "META",
        "META": "META",
        "NETFLIX": "NFLX",
        "RELIANCE": "RELIANCE.NS",
        "TATA": "TATAMOTORS.NS",
        "ZOMATO": "ZOMATO.NS"
    }

    def find_ticker(self, query: str) -> str:
        """
        Attempts to resolve a company name to a stock ticker.
        Strategies:
        1. Check the local cache (COMMON_TICKERS).
        2. Check if it looks like a ticker already (e.g. "INFY").
        3. Use DuckDuckGo to search for it.
        """
        clean_query = query.strip().upper()

        # Strategy 1: Fast Lookup
        if clean_query in self.COMMON_TICKERS:
            return self.COMMON_TICKERS[clean_query]

        # Strategy 2: Is it already a ticker? (Heuristic: Short, no spaces)
        if len(clean_query) <= 5 and " " not in clean_query:
             # We assume it's valid if it looks like one. Verification happens during fetch.
             return clean_query

        # Strategy 3: Search the web
        print(f"Unknown symbol '{query}'. Identifying via DuckDuckGo...")
        
        try:
            # We search for "ticker symbol for <name>" to get high-relevance results
            search_query = f"ticker symbol for {query}"
            results = DDGS().text(search_query, max_results=3)
            
            for res in results:
                href = res.get('href', '')
                
                # Check for trustworthy financial domains
                if "finance.yahoo.com/quote/" in href:
                    # Parse URL structure: .../quote/SYMBOL/...
                    return href.split("finance.yahoo.com/quote/")[1].split("/")[0].split("?")[0]
                
                if "marketwatch.com/investing/stock/" in href:
                     return href.split("marketwatch.com/investing/stock/")[1].split("?")[0].upper()

                if "google.com/finance/quote/" in href:
                     return href.split("google.com/finance/quote/")[1].split(":")[0] 

            # Fallback: specific site search
            direct_results = DDGS().text(f"{query} site:finance.yahoo.com", max_results=1)
            if direct_results:
                 href = direct_results[0]['href']
                 if "finance.yahoo.com/quote/" in href:
                    return href.split("finance.yahoo.com/quote/")[1].split("/")[0].split("?")[0]

        except Exception as e:
            print(f"⚠️ Search warning: Could not resolve '{query}' via web. Error: {e}")
        
        # If all else fails, return the original query. 
        # yfinance might still be able to find it if we got lucky.
        return clean_query

    def get_financial_summary(self, user_query: str):
        """
        The main public method. 
        Orchestrates the entire analysis pipeline.
        """
        # 1. Resolve to a unified ticker symbol
        ticker_symbol = self.find_ticker(user_query)
        print(f"Analyzing Ticker: {ticker_symbol}")

        stock = yf.Ticker(ticker_symbol)
        
        # Container for our response
        summary = {
            "symbol": ticker_symbol,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        # 2. Fetch Live Market Data
        # We try 'fast_info' first as it's optimized for recent prices.
        try:
            def safe_get(key, default=0.0):
                 return stock.fast_info.get(key, default) if hasattr(stock, 'fast_info') else default

            price = safe_get('last_price')
            
            # If fast_info failed (value is 0), fall back to standard metadata
            if price == 0.0:
                 price = stock.info.get('currentPrice', stock.info.get('regularMarketPrice', 0.0))
            
            prev_close = safe_get('previous_close')
            if prev_close == 0.0:
                prev_close = stock.info.get('previousClose', 1.0) # Avoid div by zero

            if prev_close and price:
                change_pct = ((price - prev_close) / prev_close) * 100
            else:
                change_pct = 0.0
            
            # Populate basic info
            summary["price"] = round(price, 2)
            summary["change_percent"] = round(change_pct, 2)
            summary["currency"] = stock.info.get('currency', 'USD')
            
        except Exception as e:
            # If we can't get a price, the ticker is likely invalid/delisted.
            return {"error": f"I couldn't find market data for '{ticker_symbol}'. It might be delisted or misspelled."}

        # 3. Fetch Fundamental Data (Deep Dive)
        # Note: This network call is heavier.
        try:
            info = stock.info
            summary["fundamentals"] = {
                "market_cap": self._format_large_number(info.get("marketCap")),
                "pe_ratio": round(info.get("trailingPE", 0), 2) if info.get("trailingPE") else "N/A",
                "sector": info.get("sector", "Unknown"),
                "long_name": info.get("longName", ticker_symbol)
            }
        except:
             summary["fundamentals"] = {} # Graceful degradation

        # 4. Technical Indicator (Simple Moving Average)
        try:
            # Get last 3 months to have enough data points for 50-day average
            hist = stock.history(period="3mo")
            if not hist.empty and len(hist) > 50:
                sma_50 = hist['Close'].tail(50).mean()
                current_close = hist['Close'].iloc[-1]
                
                trend = "BULLISH (Price > 50d SMA)" if current_close > sma_50 else "BEARISH (Price < 50d SMA)"
                summary["technicals"] = {
                    "50_day_sma": round(sma_50, 2),
                    "trend": trend
                }
            else:
                 summary["technicals"] = {"trend": "Not enough data"}
        except:
            summary["technicals"] = {"trend": "Analysis failed"}

        # 5. News Sentiment
        try:
            news = stock.news[:3] if stock.news else []
            summary["news"] = news
        except:
            summary["news"] = []

        return summary
    
    def _format_large_number(self, num):
        """Helper to make market cap readable (e.g. 1.5T, 20B)"""
        if not num: return "N/A"
        if num >= 1_000_000_000_000:
            return f"{num/1_000_000_000_000:.2f}T"
        if num >= 1_000_000_000:
            return f"{num/1_000_000_000:.2f}B"
        if num >= 1_000_000:
            return f"{num/1_000_000:.2f}M"
        return str(num)

if __name__ == "__main__":
    # Developer Test Stub
    skill = MarketSkills()
    print(skill.get_financial_summary("Zomato"))
