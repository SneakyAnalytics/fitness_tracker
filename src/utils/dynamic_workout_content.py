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
        
        # For all other contexts, pull from APIs ONLY (no static fallbacks)
        content_getters = [
            self._get_quote,
            self._get_dad_joke,
            self._get_fun_fact,
            self._get_ai_generated_encouragement,
            self._get_number_fact,
            self._get_advice_slip,
            self._get_affirmation,
            self._get_chuck_norris_fact,
            self._get_kanye_quote,
            self._get_science_news,
            self._get_arxiv_paper,
            self._get_wikipedia_today,
        ]
        
        # Randomize order to vary content types
        random.shuffle(content_getters)
        
        # Try each API until one works - retry up to 3 times if needed
        max_attempts = 3
        for attempt in range(max_attempts):
            for getter in content_getters:
                try:
                    message = getter()
                    if message and message not in self.used_messages:
                        self.used_messages.add(message)
                        return message
                except Exception as e:
                    print(f"API call failed (attempt {attempt + 1}/{max_attempts}): {e}")
                    continue
        
        # If all APIs fail after retries, return simple encouragement (no canned facts)
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
    
    def get_trivia_pair(self) -> Optional[tuple[str, str]]:
        """Get sports trivia question AND answer as a pair to ensure they appear together"""
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
                    
                    # Return both as a tuple for guaranteed pairing
                    question_msg = f'🏆 Sports Trivia: {question}'
                    answer_msg = f'🏆 Answer: {answer}'
                    
                    # Mark both as used
                    self.used_messages.add(question_msg)
                    self.used_messages.add(answer_msg)
                    
                    return (question_msg, answer_msg)
        except Exception as e:
            print(f"Trivia API failed: {e}")
        return None
    
    # REMOVED: _get_cycling_fact
    # User doesn't want canned/static cycling facts - they want fresh API content only
    
    def _get_number_fact(self) -> Optional[str]:
        """Get random number fact from Numbers API"""
        try:
            response = requests.get(
                'http://numbersapi.com/random/trivia',
                timeout=self.api_timeout
            )
            if response.status_code == 200:
                fact = response.text
                return f'🔢 {fact}'
        except:
            pass
        return None
    
    def _get_advice_slip(self) -> Optional[str]:
        """Get random advice from Advice Slip API"""
        try:
            response = requests.get(
                'https://api.adviceslip.com/advice',
                timeout=self.api_timeout
            )
            if response.status_code == 200:
                data = response.json()
                advice = data['slip']['advice']
                return f'💡 {advice}'
        except:
            pass
        return None
    
    def _get_affirmation(self) -> Optional[str]:
        """Get positive affirmation"""
        try:
            response = requests.get(
                'https://www.affirmations.dev/',
                timeout=self.api_timeout
            )
            if response.status_code == 200:
                data = response.json()
                affirmation = data['affirmation']
                return f'✨ {affirmation}'
        except:
            pass
        return None
    
    def _get_chuck_norris_fact(self) -> Optional[str]:
        """Get Chuck Norris fact (usually funny/absurd)"""
        try:
            response = requests.get(
                'https://api.chucknorris.io/jokes/random',
                timeout=self.api_timeout
            )
            if response.status_code == 200:
                data = response.json()
                fact = data['value']
                # Keep it short and appropriate
                if len(fact) < 150:
                    return f'💥 {fact}'
        except:
            pass
        return None
    
    def _get_kanye_quote(self) -> Optional[str]:
        """Get Kanye West quote (often motivational/entertaining)"""
        try:
            response = requests.get(
                'https://api.kanye.rest/',
                timeout=self.api_timeout
            )
            if response.status_code == 200:
                data = response.json()
                quote = data['quote']
                return f'🎤 Kanye: "{quote}"'
        except:
            pass
        return None
    
    def _get_science_news(self) -> Optional[str]:
        """Get science news headlines from various sources"""
        try:
            # Try New York Times Science section (free API)
            # Note: For production, get free API key from https://developer.nytimes.com/
            # For now, try RSS feeds or other free sources
            
            # Hacker News API - often has science/research posts
            response = requests.get(
                'https://hacker-news.firebaseio.com/v0/topstories.json',
                timeout=self.api_timeout
            )
            if response.status_code == 200:
                story_ids = response.json()[:10]  # Get top 10
                # Get a random story from top 10
                story_id = random.choice(story_ids)
                story_response = requests.get(
                    f'https://hacker-news.firebaseio.com/v0/item/{story_id}.json',
                    timeout=self.api_timeout
                )
                if story_response.status_code == 200:
                    story = story_response.json()
                    title = story.get('title', '')
                    # Filter for science-y keywords
                    science_keywords = ['study', 'research', 'science', 'discover', 'health', 'medical', 'brain', 'AI', 'tech']
                    if any(keyword.lower() in title.lower() for keyword in science_keywords):
                        if len(title) < 120:
                            return f'🔬 Tech/Science: {title}'
        except:
            pass
        return None
    
    def _get_arxiv_paper(self) -> Optional[str]:
        """Get recent research paper title from arXiv"""
        try:
            # arXiv API - recent papers in health/biology/sports science
            categories = ['q-bio', 'physics', 'cs.AI']  # Biology, Physics, AI
            category = random.choice(categories)
            
            response = requests.get(
                f'http://export.arxiv.org/api/query?search_query=cat:{category}&sortBy=submittedDate&sortOrder=descending&max_results=20',
                timeout=self.api_timeout
            )
            if response.status_code == 200:
                import xml.etree.ElementTree as ET
                root = ET.fromstring(response.content)
                
                # Get random entry from results
                entries = root.findall('{http://www.w3.org/2005/Atom}entry')
                if entries:
                    entry = random.choice(entries)
                    title = entry.find('{http://www.w3.org/2005/Atom}title')
                    if title is not None:
                        title_text = title.text.strip().replace('\n', ' ')
                        if len(title_text) < 120:
                            return f'📚 Research: {title_text}'
        except:
            pass
        return None
    
    def _get_wikipedia_today(self) -> Optional[str]:
        """Get 'On This Day' from Wikipedia or featured article"""
        try:
            # Wikipedia's "On This Day" API
            today = datetime.now()
            response = requests.get(
                f'https://api.wikimedia.org/feed/v1/wikipedia/en/onthisday/all/{today.month}/{today.day}',
                timeout=self.api_timeout
            )
            if response.status_code == 200:
                data = response.json()
                # Get a random event from today in history
                if 'events' in data and data['events']:
                    event = random.choice(data['events'][:5])  # Pick from top 5 events
                    year = event.get('year', '')
                    text = event.get('text', '')
                    if text and len(text) < 120:
                        return f'📅 On this day in {year}: {text}'
                
                # Try featured article instead
                if 'selected' in data and data['selected']:
                    article = random.choice(data['selected'])
                    text = article.get('text', '')
                    if text and len(text) < 120:
                        return f'📖 {text}'
        except:
            pass
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
