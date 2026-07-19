import logging
from datetime import datetime
from functools import lru_cache

from duckduckgo_search import DDGS

logger = logging.getLogger(__name__)

@lru_cache(maxsize=32)
def search_recent_news(sport, max_results=1):
    """
    Search DuckDuckGo for recent news about the selected sport.
    Returns the top 3 snippets joined as a single string.
    If the search fails (e.g. rate limit, connection issues, package API changes),
    returns a friendly fallback string instead of crashing.
    """
    current_year = datetime.now().year
    query = f"latest {sport} sports news results records matches {current_year}"
    try:
        # Standard context manager usage for DDGS v5+
        with DDGS(timeout=1) as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
            
            if not results:
                return f"Fallback Context: No active search results found for {sport}."
                
            snippets = []
            for idx, r in enumerate(results, 1):
                title = r.get("title", "News")
                body = r.get("body", "").strip()
                href = r.get("href", "").strip()
                if body:
                    source = f" Source: {href}" if href else ""
                    snippets.append(f"[{idx}] {title}: {body}{source}")
            
            if snippets:
                return "\n\n".join(snippets)
            return f"Fallback Context: Empty search results found for {sport}."
            
    except Exception as e:
        logger.warning(f"DuckDuckGo search failed for {sport}: {e}")
        return (
            f"Fallback Context: DuckDuckGo search is temporarily unavailable (Error: {str(e)}). "
            f"Grounding will rely strictly on database facts."
        )
