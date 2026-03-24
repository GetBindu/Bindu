#!/usr/bin/env python
"""Comprehensive validation of agent trust implementation."""

import json
from pathlib import Path
from bindu.penguin.config_validator import ConfigValidator

def test_all_scenarios():
    """Test various agent trust scenarios."""
    test_cases = [
        {
            "name": "Minimal Valid Config",
            "config": {
                "author": "test@example.com",
                "deployment": {},
                "agent_trust": {
                    "required_verification_level": "guest",
                    "max_agent_hierarchy_depth": 1
                }
            },
            "should_pass": True
        },
        {
            "name": "Full Config with All Fields",
            "config": {
                "author": "test@example.com",
                "deployment": {},
                "agent_trust": {
                    "identity_provider": "hydra",
                    "required_verification_level": "super_admin",
                    "allowed_origins": ["https://example.com", "https://*.example.com"],
                    "max_agent_hierarchy_depth": 10,
                    "trust_verification_required": True,
                    "certificate_required": True,
                    "metadata": {"key": "value"}
                }
            },
            "should_pass": True
        },
        {
            "name": "No Agent Trust (None)",
            "config": {
                "author": "test@example.com",
                "deployment": {},
                "agent_trust": None
            },
            "should_pass": True
        },
        {
            "name": "Invalid Verification Level",
            "config": {
                "author": "test@example.com",
                "deployment": {},
                "agent_trust": {
                    "required_verification_level": "invalid",
                    "max_agent_hierarchy_depth": 5
                }
            },
            "should_pass": False,
            "expected_error": "Invalid required_verification_level"
        },
        {
            "name": "Invalid Hierarchy Depth (Zero)",
            "config": {
                "author": "test@example.com",
                "deployment": {},
                "agent_trust": {
                    "required_verification_level": "admin",
                    "max_agent_hierarchy_depth": 0
                }
            },
            "should_pass": False,
            "expected_error": "Invalid max_agent_hierarchy_depth"
        },
        {
            "name": "Invalid Origin Format",
            "config": {
                "author": "test@example.com",
                "deployment": {},
                "agent_trust": {
                    "required_verification_level": "manager",
                    "allowed_origins": ["not-a-valid-url"],
                    "max_agent_hierarchy_depth": 5
                }
            },
            "should_pass": False,
            "expected_error": "Invalid origin format"
        },
        {
            "name": "All Valid Trust Levels",
            "config": {
                "author": "test@example.com",
                "deployment": {},
                "agent_trust": {
                    "required_verification_level": "admin",
                    "max_agent_hierarchy_depth": 5
                }
            },
            "should_pass": True,
            "validate_levels": True
        }
    ]
    
    passed = 0
    failed = 0
    
    print("=" * 70)
    print("AGENT TRUST CONFIGURATION VALIDATION TESTS")
    print("=" * 70)
    
    for test_case in test_cases:
        print(f"\n▶ {test_case['name']}")
        
        try:
            result = ConfigValidator.validate_and_process(test_case['config'])
            
            if test_case['should_pass']:
                print(f"  ✅ PASS - Configuration validated successfully")
                if 'agent_trust' in result and result['agent_trust']:
                    trust = result['agent_trust']
                    print(f"     - Level: {trust.get('required_verification_level', 'N/A')}")
                    print(f"     - Max Depth: {trust.get('max_agent_hierarchy_depth', 'N/A')}")
                passed += 1
            else:
                print(f"  ❌ FAIL - Should have raised error but passed")
                failed += 1
                
        except ValueError as e:
            if not test_case['should_pass']:
                if test_case.get('expected_error') in str(e):
                    print(f"  ✅ PASS - Correctly rejected with expected error")
                    passed += 1
                else:
                    print(f"  ❌ FAIL - Got wrong error: {e}")
                    failed += 1
            else:
                print(f"  ❌ FAIL - Unexpected error: {e}")
                failed += 1
    
    # Validate all trust levels
    print("\n▶ Testing All Valid Trust Levels")
    trust_levels = [
        "admin", "analyst", "auditor", "editor", "guest",
        "manager", "operator", "super_admin", "support", "viewer"
    ]
    
    level_pass = 0
    for level in trust_levels:
        config = {
            "author": "test@example.com",
            "deployment": {},
            "agent_trust": {
                "required_verification_level": level,
                "max_agent_hierarchy_depth": 5
            }
        }
        try:
            ConfigValidator.validate_and_process(config)
            print(f"  ✅ {level}")
            level_pass += 1
        except ValueError:
            print(f"  ❌ {level}")
    
    if level_pass == len(trust_levels):
        print(f"  ✅ All {level_pass} trust levels validated")
        passed += 1
    else:
        print(f"  ❌ Only {level_pass}/{len(trust_levels)} trust levels validated")
        failed += 1
    
    # Summary
    print("\n" + "=" * 70)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("=" * 70)
    
    return failed == 0

if __name__ == "__main__":
    import sys
    success = test_all_scenarios()
    sys.exit(0 if success else 1)
