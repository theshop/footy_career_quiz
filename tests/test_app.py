"""
Tests for the Flask application routes of the Football Career Quiz application.

These tests verify that the routes correctly handle requests and return
the expected responses.
"""

import pytest
import json
import os
import sys
from unittest.mock import patch, MagicMock

# Add the parent directory to the path so we can import the app module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import app as flask_app


@pytest.fixture
def app():
    """Create and configure a Flask app for testing."""
    # Set testing config
    flask_app.app.config.update({
        "TESTING": True,
        "SECRET_KEY": "test_key",
        "DEBUG": False,
    })
    
    # Create test directories if they don't exist
    os.makedirs('frontend/templates', exist_ok=True)
    os.makedirs('frontend/static', exist_ok=True)
    os.makedirs('mock_data', exist_ok=True)
    
    return flask_app.app


@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()


@pytest.fixture
def mock_player_data():
    """Sample player data for testing."""
    return {
        "player": {
            "search_query": "Lionel Messi",
            "wikipedia_title": "Lionel Messi",
            "career": {
                "full_name": "█████ █████ █████",
                "position": "Forward",
                "birth_date": "24 June 1987",
                "height": "1.70 m (5 ft 7 in)",
                "clubs": [
                    {"name": "Barcelona", "years": "2004–2021", "apps": "520", "goals": "474"},
                    {"name": "Paris Saint-Germain", "years": "2021–2023", "apps": "58", "goals": "21"},
                    {"name": "Inter Miami", "years": "2023–", "apps": "14", "goals": "11"}
                ],
                "national_team": [
                    {"name": "Argentina", "years": "2005–", "apps": "180", "goals": "106"}
                ],
                "honors": [
                    "FIFA World Cup: 2022",
                    "Copa América: 2021",
                    "Champions League: 2006, 2009, 2011, 2015",
                    "Ballon d'Or: 7 times (2009–2012, 2015, 2019, 2021)"
                ]
            }
        }
    }


# Tests for the home route
def test_home_route(client):
    """Test that the home route returns the index page."""
    # Patch the render_template function to avoid actual template rendering
    with patch('app.render_template', return_value='Mocked Index Template') as mock_render:
        response = client.get('/')
        
        # Check response status
        assert response.status_code == 200
        
        # Check that the correct template was rendered
        mock_render.assert_called_once_with('index.html')


# Tests for the search route
def test_search_route_with_player(client):
    """Test the search route with a valid player name."""
    response = client.post('/search', data={'player_name': 'Lionel Messi'})
    
    # Check that we get redirected to the quiz page
    assert response.status_code == 302
    assert '/quiz?player_name=Lionel+Messi' in response.headers['Location']


def test_search_route_empty_player(client):
    """Test the search route with an empty player name."""
    response = client.post('/search', data={'player_name': ''})
    
    # Check that we get redirected to the home page
    assert response.status_code == 302
    assert '/' in response.headers['Location']


# Tests for the quiz route
def test_quiz_route_with_player(client):
    """Test the quiz route with a valid player name."""
    # Patch the render_template function to avoid actual template rendering
    with patch('app.render_template', return_value='Mocked Quiz Template') as mock_render:
        response = client.get('/quiz?player_name=Lionel+Messi')
        
        # Check response status
        assert response.status_code == 200
        
        # Check that the correct template was rendered with the player name
        mock_render.assert_called_once_with('quiz.html', player_name='Lionel Messi')


def test_quiz_route_without_player(client):
    """Test the quiz route without a player name."""
    response = client.get('/quiz')
    
    # Check that we get redirected to the home page
    assert response.status_code == 302
    assert '/' in response.headers['Location']


# Tests for the API player route
@patch('app.search_player')
@patch('app.get_player_page')
@patch('app.extract_career_info')
@patch('app.obscure_player_name')
def test_api_player_route_success(mock_obscure, mock_extract, mock_get_page, mock_search, client, mock_player_data):
    """Test the API player route with a successful player lookup."""
    # Mock the search results
    mock_search.return_value = ["Lionel Messi"]
    
    # Mock the page HTML
    mock_get_page.return_value = "<html>Mocked Wikipedia page</html>"
    
    # Mock the career info extraction
    mock_extract.return_value = mock_player_data["player"]["career"]
    
    # Mock the name obscuring
    mock_obscure.return_value = mock_player_data["player"]["career"]
    
    # Make the API request
    response = client.get('/api/player?name=Lionel+Messi')
    
    # Check response status
    assert response.status_code == 200
    
    # Check response content
    data = json.loads(response.data)
    assert data["player"]["search_query"] == "Lionel Messi"
    assert data["player"]["wikipedia_title"] == "Lionel Messi"
    assert "career" in data["player"]
    
    # Verify the mocked functions were called correctly
    mock_search.assert_called_once_with("Lionel Messi")
    mock_get_page.assert_called_once_with("Lionel Messi")
    mock_extract.assert_called_once_with("<html>Mocked Wikipedia page</html>", "Lionel Messi")
    mock_obscure.assert_called_once()


