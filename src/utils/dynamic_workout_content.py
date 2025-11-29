# src/utils/dynamic_workout_content.py

import json
import random
import requests
from typing import Dict, Any, List, Optional, Set
from datetime import datetime
import os

class DynamicWorkoutContent:
    """
    Dynamic content generator for Zwift workout text events.
    Pulls fresh content from APIs to ensure ZERO repetition across workouts.
    """
    
    def __init__(self):
        self.used_messages: Set[str] = set()
        self.api_timeout = 3  # seconds
        self.gemini_api_key = os.getenv('GEMINI_API_KEY')
        
    def get_fresh_content(self, context: str = "general", workout_type: str = "", 
                         interval_name: str = "", duration: int = 0) -> str:
        """
        Get completely fresh, never-repeated content from various APIs.
        Falls back to minimal static content only if all APIs fail.
        
        Args:
            context: welcome, general, closing (not really used for API content)
            workout_type: Type of workout
            interval_name: Current interval name  
            duration: Duration in seconds
            
        Returns:
            Fresh, unique message
        """
        
        # Special handling for welcome/closing
        if context == "welcome":
            return self._get_welcome_message()
        elif context == "closing":
            return self._get_closing_message()
        elif context == "daily_special":
            return self._get_daily_special()
        
        # For all other contexts, pull from APIs in random order
        content_getters = [
            self._get_quote,
            self._get_dad_joke,
            self._get_fun_fact,
            self._get_trivia,
            self._get_cycling_fact,
            self._get_ai_generated_encouragement,
        ]
        
        # Randomize order to vary content types
        random.shuffle(content_getters)
        
        # Try each API until one works
        for getter in content_getters:
            try:
                message = getter()
                if message and message not in self.used_messages:
                    self.used_messages.add(message)
                    return message
            except Exception as e:
                print(f"API call failed: {e}")
                continue
        
        # If all APIs fail, use simple fallback
        return self._get_simple_fallback()
    
    def _get_quote(self) -> Optional[str]:
        """Get inspirational/motivational quote from Quotable API"""
        try:
            response = requests.get(
                'https://api.quotable.io/random?tags=inspirational|motivational|sports',
                timeout=self.api_timeout
            )
            if response.status_code == 200:
                data = response.json()
                quote = data['content']
                author = data.get('author', 'Unknown')
                return f'💬 "{quote}" - {author}'
        except:
            pass
        return None
    
    def _get_dad_joke(self) -> Optional[str]:
        """Get random dad joke from icanhazdadjoke API"""
        try:
            response = requests.get(
                'https://icanhazdadjoke.com/',
                headers={'Accept': 'application/json'},
                timeout=self.api_timeout
            )
            if response.status_code == 200:
                data = response.json()
                joke = data['joke']
                return f'😄 {joke}'
        except:
            pass
        
        # Try backup joke API
        try:
            response = requests.get(
                'https://official-joke-api.appspot.com/random_joke',
                timeout=self.api_timeout
            )
            if response.status_code == 200:
                data = response.json()
                setup = data['setup']
                punchline = data['punchline']
                return f'😄 {setup} ... {punchline}'
        except:
            pass
        
        return None
    
    def _get_fun_fact(self) -> Optional[str]:
        """Get random interesting fact from Useless Facts API"""
        try:
            response = requests.get(
                'https://uselessfacts.jsph.pl/random.json?language=en',
                timeout=self.api_timeout
            )
            if response.status_code == 200:
                data = response.json()
                fact = data['text']
                return f'🤓 Fun Fact: {fact}'
        except:
            pass
        return None
    
    def _get_trivia(self) -> Optional[str]:
        """Get sports trivia from Open Trivia Database - returns just the question"""
        try:
            response = requests.get(
                'https://opentdb.com/api.php?amount=1&category=21&type=multiple',  # Sports category
                timeout=self.api_timeout
            )
            if response.status_code == 200:
                data = response.json()
                if data['response_code'] == 0 and data['results']:
                    question = data['results'][0]['question']
                    answer = data['results'][0]['correct_answer']
                    # Decode HTML entities
                    import html
                    question = html.unescape(question)
                    answer = html.unescape(answer)
                    
                    # Store answer for later retrieval
                    self._pending_trivia_answer = f'🏆 Answer: {answer}'
                    
                    return f'🏆 Sports Trivia: {question}'
        except:
            pass
        return None
    
    def get_trivia_answer(self) -> Optional[str]:
        """Get the answer to the last trivia question"""
        if hasattr(self, '_pending_trivia_answer'):
            answer = self._pending_trivia_answer
            delattr(self, '_pending_trivia_answer')
            return answer
        return None
    
    def _get_cycling_fact(self) -> Optional[str]:
        """Get cycling-related facts (could use Wikipedia API or custom list)"""
        cycling_facts = [
            "🚴 Did you know? The fastest recorded speed on a bicycle is 183.9 mph (296 km/h)!",
            "🚴 Cycling fact: Your bike has more parts than a typical car engine!",
            "🚴 Pro cyclists can burn 8,000-10,000 calories during a Tour de France stage!",
            "🚴 The world record for distance cycled in 24 hours is 556 miles (895 km)!",
            "🚴 Cycling increases your lung capacity by up to 20%!",
            "🚴 The bicycle is the most efficient mode of human-powered transportation!",
            "🚴 Elite cyclists have resting heart rates as low as 28 bpm!",
            "🚴 Indoor cycling was invented in the 1990s as a winter training tool!",
            "🚴 Your quads are the largest muscle group working during cycling!",
            "🚴 Cycling can reduce your biological age by up to 10 years!",
        ]
        
        # Filter out used facts
        available_facts = [f for f in cycling_facts if f not in self.used_messages]
        if available_facts:
            return random.choice(available_facts)
        return None
    
    def _get_ai_generated_encouragement(self) -> Optional[str]:
        """Use Gemini AI to generate unique workout encouragement"""
        if not self.gemini_api_key:
            return None
        
        try:
            import google.generativeai as genai
            genai.configure(api_key=self.gemini_api_key)
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            prompt = """Generate ONE short, motivational message for a cyclist during an indoor training workout.
            
            Requirements:
            - Maximum 100 characters
            - Encouraging and energizing tone
            - No emojis
            - Not a quote from anyone famous
            - Should be about effort, power, or endurance
            
            Just return the message, nothing else."""
            
            response = model.generate_content(prompt)
            message = response.text.strip().strip('"\'')
            
            if len(message) < 150:  # Reasonable length check
                return f'💪 {message}'
        except Exception as e:
            print(f"Gemini API failed: {e}")
        
        return None
    
    def _get_welcome_message(self) -> str:
        """Get welcome message at workout start"""
        welcome_messages = [
            "🎯 Time to make this workout count!",
            "⚡ Let's transform this session into strength!",
            "🔥 Ready to build some power? Let's ride!",
            "💪 Another opportunity to become stronger - let's go!",
            "🚀 Workout mode: ACTIVATED. Let's crush this!",
        ]
        
        # Try to get AI-generated welcome
        try:
            if self.gemini_api_key:
                import google.generativeai as genai
                genai.configure(api_key=self.gemini_api_key)
                model = genai.GenerativeModel('gemini-1.5-flash')
                
                prompt = "Generate a short (max 80 chars), energizing welcome message for starting a cycling workout. No quotes, no emojis."
                response = model.generate_content(prompt)
                ai_message = response.text.strip().strip('"\'')
                if len(ai_message) < 100:
                    return f"🎯 {ai_message}"
        except:
            pass
        
        return random.choice(welcome_messages)
    
    def _get_closing_message(self) -> str:
        """Get closing message at workout end"""
        closing_messages = [
            "🎉 Workout complete! You're officially stronger than when you started!",
            "💪 Great work! Another quality session in the books!",
            "🏆 That's how champions train! Excellent effort today!",
            "✨ Session crushed! Your future self will thank you!",
            "🔥 Workout done! Time to recover and refuel!",
        ]
        return random.choice(closing_messages)
    
    def _get_daily_special(self) -> str:
        """Get date-based special content (used once per workout)"""
        today = datetime.now()
        
        # Try to get a dad joke
        joke = self._get_dad_joke()
        if joke:
            return joke
        
        # Fallback to date-based content
        day_of_year = today.timetuple().tm_yday
        
        daily_specials = [
            "🌟 Today's energy: Making excuses or making gains? You chose gains!",
            "⚡ Daily reminder: You're not just riding, you're evolving!",
            "🎯 Today's mission: Be 1% better than yesterday!",
            "💎 Daily truth: The only bad workout is the one that didn't happen!",
            "🔥 Today's goal: Make yourself proud!",
        ]
        
        # Rotate through list based on day of year
        return daily_specials[day_of_year % len(daily_specials)]
    
    def _get_simple_fallback(self) -> str:
        """Ultra-simple fallback if all APIs fail"""
        fallbacks = [
            "💪 Keep pushing - you've got this!",
            "🔥 Great effort - stay strong!",
            "⚡ You're doing amazing!",
            "🎯 Power through - almost there!",
            "🚀 Keep that energy up!",
            "💎 Digging deep - that's where growth happens!",
            "🏆 This is the work that pays off!",
            "⭐ Every pedal stroke counts!",
        ]
        return random.choice(fallbacks)
    
    def reset_used_messages(self):
        """Reset the used messages set (call between workouts)"""
        self.used_messages.clear()


# Global instance
dynamic_content = DynamicWorkoutContent()
