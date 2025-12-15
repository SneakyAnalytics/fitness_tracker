"""
Dynamic Gemini Model Discovery
===============================

Automatically discovers available free Gemini models from Google's API
and provides smart fallback logic for high-volume operations.

This ensures the system stays working as Google updates their model lineup.
"""

import os
import google.generativeai as genai
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import json
from pathlib import Path
from google.api_core import exceptions


class GeminiModelDiscovery:
    """
    Dynamically discover and manage free Gemini models.
    
    Caches model list to avoid excessive API calls.
    """
    
    # Cache file location
    CACHE_FILE = Path(__file__).parent.parent.parent / 'data' / 'gemini_models_cache.json'
    CACHE_DURATION_HOURS = 24  # Refresh cache daily
    
    # Model tier preferences for free models
    FREE_MODEL_PREFERENCES = [
        'flash',      # Fast and free
        'pro',        # More capable
        'gemini',     # Generic
    ]
    
    # Known experimental/stable markers (prefer stable for production)
    STABILITY_PREFERENCES = [
        '',           # No suffix = stable
        '002',        # Versioned stable
        '001',        # Versioned stable
        'exp',        # Experimental (fast updates but may break)
        'latest',     # Latest (may change frequently)
    ]
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize model discovery.
        
        Args:
            api_key: Optional Gemini API key. Falls back to env var.
        """
        self.api_key = api_key or os.environ.get('GEMINI_API_KEY')
        if not self.api_key:
            raise ValueError("Gemini API key required. Set GEMINI_API_KEY environment variable.")
        
        genai.configure(api_key=self.api_key)
        self._cached_models: Optional[List[str]] = None
        self._cache_timestamp: Optional[datetime] = None
    
    def _load_cache(self) -> Optional[Dict[str, Any]]:
        """Load cached model list if fresh enough."""
        if not self.CACHE_FILE.exists():
            return None
        
        try:
            with open(self.CACHE_FILE, 'r') as f:
                cache = json.load(f)
            
            # Check if cache is fresh
            cache_time = datetime.fromisoformat(cache['timestamp'])
            if datetime.now() - cache_time < timedelta(hours=self.CACHE_DURATION_HOURS):
                return cache
            else:
                print(f"Model cache expired (age: {datetime.now() - cache_time})")
                return None
        except Exception as e:
            print(f"Error loading model cache: {e}")
            return None
    
    def _save_cache(self, models: List[str]):
        """Save model list to cache."""
        try:
            self.CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
            cache = {
                'timestamp': datetime.now().isoformat(),
                'models': models
            }
            with open(self.CACHE_FILE, 'w') as f:
                json.dump(cache, f, indent=2)
            print(f"✅ Cached {len(models)} models to {self.CACHE_FILE}")
        except Exception as e:
            print(f"⚠️  Could not save model cache: {e}")
    
    def discover_models(self, force_refresh: bool = False) -> List[str]:
        """
        Discover all available Gemini models from Google's API.
        
        Args:
            force_refresh: Bypass cache and fetch fresh list
            
        Returns:
            List of model names (e.g., ['gemini-1.5-flash', 'gemini-pro'])
        """
        # Try cache first
        if not force_refresh:
            cache = self._load_cache()
            if cache:
                print(f"📦 Using cached models ({len(cache['models'])} models)")
                return cache['models']
        
        print("🔍 Discovering available Gemini models...")
        
        try:
            # Query Google's API for available models
            available_models = []
            for model in genai.list_models():
                # Only include generative models (not embeddings, etc.)
                if 'generateContent' in model.supported_generation_methods:
                    model_name = model.name.replace('models/', '')
                    available_models.append(model_name)
            
            print(f"✅ Found {len(available_models)} generative models")
            
            # Save to cache
            self._save_cache(available_models)
            
            return available_models
        
        except Exception as e:
            print(f"❌ Error discovering models: {e}")
            
            # Fall back to hardcoded list if API fails
            fallback_models = [
                'gemini-1.5-flash-002',
                'gemini-1.5-flash',
                'gemini-1.5-flash-8b',
                'gemini-1.5-pro',
                'gemini-pro',
            ]
            print(f"⚠️  Using fallback model list ({len(fallback_models)} models)")
            return fallback_models
    
    def get_free_models(self, force_refresh: bool = False) -> List[str]:
        """
        Get list of free Gemini models, sorted by preference.
        
        Prioritizes:
        1. Stable versions over experimental
        2. Flash (fast) over Pro (slower but more capable)
        3. Newer versions over older
        
        Args:
            force_refresh: Bypass cache and fetch fresh list
            
        Returns:
            Sorted list of free model names
        """
        all_models = self.discover_models(force_refresh)
        
        # Filter for models that are likely free
        # Free tier usually includes: flash variants, pro (base), gemini-pro
        free_models = [
            m for m in all_models
            if any(tier in m.lower() for tier in ['flash', 'pro', 'gemini'])
            and 'vision' not in m.lower()  # Vision models may have different pricing
        ]
        
        # Score and sort models
        scored_models = []
        for model in free_models:
            score = self._score_model_preference(model)
            scored_models.append((score, model))
        
        # Sort by score (higher is better) and return model names
        scored_models.sort(reverse=True)
        sorted_models = [model for _, model in scored_models]
        
        print(f"📊 Prioritized {len(sorted_models)} free models:")
        for i, model in enumerate(sorted_models[:5], 1):
            print(f"   {i}. {model}")
        if len(sorted_models) > 5:
            print(f"   ... and {len(sorted_models) - 5} more")
        
        return sorted_models
    
    def _score_model_preference(self, model_name: str) -> int:
        """
        Score a model based on our preferences.
        Higher score = higher preference.
        """
        score = 0
        model_lower = model_name.lower()
        
        # Prefer flash over pro (flash is faster and free)
        if 'flash' in model_lower:
            score += 100
        elif 'pro' in model_lower:
            score += 50
        
        # Prefer stable over experimental
        if 'exp' in model_lower or 'experimental' in model_lower:
            score += 10  # Still usable but lower priority
        else:
            score += 50  # Stable
        
        # Prefer versioned models (e.g., -002, -001)
        if '-002' in model_lower:
            score += 30
        elif '-001' in model_lower:
            score += 20
        
        # Prefer newer model families
        if '2.0' in model_lower or '2-0' in model_lower:
            score += 40
        elif '1.5' in model_lower or '1-5' in model_lower:
            score += 30
        elif '1.0' in model_lower or '1-0' in model_lower:
            score += 10
        
        # Prefer 8b (lightweight) for high-volume tasks
        if '8b' in model_lower:
            score += 25
        
        return score
    
    def test_model_availability(self, model_name: str) -> bool:
        """
        Test if a specific model is available and working.
        
        Args:
            model_name: Name of model to test
            
        Returns:
            True if model works, False otherwise
        """
        try:
            model = genai.GenerativeModel(model_name)
            # Simple test prompt
            response = model.generate_content("Say 'OK' if you're working")
            return bool(response.text)
        except exceptions.InvalidArgument:
            print(f"⚠️  Model {model_name} not available")
            return False
        except exceptions.ResourceExhausted:
            print(f"⚠️  Model {model_name} quota exhausted")
            return False
        except Exception as e:
            print(f"⚠️  Model {model_name} test failed: {e}")
            return False
    
    def get_working_model(self, force_refresh: bool = False) -> Optional[str]:
        """
        Get the first working free model.
        
        Tests models in priority order and returns the first one that works.
        
        Args:
            force_refresh: Bypass cache and fetch fresh list
            
        Returns:
            Name of working model or None if all failed
        """
        free_models = self.get_free_models(force_refresh)
        
        print("🧪 Testing models for availability...")
        for model_name in free_models:
            print(f"   Testing {model_name}...", end=" ")
            if self.test_model_availability(model_name):
                print("✅ Working!")
                return model_name
            else:
                print("❌ Failed")
        
        print("❌ No working models found")
        return None


def get_best_free_models(max_models: int = 7, force_refresh: bool = False) -> List[str]:
    """
    Convenience function to get best free models for use in FitFileAnalyzer.
    
    Args:
        max_models: Maximum number of models to return
        force_refresh: Bypass cache and fetch fresh list
        
    Returns:
        List of model names sorted by preference
    """
    try:
        discovery = GeminiModelDiscovery()
        free_models = discovery.get_free_models(force_refresh)
        return free_models[:max_models]
    except Exception as e:
        print(f"⚠️  Model discovery failed: {e}")
        # Fallback to hardcoded list
        return [
            'gemini-1.5-flash-002',
            'gemini-1.5-flash',
            'gemini-1.5-flash-8b',
            'gemini-2.0-flash-exp',
            'gemini-1.5-pro',
            'gemini-pro',
        ][:max_models]


if __name__ == "__main__":
    """Test the model discovery system"""
    print("=" * 60)
    print("GEMINI MODEL DISCOVERY TEST")
    print("=" * 60)
    
    discovery = GeminiModelDiscovery()
    
    print("\n1. Discovering all models...")
    all_models = discovery.discover_models(force_refresh=True)
    
    print("\n2. Getting free models...")
    free_models = discovery.get_free_models()
    
    print("\n3. Finding working model...")
    working_model = discovery.get_working_model()
    if working_model:
        print(f"\n✅ Best working model: {working_model}")
    else:
        print("\n❌ No working models found!")
