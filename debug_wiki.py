#!/usr/bin/env python
"""
Debug script for testing Wikipedia API integration in Football Career Quiz.

This script allows direct testing of the Wikipedia search, page retrieval,
and parsing functionality without running the full web application.

Usage:
    python debug_wiki.py search "Lionel Messi"
    python debug_wiki.py get "Lionel Messi"
    python debug_wiki.py parse "Lionel Messi"
    python debug_wiki.py full "Lionel Messi"
    python debug_wiki.py save "Lionel Messi" --output messi_data.json
"""

import argparse
import json
import os
import sys
import time
import traceback
from typing import Any, Dict, List, Optional, Tuple

# Add parent directory to path to import core modules
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Import the enhanced Wikipedia module
try:
    from core.wiki_fix import (
        search_player,
        get_player_page,
        get_player_info,
        is_footballer,
        suggest_players,
        clear_cache
    )
    from core.parser import extract_career_info, obscure_player_name
except ImportError:
    print("Error: Could not import core modules. Make sure you're running this script from the project root.")
    sys.exit(1)

# ANSI color codes for terminal output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def print_header(text: str) -> None:
    """Print a formatted header."""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'=' * 50}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text.center(50)}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'=' * 50}{Colors.ENDC}\n")


def print_section(text: str) -> None:
    """Print a formatted section header."""
    print(f"\n{Colors.BLUE}{Colors.BOLD}{text}{Colors.ENDC}")
    print(f"{Colors.BLUE}{'-' * len(text)}{Colors.ENDC}")


def print_success(text: str) -> None:
    """Print a success message."""
    print(f"{Colors.GREEN}✓ {text}{Colors.ENDC}")


def print_error(text: str) -> None:
    """Print an error message."""
    print(f"{Colors.RED}✗ {text}{Colors.ENDC}")


def print_warning(text: str) -> None:
    """Print a warning message."""
    print(f"{Colors.YELLOW}⚠ {text}{Colors.ENDC}")


def print_info(text: str) -> None:
    """Print an info message."""
    print(f"{Colors.CYAN}ℹ {text}{Colors.ENDC}")


def print_data(label: str, data: Any) -> None:
    """Print labeled data with appropriate formatting."""
    if isinstance(data, (dict, list)):
        print(f"{Colors.BOLD}{label}:{Colors.ENDC}")
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        print(f"{Colors.BOLD}{label}:{Colors.ENDC} {data}")


def test_search(player_name: str, verbose: bool = False) -> List[str]:
    """Test the player search functionality."""
    print_section(f"Searching for player: {player_name}")
    
    try:
        start_time = time.time()
        results = search_player(player_name)
        elapsed_time = time.time() - start_time
        
        if results:
            print_success(f"Found {len(results)} results in {elapsed_time:.2f} seconds")
            for i, result in enumerate(results, 1):
                print(f"  {i}. {result}")
            return results
        else:
            print_error(f"No results found for '{player_name}'")
            
            # Suggest alternatives
            print_info("Trying to suggest alternatives...")
            suggestions = suggest_players(player_name)
            if suggestions:
                print_info("You might try one of these players instead:")
                for i, suggestion in enumerate(suggestions, 1):
                    print(f"  {i}. {suggestion['name']}")
            
            return []
    except Exception as e:
        print_error(f"Error during search: {str(e)}")
        if verbose:
            print(traceback.format_exc())
        return []


