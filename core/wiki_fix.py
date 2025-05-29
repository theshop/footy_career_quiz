"""
Enhanced Wikipedia search and retrieval module for Football Career Quiz.

This module provides more reliable functions to search for football players on Wikipedia
and retrieve their pages for parsing, using direct MediaWiki API calls.
"""

import requests
import logging
import re
import time
import json
from typing import List, Dict, Optional, Union, Tuple
from functools import lru_cache
from urllib.parse import quote

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# MediaWiki API endpoints
WIKIPEDIA_API_URL = "https://en.wikipedia.org/w/api.php"
WIKIPEDIA_REST_API_URL = "https://en.wikipedia.org/api/rest_v1/page"
WIKIPEDIA_BASE_URL = "https://en.wikipedia.org/wiki/"

# User agent for API requests
USER_AGENT = "FootballCareerQuiz/1.0 (https://github.com/theshop/footy_career_quiz)"

# Cache settings
CACHE_TIMEOUT = 3600  # 1 hour in seconds
search_cache = {}
page_cache = {}
footballer_cache = {}

# Football-related keywords to improve search relevance
FOOTBALL_KEYWORDS = [
    "footballer", "soccer player", "football player", 
    "midfielder", "forward", "defender", "goalkeeper", 
    "striker", "winger", "centre-back", "full-back",
    "football career", "football club", "national team"
]

# Common football leagues and competitions to improve search context
FOOTBALL_LEAGUES = [
    "Premier League", "La Liga", "Bundesliga", "Serie A", 
    "Ligue 1", "Champions League", "World Cup", "UEFA", "FIFA",
    "Copa America", "CONMEBOL", "CONCACAF", "AFC", "CAF"
]


def clear_cache() -> None:
    """Clear all caches."""
    search_cache.clear()
    page_cache.clear()
    footballer_cache.clear()
    logger.info("All caches cleared")


def search_player(player_name: str, max_retries: int = 3) -> List[str]:
    """
    Search for a football player on Wikipedia with improved reliability.
    
    Args:
        player_name: The name of the player to search for
        max_retries: Maximum number of retry attempts for API calls
        
    Returns:
        A list of page titles matching the search query, ordered by relevance
    """
    if not player_name or len(player_name.strip()) < 2:
        logger.warning("Empty or too short player name provided")
        return []
    
    # Check cache first
    cache_key = player_name.lower().strip()
    if cache_key in search_cache:
        cache_entry = search_cache[cache_key]
        if time.time() - cache_entry["timestamp"] < CACHE_TIMEOUT:
            logger.info(f"Cache hit for search: {player_name}")
            return cache_entry["results"]
    
    logger.info(f"Searching Wikipedia for: {player_name}")
    
    # Try direct title match first (most reliable)
    direct_title = try_direct_title_match(player_name)
    if direct_title:
        logger.info(f"Found direct title match: {direct_title}")
        results = [direct_title]
        search_cache[cache_key] = {"results": results, "timestamp": time.time()}
        return results
    
    # Try enhanced search with football context
    results = []
    retry_count = 0
    
    while retry_count < max_retries and not results:
        try:
            # First try with football-specific search
            results = search_with_football_context(player_name)
            
            # If no results, try a more general search
            if not results and retry_count > 0:
                results = general_search(player_name)
                
            # Cache valid results
            if results:
                search_cache[cache_key] = {"results": results, "timestamp": time.time()}
                logger.info(f"Found {len(results)} potential matches for {player_name}")
            else:
                logger.warning(f"No results found for {player_name} (attempt {retry_count + 1}/{max_retries})")
                time.sleep(1)  # Brief delay before retry
                
        except Exception as e:
            logger.error(f"Error searching for {player_name} (attempt {retry_count + 1}/{max_retries}): {str(e)}")
            time.sleep(1)  # Brief delay before retry
            
        retry_count += 1
    
    return results


