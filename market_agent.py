"""
Market Analyst Agent - A specialized node for financial intelligence.
"""
import json
from bindu.penguin.bindufy import bindufy
from skills.market_skills import MarketSkills

# Initialize the skill logic
market_skill = MarketSkills()

def handler(messages: list[dict[str, str]]):
    """
    Process incoming messages.
    Expected usage: User sends a stock name or ticker.
    """
    try:
        # 1. Extract the latest user message
        if not messages:
             return [{"role": "assistant", "content": "Hello! I am the Financial Analyst Agent. Ask me about any stock."}]
        
        last_message = messages[-1]["content"]
        
        # 2. Heuristic: Check if the user is just saying hello
        if last_message.lower().strip() in ["hi", "hello", "help", "start"]:
             return [{"role": "assistant", "content": "I am ready. Ask me to 'Analyze Tesla' or 'Start check on Reliance'."}]

        # 3. Clean the input (Basic extraction)
        # In a real agent, we might use an LLM here to extract the entity.
        # For now, we assume the message contains the query directly or is "Analyze <Query>"
        query = last_message
        for prefix in ["Analyze ", "Check ", "Price of "]:
            if query.lower().startswith(prefix.lower()):
                query = query[len(prefix):]
        
        # 4. Execute the Skill
        print(f"🤖 Agent received query: {query}")
        result = market_skill.get_financial_summary(query)
        
        # 5. Format the output
        # We return the raw JSON in the content for now, or a formatted string.
        # Let's do a nice markdown summary.
        
        if "error" in result:
             response_text = f"**Error**: {result['error']}"
        else:
            symbol = result.get('symbol', 'N/A')
            price = result.get('price', 'N/A')
            currency = result.get('currency', 'N/A')
            change_percent = result.get('change_percent', 0.0)
            
            # Add a text indicator based on the trend
            trend_indicator = "UP" if change_percent >= 0 else "DOWN"
            
            response_text = f"""
## Market Report: {symbol}

**Price Action**
The stock is currently trading at **{price} {currency}**, which is a move of **{change_percent}%** {trend_indicator}.
**Trend**: {result.get('technicals', {}).get('trend', 'N/A')}

**Fundamentals**:
- Market Cap: {result.get('fundamentals', {}).get('market_cap')}
- P/E Ratio: {result.get('fundamentals', {}).get('pe_ratio')}

**News**:
"""
            for news in result.get('news', [])[:3]:
                if isinstance(news, dict):
                    response_text += f"- [{news.get('title')}]({news.get('link')})\n"
                else:
                    response_text += f"- {news}\n"

        return [{"role": "assistant", "content": response_text}]

    except Exception as e:
        return [{"role": "assistant", "content": f"Internal Agent Error: {str(e)}"}]

# Bindu Configuration
config = {
    "author": "student@getbindu.com",
    "name": "market_analyst_agent",
    "description": "A verified node for real-time financial market analysis.",
    "deployment": {"url": "http://localhost:3773", "expose": True},
    "skills": ["skills/market_skill.yaml"] 
}

if __name__ == "__main__":
    # Start the Bindu service
    print("🚀 Starting Market Analyst Agent on port 3773...")
    bindufy(config, handler)
