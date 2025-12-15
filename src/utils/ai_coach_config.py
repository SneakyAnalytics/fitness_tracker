"""
🏋️ AI Coach Configuration Module
=================================
Manages AI model selection, API credentials, and cost tracking
for the automated coaching system.

🎯 Supports multiple AI models:
- Google Gemini (FREE tier available)
- Claude Haiku (cheap ~$0.25/week)
- Claude Sonnet 4 (high quality ~$1.00/week)
"""

import os
from typing import Dict, Optional
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file in project root
project_root = Path(__file__).parent.parent.parent
env_path = project_root / ".env"
load_dotenv(dotenv_path=env_path)


class AIModel(Enum):
    """Available AI models for coaching (Dec 2025)"""
    # Google Gemini (FREE tier available, recommended for cost-conscious use)
    GEMINI_FREE = "gemini-1.5-flash-002"  # Stable production, free tier
    GEMINI_FLASH = "gemini-1.5-flash"     # Stable fallback
    GEMINI_FLASH_8B = "gemini-1.5-flash-8b"  # Lightweight, fast
    GEMINI_PRO = "gemini-1.5-pro"         # Higher quality
    GEMINI_2_FLASH = "gemini-2.0-flash-exp"  # Latest experimental
    
    # Claude 3 series (older, being deprecated)
    CLAUDE_3_HAIKU = "claude-3-haiku-20240307"
    CLAUDE_3_5_HAIKU = "claude-3-5-haiku-20241022"
    
    # Claude 4 series (current generation)
    CLAUDE_HAIKU_4_5 = "claude-haiku-4-5-20251001"  # Fastest, cheapest
    CLAUDE_SONNET_4 = "claude-sonnet-4-20250514"    # Balanced
    CLAUDE_SONNET_4_5 = "claude-sonnet-4-5-20250929"  # Best quality/price
    CLAUDE_OPUS_4 = "claude-opus-4-20250514"        # Highest quality
    CLAUDE_OPUS_4_1 = "claude-opus-4-1-20250805"    # Latest flagship
    
    # Aliases for convenience
    CLAUDE_HAIKU = "claude-haiku-4-5-20251001"  # Latest Haiku
    CLAUDE_SONNET = "claude-sonnet-4-5-20250929"  # Latest Sonnet (RECOMMENDED)
    CLAUDE_OPUS = "claude-opus-4-1-20250805"    # Latest Opus


@dataclass
class ModelCosts:
    """Cost per million tokens (input/output)"""
    input_cost: float  # Per million input tokens
    output_cost: float  # Per million output tokens
    provider: str
    
    def estimate_weekly_cost(self, 
                            input_tokens: int = 15000, 
                            output_tokens: int = 5000) -> float:
        """
        Estimate cost for a typical weekly coaching session.
        
        Default estimates:
        - 15K input tokens (~20 pages of text: weekly summary + RAG context)
        - 5K output tokens (~7 pages: analysis + workout JSON)
        """
        input_cost = (input_tokens / 1_000_000) * self.input_cost
        output_cost = (output_tokens / 1_000_000) * self.output_cost
        return input_cost + output_cost