def try_direct_title_match(player_name: str) -> Optional[str]:
    """
    Try to find an exact Wikipedia page title match.
    
    Args:
        player_name: The player name to search for
        
    Returns:
        The matched page title or None if no match
    """
    try:
        # Try exact title match
        params = {
            "action": "query",
            "format": "json",
            "titles": player_name,
            "redirects": 1,  # Follow redirects
            "prop": "info",
            "inprop": "url"
        }
        
        response = requests.get(
            WIKIPEDIA_API_URL, 
            params=params, 
            headers={"User-Agent": USER_AGENT},
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        
        # Check if page exists
        pages = data.get("query", {}).get("pages", {})
        for page_id, page_info in pages.items():
            if int(page_id) > 0:  # Valid page ID (not -1)
                return page_info.get("title")
        
        # Try with common footballer suffixes
        for suffix in [" (footballer)", " (soccer player)", " (soccer)"]:
            params["titles"] = player_name + suffix
            response = requests.get(
                WIKIPEDIA_API_URL, 
                params=params, 
                headers={"User-Agent": USER_AGENT},
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            pages = data.get("query", {}).get("pages", {})
            for page_id, page_info in pages.items():
                if int(page_id) > 0:  # Valid page ID (not -1)
                    return page_info.get("title")
        
        return None
        
    except Exception as e:
        logger.error(f"Error in direct title match for {player_name}: {str(e)}")
        return None


def search_with_football_context(player_name: str) -> List[str]:
    """
    Search for a player with football-specific context.
    
    Args:
        player_name: The player name to search for
        
    Returns:
        List of relevant page titles
    """
    try:
        # Prepare football-specific search query
        football_terms = " OR ".join(FOOTBALL_KEYWORDS[:5])  # Use top 5 keywords
        search_query = f"{player_name} ({football_terms})"
        
        params = {
            "action": "query",
            "format": "json",
            "list": "search",
            "srsearch": search_query,
            "srlimit": 10,
            "srinfo": "totalhits",
            "srprop": "snippet|titlesnippet",
            "srnamespace": 0,  # Main namespace only
            "srqiprofile": "classic"  # Use classic relevance profile
        }
        
        response = requests.get(
            WIKIPEDIA_API_URL, 
            params=params, 
            headers={"User-Agent": USER_AGENT},
            timeout=10
        )
        response.raise_for_status()
        
        data = response.json()
        search_results = data.get("query", {}).get("search", [])
        
        # Filter and score results based on football relevance
        scored_results = []
        for result in search_results:
            title = result.get("title", "")
            snippet = result.get("snippet", "").lower()
            
            # Skip disambiguation pages
            if "(disambiguation)" in title:
                continue
                
            # Calculate football relevance score
            score = calculate_football_relevance(title, snippet)
            
            if score > 0:  # Only include results with some football relevance
                scored_results.append((title, score))
        
        # Sort by relevance score (descending)
        scored_results.sort(key=lambda x: x[1], reverse=True)
        
        # Return just the titles
        return [title for title, score in scored_results]
        
    except Exception as e:
        logger.error(f"Error in football context search for {player_name}: {str(e)}")
        return []


def general_search(player_name: str) -> List[str]:
    """
    Perform a general Wikipedia search as fallback.
    
    Args:
        player_name: The player name to search for
        
    Returns:
        List of page titles
    """
    try:
        params = {
            "action": "opensearch",
            "search": player_name,
            "limit": 10,
            "namespace": 0,
            "format": "json"
        }
        
        response = requests.get(
            WIKIPEDIA_API_URL, 
            params=params, 
            headers={"User-Agent": USER_AGENT},
            timeout=10
        )
        response.raise_for_status()
        
        data = response.json()
        if len(data) >= 2:
            return data[1]  # Second element contains the titles
        
        return []
        
    except Exception as e:
        logger.error(f"Error in general search for {player_name}: {str(e)}")
        return []


def calculate_football_relevance(title: str, snippet: str) -> int:
    """
    Calculate a relevance score for football content.
    
    Args:
        title: The page title
        snippet: The page snippet
        
    Returns:
        A relevance score (higher = more relevant)
    """
    score = 0
    combined_text = (title + " " + snippet).lower()
    
    # Check for footballer-specific title patterns
    if re.search(r'\(football(er)?\)', title.lower()):
        score += 50
    
    # Check for football keywords in title
    for keyword in FOOTBALL_KEYWORDS:
        if keyword.lower() in title.lower():
            score += 30
            break
    
    # Check for football keywords in snippet
    for keyword in FOOTBALL_KEYWORDS:
        if keyword.lower() in snippet:
            score += 10
    
    # Check for football leagues/competitions
    for league in FOOTBALL_LEAGUES:
        if league.lower() in combined_text:
            score += 5
    
    # Check for common football statistical patterns
    if re.search(r'caps|goals|appearances|matches|scored', snippet):
        score += 15
    
    # Check for career-related terms
    if re.search(r'career|season|signed|transfer|club|team', snippet):
        score += 10
    
    return score


def get_player_page(page_title: str, max_retries: int = 3) -> Optional[str]:
    """
    Retrieve the HTML content of a player's Wikipedia page with improved reliability.
    
    Args:
        page_title: The title of the Wikipedia page to retrieve
        max_retries: Maximum number of retry attempts
        
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
    
    # Try multiple retrieval methods with retries
    html_content = None
    retry_count = 0
    
    while retry_count < max_retries and not html_content:
        try:
            # Try REST API first (most reliable for HTML content)
            html_content = get_page_via_rest_api(page_title)
            
            # Fallback to direct URL request
            if not html_content:
                html_content = get_page_via_direct_request(page_title)
                
            # Fallback to action=parse API
            if not html_content:
                html_content = get_page_via_parse_api(page_title)
            
            # Cache successful result
            if html_content:
                page_cache[cache_key] = {"html": html_content, "timestamp": time.time()}
                logger.info(f"Successfully retrieved page: {page_title}")
            else:
                logger.warning(f"Failed to retrieve page: {page_title} (attempt {retry_count + 1}/{max_retries})")
                time.sleep(1)  # Brief delay before retry
                
        except Exception as e:
            logger.error(f"Error retrieving page {page_title} (attempt {retry_count + 1}/{max_retries}): {str(e)}")
            time.sleep(1)  # Brief delay before retry
            
        retry_count += 1
    
    return html_content


def get_page_via_rest_api(page_title: str) -> Optional[str]:
    """
    Get page HTML via Wikipedia's REST API.
    
    Args:
        page_title: The page title
        
    Returns:
        HTML content or None
    """
    try:
        # URL encode the page title
        encoded_title = quote(page_title.replace(" ", "_"))
        url = f"{WIKIPEDIA_REST_API_URL}/html/{encoded_title}"
        
        response = requests.get(
            url,
            headers={"User-Agent": USER_AGENT, "Accept": "text/html"},
            timeout=15
        )
        response.raise_for_status()
        
        return response.text
        
    except Exception as e:
        logger.error(f"REST API retrieval failed for {page_title}: {str(e)}")
        return None


def get_page_via_direct_request(page_title: str) -> Optional[str]:
    """
    Get page HTML via direct Wikipedia URL.
    
    Args:
        page_title: The page title
        
    Returns:
        HTML content or None
    """
    try:
        # URL encode the page title
        encoded_title = quote(page_title.replace(" ", "_"))
        url = f"{WIKIPEDIA_BASE_URL}{encoded_title}"
        
        response = requests.get(
            url,
            headers={"User-Agent": USER_AGENT},
            timeout=15
        )
        response.raise_for_status()
        
        return response.text
        
    except Exception as e:
        logger.error(f"Direct URL retrieval failed for {page_title}: {str(e)}")
        return None


def get_page_via_parse_api(page_title: str) -> Optional[str]:
    """
    Get page HTML via MediaWiki action=parse API.
    
    Args:
        page_title: The page title
        
    Returns:
        HTML content or None
    """
    try:
        params = {
            "action": "parse",
            "page": page_title,
            "prop": "text",
            "formatversion": "2",
            "format": "json"
        }
        
        response = requests.get(
            WIKIPEDIA_API_URL,
            params=params,
            headers={"User-Agent": USER_AGENT},
            timeout=15
        )
        response.raise_for_status()
        
        data = response.json()
        html = data.get("parse", {}).get("text", "")
        
        # Wrap in basic HTML structure if needed
        if html and not html.startswith("<!DOCTYPE html>"):
            html = f"""
            <!DOCTYPE html>
            <html>
            <head><title>{page_title} - Wikipedia</title></head>
            <body>
                <h1 id="firstHeading">{page_title}</h1>
                <div class="mw-parser-output">{html}</div>
            </body>
            </html>
            """
        
        return html
        
    except Exception as e:
        logger.error(f"Parse API retrieval failed for {page_title}: {str(e)}")
        return None


def get_player_info(player_name: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Search for a player and get their page in one operation with improved reliability.
    
    Args:
        player_name: The name of the player to search for
        
    Returns:
        A tuple containing (page_title, page_html) or (None, None) if not found
    """
    search_results = search_player(player_name)
    if not search_results:
        logger.warning(f"No results found for player: {player_name}")
        return None, None
    
    # Try each search result until we find a valid footballer page
    for result in search_results:
        page_html = get_player_page(result)
        
        if not page_html:
            logger.warning(f"Failed to retrieve page for: {result}")
            continue
        
        # Check if this is actually a footballer
        if is_footballer(result, page_html):
            logger.info(f"Found footballer page: {result}")
            return result, page_html
        else:
            logger.info(f"Skipping non-footballer page: {result}")
    
    # If we get here, none of the results were valid footballer pages
    logger.warning(f"No valid footballer pages found for: {player_name}")
    
    # Return the first result anyway as fallback
    if search_results and (page_html := get_player_page(search_results[0])):
        return search_results[0], page_html
    
    return None, None


def is_footballer(page_title: str, page_html: Optional[str] = None) -> bool:
    """
    Check if a Wikipedia page is likely about a footballer with improved reliability.
    
    Args:
        page_title: The title of the Wikipedia page
        page_html: Optional pre-fetched HTML content
        
    Returns:
        True if the page is likely about a footballer, False otherwise
    """
    # Check cache first
    cache_key = page_title.lower().strip()
    if cache_key in footballer_cache:
        return footballer_cache[cache_key]
    
    # Get the page HTML if not provided
    if not page_html:
        page_html = get_player_page(page_title)
        if not page_html:
            return False
    
    # Look for strong indicators in the title
    if re.search(r'\(football(er)?\)', page_title, re.IGNORECASE):
        footballer_cache[cache_key] = True
        return True
    
    # Check for football-related keywords in the first paragraph
    first_para_match = re.search(r'<p>(.+?)</p>', page_html, re.DOTALL)
    if first_para_match:
        first_para = first_para_match.group(1).lower()
        
        # Check for position indicators
        position_match = re.search(r'plays as an? ([\w\s-]+)', first_para) or \
                         re.search(r'plays as an? ([\w\s-]+)', first_para) or \
                         re.search(r'is an? ([\w\s-]+)', first_para)
                         
        if position_match:
            position = position_match.group(1).lower()
            for keyword in FOOTBALL_KEYWORDS:
                if keyword.lower() in position:
                    footballer_cache[cache_key] = True
                    return True
        
        # Check for general football keywords
        for keyword in FOOTBALL_KEYWORDS:
            if keyword.lower() in first_para:
                footballer_cache[cache_key] = True
                return True
    
    # Check for football infobox
    if re.search(r'infobox football biography', page_html, re.IGNORECASE) or \
       re.search(r'infobox football player', page_html, re.IGNORECASE):
        footballer_cache[cache_key] = True
        return True
    
    # Check for football career section
    if re.search(r'<span[^>]*>Club career</span>', page_html, re.IGNORECASE) or \
       re.search(r'<span[^>]*>International career</span>', page_html, re.IGNORECASE):
        footballer_cache[cache_key] = True
        return True
    
    # Not enough evidence
    footballer_cache[cache_key] = False
    return False


def suggest_players(partial_name: str, limit: int = 5) -> List[Dict[str, str]]:
    """
    Suggest football players based on a partial name with improved reliability.
    Useful for autocomplete functionality.
    
    Args:
        partial_name: The partial name to search for
        limit: Maximum number of suggestions to return
        
    Returns:
        A list of dictionaries with player names and their Wikipedia page titles
    """
    if len(partial_name) < 2:
        return []
    
    try:
        # First try with football context
        params = {
            "action": "opensearch",
            "search": f"{partial_name} footballer",
            "limit": limit * 2,  # Get more results to filter
            "namespace": 0,
            "format": "json"
        }
        
        response = requests.get(
            WIKIPEDIA_API_URL, 
            params=params, 
            headers={"User-Agent": USER_AGENT},
            timeout=10
        )
        response.raise_for_status()
        
        data = response.json()
        suggestions = []
        
        if len(data) >= 2:
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
                
                # Quick check if it's likely a footballer
                if is_likely_footballer_from_title(name):
                    suggestions.append({
                        "name": name,
                        "page_title": page_title
                    })
        
        # If we don't have enough suggestions, try a more general search
        if len(suggestions) < limit:
            params["search"] = partial_name
            response = requests.get(
                WIKIPEDIA_API_URL, 
                params=params, 
                headers={"User-Agent": USER_AGENT},
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            if len(data) >= 2:
                names = data[1]
                urls = data[3] if len(data) > 3 else []
                
                for i, name in enumerate(names):
                    if len(suggestions) >= limit:
                        break
                    
                    # Skip if already in suggestions
                    if any(s["name"] == name for s in suggestions):
                        continue
                        
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
        
    except Exception as e:
        logger.error(f"Error suggesting players for '{partial_name}': {str(e)}")
        return []


def is_likely_footballer_from_title(title: str) -> bool:
    """
    Quick check if a title is likely about a footballer.
    
    Args:
        title: The page title
        
    Returns:
        True if likely a footballer, False otherwise
    """
    lower_title = title.lower()
    
    # Check for football indicators in title
    if re.search(r'\(football(er)?\)', lower_title) or \
       re.search(r'\(soccer\)', lower_title) or \
       re.search(r'football player', lower_title) or \
       re.search(r'soccer player', lower_title):
        return True
    
    return False
