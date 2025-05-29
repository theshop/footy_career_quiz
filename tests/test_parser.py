"""
Tests for the parser module of the Football Career Quiz application.

These tests verify that the parser correctly extracts player information
from Wikipedia pages and properly obscures player names.
"""

import pytest
from bs4 import BeautifulSoup
import os
import sys
from unittest.mock import patch

# Add the parent directory to the path so we can import the core modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.parser import (
    extract_career_info,
    extract_full_name,
    extract_position,
    extract_birth_date,
    extract_height,
    extract_club_career,
    extract_national_team,
    extract_honors,
    obscure_player_name,
    generate_name_variants,
    obscure_text,
    find_section,
    clean_text
)


# Sample HTML fixtures
@pytest.fixture
def sample_player_html():
    """Returns a sample Wikipedia HTML for a fictional player."""
    return """
    <html>
        <head>
            <title>John Doe (footballer) - Wikipedia</title>
        </head>
        <body>
            <h1 id="firstHeading">John Doe (footballer)</h1>
            <div class="mw-parser-output">
                <p>
                    <b>John Michael Doe</b> (born 15 June 1985) is an English professional footballer 
                    who plays as a midfielder for Premier League club Arsenal and the England national team.
                </p>
                <table class="infobox">
                    <caption>John Doe</caption>
                    <tbody>
                        <tr>
                            <th>Full name</th>
                            <td>John Michael Doe</td>
                        </tr>
                        <tr>
                            <th>Date of birth</th>
                            <td><span class="bday">15 June 1985</span> (age 38)</td>
                        </tr>
                        <tr>
                            <th>Place of birth</th>
                            <td>London, England</td>
                        </tr>
                        <tr>
                            <th>Height</th>
                            <td>1.85 m (6 ft 1 in)</td>
                        </tr>
                        <tr>
                            <th>Position(s)</th>
                            <td>Central midfielder</td>
                        </tr>
                    </tbody>
                </table>
                
                <h2><span id="Club_career">Club career</span></h2>
                <table class="wikitable">
                    <thead>
                        <tr>
                            <th>Club</th>
                            <th>Years</th>
                            <th>Apps</th>
                            <th>Goals</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td>Chelsea Youth</td>
                            <td>2003–2005</td>
                            <td>34</td>
                            <td>12</td>
                        </tr>
                        <tr>
                            <td>Chelsea</td>
                            <td>2005–2010</td>
                            <td>125</td>
                            <td>24</td>
                        </tr>
                        <tr>
                            <td>Manchester United</td>
                            <td>2010–2018</td>
                            <td>220</td>
                            <td>45</td>
                        </tr>
                        <tr>
                            <td>Arsenal</td>
                            <td>2018–</td>
                            <td>98</td>
                            <td>22</td>
                        </tr>
                        <tr>
                            <td>Total</td>
                            <td></td>
                            <td>477</td>
                            <td>103</td>
                        </tr>
                    </tbody>
                </table>
                
                <h2><span id="International_career">International career</span></h2>
                <table class="wikitable">
                    <thead>
                        <tr>
                            <th>National team</th>
                            <th>Years</th>
                            <th>Caps</th>
                            <th>Goals</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td>England U21</td>
                            <td>2005–2007</td>
                            <td>15</td>
                            <td>3</td>
                        </tr>
                        <tr>
                            <td>England</td>
                            <td>2007–</td>
                            <td>85</td>
                            <td>18</td>
                        </tr>
                    </tbody>
                </table>
                
                <h2><span id="Honours">Honours</span></h2>
                <ul>
                    <li>Premier League: 2009–10, 2012–13, 2013–14</li>
                    <li>FA Cup: 2010, 2019</li>
                    <li>UEFA Champions League: 2008</li>
                    <li>FIFA Club World Cup: 2009</li>
                </ul>
                
                <h2><span id="Personal_life">Personal life</span></h2>
                <p>
                    John Doe married Jane Smith in 2012, and they have two children. 
                    Doe is known for his charity work with the John Doe Foundation.
                </p>
            </div>
        </body>
    </html>
    """