def test_page_retrieval(page_title: str, verbose: bool = False, save_html: bool = False) -> Optional[str]:
    """Test retrieving a Wikipedia page."""
    print_section(f"Retrieving page: {page_title}")
    
    try:
        start_time = time.time()
        html = get_player_page(page_title)
        elapsed_time = time.time() - start_time
        
        if html:
            print_success(f"Retrieved page ({len(html)} bytes) in {elapsed_time:.2f} seconds")
            
            # Check if it's a footballer
            is_football_player = is_footballer(page_title, html)
            if is_football_player:
                print_success("Page appears to be about a footballer")
            else:
                print_warning("Page does not appear to be about a footballer")
            
            # Save HTML if requested
            if save_html:
                filename = f"{page_title.replace(' ', '_')}_wiki.html"
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(html)
                print_info(f"Saved HTML to {filename}")
            
            return html
        else:
            print_error(f"Failed to retrieve page for '{page_title}'")
            return None
    except Exception as e:
        print_error(f"Error during page retrieval: {str(e)}")
        if verbose:
            print(traceback.format_exc())
        return None


def test_parser(page_html: str, player_name: str, verbose: bool = False) -> Dict[str, Any]:
    """Test parsing a Wikipedia page for player career information."""
    print_section("Parsing career information")
    
    try:
        start_time = time.time()
        career_info = extract_career_info(page_html, player_name)
        elapsed_time = time.time() - start_time
        
        if career_info:
            print_success(f"Extracted career information in {elapsed_time:.2f} seconds")
            
            # Print basic info
            if 'full_name' in career_info:
                print_info(f"Full name: {career_info['full_name']}")
            if 'position' in career_info:
                print_info(f"Position: {career_info['position']}")
            if 'birth_date' in career_info:
                print_info(f"Birth date: {career_info['birth_date']}")
            
            # Print club career summary
            if 'clubs' in career_info and career_info['clubs']:
                print_info(f"Found {len(career_info['clubs'])} clubs in career")
                for i, club in enumerate(career_info['clubs'][:3], 1):  # Show first 3 clubs
                    print(f"  {i}. {club.get('name', 'Unknown')} ({club.get('years', 'Unknown')})")
                if len(career_info['clubs']) > 3:
                    print(f"  ... and {len(career_info['clubs']) - 3} more")
            else:
                print_warning("No club career information found")
            
            # Print national team summary
            if 'national_team' in career_info and career_info['national_team']:
                print_info(f"Found {len(career_info['national_team'])} national teams")
                for team in career_info['national_team']:
                    print(f"  • {team.get('name', 'Unknown')} ({team.get('years', 'Unknown')})")
            else:
                print_warning("No national team information found")
            
            # Print honors summary
            if 'honors' in career_info and career_info['honors']:
                print_info(f"Found {len(career_info['honors'])} honors/achievements")
                for i, honor in enumerate(career_info['honors'][:3], 1):  # Show first 3 honors
                    print(f"  {i}. {honor}")
                if len(career_info['honors']) > 3:
                    print(f"  ... and {len(career_info['honors']) - 3} more")
            else:
                print_warning("No honors information found")
            
            # Test name obscuring
            print_info("Testing name obscuring...")
            obscured_info = obscure_player_name(career_info, player_name)
            if 'full_name' in obscured_info:
                print_info(f"Obscured name: {obscured_info['full_name']}")
            
            return career_info
        else:
            print_error("Failed to extract career information")
            return {}
    except Exception as e:
        print_error(f"Error during parsing: {str(e)}")
        if verbose:
            print(traceback.format_exc())
        return {}


def test_full_pipeline(player_name: str, verbose: bool = False) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
    """Test the full pipeline from search to parsing."""
    print_header(f"FULL PIPELINE TEST FOR: {player_name}")
    
    # Step 1: Search for the player
    search_results = test_search(player_name, verbose)
    if not search_results:
        return None, None
    
    # Step 2: Get the player's Wikipedia page
    page_title = search_results[0]
    page_html = test_page_retrieval(page_title, verbose)
    if not page_html:
        return page_title, None
    
    # Step 3: Parse the player's career information
    career_info = test_parser(page_html, player_name, verbose)
    
    return page_title, career_info


