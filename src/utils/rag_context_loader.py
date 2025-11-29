"""
📚 RAG Context Loader for AI Coaching
=====================================
Loads and manages cycling science knowledge base for AI coach prompts.

🎓 EDUCATIONAL NOTE - How RAG Works:
------------------------------------

**The Problem:**
- We have ~1500 lines of cycling science across 7 markdown files
- That's roughly 30,000-50,000 tokens
- AI models have context windows (100K-200K tokens for Gemini/Claude)
- But we also need room for: athlete data, coaching notes, conversation history
- Can't fit EVERYTHING in every prompt

**The Solution - RAG (Retrieval-Augmented Generation):**

1. **Chunking**: Break documents into logical pieces (sections, paragraphs)
   - Why? Smaller chunks = more precise retrieval
   - Example: Instead of entire "best practices" doc, just the "VO2max training" section
   
2. **Indexing**: Create searchable metadata for each chunk
   - Topic tags (e.g., "threshold", "periodization", "recovery")
   - Headers/titles
   - Key concepts
   
3. **Retrieval**: When AI coach needs knowledge, fetch ONLY relevant chunks
   - User asks about VO2max workouts → retrieve VO2max sections
   - Generating recovery week → retrieve recovery protocols
   - This keeps context small and focused
   
4. **Augmentation**: Add retrieved chunks to AI prompt
   - Original prompt: "Generate workout plan..."
   - Augmented: "Using this cycling science: [chunks]... Generate workout plan..."
   
5. **Generation**: AI creates response informed by specific knowledge

**Benefits:**
- Efficient token usage (only ~5K tokens instead of 50K)
- More relevant responses (AI sees exactly what it needs)
- Scalable (can add more docs without hitting limits)
- Explainable (we know which knowledge was used)

**Our Implementation:**
- Simple topic-based retrieval (no embeddings needed for structured docs)
- Hierarchical chunking (by headers)
- Smart defaults (always include JSON schema, some docs always loaded)
"""

import re
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass
from enum import Enum


class ChunkPriority(Enum):
    """Priority levels for knowledge chunks."""
    ALWAYS = 1      # Always include (e.g., JSON schema)
    HIGH = 2        # Include for most queries (e.g., core principles)
    MEDIUM = 3      # Include when topic matches
    LOW = 4         # Include only if specifically requested


@dataclass
class KnowledgeChunk:
    """
    A piece of knowledge from the RAG context.
    
    Why we need this structure:
    - source_file: Track where knowledge came from (for debugging/citations)
    - title: Human-readable identifier
    - content: The actual knowledge text
    - topics: Tags for retrieval (e.g., ["vo2max", "intervals", "high-intensity"])
    - priority: How important is this chunk?
    - token_estimate: Approximate tokens (for budgeting)
    """
    source_file: str
    title: str
    content: str
    topics: Set[str]
    priority: ChunkPriority
    token_estimate: int
    
    def matches_topics(self, query_topics: Set[str]) -> bool:
        """Check if this chunk is relevant to query topics."""
        return bool(self.topics.intersection(query_topics))


