#!/usr/bin/env python
"""Test ConfigValidator with sample configs - direct module import."""

import sys
import json
from pathlib import Path

# Direct import to avoid circular dependencies
sys.path.insert(0, str(Path(__file__).parent))

from bindu.penguin.config_validator import ConfigValidator

def test_sample_config():
    """Test validation of sample config with trust configuration."""
    config_path = Path("examples/test_config_with_trust.json")
    
    if not config_path.exists():
        print(f"Error: Config file not found: {config_path}")
        return False
    
    print(f"Loading config from {config_path}...")
    with open(config_path, "r") as f:
        raw_config = json.load(f)
    
    try:
        print("Validating configuration...")
        result = ConfigValidator.validate_and_process(raw_config)
        
        print("✅ Configuration validation PASSED")
        print(f"   Name: {result['name']}")
        print(f"   Author: {result['author']}")
        print(f"   Trust Level: {result['agent_trust']['required_verification_level']}")
        print(f"   Max Hierarchy Depth: {result['agent_trust']['max_agent_hierarchy_depth']}")
        print(f"   Allowed Origins: {result['agent_trust']['allowed_origins']}")
        print(f"   Trust Verification Required: {result['agent_trust']['trust_verification_required']}")
        print(f"   Metadata: {result['agent_trust'].get('metadata', {})}")
        
        print("\n✅ CREATE BINDUFY CONFIG TEST")
        bindufy_config = ConfigValidator.create_bindufy_config(raw_config)
        print(f"   Storage: {bindufy_config['storage']}")
        print(f"   Scheduler: {bindufy_config['scheduler']}")
        print(f"   Deployment: {list(bindufy_config['deployment'].keys())}")
        
        return True
        
    except ValueError as e:
        print(f"❌ Validation failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_sample_config()
    sys.exit(0 if success else 1)
