import yfinance as yf
from skills.market_skills import MarketSkills

def test_price(query):
    print(f"\n--- Debugging Price for: '{query}' ---")
    
    skill = MarketSkills()
    
    # 1. Check Ticker Resolution
    print("1. resolving ticker...")
    ticker = skill.find_ticker(query)
    print(f"   Resolved Ticker: '{ticker}'")
    
    # 2. Check Yfinance History
    print(f"2. Fetching history for {ticker}...")
    stock = yf.Ticker(ticker)
    
    try:
        hist = stock.history(period="5d")
        print(f"   History Shape: {hist.shape}")
        
        if hist.empty:
            print("   ❌ History is EMPTY. yfinance returned no data.")
            print("   Possible reasons: Wrong ticker, delisted, or yfinance blocked.")
        else:
            print("   ✅ History Found:")
            print(hist[['Close']].tail())
            current_price = hist['Close'].iloc[-1]
            print(f"   Current Price: {current_price} {stock.info.get('currency', 'Unknown')}")

    except Exception as e:
        print(f"   ❌ Error fetching history: {e}")

if __name__ == "__main__":
    # Test the problematic one
    test_price("Tata Elxsi")
    
    # Test a known working one
    test_price("Tesla")
