from flask import Flask, render_template, request, jsonify, redirect, url_for
import os
import json
import argparse
import datetime
import traceback
from dotenv import load_dotenv

# Import from the new wiki_fix module instead of the original wiki module
from core.wiki_fix import search_player, get_player_page, get_player_info, is_footballer, suggest_players
from core.parser import extract_career_info, obscure_player_name

# Load environment variables
load_dotenv()

app = Flask(__name__, 
            static_folder='frontend/static',
            template_folder='frontend/templates')

# Configuration
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev_key_for_football_quiz')
app.config['DEBUG'] = os.getenv('FLASK_ENV', 'development') == 'development'

# Configure more detailed logging
if app.config['DEBUG']:
    import logging
    logging.basicConfig(level=logging.DEBUG)
    app.logger.setLevel(logging.DEBUG)

@app.route('/')
def home():
    """Render the home page with the search form."""
    return render_template('index.html', now=datetime.datetime.now())

@app.route('/search', methods=['POST'])
def search():
    """Search for a player and redirect to the quiz page."""
    player_name = request.form.get('player_name', '')
    if not player_name:
        return redirect(url_for('home'))
    
    # Redirect to the quiz page with the player name as a parameter
    return redirect(url_for('quiz', player_name=player_name))

@app.route('/quiz')
def quiz():
    """Display the quiz page with the obscured player career."""
    player_name = request.args.get('player_name', '')
    if not player_name:
        return redirect(url_for('home'))
    
    return render_template('quiz_improved.html', player_name=player_name, now=datetime.datetime.now())

@app.route('/api/player', methods=['GET'])
def get_player_data():
    """API endpoint to get player data with obscured name."""
    player_name = request.args.get('name', '')
    if not player_name:
        return jsonify({'error': 'Player name is required'}), 400
    
    try:
        app.logger.info(f"Processing request for player: {player_name}")
        
        # Use the improved get_player_info function which handles both search and page retrieval
        page_title, page_html = get_player_info(player_name)
        
        if not page_title:
            app.logger.warning(f"No Wikipedia page found for player: {player_name}")
            return jsonify({
                'error': 'Player not found',
                'details': 'No matching Wikipedia page could be found. Try a different spelling or a more specific name.'
            }), 404
        
        if not page_html:
            app.logger.error(f"Failed to fetch Wikipedia page for: {page_title}")
            return jsonify({
                'error': 'Failed to fetch player page',
                'details': f"Could not retrieve the Wikipedia page for {page_title}. This might be a temporary issue."
            }), 500
        
        # Check if this is actually a footballer
        if not is_footballer(page_title, page_html):
            app.logger.warning(f"Page found but not a footballer: {page_title}")
            return jsonify({
                'error': 'Not a footballer',
                'details': f"The page for {page_title} doesn't appear to be about a footballer. Try a more specific search."
            }), 400
        
        # Extract career information
        app.logger.info(f"Extracting career information for: {page_title}")
        career_info = extract_career_info(page_html, player_name)
        
        if not career_info or not career_info.get('clubs'):
            app.logger.warning(f"Failed to extract career information for: {page_title}")
            # Try to provide more context about what was found
            info_found = "No career information could be extracted"
            if career_info:
                info_found = f"Found: {', '.join(career_info.keys())}"
                
            return jsonify({
                'error': 'Failed to extract career information',
                'details': f"Could not find career details on the Wikipedia page. {info_found}.",
                'page_title': page_title,
                'partial_data': career_info or {}
            }), 500
        
        # Obscure the player's name
        app.logger.info(f"Obscuring player name for: {page_title}")
        obscured_info = obscure_player_name(career_info, player_name)
        
        # Explicitly remove honors data to match UI changes
        if 'honors' in obscured_info:
            del obscured_info['honors']
        
        app.logger.info(f"Successfully processed player data for: {page_title}")
        return jsonify({
            'player': {
                'search_query': player_name,
                'wikipedia_title': page_title,
                'career': obscured_info
            }
        })
    
    except Exception as e:
        app.logger.error(f"Error processing player data: {str(e)}")
        app.logger.error(traceback.format_exc())
        return jsonify({
            'error': 'An unexpected error occurred',
            'details': str(e) if app.config['DEBUG'] else "Please try again later."
        }), 500

