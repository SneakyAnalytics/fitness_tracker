"""
AI Coach Configuration Module

Manages AI model selection, API credentials, and cost tracking
for the automated coaching system.

Supported models:
- Google Gemini (FREE tier available)
- Claude Haiku 4.5 (fast, ~$0.025/week)
- Claude Sonnet 4.6 (best quality, ~$0.27/week) RECOMMENDED
- GitHub GPT-4o (FREE via GitHub token)
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
    """Available AI models for coaching (refreshed Sept 2026)"""
    # Google Gemini (FREE tier available, recommended for cost-conscious use)
    # Uses Google's rolling "-latest" aliases so this never goes stale again;
    # verified live against the Gemini API (see data/gemini_models_cache.json).
    GEMINI_FREE = "gemini-flash-latest"   # Rolling latest Flash, free tier
    GEMINI_FLASH_LITE = "gemini-flash-lite-latest"  # Lightweight, fastest/cheapest
    GEMINI_PRO = "gemini-pro-latest"      # Rolling latest Pro, higher quality

    # Claude 4 series (current generation)
    CLAUDE_HAIKU_4_5 = "claude-haiku-4-5-20251001"  # Fastest, cheapest
    CLAUDE_SONNET_4_6 = "claude-sonnet-4-6"          # Latest Sonnet (Mar 2026)
    CLAUDE_OPUS_4_6 = "claude-opus-4-6"             # Latest Opus (Mar 2026)

    # Aliases for convenience — always point to the latest released version
    CLAUDE_HAIKU = "claude-haiku-4-5-20251001"  # Latest Haiku (4.5)
    CLAUDE_SONNET = "claude-sonnet-4-6"          # Latest Sonnet (4.6) — RECOMMENDED
    CLAUDE_OPUS = "claude-opus-4-6"              # Latest Opus (4.6)

    # GitHub Models (FREE via GitHub Copilot / PAT token)
    # Uses OpenAI-compatible endpoint: https://models.inference.ai.azure.com
    # Note: Anthropic Claude is NOT available on GitHub Models — uses Azure OpenAI GPT-4o
    GITHUB_GPT4O_MINI = "github-gpt4o-mini"   # GPT-4o mini via GitHub Models (fast, free)
    GITHUB_GPT4O      = "github-gpt4o"        # GPT-4o via GitHub Models (best, free)


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
    AIModel.GEMINI_FLASH_LITE: ModelCosts(
        input_cost=0.0,
        output_cost=0.0,
        provider="google"
    ),
    AIModel.GEMINI_PRO: ModelCosts(
        input_cost=1.25,  # $1.25 per million
        output_cost=5.00,  # $5.00 per million
        provider="google"
    ),

    # Claude 4 series (current generation)
    AIModel.CLAUDE_HAIKU_4_5: ModelCosts(
        input_cost=0.40,  # $0.40 per million (50% cheaper than 3.5!)
        output_cost=2.00,  # $2.00 per million
        provider="anthropic"
    ),
    AIModel.CLAUDE_SONNET_4_6: ModelCosts(
        input_cost=3.00,  # $3.00 per million
        output_cost=15.00,  # $15.00 per million
        provider="anthropic"
    ),
    AIModel.CLAUDE_OPUS_4_6: ModelCosts(
        input_cost=5.00,   # $5.00 per million
        output_cost=25.00,  # $25.00 per million
        provider="anthropic"
    ),
    
    # Convenience aliases (point to latest versions)
    AIModel.CLAUDE_HAIKU: ModelCosts(
        input_cost=0.40,  # $0.40 per million
        output_cost=2.00,  # $2.00 per million
        provider="anthropic"
    ),
    AIModel.CLAUDE_SONNET: ModelCosts(
        input_cost=3.00,   # $3.00 per million — Sonnet 4.6 (BEST VALUE!)
        output_cost=15.00,  # $15.00 per million
        provider="anthropic"
    ),
    AIModel.CLAUDE_OPUS: ModelCosts(
        input_cost=5.00,   # $5.00 per million — Opus 4.6
        output_cost=25.00,  # $25.00 per million
        provider="anthropic"
    ),

    # GitHub Models — no direct token cost (covered by Copilot subscription)
    AIModel.GITHUB_GPT4O_MINI: ModelCosts(
        input_cost=0.0,
        output_cost=0.0,
        provider="github"
    ),
    AIModel.GITHUB_GPT4O: ModelCosts(
        input_cost=0.0,
        output_cost=0.0,
        provider="github"
    ),
}


class AICoachConfig:
    """Configuration manager for AI coaching system"""
    
    def __init__(self):
        # Check for both naming conventions
        self.gemini_api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        self.claude_api_key = os.getenv("CLAUDE_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
        self.github_token   = os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")

        # Default: prefer GitHub Copilot (free) when a token is available,
        # otherwise fall back to Gemini free tier.
        if self.github_token:
            self.default_model = AIModel.GITHUB_GPT4O
        else:
            self.default_model = AIModel.GEMINI_FREE
        
    def get_api_key(self, model: AIModel) -> Optional[str]:
        """Get API key for specified model"""
        costs = MODEL_COSTS[model]
        
        if costs.provider == "google":
            return self.gemini_api_key
        elif costs.provider == "anthropic":
            return self.claude_api_key
        elif costs.provider == "github":
            return self.github_token

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
