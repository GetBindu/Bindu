import pytest
from skills.market_skills import MarketSkills

class TestMarketSkills:
    @pytest.fixture
    def skills(self):
        return MarketSkills()

    def test_find_ticker_common(self, skills):
        """Test that common tickers are resolved locally."""
        assert skills.find_ticker("Tesla") == "TSLA"
        assert skills.find_ticker("Reliance") == "RELIANCE.NS"
        assert skills.find_ticker("Tata Elxsi") == "TATAELXSI.NS"

    def test_find_ticker_search(self, skills):
        """Test that unknown tickers are searched (Live Test)."""
        # This makes a real network call, so it tests the DDGS integration
        ticker = skills.find_ticker("Microsoft")
        assert ticker in ["MSFT", "MSFT.O", "MSFT.NASDAQ"]

    def test_financial_summary_structure(self, skills):
        """Test that the summary returns the correct schema."""
        result = skills.get_financial_summary("Tesla")
        
        assert "symbol" in result
        assert result["symbol"] == "TSLA"
        assert "price" in result
        assert isinstance(result["price"], (int, float))
        assert "currency" in result
        
        # Check fundamentals
        assert "fundamentals" in result
        assert "market_cap" in result["fundamentals"]
        
        # Check news
        assert "news" in result
        assert isinstance(result["news"], list)

    def test_indian_stock_resolution(self, skills):
        """Test specific logic for Indian markets (suffix handling)."""
        result = skills.get_financial_summary("Tata Elxsi")
        assert result["symbol"] == "TATAELXSI.NS"
        assert result["price"] > 0
        assert result["currency"] == "INR"