@pytest.fixture
def sample_player_with_missing_data_html():
    """Returns a sample Wikipedia HTML with missing data sections."""
    return """
    <html>
        <head>
            <title>Jane Smith - Wikipedia</title>
        </head>
        <body>
            <h1 id="firstHeading">Jane Smith</h1>
            <div class="mw-parser-output">
                <p>
                    <b>Jane Smith</b> is a professional footballer who plays as a forward.
                </p>
                <table class="infobox">
                    <caption>Jane Smith</caption>
                    <tbody>
                        <tr>
                            <th>Full name</th>
                            <td>Jane Elizabeth Smith</td>
                        </tr>
                    </tbody>
                </table>
                
                <h2><span id="Career">Career</span></h2>
                <p>
                    Smith began her career in 2015 and has played for several clubs.
                </p>
            </div>
        </body>
    </html>
    """


@pytest.fixture
def soup(sample_player_html):
    """Returns a BeautifulSoup object for the sample player HTML."""
    return BeautifulSoup(sample_player_html, 'lxml')


@pytest.fixture
def soup_missing_data(sample_player_with_missing_data_html):
    """Returns a BeautifulSoup object for the sample player with missing data HTML."""
    return BeautifulSoup(sample_player_with_missing_data_html, 'lxml')


# Tests for extraction functions
def test_extract_full_name(soup):
    """Test extracting the player's full name."""
    name = extract_full_name(soup, "John Doe")
    assert name == "John Doe (footballer)"
    
    # Test with a different element structure
    soup.find('h1', {'id': 'firstHeading'}).decompose()
    name = extract_full_name(soup, "John Doe")
    assert name == "John Doe"


def test_extract_position(soup, soup_missing_data):
    """Test extracting the player's position."""
    position = extract_position(soup)
    assert position == "Central midfielder"
    
    # Test with missing position data
    position = extract_position(soup_missing_data)
    assert position == "Forward"  # Should extract from the first paragraph


def test_extract_birth_date(soup, soup_missing_data):
    """Test extracting the player's birth date."""
    birth_date = extract_birth_date(soup)
    assert birth_date == "15 June 1985"
    
    # Test with missing birth date
    birth_date = extract_birth_date(soup_missing_data)
    assert birth_date is None


def test_extract_height(soup, soup_missing_data):
    """Test extracting the player's height."""
    height = extract_height(soup)
    assert height == "1.85 m (6 ft 1 in)"
    
    # Test with missing height
    height = extract_height(soup_missing_data)
    assert height is None


def test_extract_club_career(soup, soup_missing_data):
    """Test extracting the player's club career."""
    clubs = extract_club_career(soup)
    assert len(clubs) == 4  # Should not include the "Total" row
    assert clubs[0]["name"] == "Chelsea Youth"
    assert clubs[0]["years"] == "2003–2005"
    assert clubs[0]["apps"] == "34"
    assert clubs[0]["goals"] == "12"
    
    # Test with missing club career data
    clubs = extract_club_career(soup_missing_data)
    assert len(clubs) == 0


def test_extract_national_team(soup, soup_missing_data):
    """Test extracting the player's national team career."""
    teams = extract_national_team(soup)
    assert len(teams) == 2
    assert teams[1]["name"] == "England"
    assert teams[1]["years"] == "2007–"
    assert teams[1]["apps"] == "85"
    assert teams[1]["goals"] == "18"
    
    # Test with missing national team data
    teams = extract_national_team(soup_missing_data)
    assert len(teams) == 0


def test_extract_honors(soup, soup_missing_data):
    """Test extracting the player's honors."""
    honors = extract_honors(soup)
    assert len(honors) == 4
    assert "Premier League: 2009–10, 2012–13, 2013–14" in honors
    assert "UEFA Champions League: 2008" in honors
    
    # Test with missing honors data
    honors = extract_honors(soup_missing_data)
    assert len(honors) == 0


def test_extract_career_info(sample_player_html):
    """Test the main function that extracts all career information."""
    info = extract_career_info(sample_player_html, "John Doe")
    
    assert info["full_name"] == "John Doe (footballer)"
    assert info["position"] == "Central midfielder"
    assert info["birth_date"] == "15 June 1985"
    assert info["height"] == "1.85 m (6 ft 1 in)"
    assert len(info["clubs"]) == 4
    assert len(info["national_team"]) == 2
    assert len(info["honors"]) == 4
    
    # Test with empty HTML
    info = extract_career_info("", "John Doe")
    assert info == {}


