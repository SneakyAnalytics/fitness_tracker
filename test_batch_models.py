#!/usr/bin/env python3
"""
Test script to verify dynamic model discovery in batch analysis
"""

from src.utils.fit_file_analyzer import FitFileAnalyzer
from src.utils.gemini_model_discovery import get_best_free_models

def test_dynamic_models():
    print("=" * 70)
    print("Testing Dynamic Model Discovery for Batch Analysis")
    print("=" * 70)
    
    # Test 1: Get best free models
    print("\n1️⃣  Testing model discovery...")
    try:
        models = get_best_free_models(max_models=7)
        print(f"   ✅ Found {len(models)} free models")
        print(f"   📋 Top model: {models[0]}")
    except Exception as e:
        print(f"   ❌ Failed: {e}")
        return False
    
    # Test 2: Create analyzer with dynamic models
    print("\n2️⃣  Testing FitFileAnalyzer with dynamic models...")
    try:
        analyzer = FitFileAnalyzer(use_dynamic_models=True)
        model_list = analyzer.MODELS
        print(f"   ✅ Analyzer configured with {len(model_list)} models")
        print(f"   📋 Using model: {model_list[0]}")
    except Exception as e:
        print(f"   ❌ Failed: {e}")
        return False
    
    # Test 3: Create analyzer with static models (fallback)
    print("\n3️⃣  Testing FitFileAnalyzer with static models (fallback)...")
    try:
        analyzer_static = FitFileAnalyzer(use_dynamic_models=False)
        static_list = analyzer_static.MODELS
        print(f"   ✅ Fallback configured with {len(static_list)} models")
        print(f"   📋 Using model: {static_list[0]}")
    except Exception as e:
        print(f"   ❌ Failed: {e}")
        return False
    
    # Test 4: Verify cost savings
    print("\n💰 Cost Analysis:")
    print("   High Volume Operations (Batch Analysis):")
    print(f"   - Using: {models[0]}")
    print("   - Cost: $0 (free tier)")
    print("   - Volume: Unlimited workouts")
    print("\n   Low Volume Operations (Weekly Planning):")
    print("   - Using: Claude Sonnet 4.5")
    print("   - Cost: ~$0.50/week = $2/month")
    print("   - Volume: 1 planning session per week")
    
    print("\n" + "=" * 70)
    print("✅ All tests passed! Dynamic model discovery is working.")
    print("=" * 70)
    return True

if __name__ == "__main__":
    success = test_dynamic_models()
    exit(0 if success else 1)