class RAGContextLoader:
    """
    Loads cycling science knowledge and provides smart retrieval.
    
    Educational walkthrough:
    1. Initialize: Load all markdown files into chunks
    2. Index: Tag each chunk with topics
    3. Retrieve: Get relevant chunks for a query
    4. Budget: Ensure we don't exceed token limits
    """
    
    def __init__(self, rag_dir: Optional[Path] = None):
        if rag_dir is None:
            project_root = Path(__file__).parent.parent.parent
            rag_dir = project_root / "data" / "rag_context"
        
        self.rag_dir = Path(rag_dir)
        
        if not self.rag_dir.exists():
            raise FileNotFoundError(f"RAG context directory not found at {self.rag_dir}")
        
        # Storage for all knowledge chunks
        self.chunks: List[KnowledgeChunk] = []
        
        # Load and parse all documents
        self._load_all_documents()
    
    def _estimate_tokens(self, text: str) -> int:
        """
        Estimate token count for text.
        
        Educational note: Why estimate?
        - Actual tokenization varies by model (GPT uses different tokenizer than Claude)
        - Rough estimate: 1 token ≈ 4 characters (English text)
        - We use 3.5 to be conservative (gives us buffer)
        """
        return len(text) // 4  # Rough estimate: ~4 chars per token
    
    def _extract_topics(self, text: str, filename: str) -> Set[str]:
        """
        Extract topic tags from content.
        
        Educational note: Topic extraction strategies:
        1. Keywords in headers (## VO2max Training → "vo2max")
        2. Common terms (threshold, recovery, intervals, etc.)
        3. File-level topics (json_requirements → "json", "format")
        
        More advanced: Could use embeddings, TF-IDF, or LLM-based tagging
        For cycling science, simple keyword matching works well!
        """
        topics = set()
        text_lower = text.lower()
        
        # Common cycling training topics
        topic_keywords = {
            'vo2max': ['vo2max', 'vo2', 'vo₂max', 'maximal aerobic'],
            'threshold': ['threshold', 'ftp', 'lactate threshold', 'functional threshold'],
            'endurance': ['endurance', 'base', 'zone 2', 'aerobic'],
            'recovery': ['recovery', 'rest', 'regeneration', 'easy'],
            'intervals': ['intervals', 'interval training', 'repeats'],
            'tempo': ['tempo', 'sweet spot', 'zone 3'],
            'periodization': ['periodization', 'training phases', 'base build peak'],
            'nutrition': ['nutrition', 'fueling', 'carbohydrate', 'glycogen'],
            'power': ['power', 'watts', 'normalized power'],
            'heart_rate': ['heart rate', 'hr zones', 'cardiac'],
            'gravel': ['gravel', 'off-road', 'unpaved'],
            'json': ['json', 'format', 'structure', 'schema'],
            'zwift': ['zwift', 'indoor', 'trainer'],
            'tss': ['tss', 'training stress', 'load'],
            'testing': ['test', 'assessment', 'ramp test']
        }
        
        # Check for topic keywords
        for topic, keywords in topic_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                topics.add(topic)
        
        # File-specific topics
        if 'json_output' in filename:
            topics.update(['json', 'format', 'schema'])
        elif 'best_practices' in filename:
            topics.update(['training', 'science', 'principles'])
        elif 'off_road' in filename or 'gravel' in filename:
            topics.add('gravel')
        elif 'endurance' in filename:
            topics.add('endurance')
        elif 'practical' in filename:
            topics.add('application')
        
        return topics
    
    def _chunk_by_headers(self, content: str, filename: str) -> List[Tuple[str, str]]:
        """
        Split document into chunks by markdown headers.
        
        Educational note: Chunking strategies:
        
        1. **Fixed-size chunking**: Split every N characters/tokens
           - Pros: Simple, predictable size
           - Cons: Breaks mid-sentence, loses context
        
        2. **Sentence-based**: Split on sentence boundaries
           - Pros: Natural breaks
           - Cons: Variable size, still loses topic context
        
        3. **Hierarchical (what we use)**: Split on headers (##, ###)
           - Pros: Respects document structure, preserves topic coherence
           - Cons: Variable chunk sizes
           - Best for: Structured docs like our markdown files
        
        Example:
        ## VO2max Training    ← Start chunk 1
        Content about VO2...
        ### Interval Design  ← Start chunk 2 (nested under VO2max)
        Content about intervals...
        ## Recovery          ← Start chunk 3
        """
        chunks = []
        
        # Split by headers (## or ###)
        header_pattern = r'^(#{2,3})\s+(.+)$'
        lines = content.split('\n')
        
        current_chunk_title = filename
        current_chunk_content = []
        
        for line in lines:
            header_match = re.match(header_pattern, line)
            
            if header_match:
                # Save previous chunk if it has content
                if current_chunk_content:
                    chunks.append((
                        current_chunk_title,
                        '\n'.join(current_chunk_content).strip()
                    ))
                
                # Start new chunk
                current_chunk_title = header_match.group(2).strip()
                current_chunk_content = [line]  # Include header in content
            else:
                current_chunk_content.append(line)
        
        # Save final chunk
        if current_chunk_content:
            chunks.append((
                current_chunk_title,
                '\n'.join(current_chunk_content).strip()
            ))
        
        return chunks
    
    def _determine_priority(self, filename: str, topics: Set[str]) -> ChunkPriority:
        """
        Assign priority to chunks.
        
        Educational note: Priority helps with token budgeting
        - ALWAYS: Critical for every request (JSON schema)
        - HIGH: Core training principles (used frequently)
        - MEDIUM: Specific topics (use when relevant)
        - LOW: Advanced/niche content (rarely needed)
        """
        # JSON requirements always included
        if 'json_output' in filename:
            return ChunkPriority.ALWAYS
        
        # Core training principles are high priority
        if 'best_practices' in filename or 'practical' in filename:
            return ChunkPriority.HIGH
        
        # Specific topics are medium
        if topics.intersection({'vo2max', 'threshold', 'endurance', 'recovery', 'periodization'}):
            return ChunkPriority.MEDIUM
        
        # Everything else is low
        return ChunkPriority.LOW
    
    def _load_all_documents(self):
        """
        Load all markdown files and create knowledge chunks.
        
        This is called during __init__ to prepare the knowledge base.
        """
        print(f"📚 Loading RAG context from {self.rag_dir}")
        
        for md_file in self.rag_dir.glob("*.md"):
            print(f"  Loading: {md_file.name}")
            
            try:
                content = md_file.read_text(encoding='utf-8')
                
                # Split into chunks by headers
                text_chunks = self._chunk_by_headers(content, md_file.stem)
                
                for title, chunk_content in text_chunks:
                    # Skip very small chunks (< 50 chars)
                    if len(chunk_content) < 50:
                        continue
                    
                    topics = self._extract_topics(chunk_content, md_file.stem)
                    priority = self._determine_priority(md_file.stem, topics)
                    tokens = self._estimate_tokens(chunk_content)
                    
                    chunk = KnowledgeChunk(
                        source_file=md_file.name,
                        title=title,
                        content=chunk_content,
                        topics=topics,
                        priority=priority,
                        token_estimate=tokens
                    )
                    
                    self.chunks.append(chunk)
                
            except Exception as e:
                print(f"  ⚠️  Error loading {md_file.name}: {e}")
        
        print(f"✅ Loaded {len(self.chunks)} knowledge chunks")
        
        # Show distribution by priority
        priority_counts = {}
        for chunk in self.chunks:
            priority_counts[chunk.priority] = priority_counts.get(chunk.priority, 0) + 1
        
        print(f"   Priority distribution:")
        for priority, count in sorted(priority_counts.items(), key=lambda x: x[0].value):
            print(f"     {priority.name}: {count} chunks")
    
    def retrieve(self, query_topics: Optional[Set[str]] = None, 
                 max_tokens: int = 20000) -> List[KnowledgeChunk]:
        """
        Retrieve relevant knowledge chunks for a query.
        
        Educational note: This is the core RAG retrieval logic
        
        Steps:
        1. Start with ALWAYS priority chunks (JSON schema)
        2. Add HIGH priority chunks (core principles)
        3. Add MEDIUM chunks that match query topics
        4. Add LOW chunks if there's room and they match
        5. Stop when we hit token budget
        
        Args:
            query_topics: Set of topic keywords (e.g., {'vo2max', 'intervals'})
            max_tokens: Maximum tokens to return (default 20K)
        
        Returns:
            List of relevant chunks, ordered by priority
        """
        if query_topics is None:
            query_topics = set()
        
        selected_chunks = []
        total_tokens = 0
        
        # Sort chunks by priority
        sorted_chunks = sorted(self.chunks, key=lambda c: c.priority.value)
        
        for chunk in sorted_chunks:
            # Check if we should include this chunk
            include = False
            
            if chunk.priority == ChunkPriority.ALWAYS:
                include = True
            elif chunk.priority == ChunkPriority.HIGH:
                include = True
            elif chunk.priority == ChunkPriority.MEDIUM:
                include = chunk.matches_topics(query_topics)
            elif chunk.priority == ChunkPriority.LOW:
                include = chunk.matches_topics(query_topics)
            
            # Add if relevant and within budget
            if include and (total_tokens + chunk.token_estimate <= max_tokens):
                selected_chunks.append(chunk)
                total_tokens += chunk.token_estimate
        
        print(f"🔍 Retrieved {len(selected_chunks)} chunks ({total_tokens:,} tokens)")
        return selected_chunks
    
    def format_for_prompt(self, chunks: List[KnowledgeChunk]) -> str:
        """
        Format retrieved chunks for AI prompt.
        
        Educational note: How we structure the context
        - Clear section markers
        - Include source attribution
        - Organized by topic/priority
        """
        if not chunks:
            return ""
        
        sections = []
        sections.append("# 📚 Cycling Science Knowledge Base\n")
        sections.append("Use this knowledge to inform your coaching decisions:\n")
        
        # Group by priority for better organization
        by_priority = {}
        for chunk in chunks:
            if chunk.priority not in by_priority:
                by_priority[chunk.priority] = []
            by_priority[chunk.priority].append(chunk)
        
        # Output in priority order
        for priority in sorted(by_priority.keys(), key=lambda p: p.value):
            chunks_in_priority = by_priority[priority]
            
            for chunk in chunks_in_priority:
                sections.append(f"\n## {chunk.title}")
                sections.append(f"*Source: {chunk.source_file}*\n")
                sections.append(chunk.content)
                sections.append("\n---\n")
        
        return "\n".join(sections)
    
    def get_stats(self) -> Dict:
        """Get statistics about the knowledge base."""
        total_tokens = sum(c.token_estimate for c in self.chunks)
        
        by_file = {}
        for chunk in self.chunks:
            if chunk.source_file not in by_file:
                by_file[chunk.source_file] = {'chunks': 0, 'tokens': 0}
            by_file[chunk.source_file]['chunks'] += 1
            by_file[chunk.source_file]['tokens'] += chunk.token_estimate
        
        all_topics = set()
        for chunk in self.chunks:
            all_topics.update(chunk.topics)
        
        return {
            'total_chunks': len(self.chunks),
            'total_tokens': total_tokens,
            'by_file': by_file,
            'unique_topics': sorted(all_topics),
            'topic_count': len(all_topics)
        }


