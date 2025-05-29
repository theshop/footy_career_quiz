"""
Tests for the Wikipedia search and retrieval module of the Football Career Quiz application.

These tests verify that the wiki module correctly searches for players and retrieves
their Wikipedia pages.
"""

import pytest
import os
import sys
from unittest.mock import patch, MagicMock

# Add the parent directory to the path so we can import the core modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.wiki import (
    search_player,
    get_player_page,
    get_player_info,
    is_footballer,
    clear_cache
)


# Mock response for search API
@pytest.fixture
def mock_search_response():
    """Returns a mock response for the Wikipedia search API."""
    return {
        "query": {
            "search": [
                {
                    "title": "Lionel Messi",
                    "snippet": "Lionel Andrés Messi (Spanish pronunciation: [ljoˈnel anˈdɾes ˈmesi] (listen); born 24 June 1987), also known as Leo Messi, is an Argentine professional footballer who plays as a forward for and captains both Major League Soccer club Inter Miami and the Argentina national team."
                },
                {
                    "title": "Lionel Messi career statistics",
                    "snippet": "The following is a detailed list of the career statistics of Argentine professional footballer Lionel Messi. Messi has played in over 1,000 matches and scored over 800 goals for club and country."
                }
            ]
        }
    }


# Mock response for page API
@pytest.fixture
def mock_page_html():
    """Returns mock HTML content for a player's Wikipedia page."""
    return """
    <html>
        <head>
            <title>Lionel Messi - Wikipedia</title>
        </head>
        <body>
            <h1 id="firstHeading">Lionel Messi</h1>
            <div class="mw-parser-output">
                <p>
                    <b>Lionel Andrés Messi</b> (Spanish pronunciation: [ljoˈnel anˈdɾes ˈmesi]; born 24 June 1987), 
                    also known as Leo Messi, is an Argentine professional footballer who plays as a forward for 
                    Major League Soccer club Inter Miami and captains the Argentina national team.
                </p>
                <!-- More content would be here -->
            </div>
        </body>
    </html>
    """


# Tests for search_player function
@patch('requests.get')
@patch('wikipediaapi.Wikipedia.page')
def test_search_player_exact_match(mock_wiki_page, mock_requests_get, mock_page_html):
    """Test searching for a player with an exact match."""
    # Mock the Wikipedia API page response for exact match
    mock_page = MagicMock()
    mock_page.exists.return_value = True
    mock_page.title = "Lionel Messi"
    mock_wiki_page.return_value = mock_page
    
    # Call the function
    results = search_player("Lionel Messi")
    
    # Verify results
    assert len(results) == 1
    assert results[0] == "Lionel Messi"
    
    # Verify the Wikipedia API was called correctly
    mock_wiki_page.assert_called_once_with("Lionel Messi")
    
    # Verify requests.get was not called (since exact match was found)
    mock_requests_get.assert_not_called()


@patch('requests.get')
@patch('wikipediaapi.Wikipedia.page')
def test_search_player_search_results(mock_wiki_page, mock_requests_get, mock_search_response):
    """Test searching for a player that requires a search."""
    # Mock the Wikipedia API page response for no exact match
    mock_page = MagicMock()
    mock_page.exists.return_value = False
    mock_wiki_page.return_value = mock_page
    
    # Mock the search API response
    mock_response = MagicMock()
    mock_response.json.return_value = mock_search_response
    mock_response.raise_for_status.return_value = None
    mock_requests_get.return_value = mock_response
    
    # Call the function
    results = search_player("Messi")
    
    # Verify results
    assert len(results) == 2
    assert results[0] == "Lionel Messi"
    assert results[1] == "Lionel Messi career statistics"
    
    # Verify the Wikipedia API was called correctly
    mock_wiki_page.assert_called_once_with("Messi")
    
    # Verify the search API was called
    mock_requests_get.assert_called_once()
    args, kwargs = mock_requests_get.call_args
    assert "srsearch" in kwargs["params"]
    assert "Messi footballer soccer player" in kwargs["params"]["srsearch"]


@patch('requests.get')
def test_search_player_empty_name(mock_requests_get):
    """Test searching with an empty player name."""
    # Call the function with empty name
    results = search_player("")
    
    # Verify results
    assert results == []
    
    # Verify no API calls were made
    mock_requests_get.assert_not_called()


@patch('requests.get')
@patch('wikipediaapi.Wikipedia.page')
def test_search_player_api_error(mock_wiki_page, mock_requests_get):
    """Test handling of API errors during search."""
    # Mock the Wikipedia API page response for no exact match
    mock_page = MagicMock()
    mock_page.exists.return_value = False
    mock_wiki_page.return_value = mock_page
    
    # Mock the search API to raise an exception
    mock_requests_get.side_effect = Exception("API Error")
    
    # Call the function
    results = search_player("Error Test")
    
    # Verify results (should be empty due to error)
    assert results == []


