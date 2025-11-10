# src/utils/dynamic_workout_content.py

import json
import random
import requests
from typing import Dict, Any, List, Optional, Set
from datetime import datetime
import hashlib
import time
import calendar

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
        
        # Daily special content - date-based rotation
        self.daily_jokes = [
            "Why don't cyclists ever get lost? Because they always know which way is up-hill! 🚵‍♂️",
            "What's a cyclist's favorite type of music? Anything with a good beat per minute! 🎵",
            "Why did the cyclist bring a ladder to the race? To get over the competition! 🪜",
            "What do you call a cyclist who doesn't wear lycra? Underdressed! 👕",
            "Why don't cyclists ever retire? Because they can't stop pedaling! 🔄",
            "What's the hardest part about cycling? Telling your spouse how much your bike cost! 💰",
            "Why did the cyclist cross the road? To get to the bike shop on the other side! 🚴‍♂️",
            "What do you call a cyclist's favorite dessert? Spoke-cake! 🎂",
            "Why don't cyclists make good comedians? Their timing is always off the chain! ⛓️",
            "What's a cyclist's favorite math? Geometry - they love acute angles! 📐"
        ]
        
        self.fitness_facts = [
            "💪 Daily Fact: Your heart is a muscle that gets stronger with every workout!",
            "🧠 Daily Fact: Exercise increases BDNF, literally growing new brain cells!",
            "🔥 Daily Fact: Your metabolism stays elevated for up to 24 hours after intense exercise!",
            "💨 Daily Fact: Elite cyclists can consume 8 liters of oxygen per minute!",
            "⚡ Daily Fact: Muscle fibers can contract in just 50 milliseconds!",
            "🏆 Daily Fact: Regular exercise can add 3-7 years to your lifespan!",
            "🎯 Daily Fact: Your body burns calories 15x faster during exercise than at rest!",
            "🔋 Daily Fact: Mitochondria (cellular powerhouses) increase 40% with training!",
            "🌟 Daily Fact: Exercise releases endorphins that are 200x more powerful than morphine!",
            "💎 Daily Fact: Bone density increases with resistance training at any age!"
        ]
        
        self.cycling_history = [
            "🚴 Cycling History: The first bicycle race was held in Paris in 1868!",
            "📜 Cycling History: The Tour de France was created in 1903 to sell newspapers!",
            "🏅 Cycling History: The Olympic cycling track has a 42-degree banking angle!",
            "⚙️ Cycling History: The derailleur wasn't allowed in Tour de France until 1937!",
            "🌍 Cycling History: The first bicycle world championship was held in 1893!",
            "👑 Cycling History: Eddy Merckx won 525 races in his career - simply 'The Cannibal'!",
            "🎪 Cycling History: The first indoor cycling track was built in 1869!",
            "🇺🇸 Cycling History: The first American Tour de France winner was Greg LeMond in 1985!",
            "🚴‍♀️ Cycling History: Women's cycling became Olympic in 1984!",
            "⏰ Cycling History: The hour record has been broken over 50 times since 1893!"
        ]
        
        self.this_day_in_sports = [
            "🏆 Sports History: Muhammad Ali won his first heavyweight title on this day in history!",
            "⚽ Sports History: The first FIFA World Cup match was played in 1930!",
            "🏀 Sports History: Basketball was invented by Dr. James Naismith in 1891!",
            "🏈 Sports History: The first Super Bowl was played in 1967!",
            "⚾ Sports History: Babe Ruth hit his first home run on this day in 1915!",
            "🎾 Sports History: Wimbledon started as a croquet club in 1868!",
            "🏓 Sports History: Table tennis became an Olympic sport in 1988!",
            "🏊 Sports History: The first swimming pool was built in 1837!",
            "🏃 Sports History: The marathon distance was standardized in 1908!",
            "🥇 Sports History: The modern Olympics began in Athens in 1896!"
        ]
        
        self.motivational_mantras = [
            "🧘 Daily Mantra: 'I am stronger than my excuses.'",
            "🎯 Daily Mantra: 'Every rep, every mile, every breath makes me better.'",
            "💪 Daily Mantra: 'My body can do it. It's my mind I need to convince.'",
            "🔥 Daily Mantra: 'I don't train to be skinny. I train to be a badass.'",
            "🌟 Daily Mantra: 'The pain you feel today will be the strength you feel tomorrow.'",
            "⚡ Daily Mantra: 'Success is the sum of small efforts repeated daily.'",
            "🎨 Daily Mantra: 'My body is my masterpiece in progress.'",
            "🏆 Daily Mantra: 'Champions train when they don't feel like it.'",
            "🚀 Daily Mantra: 'I am not in competition with anyone but yesterday's me.'",
            "💎 Daily Mantra: 'Pressure makes diamonds. I choose to shine.'"
        ]
        
        self.training_wisdom = [
            "👨‍🏫 Coach Wisdom: 'Consistency beats intensity when intensity can't be consistent.'",
            "📚 Training Tip: 'Your weakest day is still stronger than your strongest excuse.'",
            "🎓 Pro Insight: 'Recovery is not a reward for hard work. It IS the hard work.'",
            "🧠 Training Psychology: 'The body achieves what the mind believes.'",
            "📈 Performance Tip: 'Progress is not linear. Trust the process.'",
            "⚖️ Training Balance: 'Train smart today so you can train hard tomorrow.'",
            "🎯 Focus Tip: 'Don't just count your reps. Make your reps count.'",
            "🔄 Adaptation Rule: 'Your body adapts to what you do most often. Choose wisely.'",
            "💡 Training Secret: 'The magic happens outside your comfort zone.'",
            "🏁 Performance Mindset: 'Every workout is a step towards your best self.'"
        ]
        
        self.weekend_motivation = [
            "🎉 Weekend Warrior: 'Saturday's sweat is Sunday's strength!'",
            "☀️ Weekend Vibes: 'Weekends are for adventures on two wheels!'",
            "🏞️ Weekend Goals: 'The best therapy is bike therapy!'",
            "💪 Weekend Mindset: 'Weekend warriors rest on Monday!'",
            "🚴‍♂️ Weekend Spirit: 'Life is a beautiful ride - especially on weekends!'",
            "🌅 Weekend Energy: 'Early weekend rides catch the best views!'",
            "🔋 Weekend Recharge: 'Weekends are for refilling the tank!'",
            "🎯 Weekend Focus: 'Play hard, recover harder!'",
            "🌟 Weekend Magic: 'Weekend miles are smile miles!'",
            "🏆 Weekend Achievement: 'Making weekends count, one pedal at a time!'"
        ]
    
    def get_fresh_content(self, context: str, workout_type: str = "", 
                         interval_name: str = "", duration: int = 0, 
                         workout_date: Optional[datetime] = None) -> str:
        """
        Get fresh, contextually appropriate content with anti-repetition logic.
        
        Args:
            context: Type of message (welcome, recovery, intensity, encouragement, humor, science, closing, daily_special)
            workout_type: Type of workout (bike, run, etc.)
            interval_name: Name of current interval
            duration: Duration of current interval in seconds
            workout_date: Optional specific date for the workout (for daily special content)
            
        Returns:
            Fresh, contextually appropriate message
        """
        
        # Handle daily special content
        if context == "daily_special":
            return self.get_daily_special_content(workout_date)
        
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

    def get_daily_special_content(self, target_date: Optional[datetime] = None) -> str:
        """
        Get special daily content that rotates based on the date.
        Each day of the year gets a different combination of content types.
        
        Args:
            target_date: Optional specific date for content. If None, uses current date.
        """
        if target_date is None:
            target_date = datetime.now()
        
        day_of_year = target_date.timetuple().tm_yday
        day_name = target_date.strftime("%A")
        
        # Create a seed based on the date for consistent daily content
        random.seed(day_of_year + target_date.year)
        
        # Determine content type based on day of week and day of year
        content_type = self._get_daily_content_type(day_of_year, day_name)
        
        try:
            if content_type == "joke":
                content = self._get_daily_joke_with_api() or self._get_daily_joke(target_date)
            elif content_type == "fact":
                content = self._get_daily_fact_with_api() or self._get_daily_fact(target_date)
            elif content_type == "history":
                content = self._get_daily_history_with_api(target_date) or self._get_daily_history(target_date)
            elif content_type == "mantra":
                content = self._get_daily_mantra(target_date)
            elif content_type == "wisdom":
                content = self._get_daily_wisdom(target_date)
            elif content_type == "weekend":
                content = self._get_weekend_content(target_date)
            else:
                content = self._get_daily_fact(target_date)
                
        except Exception as e:
            print(f"Error getting daily special content: {e}")
            content = self._get_daily_fact(target_date)
        
        # Reset random seed to current time
        random.seed()
        
        return f"🗓️ Daily Special: {content}"
    
    def _get_daily_content_type(self, day_of_year: int, day_name: str) -> str:
        """Determine what type of daily content to show"""
        
        # Weekend content on weekends
        if day_name in ["Saturday", "Sunday"]:
            return "weekend"
        
        # Rotation based on day of year - ensure each day gets unique content type
        content_cycle = day_of_year % 7
        
        if content_cycle == 0:
            return "joke"
        elif content_cycle == 1:
            return "fact"
        elif content_cycle == 2:
            return "history"
        elif content_cycle == 3:
            return "mantra"
        elif content_cycle == 4:
            return "wisdom"
        elif content_cycle == 5:
            return "joke"  # Second joke day for variety
        else:  # content_cycle == 6
            return "history"  # Second history day instead of repeating fact
    
    def _get_daily_joke_with_api(self, target_date: Optional[datetime] = None) -> Optional[str]:
        """Try to get joke from API - prefer fresh API content over static"""
        try:
            # Try JokesAPI (free, no key required) - make multiple attempts for variety
            for _ in range(3):  # Try up to 3 times for different jokes
                response = requests.get("https://v2.jokeapi.dev/joke/Programming,Miscellaneous?blacklistFlags=nsfw,religious,political,racist,sexist,explicit&type=single", timeout=3)
                if response.status_code == 200:
                    data = response.json()
                    if not data.get('error') and data.get('joke'):
                        joke = data.get('joke')
                        if len(joke) < 120:  # Keep it concise for workout display
                            return f"😂 {joke}"
        except Exception:
            pass
        return None
    
    def _get_daily_joke(self, target_date: Optional[datetime] = None) -> str:
        """Get curated daily joke"""
        if target_date is None:
            target_date = datetime.now()
        joke_index = target_date.timetuple().tm_yday % len(self.daily_jokes)
        return self.daily_jokes[joke_index]
    
    def _get_daily_fact_with_api(self, target_date: Optional[datetime] = None) -> Optional[str]:
        """Try to get fact from API - prefer fresh API content"""
        try:
            # Try NumbersAPI for interesting facts - make multiple attempts for variety
            for _ in range(3):  # Try up to 3 times for different facts
                response = requests.get("http://numbersapi.com/random/trivia", timeout=3)
                if response.status_code == 200:
                    fact = response.text.strip()
                    if len(fact) < 120:  # Keep it concise for workout display
                        return f"🤓 Random Fact: {fact}"
        except Exception:
            pass
        return None
    
    def _get_daily_fact(self, target_date: Optional[datetime] = None) -> str:
        """Get curated daily fitness fact"""
        if target_date is None:
            target_date = datetime.now()
        fact_index = target_date.timetuple().tm_yday % len(self.fitness_facts)
        return self.fitness_facts[fact_index]
    
    def _get_daily_history_with_api(self, target_date: Optional[datetime] = None) -> Optional[str]:
        """Try to get historical fact from API"""
        try:
            if target_date is None:
                target_date = datetime.now()
            month = target_date.month
            day = target_date.day
            
            # Try Wikipedia API for "On This Day"
            url = f"https://en.wikipedia.org/api/rest_v1/feed/onthisday/events/{month}/{day}"
            response = requests.get(url, timeout=3)
            if response.status_code == 200:
                data = response.json()
                events = data.get('events', [])
                if events:
                    # Get a random recent event
                    recent_events = [e for e in events if e.get('year', 0) > 1800]
                    if recent_events:
                        event = random.choice(recent_events[:5])  # Pick from top 5 recent events
                        year = event.get('year')
                        text = event.get('text', '')
                        if text and len(text) < 100:
                            return f"📅 On This Day ({year}): {text}"
        except Exception:
            pass
        return None
    
    def _get_daily_history(self, target_date: Optional[datetime] = None) -> str:
        """Get curated daily cycling history"""
        if target_date is None:
            target_date = datetime.now()
        history_index = target_date.timetuple().tm_yday % len(self.cycling_history)
        return self.cycling_history[history_index]
    
    def _get_daily_mantra(self, target_date: Optional[datetime] = None) -> str:
        """Get daily motivational mantra"""
        if target_date is None:
            target_date = datetime.now()
        mantra_index = target_date.timetuple().tm_yday % len(self.motivational_mantras)
        return self.motivational_mantras[mantra_index]
    
    def _get_daily_wisdom(self, target_date: Optional[datetime] = None) -> str:
        """Get daily training wisdom"""
        if target_date is None:
            target_date = datetime.now()
        wisdom_index = target_date.timetuple().tm_yday % len(self.training_wisdom)
        return self.training_wisdom[wisdom_index]
    
    def _get_weekend_content(self, target_date: Optional[datetime] = None) -> str:
        """Get weekend-specific content"""
        if target_date is None:
            target_date = datetime.now()
        weekend_index = target_date.timetuple().tm_yday % len(self.weekend_motivation)
        return self.weekend_motivation[weekend_index]


# Global instance for workout generation
dynamic_content = DynamicWorkoutContent()