# Tests for name obscuring functions
def test_generate_name_variants():
    """Test generating variations of a player's name."""
    variants = generate_name_variants("John Michael Doe")
    
    # Check for expected variants
    assert "John Michael Doe" in variants
    assert "john michael doe" in variants
    assert "John" in variants
    assert "Doe" in variants
    assert "John Doe" in variants
    
    # Test with empty name
    variants = generate_name_variants("")
    assert len(variants) == 0


def test_obscure_text():
    """Test obscuring text containing player names."""
    name_variants = {"John Doe", "John", "Doe"}
    
    # Test basic obscuring
    text = "John Doe is a footballer who plays for Arsenal."
    obscured = obscure_text(text, name_variants)
    assert "████ ███" in obscured
    assert "Arsenal" in obscured
    
    # Test with multiple occurrences
    text = "John scored a goal. Doe was awarded man of the match. John Doe celebrated."
    obscured = obscure_text(text, name_variants)
    assert "████" in obscured
    assert "███" in obscured
    assert "████ ███" in obscured
    assert "scored a goal" in obscured
    assert "was awarded man of the match" in obscured
    assert "celebrated" in obscured
    
    # Test with empty text or variants
    assert obscure_text("", name_variants) == ""
    assert obscure_text(text, set()) == text


def test_obscure_player_name():
    """Test obscuring player names in career information."""
    career_info = {
        "full_name": "John Michael Doe",
        "position": "Midfielder",
        "clubs": [
            {"name": "Arsenal", "years": "2018–", "apps": "98", "goals": "22"}
        ],
        "honors": [
            "Premier League Player of the Month: January 2019 (John Doe)",
            "PFA Team of the Year: 2018–19 Premier League"
        ]
    }
    
    obscured = obscure_player_name(career_info, "John Doe")
    
    assert "████" not in obscured["position"]  # Position shouldn't be obscured
    assert "████ ███████ ███" in obscured["full_name"]
    assert "████ ███" in obscured["honors"][0]
    assert "PFA Team of the Year" in obscured["honors"][1]  # This shouldn't be obscured
    
    # Test with empty career info
    assert obscure_player_name({}, "John Doe") == {}


def test_find_section(soup):
    """Test finding a section in the Wikipedia page."""
    # Test finding existing sections
    club_section = find_section(soup, ["Club career"])
    assert club_section is not None
    
    international_section = find_section(soup, ["International career"])
    assert international_section is not None
    
    # Test with multiple possible titles
    honors_section = find_section(soup, ["Honours", "Honors", "Achievements"])
    assert honors_section is not None
    
    # Test with non-existent section
    nonexistent_section = find_section(soup, ["Statistics"])
    assert nonexistent_section is None


def test_clean_text():
    """Test cleaning text by removing citations, excessive whitespace, etc."""
    # Test with citations
    text = "John Doe[1][2] won the Premier League[3] in 2010."
    cleaned = clean_text(text)
    assert cleaned == "John Doe won the Premier League in 2010."
    
    # Test with parenthetical notes
    text = "John Doe (born 1985) is a footballer (midfielder) from England."
    cleaned = clean_text(text)
    assert cleaned == "John Doe is a footballer from England."
    
    # Test with excessive whitespace
    text = "John  Doe    is  a   footballer."
    cleaned = clean_text(text)
    assert cleaned == "John Doe is a footballer."
    
    # Test with empty text
    assert clean_text("") == ""
    assert clean_text(None) == ""


# Integration test
def test_full_extraction_and_obscuring_pipeline(sample_player_html):
    """Test the full pipeline of extracting and obscuring player information."""
    # Extract career info
    career_info = extract_career_info(sample_player_html, "John Doe")
    
    # Verify extraction worked
    assert career_info["full_name"] == "John Doe (footballer)"
    assert len(career_info["clubs"]) > 0
    
    # Obscure the player name
    obscured_info = obscure_player_name(career_info, "John Doe")
    
    # Verify obscuring worked
    assert "John" not in obscured_info["full_name"]
    assert "Doe" not in obscured_info["full_name"]
    
    # Check that honors are properly obscured
    for honor in obscured_info["honors"]:
        assert "John" not in honor
        assert "Doe" not in honor
    
    # But club names should not be obscured
    assert any("Arsenal" in club["name"] for club in obscured_info["clubs"])
    assert any("Chelsea" in club["name"] for club in obscured_info["clubs"])
