"""
Wikipedia search and retrieval module for Football Career Quiz.

This module provides functions to search for football players on Wikipedia
and retrieve their pages for parsing.
"""

import requests
import wikipediaapi
import logging
import re
import time
from typing import List, Dict, Optional, Union, Tuple
from functools import lru_cache

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Wikipedia API
USER_AGENT = "FootballCareerQuiz/1.0 (https://github.com/theshop/footy_career_quiz)"
wiki_wiki = wikipediaapi.Wikipedia(
    language="en", 
    extract_format=wikipediaapi.ExtractFormat.HTML,
    user_agent=USER_AGENT
)

# Direct Wikipedia API endpoints
WIKIPEDIA_API_URL = "https://en.wikipedia.org/w/api.php"
WIKIPEDIA_BASE_URL = "https://en.wikipedia.org/wiki/"

# Cache settings
CACHE_TIMEOUT = 3600  # 1 hour in seconds
search_cache = {}
page_cache = {}


def clear_cache() -> None:
    """Clear all caches."""
    search_cache.clear()
    page_cache.clear()
    logger.info("Cache cleared")


def search_player(player_name: str) -> List[str]:
    """
    Search for a football player on Wikipedia.
    
    Args:
        player_name: The name of the player to search for
        
    Returns:
        A list of page titles matching the search query, ordered by relevance
    """
    if not player_name:
        logger.warning("Empty player name provided")
        return []
    
    # Check cache first
    cache_key = player_name.lower().strip()
    if cache_key in search_cache:
        cache_entry = search_cache[cache_key]
        if time.time() - cache_entry["timestamp"] < CACHE_TIMEOUT:
            logger.info(f"Cache hit for search: {player_name}")
            return cache_entry["results"]
    
    logger.info(f"Searching Wikipedia for: {player_name}")
    
    # Try exact match first
    exact_page = wiki_wiki.page(player_name)
    if exact_page.exists():
        logger.info(f"Found exact match: {exact_page.title}")
        results = [exact_page.title]
        search_cache[cache_key] = {"results": results, "timestamp": time.time()}
        return results
    
    # If no exact match, perform a search
    try:
        params = {
            "action": "query",
            "format": "json",
            "list": "search",
            "srsearch": f"{player_name} footballer soccer player",
            "srlimit": 10,
            "srprop": "snippet"
        }
        
        response = requests.get(WIKIPEDIA_API_URL, params=params, headers={"User-Agent": USER_AGENT})
        response.raise_for_status()
        
        data = response.json()
        search_results = data.get("query", {}).get("search", [])
        
        # Filter results to likely be football players
        filtered_results = []
        football_keywords = ["footballer", "soccer", "football player", "midfielder", 
                            "forward", "defender", "goalkeeper", "striker", 
                            "winger", "club", "international", "national team"]
        
        for result in search_results:
            title = result.get("title", "")
            snippet = result.get("snippet", "").lower()
            
            # Check if the snippet contains football-related keywords
            if any(keyword in snippet for keyword in football_keywords):
                filtered_results.append(title)
        
        # Cache the results
        search_cache[cache_key] = {"results": filtered_results, "timestamp": time.time()}
        
        logger.info(f"Found {len(filtered_results)} potential matches for {player_name}")
        return filtered_results
        
    except Exception as e:
        logger.error(f"Error searching for {player_name}: {str(e)}")
        return []


@lru_cache(maxsize=100)
def get_player_page(page_title: str) -> Optional[str]:
    """
    Retrieve the HTML content of a player's Wikipedia page.
    
    Args:
        page_title: The title of the Wikipedia page to retrieve
        
    Returns:
        The HTML content of the page, or None if retrieval failed
    """
    if not page_title:
        logger.warning("Empty page title provided")
        return None
    
    # Check cache first
    cache_key = page_title.lower().strip()
    if cache_key in page_cache:
        cache_entry = page_cache[cache_key]
        if time.time() - cache_entry["timestamp"] < CACHE_TIMEOUT:
            logger.info(f"Cache hit for page: {page_title}")
            return cache_entry["html"]
    
    logger.info(f"Retrieving Wikipedia page: {page_title}")
    
    try:
        # First try using wikipediaapi
        page = wiki_wiki.page(page_title)
        if not page.exists():
            logger.warning(f"Page does not exist: {page_title}")
            return None
        
        # If the page exists, fetch the full HTML using requests for better parsing
        url = WIKIPEDIA_BASE_URL + page_title.replace(" ", "_")
        response = requests.get(url, headers={"User-Agent": USER_AGENT})
        response.raise_for_status()
        
        html_content = response.text
        
        # Cache the result
        page_cache[cache_key] = {"html": html_content, "timestamp": time.time()}
        
        return html_content
        
    except Exception as e:
        logger.error(f"Error retrieving page {page_title}: {str(e)}")
        return None


def get_player_info(player_name: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Search for a player and get their page in one operation.
    
    Args:
        player_name: The name of the player to search for
        
    Returns:
        A tuple containing (page_title, page_html) or (None, None) if not found
    """
    search_results = search_player(player_name)
    if not search_results:
        logger.warning(f"No results found for player: {player_name}")
        return None, None
    
    # Get the first (most relevant) result
    page_title = search_results[0]
    page_html = get_player_page(page_title)
    
    if not page_html:
        logger.warning(f"Failed to retrieve page for: {page_title}")
        return page_title, None
    
    return page_title, page_html


def is_footballer(page_title: str) -> bool:
    """
    Check if a Wikipedia page is likely about a footballer.
    
    Args:
        page_title: The title of the Wikipedia page
        
    Returns:
        True if the page is likely about a footballer, False otherwise
    """
    page_html = get_player_page(page_title)
    if not page_html:
        return False
    
    # Check for football-related keywords in the first paragraph
    football_keywords = [
        "footballer", "soccer player", "football player", 
        "midfielder", "forward", "defender", "goalkeeper", 
        "striker", "winger"
    ]
    
    # Simple pattern to extract the first paragraph
    first_para_match = re.search(r'<p>(.+?)</p>', page_html, re.DOTALL)
    if first_para_match:
        first_para = first_para_match.group(1).lower()
        return any(keyword in first_para for keyword in football_keywords)
    
    return False


def suggest_players(partial_name: str, limit: int = 5) -> List[Dict[str, str]]:
    """
    Suggest football players based on a partial name.
    Useful for autocomplete functionality.
    
    Args:
        partial_name: The partial name to search for
        limit: Maximum number of suggestions to return
        
    Returns:
        A list of dictionaries with player names and their Wikipedia page titles
    """
    if len(partial_name) < 3:
        return []
    
    try:
        params = {
            "action": "opensearch",
            "format": "json",
            "search": f"{partial_name} footballer",
            "limit": limit * 2,  # Get more results to filter
            "namespace": 0
        }
        
        response = requests.get(WIKIPEDIA_API_URL, params=params, headers={"User-Agent": USER_AGENT})
        response.raise_for_status()
        
        data = response.json()
        if len(data) >= 2:
            suggestions = []
            names = data[1]
            urls = data[3] if len(data) > 3 else []
            
            for i, name in enumerate(names):
                if len(suggestions) >= limit:
                    break
                    
                # Extract page title from URL
                page_title = name
                if i < len(urls):
                    url_parts = urls[i].split("/wiki/")
                    if len(url_parts) > 1:
                        page_title = url_parts[1].replace("_", " ")
                
                suggestions.append({
                    "name": name,
                    "page_title": page_title
                })
            
            return suggestions
        
        return []
        
    except Exception as e:
        logger.error(f"Error suggesting players for '{partial_name}': {str(e)}")
        return []
