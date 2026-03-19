import pandas as pd
from ai_data_analysis_agent import analyze_dataset

def test_analyze_dataset_valid_csv(tmp_path):
    """Test that the tool correctly parses a valid CSV and returns summary stats."""
    # 1. Create a temporary fake dataset
    df = pd.DataFrame({
        "Product": ["Laptop", "Mouse", "Keyboard"],
        "Sales": [1200, 25, 75]
    })
    test_file = tmp_path / "dummy_sales.csv"
    df.to_csv(test_file, index=False)

    # 2. Run your tool
    result = analyze_dataset(str(test_file))

    # 3. Assert the tool calculated everything correctly
    assert "Dataset Shape: 3 rows, 2 columns" in result
    assert "Product" in result
    assert "Sales" in result
    assert "Missing Values" in result

def test_analyze_dataset_file_not_found():
    """Test that the tool gracefully handles missing files."""
    result = analyze_dataset("this_file_does_not_exist.csv")
    assert "Error: File not found" in result
