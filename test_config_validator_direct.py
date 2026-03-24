#!/usr/bin/env python
"""Direct test of ConfigValidator without pytest dependencies."""

import sys
sys.path.insert(0, '/dev/null')  # Prevent issues with cached imports

from bindu.penguin.config_validator import ConfigValidator

def test_basic_validation():
    """Test basic configuration validation."""
    print("Testing basic validation...")
    config = {"author": "test@example.com", "deployment": {}}
    result = ConfigValidator.validate_and_process(config)
    assert result["author"] == "test@example.com"
    print("✓ Basic validation passed")

def test_agent_trust_valid():
    """Test valid agent trust configuration."""
    print("Testing valid agent trust...")
    config = {
        "author": "test@example.com",
        "deployment": {},
        "agent_trust": {
            "required_verification_level": "admin",
            "max_agent_hierarchy_depth": 5,
            "allowed_origins": ["https://example.com"],
        },
    }
    result = ConfigValidator.validate_and_process(config)
    assert result["agent_trust"]["required_verification_level"] == "admin"
    assert result["agent_trust"]["max_agent_hierarchy_depth"] == 5
    print("✓ Valid agent trust passed")

def test_agent_trust_invalid_level():
    """Test invalid verification level."""
    print("Testing invalid verification level...")
    config = {
        "author": "test@example.com",
        "deployment": {},
        "agent_trust": {
            "required_verification_level": "invalid_level",
            "max_agent_hierarchy_depth": 5,
        },
    }
    try:
        ConfigValidator.validate_and_process(config)
        print("✗ Should have raised ValueError")
        sys.exit(1)
    except ValueError as e:
        if "Invalid required_verification_level" in str(e):
            print("✓ Invalid level correctly rejected")
        else:
            print(f"✗ Wrong error: {e}")
            sys.exit(1)

def test_agent_trust_invalid_depth():
    """Test invalid hierarchy depth."""
    print("Testing invalid hierarchy depth...")
    config = {
        "author": "test@example.com",
        "deployment": {},
        "agent_trust": {
            "required_verification_level": "admin",
            "max_agent_hierarchy_depth": 0,
        },
    }
    try:
        ConfigValidator.validate_and_process(config)
        print("✗ Should have raised ValueError")
        sys.exit(1)
    except ValueError as e:
        if "Invalid max_agent_hierarchy_depth" in str(e):
            print("✓ Invalid depth correctly rejected")
        else:
            print(f"✗ Wrong error: {e}")
            sys.exit(1)

def test_agent_trust_invalid_origin():
    """Test invalid origin format."""
    print("Testing invalid origin format...")
    config = {
        "author": "test@example.com",
        "deployment": {},
        "agent_trust": {
            "required_verification_level": "admin",
            "max_agent_hierarchy_depth": 5,
            "allowed_origins": ["invalid-origin"],
        },
    }
    try:
        ConfigValidator.validate_and_process(config)
        print("✗ Should have raised ValueError")
        sys.exit(1)
    except ValueError as e:
        if "Invalid origin format" in str(e):
            print("✓ Invalid origin correctly rejected")
        else:
            print(f"✗ Wrong error: {e}")
            sys.exit(1)

def test_defaults_applied():
    """Test that defaults are applied."""
    print("Testing defaults...")
    config = {"author": "test@example.com", "deployment": {}}
    result = ConfigValidator.validate_and_process(config)
    assert result["name"] == "bindu-agent"
    assert result["debug_mode"] is False
    assert result["telemetry"] is True
    print("✓ Defaults applied correctly")

if __name__ == "__main__":
    try:
        test_basic_validation()
        test_agent_trust_valid()
        test_agent_trust_invalid_level()
        test_agent_trust_invalid_depth()
        test_agent_trust_invalid_origin()
        test_defaults_applied()
        print("\n✅ All tests passed!")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