def test_api_player_route_no_name(client):
    """Test the API player route without a player name."""
    response = client.get('/api/player')
    
    # Check response status (should be bad request)
    assert response.status_code == 400
    
    # Check error message
    data = json.loads(response.data)
    assert "error" in data
    assert "Player name is required" in data["error"]


@patch('app.search_player')
def test_api_player_route_player_not_found(mock_search, client):
    """Test the API player route with a player that doesn't exist."""
    # Mock empty search results
    mock_search.return_value = []
    
    # Make the API request
    response = client.get('/api/player?name=NonexistentPlayer')
    
    # Check response status (should be not found)
    assert response.status_code == 404
    
    # Check error message
    data = json.loads(response.data)
    assert "error" in data
    assert "Player not found" in data["error"]


@patch('app.search_player')
@patch('app.get_player_page')
def test_api_player_route_page_fetch_error(mock_get_page, mock_search, client):
    """Test the API player route when page fetching fails."""
    # Mock search results
    mock_search.return_value = ["Lionel Messi"]
    
    # Mock page fetch failure
    mock_get_page.return_value = None
    
    # Make the API request
    response = client.get('/api/player?name=Lionel+Messi')
    
    # Check response status (should be server error)
    assert response.status_code == 500
    
    # Check error message
    data = json.loads(response.data)
    assert "error" in data
    assert "Failed to fetch player page" in data["error"]


@patch('app.search_player')
@patch('app.get_player_page')
@patch('app.extract_career_info')
def test_api_player_route_extraction_error(mock_extract, mock_get_page, mock_search, client):
    """Test the API player route when career extraction fails."""
    # Mock search results
    mock_search.return_value = ["Lionel Messi"]
    
    # Mock page HTML
    mock_get_page.return_value = "<html>Mocked Wikipedia page</html>"
    
    # Mock extraction failure
    mock_extract.return_value = None
    
    # Make the API request
    response = client.get('/api/player?name=Lionel+Messi')
    
    # Check response status (should be server error)
    assert response.status_code == 500
    
    # Check error message
    data = json.loads(response.data)
    assert "error" in data
    assert "Failed to extract career information" in data["error"]


# Test for error handlers
def test_404_handler(client):
    """Test the 404 error handler."""
    # Patch the render_template function to avoid actual template rendering
    with patch('app.render_template', return_value='Mocked 404 Template') as mock_render:
        response = client.get('/nonexistent-route')
        
        # Check response status
        assert response.status_code == 404
        
        # Check that the correct template was rendered
        mock_render.assert_called_once_with('404.html')


# Test for demo route (development only)
def test_demo_route_in_development(client):
    """Test the demo route in development mode."""
    # Set app to debug mode
    flask_app.app.config['DEBUG'] = True
    
    # Create mock data file
    os.makedirs('mock_data', exist_ok=True)
    with open('mock_data/example_player.json', 'w') as f:
        json.dump({"player": {"search_query": "Test Player"}}, f)
    
    # Patch the render_template function to avoid actual template rendering
    with patch('app.render_template', return_value='Mocked Demo Template') as mock_render:
        response = client.get('/demo')
        
        # Check response status
        assert response.status_code == 200
        
        # Check that the correct template was rendered with mock data
        mock_render.assert_called_once()
        assert 'quiz.html' in mock_render.call_args[0]
        assert 'demo_mode' in mock_render.call_args[1]
        assert mock_render.call_args[1]['demo_mode'] is True
    
    # Clean up
    if os.path.exists('mock_data/example_player.json'):
        os.remove('mock_data/example_player.json')


def test_demo_route_in_production(client):
    """Test the demo route in production mode."""
    # Set app to production mode
    flask_app.app.config['DEBUG'] = False
    
    response = client.get('/demo')
    
    # Check that we get redirected to the home page
    assert response.status_code == 302
    assert '/' in response.headers['Location']