def save_data(player_name: str, output_file: str, verbose: bool = False) -> None:
    """Save all data for a player to a JSON file."""
    print_header(f"SAVING DATA FOR: {player_name}")
    
    try:
        # Get player info
        page_title, page_html = get_player_info(player_name)
        
        if not page_title or not page_html:
            print_error(f"Could not find Wikipedia page for '{player_name}'")
            return
        
        # Extract career info
        career_info = extract_career_info(page_html, player_name)
        
        # Create data structure
        data = {
            "search_query": player_name,
            "wikipedia_title": page_title,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "is_footballer": is_footballer(page_title, page_html),
            "career_info": career_info,
            "obscured_info": obscure_player_name(career_info, player_name) if career_info else None
        }
        
        # Save to file
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print_success(f"Data saved to {output_file}")
        
    except Exception as e:
        print_error(f"Error saving data: {str(e)}")
        if verbose:
            print(traceback.format_exc())


def main() -> None:
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Debug tool for testing Wikipedia API integration in Football Career Quiz",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    # Add subparsers for different commands
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Search command
    search_parser = subparsers.add_parser("search", help="Search for a player")
    search_parser.add_argument("player_name", help="Name of the player to search for")
    
    # Get command
    get_parser = subparsers.add_parser("get", help="Retrieve a player's Wikipedia page")
    get_parser.add_argument("player_name", help="Name of the player to retrieve")
    get_parser.add_argument("--save-html", action="store_true", help="Save the HTML to a file")
    
    # Parse command
    parse_parser = subparsers.add_parser("parse", help="Parse a player's career information")
    parse_parser.add_argument("player_name", help="Name of the player to parse")
    
    # Full command
    full_parser = subparsers.add_parser("full", help="Run the full pipeline")
    full_parser.add_argument("player_name", help="Name of the player to process")
    
    # Save command
    save_parser = subparsers.add_parser("save", help="Save all data for a player")
    save_parser.add_argument("player_name", help="Name of the player to save")
    save_parser.add_argument("--output", "-o", default=None, help="Output file name")
    
    # Clear cache command
    subparsers.add_parser("clear-cache", help="Clear the search and page caches")
    
    # Global options
    parser.add_argument("--verbose", "-v", action="store_true", help="Show verbose output")
    
    # Parse arguments
    args = parser.parse_args()
    
    # Handle commands
    if args.command == "search":
        test_search(args.player_name, args.verbose)
    
    elif args.command == "get":
        # First search for the player
        search_results = test_search(args.player_name, args.verbose)
        if search_results:
            # Then get the page
            test_page_retrieval(search_results[0], args.verbose, args.save_html)
    
    elif args.command == "parse":
        # First search for the player
        search_results = test_search(args.player_name, args.verbose)
        if search_results:
            # Then get the page
            page_html = test_page_retrieval(search_results[0], args.verbose)
            if page_html:
                # Then parse the page
                test_parser(page_html, args.player_name, args.verbose)
    
    elif args.command == "full":
        test_full_pipeline(args.player_name, args.verbose)
    
    elif args.command == "save":
        output_file = args.output
        if not output_file:
            output_file = f"{args.player_name.replace(' ', '_').lower()}_data.json"
        save_data(args.player_name, output_file, args.verbose)
    
    elif args.command == "clear-cache":
        clear_cache()
        print_success("Cache cleared")
    
    else:
        parser.print_help()


if __name__ == "__main__":
    # Check if colorama is available for Windows color support
    try:
        import colorama
        colorama.init()
    except ImportError:
        # If colorama is not available, disable colors on Windows
        if sys.platform == "win32":
            Colors.HEADER = ''
            Colors.BLUE = ''
            Colors.CYAN = ''
            Colors.GREEN = ''
            Colors.YELLOW = ''
            Colors.RED = ''
            Colors.ENDC = ''
            Colors.BOLD = ''
            Colors.UNDERLINE = ''
    
    try:
        main()
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print_error(f"Unhandled error: {str(e)}")
        print(traceback.format_exc())
        sys.exit(1)
