import yfinance as yf
from ddgs import DDGS
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
        "TATA ELXSI": "TATAELXSI.NS",
        "TATAELXSI": "TATAELXSI.NS",
        "INFOSYS": "INFY.NS",
        "WIPRO": "WIPRO.NS",
        "ZOMATO": "ZOMATO.NS",
        "HDFC": "HDFCBANK.NS"
    }

    def find_ticker(self, query: str) -> str:
        """
        Attempts to resolve a company name to a stock ticker.
        """
        clean_query = query.strip().upper()

        if clean_query in self.COMMON_TICKERS:
            return self.COMMON_TICKERS[clean_query]

        # Check if it looks like a ticker already (e.g. "INFY")
        if len(clean_query) <= 5 and " " not in clean_query:
             return clean_query

        print(f"Unknown symbol '{query}'. Identifying via DuckDuckGo...")
        
        try:
            search_query = f"ticker symbol for {query}"
            results = DDGS().text(search_query, max_results=3)
            print(f"DEBUG: Search Results for '{search_query}': {results}")
            
            for res in results:
                href = res.get('href', '')
                if "finance.yahoo.com/quote/" in href:
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
        
        return clean_query

    def get_financial_summary(self, user_query: str):
        """
        The main public method. 
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
        try:
            print(f"DEBUG: Fetching history for {ticker_symbol}...")
            hist_recent = stock.history(period="5d")
            print(f"DEBUG: History Shape: {hist_recent.shape}")
            
            # RETRY LOGIC: If empty, try appending .NS (common issue for Indian stocks)
            if hist_recent.empty and "." not in ticker_symbol:
                 print(f"DEBUG: Data empty. Applying '.NS' suffix and retrying...")
                 ticker_symbol = f"{ticker_symbol}.NS"
                 summary["symbol"] = ticker_symbol # Update summary symbol
                 stock = yf.Ticker(ticker_symbol)
                 hist_recent = stock.history(period="5d")
                 print(f"DEBUG: Retry History Shape: {hist_recent.shape}")
            
            if not hist_recent.empty:
                current_price = hist_recent['Close'].iloc[-1]
                if len(hist_recent) >= 2:
                    prev_close = hist_recent['Close'].iloc[-2]
                else:
                    prev_close = stock.info.get('previousClose', current_price)

                change_pct = ((current_price - prev_close) / prev_close) * 100
                currency = stock.info.get('currency', 'USD')
            
            else:
                 # Fallback to .info
                 print("DEBUG: History failed. Using fast_info/info fallback.")
                 current_price = stock.info.get('currentPrice', stock.info.get('regularMarketPrice', 0.0))
                 prev_close = stock.info.get('previousClose', current_price)
                 change_pct = 0.0
                 currency = stock.info.get('currency', 'USD')

            summary["price"] = round(current_price, 2)
            summary["change_percent"] = round(change_pct, 2)
            summary["currency"] = currency
            
        except Exception as e:
            print(f"Error fetching data: {e}")
            return {"error": f"I couldn't find market data for '{ticker_symbol}'. It might be delisted or misspelled."}

        # 3. Fetch Fundamental Data (Deep Dive)
        try:
             # Force a refresh of info
            info = stock.info
            summary["fundamentals"] = {
                "market_cap": self._format_large_number(info.get("marketCap")),
                "pe_ratio": round(info.get("trailingPE", 0), 2) if info.get("trailingPE") else "N/A",
                "sector": info.get("sector", "Unknown"),
                "long_name": info.get("longName", ticker_symbol)
            }
        except:
             summary["fundamentals"] = {}

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

        # 5. News Sentiment (Powered by DuckDuckGo News)
        try:
            # We search for the company name instead of ticker for better news relevance
            news_query = f"{stock.info.get('longName', user_query)} stock news"
            print(f"DEBUG: Fetching news for query: '{news_query}'")
            # Use positional argument as validated by debug script
            news_results = DDGS().news(news_query, max_results=3)
            print(f"DEBUG: Raw News Results: {news_results}")
            
            clean_news = []
            for item in news_results:
                clean_news.append({
                    "title": item.get('title'),
                    "link": item.get('url'), # DDGS uses 'url', not 'link'
                    "publisher": item.get('source')
                })
            summary["news"] = clean_news
        except Exception as e:
            print(f"Error fetching news: {e}")
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