# Test and demonstrate functionality
if __name__ == "__main__":
    print("🎓 RAG Context Loader - Educational Demo\n")
    print("=" * 80)
    
    try:
        # Initialize loader
        print("\n1️⃣ INITIALIZATION - Loading all documents...")
        loader = RAGContextLoader()
        
        # Show stats
        print("\n2️⃣ KNOWLEDGE BASE STATISTICS")
        print("=" * 80)
        stats = loader.get_stats()
        
        print(f"\nTotal: {stats['total_chunks']} chunks, ~{stats['total_tokens']:,} tokens")
        print(f"Topics indexed: {stats['topic_count']}")
        print(f"\nFiles:")
        for filename, info in sorted(stats['by_file'].items()):
            print(f"  {filename:50s} {info['chunks']:3d} chunks, {info['tokens']:6,} tokens")
        
        print(f"\n📋 Available topics:")
        for i, topic in enumerate(stats['unique_topics'], 1):
            print(f"  {topic:15s}", end='')
            if i % 4 == 0:
                print()  # New line every 4 topics
        print()
        
        # Test retrieval scenarios
        print("\n3️⃣ RETRIEVAL EXAMPLES")
        print("=" * 80)
        
        # Example 1: VO2max workout planning
        print("\n📍 Scenario 1: Planning VO2max intervals")
        print("Query topics: {'vo2max', 'intervals'}")
        vo2_chunks = loader.retrieve(query_topics={'vo2max', 'intervals'}, max_tokens=10000)
        print(f"\nRetrieved chunks:")
        for chunk in vo2_chunks[:5]:  # Show first 5
            print(f"  • {chunk.title:50s} [{chunk.priority.name:8s}] {chunk.token_estimate:4d} tokens")
        if len(vo2_chunks) > 5:
            print(f"  ... and {len(vo2_chunks) - 5} more")
        
        # Example 2: Recovery week planning
        print("\n📍 Scenario 2: Planning recovery week")
        print("Query topics: {'recovery', 'endurance'}")
        recovery_chunks = loader.retrieve(query_topics={'recovery', 'endurance'}, max_tokens=10000)
        print(f"\nRetrieved chunks:")
        for chunk in recovery_chunks[:5]:
            print(f"  • {chunk.title:50s} [{chunk.priority.name:8s}] {chunk.token_estimate:4d} tokens")
        if len(recovery_chunks) > 5:
            print(f"  ... and {len(recovery_chunks) - 5} more")
        
        # Example 3: Format for prompt
        print("\n4️⃣ FORMATTED OUTPUT")
        print("=" * 80)
        print("\nHow chunks look in an AI prompt:")
        formatted = loader.format_for_prompt(vo2_chunks[:2])  # Show 2 chunks formatted
        print(formatted[:500] + "\n... (truncated)" if len(formatted) > 500 else formatted)
        
        print("\n✅ RAG system ready for AI coaching!")
        
    except FileNotFoundError as e:
        print(f"❌ Error: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
