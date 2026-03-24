#!/usr/bin/env python
"""Test ConfigValidator with real sample config files."""

import json
from pathlib import Path
from bindu.penguin.config_validator import ConfigValidator, load_and_validate_config

def test_sample_configs():
    """Test validation of sample config files."""
    
    # Test 1: Load and validate the new test config with trust
    print("Testing examples/test_config_with_trust.json...")
    config_path = Path("examples/test_config_with_trust.json")
    
    if config_path.exists():
        with open(config_path, "r") as f:
            raw_config = json.load(f)
        
        try:
            result = ConfigValidator.validate_and_process(raw_config)
            print(f"✓ Config validation successful")
            print(f"  - Agent name: {result['name']}")
            print(f"  - Author: {result['author']}")
            print(f"  - Trust level: {result['agent_trust']['required_verification_level']}")
            print(f"  - Max hierarchy depth: {result['agent_trust']['max_agent_hierarchy_depth']}")
            print(f"  - Allowed origins: {result['agent_trust']['allowed_origins']}")
            print(f"  - Trust verification required: {result['agent_trust']['trust_verification_required']}")
        except ValueError as e:
            print(f"✗ Validation failed: {e}")
            return False
    else:
        print(f"⚠ Config file not found at {config_path}")
    
    # Test 2: Test creating bindufy config
    print("\nTesting create_bindufy_config...")
    try:
        bindufy_config = ConfigValidator.create_bindufy_config(raw_config)
        print(f"✓ Bindufy config created successfully")
        print(f"  - Has storage config: {'storage' in bindufy_config}")
        print(f"  - Has scheduler config: {'scheduler' in bindufy_config}")
        print(f"  - Has deployment config: {'deployment' in bindufy_config}")
    except Exception as e:
        print(f"✗ Failed to create bindufy config: {e}")
        return False
    
    return True

if __name__ == "__main__":
    import sys
    success = test_sample_configs()
    if success:
        print("\n✅ All sample config tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Sample config tests failed!")
        sys.exit(1)