@app.route('/api/suggest', methods=['GET'])
def suggest_player_names():
    """API endpoint to suggest players for autocomplete."""
    query = request.args.get('q', '')
    if len(query) < 2:
        return jsonify({'suggestions': []})
    
    try:
        suggestions = suggest_players(query)
        return jsonify({'suggestions': suggestions})
    except Exception as e:
        app.logger.error(f"Error suggesting players: {str(e)}")
        return jsonify({'error': 'Failed to get suggestions', 'suggestions': []}), 500

@app.route('/api/debug', methods=['GET'])
def debug_info():
    """Debug endpoint to check API connectivity (only available in debug mode)."""
    if not app.config['DEBUG']:
        return jsonify({'error': 'Debug endpoint only available in development mode'}), 403
        
    player_name = request.args.get('name', 'Lionel Messi')
    
    try:
        # Test search
        search_results = search_player(player_name)
        
        # Test page retrieval
        page_html = None
        page_title = None
        if search_results:
            page_title = search_results[0]
            page_html = get_player_page(page_title)
            
        # Test footballer detection
        is_football_player = False
        if page_html:
            is_football_player = is_footballer(page_title, page_html)
            
        # Return debug info
        return jsonify({
            'debug_info': {
                'player_name': player_name,
                'search_results': search_results,
                'page_title': page_title,
                'page_retrieved': page_html is not None,
                'is_footballer': is_football_player,
                'html_length': len(page_html) if page_html else 0,
                'timestamp': datetime.datetime.now().isoformat()
            }
        })
        
    except Exception as e:
        app.logger.error(f"Error in debug endpoint: {str(e)}")
        app.logger.error(traceback.format_exc())
        return jsonify({
            'error': 'Debug API error',
            'details': str(e),
            'traceback': traceback.format_exc() if app.config['DEBUG'] else None
        }), 500

@app.errorhandler(404)
def page_not_found(e):
    """Handle 404 errors."""
    return render_template('404.html', now=datetime.datetime.now()), 404

@app.errorhandler(500)
def server_error(e):
    """Handle 500 errors."""
    return render_template('500.html', now=datetime.datetime.now()), 500

# Development route to test the template with mock data
@app.route('/demo')
def demo():
    """Demo route with mock data for frontend development."""
    if not app.config['DEBUG']:
        return redirect(url_for('home'))
    
    with open('mock_data/example_player.json', 'r') as f:
        mock_data = json.load(f)
    
    # Remove honors from mock data to match UI changes
    if 'honors' in mock_data['player']['career']:
        del mock_data['player']['career']['honors']
    
    return render_template('quiz_improved.html', 
                          player_name=mock_data['player']['search_query'],
                          demo_mode=True,
                          mock_data=mock_data,
                          now=datetime.datetime.now())

def main():
    """
    Main entry point for the application.
    Handles command-line arguments and initializes the app.
    """
    # Set up command-line argument parsing
    parser = argparse.ArgumentParser(description='Football Career Quiz - Guess the footballer from their career path!')
    parser.add_argument('--port', type=int, default=int(os.getenv('PORT', 8000)),
                        help='Port to run the server on (default: 8000 or PORT env var)')
    parser.add_argument('--host', type=str, default='0.0.0.0',
                        help='Host to run the server on (default: 0.0.0.0)')
    parser.add_argument('--debug', action='store_true',
                        help='Run in debug mode (overrides FLASK_ENV)')
    parser.add_argument('--no-setup', action='store_true',
                        help='Skip directory and mock data setup')
    
    args = parser.parse_args()
    
    # Override debug setting if specified
    if args.debug:
        app.config['DEBUG'] = True
    
    # Initialize directories and mock data if not skipped
    if not args.no_setup:
        # Ensure required directories exist
        os.makedirs('frontend/static', exist_ok=True)
        os.makedirs('frontend/templates', exist_ok=True)
        os.makedirs('mock_data', exist_ok=True)
        
        # Create mock data file if it doesn't exist
        if not os.path.exists('mock_data/example_player.json') and app.config['DEBUG']:
            example_data = {
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
                        ]
                        # Honors field removed to match UI changes
                    }
                }
            }
            with open('mock_data/example_player.json', 'w') as f:
                json.dump(example_data, f, indent=2)
    
    # Print startup message
    print(f"Starting Football Career Quiz on http://{args.host}:{args.port}")
    if app.config['DEBUG']:
        print("Running in DEBUG mode")
    
    # Run the Flask app
    app.run(host=args.host, port=args.port, debug=app.config['DEBUG'])
    
    return 0  # Return success code

if __name__ == '__main__':
    main()