# Model pricing (as of Nov 2025)
# Source: https://www.anthropic.com/pricing
MODEL_COSTS = {
    # Google Gemini
    AIModel.GEMINI_FREE: ModelCosts(
        input_cost=0.0,
        output_cost=0.0,
        provider="google"
    ),
    AIModel.GEMINI_PRO: ModelCosts(
        input_cost=1.25,  # $1.25 per million
        output_cost=5.00,  # $5.00 per million
        provider="google"
    ),
    
    # Claude 3 series (older, being deprecated)
    AIModel.CLAUDE_3_HAIKU: ModelCosts(
        input_cost=0.25,  # $0.25 per million
        output_cost=1.25,  # $1.25 per million
        provider="anthropic"
    ),
    AIModel.CLAUDE_3_5_HAIKU: ModelCosts(
        input_cost=0.80,  # $0.80 per million
        output_cost=4.00,  # $4.00 per million
        provider="anthropic"
    ),
    
    # Claude 4 series (current generation)
    AIModel.CLAUDE_HAIKU_4_5: ModelCosts(
        input_cost=0.40,  # $0.40 per million (50% cheaper than 3.5!)
        output_cost=2.00,  # $2.00 per million
        provider="anthropic"
    ),
    AIModel.CLAUDE_SONNET_4: ModelCosts(
        input_cost=3.00,  # $3.00 per million
        output_cost=15.00,  # $15.00 per million
        provider="anthropic"
    ),
    AIModel.CLAUDE_SONNET_4_5: ModelCosts(
        input_cost=3.00,  # $3.00 per million (same as Sonnet 4!)
        output_cost=15.00,  # $15.00 per million
        provider="anthropic"
    ),
    AIModel.CLAUDE_OPUS_4: ModelCosts(
        input_cost=15.00,  # $15.00 per million
        output_cost=75.00,  # $75.00 per million
        provider="anthropic"
    ),
    AIModel.CLAUDE_OPUS_4_1: ModelCosts(
        input_cost=15.00,  # $15.00 per million
        output_cost=75.00,  # $75.00 per million
        provider="anthropic"
    ),
    
    # Convenience aliases (point to latest versions)
    AIModel.CLAUDE_HAIKU: ModelCosts(
        input_cost=0.40,  # $0.40 per million
        output_cost=2.00,  # $2.00 per million
        provider="anthropic"
    ),
    AIModel.CLAUDE_SONNET: ModelCosts(
        input_cost=3.00,  # $3.00 per million (BEST VALUE!)
        output_cost=15.00,  # $15.00 per million
        provider="anthropic"
    ),
    AIModel.CLAUDE_OPUS: ModelCosts(
        input_cost=15.00,  # $15.00 per million
        output_cost=75.00,  # $75.00 per million
        provider="anthropic"
    ),
}


class AICoachConfig:
    """Configuration manager for AI coaching system"""
    
    def __init__(self):
        # Check for both naming conventions
        self.gemini_api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        self.claude_api_key = os.getenv("CLAUDE_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
        
        # Default to free model for testing
        self.default_model = AIModel.GEMINI_FREE
        
    def get_api_key(self, model: AIModel) -> Optional[str]:
        """Get API key for specified model"""
        costs = MODEL_COSTS[model]
        
        if costs.provider == "google":
            return self.gemini_api_key
        elif costs.provider == "anthropic":
            return self.claude_api_key
        
        return None
    
    def validate_model_access(self, model: AIModel) -> tuple[bool, str]:
        """
        Check if we have valid API key for the model.
        
        Returns:
            (is_valid, message)
        """
        api_key = self.get_api_key(model)
        
        if not api_key:
            costs = MODEL_COSTS[model]
            return False, f"Missing {costs.provider.upper()} API key in .env file"
        
        return True, "API key found"
    
    def get_cost_estimate(self, model: AIModel) -> str:
        """Get formatted cost estimate for a model"""
        costs = MODEL_COSTS[model]
        weekly_cost = costs.estimate_weekly_cost()
        
        if weekly_cost == 0:
            return "FREE ✨"
        elif weekly_cost < 0.10:
            return f"~${weekly_cost:.3f}/week 💰"
        else:
            return f"~${weekly_cost:.2f}/week 💵"
    
    def get_model_info(self, model: AIModel) -> Dict:
        """Get comprehensive info about a model"""
        costs = MODEL_COSTS[model]
        is_valid, message = self.validate_model_access(model)
        
        return {
            "name": model.value,
            "provider": costs.provider,
            "cost_estimate": self.get_cost_estimate(model),
            "available": is_valid,
            "status_message": message,
            "input_cost": f"${costs.input_cost}/M tokens",
            "output_cost": f"${costs.output_cost}/M tokens",
        }
    
    def list_available_models(self) -> Dict[AIModel, Dict]:
        """Get info for all models"""
        return {
            model: self.get_model_info(model)
            for model in AIModel
        }


def print_model_comparison():
    """Print a comparison table of available models (for testing/docs)"""
    config = AICoachConfig()
    
    print("\n🏃‍♂️ AI Coach Model Comparison")
    print("=" * 80)
    print(f"{'Model':<25} {'Provider':<12} {'Weekly Cost':<15} {'Status'}")
    print("-" * 80)
    
    for model in AIModel:
        info = config.get_model_info(model)
        status = "✅ Ready" if info['available'] else "❌ " + info['status_message']
        print(f"{model.value:<25} {info['provider']:<12} {info['cost_estimate']:<15} {status}")
    
    print("=" * 80)
    print("\n💡 Recommendations:")
    print("  • Testing: Use Gemini Free (unlimited, good quality)")
    print("  • Production: Use Claude Sonnet 4 for highest quality coaching")
    print("  • Budget: Use Claude Haiku for good quality at low cost")
    print()


if __name__ == "__main__":
    # Test the configuration
    print_model_comparison()
