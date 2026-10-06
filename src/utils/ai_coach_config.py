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
    """Available AI models for coaching (refreshed Oct 2026)."""
    # Google Gemini — rolling "-latest" aliases so these don't go stale.
    GEMINI_FREE = "gemini-flash-latest"            # free tier
    GEMINI_FLASH_LITE = "gemini-flash-lite-latest"  # fastest/cheapest
    GEMINI_PRO = "gemini-pro-latest"

    # Anthropic Claude — current generation. Note these models reject
    # temperature/top_p; use output_config.effort to trade cost for depth.
    CLAUDE_HAIKU = "claude-haiku-4-5"
    CLAUDE_SONNET = "claude-sonnet-5"
    CLAUDE_OPUS = "claude-opus-5"   # weekly recap + plan generation

    @property
    def is_claude(self) -> bool:
        return self.value.startswith("claude-")

    @property
    def is_gemini(self) -> bool:
        return self.value.startswith("gemini-")

    @property
    def supports_server_fallback(self) -> bool:
        """Opus 5 can re-run a refused request on a fallback model server-side."""
        return self.value.startswith("claude-opus-5")

    @property
    def supports_sampling_params(self) -> bool:
        """Sonnet 5 / Opus 5 return 400 if temperature or top_p is sent."""
        return not self.value.startswith(("claude-sonnet-5", "claude-opus-5"))


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


# Model pricing, USD per million tokens (Oct 2026). Source: anthropic.com/pricing
MODEL_COSTS = {
    AIModel.GEMINI_FREE: ModelCosts(input_cost=0.0, output_cost=0.0, provider="google"),
    AIModel.GEMINI_FLASH_LITE: ModelCosts(input_cost=0.0, output_cost=0.0, provider="google"),
    AIModel.GEMINI_PRO: ModelCosts(input_cost=1.25, output_cost=5.00, provider="google"),
    AIModel.CLAUDE_HAIKU: ModelCosts(input_cost=1.00, output_cost=5.00, provider="anthropic"),
    AIModel.CLAUDE_SONNET: ModelCosts(input_cost=2.00, output_cost=10.00, provider="anthropic"),
    AIModel.CLAUDE_OPUS: ModelCosts(input_cost=5.00, output_cost=25.00, provider="anthropic"),
}


class AICoachConfig:
    """Configuration manager for AI coaching system"""
    
    def __init__(self):
        # Check for both naming conventions
        self.gemini_api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        self.claude_api_key = os.getenv("CLAUDE_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
        # Weekly coaching defaults to the strongest model when a Claude key exists.
        self.default_model = AIModel.CLAUDE_OPUS if self.claude_api_key else AIModel.GEMINI_FREE
        
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
    print("  • Weekly recap + plan: Claude Opus 5")
    print("  • Workout narratives: Claude Sonnet 5")
    print("  • Free fallback: Gemini Flash")
    print()


if __name__ == "__main__":
    # Test the configuration
    print_model_comparison()
