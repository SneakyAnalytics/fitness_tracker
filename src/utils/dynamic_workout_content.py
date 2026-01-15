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
        self.used_stories: Set[str] = set()  # Track used story headlines
        self.content_type_counts: Dict[str, int] = {}  # Track how many times each type is used
        self.api_timeout = 3  # seconds
        self.gemini_api_key = os.getenv('GEMINI_API_KEY')
        self.news_api_key = os.getenv('NEWS_API_KEY')  # Free from newsapi.org
        
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
            ('quote', self._get_quote),
            ('joke', self._get_dad_joke),
            ('fact', self._get_fun_fact),
            ('encouragement', self._get_ai_generated_encouragement),
            ('number', self._get_number_fact),
            ('advice', self._get_advice_slip),
            ('affirmation', self._get_affirmation),
            ('chuck_norris', self._get_chuck_norris_fact),
            ('kanye', self._get_kanye_quote),
            ('science', self._get_science_news),
            ('research', self._get_arxiv_paper),
            ('wikipedia', self._get_wikipedia_today),
        ]
        
        # Randomize order to vary content types
        random.shuffle(content_getters)
        
        # Try each API until one works - retry up to 3 times if needed
        max_attempts = 3
        max_per_type = 3  # Limit each content type to 3 appearances per workout
        
        for attempt in range(max_attempts):
            for content_type, getter in content_getters:
                # Skip if we've used this type too many times already
                if self.content_type_counts.get(content_type, 0) >= max_per_type:
                    continue
                    
                try:
                    message = getter()
                    if message and message not in self.used_messages:
                        self.used_messages.add(message)
                        # Track content type usage
                        self.content_type_counts[content_type] = self.content_type_counts.get(content_type, 0) + 1
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
        
        # Backup: Try ZenQuotes API
        try:
            response = requests.get(
                'https://zenquotes.io/api/random',
                timeout=self.api_timeout
            )
            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    quote = data[0]['q']
                    author = data[0].get('a', 'Unknown')
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
    
    def get_story_with_summary(self) -> Optional[tuple[str, str]]:
        """Get a news/science story headline + AI-generated summary as a pair.
        
        This tries multiple sources:
        1. Current events from News API (if API key available)
        2. Science headlines from Hacker News
        3. Research papers from arXiv
        
        Returns: (headline_text, summary_text) or None
        """
        # Try to get a story from various sources
        story_data = None
        
        # Priority 1: News API for current events (most interesting/relevant)
        if self.news_api_key:
            story_data = self._get_news_api_story()
        
        # Priority 2: Science headlines from Hacker News
        if not story_data:
            story_data = self._get_science_headline_full()
        
        # Priority 3: Research paper from arXiv
        if not story_data:
            story_data = self._get_arxiv_story_full()
        
        # If we got a story, generate AI summary (with fallback)
        if story_data:
            headline, description = story_data
            
            # Check if already used
            if headline in self.used_stories:
                return None
            
            # Try AI summary first
            summary = self._generate_story_summary(headline, description)
            
            # Fallback: Create simple summary from description if AI unavailable
            if not summary:
                summary = self._create_simple_summary(description)
            
            if summary:
                self.used_stories.add(headline)
                self.used_messages.add(headline)
                self.used_messages.add(summary)
                return (headline, summary)
        
        return None
    
    # REMOVED: _get_cycling_fact
    # User doesn't want canned/static cycling facts - they want fresh API content only
    
    def _get_number_fact(self) -> Optional[str]:
        """Get random number fact from Numbers API"""
        # Numbers API is often slow/down, so try alternatives
        
        # Try Random Useless Facts as backup (often includes numbers)
        try:
            response = requests.get(
                'https://uselessfacts.jsph.pl/random.json?language=en',
                timeout=5  # Slightly longer timeout
            )
            if response.status_code == 200:
                data = response.json()
                fact = data['text']
                # Check if it has numbers in it
                if any(char.isdigit() for char in fact):
                    return f'🔢 {fact}'
        except:
            pass
        
        # Original Numbers API (often times out)
        try:
            response = requests.get(
                'http://numbersapi.com/random/trivia',
                timeout=5
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
                timeout=5  # Slightly longer timeout for this API
            )
            if response.status_code == 200:
                data = response.json()
                advice = data['slip']['advice']
                return f'💡 {advice}'
        except Exception as e:
            print(f"Advice API failed: {e}")
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
        """Get tech/science/innovation headlines from Hacker News"""
        try:
            # Hacker News API - tech, startups, science, innovation
            response = requests.get(
                'https://hacker-news.firebaseio.com/v0/topstories.json',
                timeout=self.api_timeout
            )
            if response.status_code == 200:
                story_ids = response.json()[:20]  # Get top 20 for more variety
                
                # Try multiple stories to find interesting ones
                for story_id in random.sample(story_ids, min(10, len(story_ids))):
                    story_response = requests.get(
                        f'https://hacker-news.firebaseio.com/v0/item/{story_id}.json',
                        timeout=self.api_timeout
                    )
                    if story_response.status_code == 200:
                        story = story_response.json()
                        title = story.get('title', '')
                        
                        # Broader filter - tech, science, innovation, startups, space, AI, etc.
                        interesting_keywords = [
                            'AI', 'tech', 'startup', 'science', 'research', 'study',
                            'discover', 'innovation', 'breakthrough', 'space', 'NASA',
                            'quantum', 'robot', 'crypto', 'blockchain', 'energy',
                            'climate', 'health', 'medical', 'brain', 'DNA', 'gene',
                            'solar', 'electric', 'battery', 'Mars', 'satellite',
                            'machine learning', 'neural', 'algorithm', 'data',
                            'breakthrough', 'invention', 'launch', 'open source'
                        ]
                        
                        # Also exclude boring stuff
                        boring_keywords = ['show hn:', 'ask hn:', 'hiring', 'jobs', 'resume']
                        
                        title_lower = title.lower()
                        
                        if any(boring.lower() in title_lower for boring in boring_keywords):
                            continue
                        
                        if any(keyword.lower() in title_lower for keyword in interesting_keywords):
                            if len(title) < 140:
                                # Vary the emoji based on topic
                                if any(word in title_lower for word in ['space', 'mars', 'nasa', 'satellite', 'rocket']):
                                    return f'🚀 Space/Tech: {title}'
                                elif any(word in title_lower for word in ['AI', 'robot', 'machine learning', 'neural']):
                                    return f'🤖 AI/Tech: {title}'
                                elif any(word in title_lower for word in ['energy', 'solar', 'battery', 'climate']):
                                    return f'⚡ Energy/Tech: {title}'
                                else:
                                    return f'🔬 Tech/Science: {title}'
        except:
            pass
        return None
    
    def _get_news_api_story(self) -> Optional[tuple[str, str]]:
        """Get trending news story from News API with description.
        
        Returns: (headline, description) tuple or None
        Get free API key from: https://newsapi.org/
        """
        if not self.news_api_key:
            return None
        
        try:
            # Get top headlines (general news, highly trafficked)
            response = requests.get(
                'https://newsapi.org/v2/top-headlines',
                params={
                    'apiKey': self.news_api_key,
                    'language': 'en',
                    'pageSize': 20,
                    'country': 'us'  # Or remove for international
                },
                timeout=self.api_timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                articles = data.get('articles', [])
                
                if articles:
                    # Pick random article from top 20
                    article = random.choice(articles)
                    title = article.get('title', '')
                    description = article.get('description', '')
                    
                    # Clean title (remove source suffix like " - CNN")
                    if ' - ' in title:
                        title = title.split(' - ')[0]
                    
                    if title and description and len(title) < 120:
                        headline = f'📰 News: {title}'
                        return (headline, description)
        except Exception as e:
            print(f"News API failed: {e}")
        
        return None
    
    def _get_science_headline_full(self) -> Optional[tuple[str, str]]:
        """Get science headline with URL/description for AI summary.
        
        Returns: (headline, description) tuple or None
        """
        try:
            response = requests.get(
                'https://hacker-news.firebaseio.com/v0/topstories.json',
                timeout=self.api_timeout
            )
            if response.status_code == 200:
                story_ids = response.json()[:20]  # Get top 20
                
                # Try to find a science story
                for story_id in random.sample(story_ids, min(10, len(story_ids))):
                    story_response = requests.get(
                        f'https://hacker-news.firebaseio.com/v0/item/{story_id}.json',
                        timeout=self.api_timeout
                    )
                    if story_response.status_code == 200:
                        story = story_response.json()
                        title = story.get('title', '')
                        url = story.get('url', '')
                        
                        # Filter for science-y keywords
                        science_keywords = ['study', 'research', 'science', 'discover', 'health', 'medical', 'brain', 'AI', 'tech']
                        if any(keyword.lower() in title.lower() for keyword in science_keywords):
                            if len(title) < 120 and url:
                                headline = f'🔬 Science: {title}'
                                # For Hacker News, we don't have full description
                                # Provide a helpful note for the fallback summary
                                description = f"A trending tech/science story: {title}. Check it out after your workout!"
                                return (headline, description)
        except:
            pass
        return None
    
    def _get_arxiv_story_full(self) -> Optional[tuple[str, str]]:
        """Get research paper with abstract for AI summary.
        
        Returns: (headline, abstract) tuple or None
        """
        try:
            categories = ['q-bio', 'physics', 'cs.AI', 'cs.LG']  # Biology, Physics, AI, Machine Learning
            category = random.choice(categories)
            
            response = requests.get(
                f'http://export.arxiv.org/api/query?search_query=cat:{category}&sortBy=submittedDate&sortOrder=descending&max_results=10',
                timeout=self.api_timeout
            )
            
            if response.status_code == 200:
                import xml.etree.ElementTree as ET
                root = ET.fromstring(response.content)
                
                entries = root.findall('{http://www.w3.org/2005/Atom}entry')
                if entries:
                    entry = random.choice(entries)
                    title_elem = entry.find('{http://www.w3.org/2005/Atom}title')
                    summary_elem = entry.find('{http://www.w3.org/2005/Atom}summary')
                    
                    if title_elem is not None and summary_elem is not None:
                        title = title_elem.text.strip().replace('\n', ' ')
                        abstract = summary_elem.text.strip().replace('\n', ' ')
                        
                        if len(title) < 120:
                            headline = f'📚 Research: {title}'
                            return (headline, abstract)
        except:
            pass
        return None
    
    def _generate_story_summary(self, headline: str, description: str) -> Optional[str]:
        """Use AI to generate a simple, understandable summary of a story.
        
        Args:
            headline: The story headline
            description: Story description or abstract
            
        Returns:
            Short summary text or None
        """
        if not self.gemini_api_key:
            return None
        
        try:
            import google.generativeai as genai
            genai.configure(api_key=self.gemini_api_key)
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            prompt = f"""Explain this story in simple, clear language that someone exercising can understand:

Headline: {headline}
Description: {description[:500]}

Provide a 1-2 sentence summary (max 150 characters) explaining what this story means in simple terms. Make it conversational and easy to understand while riding a bike.

Just return the summary, nothing else."""
            
            response = model.generate_content(prompt)
            summary = response.text.strip().strip('"\'')
            
            # Keep it concise
            if len(summary) > 200:
                summary = summary[:197] + '...'
            
            if summary:
                return f'💡 {summary}'
        except Exception as e:
            error_msg = str(e)
            if 'quota' in error_msg.lower() or 'resource_exhausted' in error_msg.lower():
                print(f"⚠️  Gemini API quota exhausted - falling back to simple summaries")
            else:
                print(f"AI summary generation failed: {error_msg[:100]}")
        
        return None
    
    def _create_simple_summary(self, description: str) -> Optional[str]:
        """Create a simple summary from description text when AI is unavailable.
        
        This is a fallback for when Gemini API quota is exhausted.
        Extracts the first 1-2 sentences from the description.
        
        Args:
            description: Story description or abstract
            
        Returns:
            Simple summary text or None
        """
        if not description:
            return None
        
        try:
            # Clean up the text
            text = description.strip()
            
            # Try to extract first 1-2 sentences
            sentences = []
            for delimiter in ['. ', '! ', '? ']:
                parts = text.split(delimiter)
                if len(parts) > 1:
                    sentences = parts
                    break
            
            if not sentences:
                # No sentence delimiters, just truncate
                summary = text[:150]
            else:
                # Take first sentence or two
                summary = sentences[0]
                if len(summary) < 80 and len(sentences) > 1:
                    summary += '. ' + sentences[1]
            
            # Truncate if still too long
            if len(summary) > 180:
                summary = summary[:177] + '...'
            
            return f'💡 {summary}'
        except Exception as e:
            print(f"Simple summary creation failed: {e}")
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
            # Wikipedia's REST API v1
            today = datetime.now()
            response = requests.get(
                f'https://en.wikipedia.org/api/rest_v1/feed/onthisday/all/{today.month:02d}/{today.day:02d}',
                headers={'User-Agent': 'FitnessTracker/1.0'},
                timeout=self.api_timeout
            )
            if response.status_code == 200:
                data = response.json()
                # Get a random event from today in history
                if 'events' in data and data['events']:
                    event = random.choice(data['events'][:10])  # Pick from top 10 events
                    year = event.get('year', '')
                    text = event.get('text', '')
                    if text and len(text) < 150:
                        return f'📅 On this day in {year}: {text}'
                
                # Try births or deaths
                if 'births' in data and data['births']:
                    person = random.choice(data['births'][:5])
                    year = person.get('year', '')
                    text = person.get('text', '')
                    if text and len(text) < 150:
                        return f'🎂 Born on this day in {year}: {text}'
        except Exception as e:
            print(f"Wikipedia Today API failed: {e}")
        
        # Backup: Try Today in History API
        try:
            today = datetime.now()
            response = requests.get(
                f'https://history.muffinlabs.com/date/{today.month}/{today.day}',
                timeout=self.api_timeout
            )
            if response.status_code == 200:
                data = response.json()
                if 'data' in data and 'Events' in data['data']:
                    events = data['data']['Events']
                    if events:
                        event = random.choice(events[:10])
                        year = event.get('year', '')
                        text = event.get('text', '')
                        if text and len(text) < 150:
                            return f'📅 {year}: {text}'
        except Exception as e:
            print(f"History API backup failed: {e}")
        
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
        self.used_stories.clear()
        self.content_type_counts.clear()  # Reset content type tracking


# Global instance
dynamic_content = DynamicWorkoutContent()
