# src/utils/dynamic_workout_content.py

import json
import random
import requests
from typing import Dict, Any, List, Optional, Set
from datetime import datetime
import hashlib
import time

class DynamicWorkoutContent:
    """
    Dynamic content generator for Zwift workout text events.
    Provides fresh, varied, and contextually appropriate messages.
    """
    
    def __init__(self):
        self.used_messages: Set[str] = set()
        self.content_cache = {}
        self.cache_expiry = 3600  # 1 hour cache
        
        # Fallback static content organized by context
        self.fallback_content = {
            "welcome": [
                "Welcome to your workout! Let's make this session amazing!",
                "Time to turn those legs into lightning! ⚡",
                "Ready to get stronger? Let's do this!",
                "Another day, another chance to become legendary!",
                "Welcome to the pain cave - population: YOU! 💪"
            ],
            "recovery": [
                "Recovery is where the magic happens - your muscles are rebuilding stronger!",
                "Easy does it - this is investment time, not ego time",
                "Think of this as money in the bank for your next hard session",
                "This might feel easy, but you're building mitochondria right now!",
                "Professional cyclists spend 80% of their time at this intensity",
                "Your future strong self is thanking you for this discipline right now",
                "Recovery rides build your aerobic engine - the foundation of all fitness!"
            ],
            "intensity": [
                "Time to show these watts who's boss!",
                "Remember: you're not just getting stronger, you're getting more awesome!",
                "This is where heroes are made - embrace the burn!",
                "Your competition is probably on the couch right now",
                "Every pedal stroke is making you faster than yesterday",
                "Pain is temporary, but PRs are forever!",
                "You've got this - your body can handle more than your mind thinks!",
                "Channel your inner Tour de France rider right now!"
            ],
            "encouragement": [
                "You're crushing it! Keep that power steady!",
                "Looking strong! This is exactly how champions train",
                "Halfway there - you're doing amazing!",
                "The hardest part is behind you now",
                "Push through - greatness is on the other side of discomfort",
                "Your endurance is building with every revolution",
                "Stay focused - you're stronger than you know!"
            ],
            "humor": [
                "Why don't cyclists ever get tired? Because they're always spinning! 🚴‍♂️",
                "Fun fact: You're currently burning enough calories to power a light bulb!",
                "Remember: suffering is optional, but so are PRs!",
                "Your bike computer is judging your watts... make it proud!",
                "Current mood: Turning breakfast into speed ⚡",
                "Plot twist: The bike is actually pedaling YOU!",
                "Breaking news: Local cyclist spotted working way too hard 📺"
            ],
            "science": [
                "Did you know? Your heart pumps 5x more blood during exercise!",
                "Fun fact: Elite cyclists can produce 1,500+ watts in a sprint!",
                "Science says: Every interval makes your mitochondria multiply!",
                "Your VO2max is literally increasing as we speak!",
                "Lactate threshold training = your new superpower",
                "Each pedal stroke recruits over 200 muscles!",
                "Your brain is releasing endorphins right... about... now!"
            ],
            "closing": [
                "Workout complete! You're officially more awesome than when you started! 🎉",
                "Another successful mission in the pain cave! Well done!",
                "That's how champions train! Excellent work today!",
                "Achievement unlocked: Stronger human! 💪",
                "Cool down complete. Time to refuel and recover like a pro!",
                "Session crushed! Your future self will thank you for this!",
                "Workout complete! Go celebrate with some quality carbs! 🥯"
            ]
        }
    
    def get_fresh_content(self, context: str, workout_type: str = "", 
                         interval_name: str = "", duration: int = 0) -> str:
        """
        Get fresh, contextually appropriate content with anti-repetition logic.
        
        Args:
            context: Type of message (welcome, recovery, intensity, encouragement, humor, science, closing)
            workout_type: Type of workout (bike, run, etc.)
            interval_name: Name of current interval
            duration: Duration of current interval in seconds
            
        Returns:
            Fresh, contextually appropriate message
        """
        
        # Try to get dynamic content first
        dynamic_content = self._get_dynamic_content(context, workout_type, interval_name, duration)
        if dynamic_content:
            return dynamic_content
        
        # Fallback to curated static content
        return self._get_fallback_content(context, interval_name, duration)
    
    def _get_dynamic_content(self, context: str, workout_type: str, 
                           interval_name: str, duration: int) -> Optional[str]:
        """Try to get fresh content from various APIs"""
        
        # Try different content sources based on context
        if context in ["humor", "encouragement"]:
            return self._get_inspirational_quote() or self._get_cycling_fact()
        elif context == "science":
            return self._get_cycling_fact() or self._get_fitness_tip()
        elif context in ["recovery", "intensity"]:
            return self._get_fitness_tip() or self._get_inspirational_quote()
        
        return None
    
    def _get_inspirational_quote(self) -> Optional[str]:
        """Get inspirational quote from API with caching"""
        cache_key = f"quotes_{datetime.now().strftime('%Y-%m-%d-%H')}"
        
        if cache_key in self.content_cache:
            quotes = self.content_cache[cache_key]
        else:
            try:
                # Try multiple quote APIs
                quotes = self._fetch_quotes_api()
                if quotes:
                    self.content_cache[cache_key] = quotes
                else:
                    return None
            except Exception as e:
                print(f"Quote API failed: {e}")
                return None
        
        # Select unused quote
        available_quotes = [q for q in quotes if q not in self.used_messages]
        if not available_quotes:
            # Reset used messages if we've exhausted all quotes
            self.used_messages.clear()
            available_quotes = quotes
        
        if available_quotes:
            quote = random.choice(available_quotes)
            self.used_messages.add(quote)
            return self._format_quote(quote)
        
        return None
    
    def _get_cycling_fact(self) -> Optional[str]:
        """Get cycling/fitness facts from API or curated list"""
        facts = [
            "Did you know? The Tour de France burns ~120,000 calories over 3 weeks!",
            "Fun fact: Cyclists have larger hearts than average humans!",
            "Science: High-intensity intervals boost mitochondrial density by 20%!",
            "Amazing: Your legs contain 50+ muscles working in perfect harmony!",
            "Research shows: Indoor training can be 40% more time-efficient!",
            "Incredible: Elite cyclists maintain 300W for 4+ hours straight!",
            "Biology fact: Exercise creates new brain cells in the hippocampus!",
            "Physics: You're converting chemical energy to kinetic energy at 25% efficiency!"
        ]
        
        available_facts = [f for f in facts if f not in self.used_messages]
        if not available_facts:
            self.used_messages.clear()
            available_facts = facts
        
        if available_facts:
            fact = random.choice(available_facts)
            self.used_messages.add(fact)
            return fact
        
        return None
    
    def _get_fitness_tip(self) -> Optional[str]:
        """Get contextual fitness tips"""
        tips = [
            "Pro tip: Focus on smooth, circular pedal strokes for efficiency!",
            "Coach advice: Breathe deeply - oxygen is your fuel right now!",
            "Training tip: Stay relaxed in your shoulders and grip!",
            "Performance hack: Visualize your power flowing through the pedals!",
            "Efficiency tip: Keep your cadence steady and smooth!",
            "Recovery wisdom: This easy pace is building your aerobic base!",
            "Power tip: Engage your core for better force transfer!",
            "Endurance secret: Consistent effort beats random heroics!"
        ]
        
        available_tips = [t for t in tips if t not in self.used_messages]
        if not available_tips:
            self.used_messages.clear()
            available_tips = tips
        
        if available_tips:
            tip = random.choice(available_tips)
            self.used_messages.add(tip)
            return tip
        
        return None
    
    def _fetch_quotes_api(self) -> Optional[List[str]]:
        """Fetch quotes from external API"""
        try:
            # Try ZenQuotes API (free, no key required)
            response = requests.get("https://zenquotes.io/api/quotes", timeout=3)
            if response.status_code == 200:
                data = response.json()
                return [f"{item['q']} - {item['a']}" for item in data if len(item['q']) < 80]
        except Exception as e:
            print(f"ZenQuotes API failed: {e}")
        
        try:
            # Try Quotable API as backup
            response = requests.get("https://api.quotable.io/quotes?limit=10&minLength=20&maxLength=80&tags=motivational|inspirational", timeout=3)
            if response.status_code == 200:
                data = response.json()
                return [f"{item['content']} - {item['author']}" for item in data['results']]
        except Exception as e:
            print(f"Quotable API failed: {e}")
        
        return None
    
    def _format_quote(self, quote: str) -> str:
        """Format quote for workout context"""
        # Add workout-specific context to quotes
        prefixes = [
            "Remember: ",
            "Inspiration: ",
            "Wisdom: ",
            "Motivation: ",
            "Mindset: "
        ]
        return f"{random.choice(prefixes)}{quote}"
    
    def _get_fallback_content(self, context: str, interval_name: str, duration: int) -> str:
        """Get fallback content from static arrays with anti-repetition"""
        
        # Determine the best context if not specified
        if not context or context == "general":
            context = self._determine_context(interval_name, duration)
        
        # Get content from appropriate fallback category
        content_pool = self.fallback_content.get(context, self.fallback_content["encouragement"])
        
        # Select unused message
        available_messages = [msg for msg in content_pool if msg not in self.used_messages]
        if not available_messages:
            # Reset if we've used everything
            self.used_messages.clear()
            available_messages = content_pool
        
        message = random.choice(available_messages)
        self.used_messages.add(message)
        return message
    
    def _determine_context(self, interval_name: str, duration: int) -> str:
        """Intelligently determine context from interval name and duration"""
        interval_lower = interval_name.lower()
        
        if "recovery" in interval_lower or "easy" in interval_lower or "cooldown" in interval_lower:
            return "recovery"
        elif any(word in interval_lower for word in ["interval", "vo2", "threshold", "sprint"]):
            return "intensity"
        elif duration > 600:  # Long intervals get science/facts
            return random.choice(["science", "encouragement"])
        else:
            return random.choice(["humor", "encouragement"])
    
    def reset_used_messages(self):
        """Reset the used messages set for a new workout"""
        self.used_messages.clear()
    
    def get_contextual_message_sequence(self, interval_name: str, duration: int) -> List[Dict[str, Any]]:
        """
        Get a sequence of contextually appropriate messages for an interval.
        
        Returns:
            List of message dictionaries with timeoffset and message content
        """
        messages = []
        
        # Start with interval name announcement
        if interval_name:
            messages.append({
                "timeoffset": 10,
                "message": interval_name
            })
        
        if duration <= 120:  # Short intervals
            return messages
        
        # 25% mark - Motivational/Technical
        time_25 = max(30, int(duration * 0.25))
        context_25 = "intensity" if "interval" in interval_name.lower() else "encouragement"
        messages.append({
            "timeoffset": time_25,
            "message": self.get_fresh_content(context_25, interval_name=interval_name, duration=duration)
        })
        
        # 50% mark - Humor/Facts (for longer intervals)
        if duration > 300:
            time_50 = max(60, int(duration * 0.5))
            context_50 = random.choice(["humor", "science"])
            messages.append({
                "timeoffset": time_50,
                "message": self.get_fresh_content(context_50, interval_name=interval_name, duration=duration)
            })
        
        # 80% mark - Encouragement/Push
        if duration > 180:
            time_80 = max(int(duration * 0.8), duration - 30)
            context_80 = "encouragement"
            messages.append({
                "timeoffset": time_80,
                "message": self.get_fresh_content(context_80, interval_name=interval_name, duration=duration)
            })
        
        return messages


# Global instance for workout generation
dynamic_content = DynamicWorkoutContent()