# Tests for get_player_page function
@patch('requests.get')
@patch('wikipediaapi.Wikipedia.page')
def test_get_player_page_success(mock_wiki_page, mock_requests_get, mock_page_html):
    """Test retrieving a player's Wikipedia page."""
    # Mock the Wikipedia API page response
    mock_page = MagicMock()
    mock_page.exists.return_value = True
    mock_wiki_page.return_value = mock_page
    
    # Mock the requests response for HTML content
    mock_response = MagicMock()
    mock_response.text = mock_page_html
    mock_response.raise_for_status.return_value = None
    mock_requests_get.return_value = mock_response
    
    # Call the function
    html = get_player_page("Lionel Messi")
    
    # Verify results
    assert html == mock_page_html
    
    # Verify the Wikipedia API was called correctly
    mock_wiki_page.assert_called_once_with("Lionel Messi")
    
    # Verify the request for HTML was made
    mock_requests_get.assert_called_once()
    args, kwargs = mock_requests_get.call_args
    assert "https://en.wikipedia.org/wiki/Lionel_Messi" in args[0]


@patch('requests.get')
@patch('wikipediaapi.Wikipedia.page')
def test_get_player_page_nonexistent(mock_wiki_page, mock_requests_get):
    """Test retrieving a non-existent Wikipedia page."""
    # Mock the Wikipedia API page response for non-existent page
    mock_page = MagicMock()
    mock_page.exists.return_value = False
    mock_wiki_page.return_value = mock_page
    
    # Call the function
    html = get_player_page("Nonexistent Player")
    
    # Verify results
    assert html is None
    
    # Verify the Wikipedia API was called correctly
    mock_wiki_page.assert_called_once_with("Nonexistent Player")
    
    # Verify no HTTP request was made
    mock_requests_get.assert_not_called()


@patch('requests.get')
def test_get_player_page_empty_title(mock_requests_get):
    """Test retrieving a page with an empty title."""
    # Call the function with empty title
    html = get_player_page("")
    
    # Verify results
    assert html is None
    
    # Verify no API calls were made
    mock_requests_get.assert_not_called()


# Tests for get_player_info function
@patch('core.wiki.get_player_page')
@patch('core.wiki.search_player')
def test_get_player_info_success(mock_search_player, mock_get_player_page, mock_page_html):
    """Test getting player info in one operation."""
    # Mock the search_player function
    mock_search_player.return_value = ["Lionel Messi"]
    
    # Mock the get_player_page function
    mock_get_player_page.return_value = mock_page_html
    
    # Call the function
    title, html = get_player_info("Messi")
    
    # Verify results
    assert title == "Lionel Messi"
    assert html == mock_page_html
    
    # Verify the search and get functions were called correctly
    mock_search_player.assert_called_once_with("Messi")
    mock_get_player_page.assert_called_once_with("Lionel Messi")


@patch('core.wiki.search_player')
def test_get_player_info_no_results(mock_search_player):
    """Test getting player info with no search results."""
    # Mock the search_player function to return no results
    mock_search_player.return_value = []
    
    # Call the function
    title, html = get_player_info("Unknown Player")
    
    # Verify results
    assert title is None
    assert html is None
    
    # Verify the search function was called correctly
    mock_search_player.assert_called_once_with("Unknown Player")


# Test for is_footballer function
@patch('core.wiki.get_player_page')
def test_is_footballer(mock_get_player_page, mock_page_html):
    """Test checking if a page is about a footballer."""
    # Mock the get_player_page function
    mock_get_player_page.return_value = mock_page_html
    
    # Call the function
    result = is_footballer("Lionel Messi")
    
    # Verify results
    assert result is True
    
    # Verify the get_player_page function was called correctly
    mock_get_player_page.assert_called_once_with("Lionel Messi")
    
    # Test with non-footballer HTML
    non_footballer_html = """
    <html><body><p>This is a page about something else entirely.</p></body></html>
    """
    mock_get_player_page.return_value = non_footballer_html
    
    # Call the function again
    result = is_footballer("Not A Footballer")
    
    # Verify results
    assert result is False


# Test for clear_cache function
@patch('core.wiki.search_cache')
@patch('core.wiki.page_cache')
def test_clear_cache(mock_page_cache, mock_search_cache):
    """Test clearing the caches."""
    # Set up mock caches
    mock_search_cache.clear = MagicMock()
    mock_page_cache.clear = MagicMock()
    
    # Call the function
    clear_cache()
    
    # Verify both caches were cleared
    mock_search_cache.clear.assert_called_once()
    mock_page_cache.clear.assert_called_once()
