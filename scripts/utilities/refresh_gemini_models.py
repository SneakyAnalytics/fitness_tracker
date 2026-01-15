#!/usr/bin/env python3
"""
Quick script to refresh the Gemini model cache.

Run this if you're getting model errors - it will discover
the latest available free models from Google's API.
"""

from src.utils.gemini_model_discovery import GeminiModelDiscovery

if __name__ == "__main__":
    print("🔄 Refreshing Gemini model cache...\n")
    
    try:
        discovery = GeminiModelDiscovery()
        
        # Force refresh the cache
        models = discovery.discover_models(force_refresh=True)
        print(f"\n✅ Found {len(models)} total models")
        
        # Show free models
        free_models = discovery.get_free_models(force_refresh=True)
        print(f"\n📋 Top 10 free models:")
        for i, model in enumerate(free_models[:10], 1):
            print(f"   {i}. {model}")
        
        print(f"\n💾 Cache saved to: {discovery.CACHE_FILE}")
        print("✅ Model discovery complete!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
