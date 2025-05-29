"""
Wikipedia HTML parser module for Football Career Quiz.

This module provides functions to extract career information from Wikipedia pages
and obscure player names for the quiz functionality.
"""

from bs4 import BeautifulSoup, Tag, NavigableString
import re
import logging
import unicodedata
from typing import Dict, List, Any, Optional, Set, Tuple, Union
import nltk
from nltk.tokenize import word_tokenize

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Download NLTK resources if needed
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt', quiet=True)


def extract_career_info(page_html: str, player_name: str) -> Dict[str, Any]:
    """
    Extract career information from a Wikipedia page.
    
    Args:
        page_html: The HTML content of the Wikipedia page
        player_name: The name of the player
        
    Returns:
        A dictionary containing the player's career information
    """
    if not page_html:
        logger.error("Empty HTML content provided")
        return {}
    
    try:
        soup = BeautifulSoup(page_html, 'lxml')
        
        # Basic player info
        player_info = {
            "full_name": extract_full_name(soup, player_name),
            "position": extract_position(soup),
            "birth_date": extract_birth_date(soup),
            "height": extract_height(soup),
            "clubs": extract_club_career(soup),
            "national_team": extract_national_team(soup),
            "honors": extract_honors(soup),
            "image_url": extract_player_image(soup)
        }
        
        # Filter out None values
        player_info = {k: v for k, v in player_info.items() if v is not None}
        
        logger.info(f"Successfully extracted career info for {player_name}")
        return player_info
        
    except Exception as e:
        logger.error(f"Error extracting career info: {str(e)}")
        return {}


def extract_full_name(soup: BeautifulSoup, player_name: str) -> str:
    """Extract the player's full name from the Wikipedia page."""
    # Try to get from the page title first
    title = soup.find('h1', {'id': 'firstHeading'})
    if title:
        return title.text.strip()
    
    # Try to get from the infobox
    infobox = soup.find('table', {'class': 'infobox'})
    if infobox:
        caption = infobox.find('caption')
        if caption:
            return caption.text.strip()
    
    # Fallback to the provided player name
    return player_name


def extract_position(soup: BeautifulSoup) -> Optional[str]:
    """Extract the player's position from the Wikipedia page."""
    infobox = soup.find('table', {'class': 'infobox'})
    if not infobox:
        return None
    
    # Look for position in the infobox
    position_row = None
    for row in infobox.find_all('tr'):
        header = row.find('th')
        if header and 'position' in header.text.lower():
            position_row = row
            break
    
    if position_row:
        position_cell = position_row.find('td')
        if position_cell:
            return clean_text(position_cell.text)
    
    # Alternative approach: look in the first paragraph
    first_para = soup.find('div', {'class': 'mw-parser-output'}).find('p')
    if first_para:
        positions = ['goalkeeper', 'defender', 'midfielder', 'forward', 'striker', 'winger', 'centre-back', 'full-back']
        para_text = first_para.text.lower()
        for pos in positions:
            if pos in para_text:
                # Try to get the complete position description
                pos_pattern = re.compile(r'(?:is|was) an? [\w\s-]+ ' + pos + r'|(?:is|was) an? ' + pos)
                match = pos_pattern.search(para_text)
                if match:
                    position_text = match.group(0).replace('is a ', '').replace('is an ', '')
                    position_text = position_text.replace('was a ', '').replace('was an ', '')
                    return position_text.strip().capitalize()
                return pos.capitalize()
    
    return None


def extract_birth_date(soup: BeautifulSoup) -> Optional[str]:
    """Extract the player's birth date from the Wikipedia page."""
    infobox = soup.find('table', {'class': 'infobox'})
    if not infobox:
        return None
    
    # Look for birth date in the infobox
    for row in infobox.find_all('tr'):
        header = row.find('th')
        if header and ('birth date' in header.text.lower() or 'born' in header.text.lower()):
            birth_cell = row.find('td')
            if birth_cell:
                # Try to find a specific birth date span
                birth_span = birth_cell.find('span', {'class': 'bday'})
                if birth_span:
                    return birth_span.text.strip()
                
                # If no specific span, clean the text
                birth_text = clean_text(birth_cell.text)
                
                # Try to extract just the date part
                date_match = re.search(r'(\d{1,2}\s+\w+\s+\d{4})', birth_text)
                if date_match:
                    return date_match.group(1)
                
                return birth_text
    
    return None


def extract_height(soup: BeautifulSoup) -> Optional[str]:
    """Extract the player's height from the Wikipedia page."""
    infobox = soup.find('table', {'class': 'infobox'})
    if not infobox:
        return None
    
    # Look for height in the infobox
    for row in infobox.find_all('tr'):
        header = row.find('th')
        if header and 'height' in header.text.lower():
            height_cell = row.find('td')
            if height_cell:
                return clean_text(height_cell.text)
    
    return None


def extract_club_career(soup: BeautifulSoup) -> List[Dict[str, str]]:
    """Extract the player's club career from the Wikipedia page."""
    clubs = []
    
    # Look for the club career section/table
    career_section = find_section(soup, ['Career statistics', 'Club career', 'Club', 'Senior career'])
    if not career_section:
        return clubs
    
    # Find tables in the section
    tables = career_section.find_all('table', {'class': 'wikitable'})
    
    # If no tables found, try to find any wikitable after the section
    if not tables:
        next_section = career_section.find_next('h2')
        if next_section:
            tables = []
            current = career_section.find_next('table', {'class': 'wikitable'})
            while current and (next_section.sourceline is None or current.sourceline < next_section.sourceline):
                tables.append(current)
                current = current.find_next('table', {'class': 'wikitable'})
    
    for table in tables:
        # Check if this table has club career data
        headers = [th.text.strip().lower() for th in table.find_all('th')]
        if not headers:
            continue
        
        # Check if this looks like a career table
        career_headers = ['club', 'team', 'years', 'season', 'apps', 'appearances', 'goals']
        if not any(header in ''.join(headers) for header in career_headers):
            continue
        
        # Find the indices for relevant columns
        club_idx = next((i for i, h in enumerate(headers) if 'club' in h or 'team' in h), None)
        years_idx = next((i for i, h in enumerate(headers) if 'years' in h or 'season' in h), None)
        apps_idx = next((i for i, h in enumerate(headers) if 'app' in h or 'games' in h or 'match' in h), None)
        goals_idx = next((i for i, h in enumerate(headers) if 'goal' in h or 'score' in h), None)
        
        if club_idx is None:
            continue
        
        # Process rows
        for row in table.find_all('tr')[1:]:  # Skip header row
            cells = row.find_all(['td', 'th'])
            if len(cells) <= club_idx:
                continue
            
            # Skip rows that are section headers
            if len(cells) == 1 or (cells[0].name == 'th' and cells[0].get('colspan')):
                continue
            
            club_name = cells[club_idx].text.strip()
            
            # Skip totals or empty rows
            if not club_name or club_name.lower() in ['total', 'career total', 'career statistics']:
                continue
            
            club_info = {"name": club_name}
            
            if years_idx is not None and years_idx < len(cells):
                club_info["years"] = clean_text(cells[years_idx].text)
            
            if apps_idx is not None and apps_idx < len(cells):
                club_info["apps"] = clean_text(cells[apps_idx].text)
            
            if goals_idx is not None and goals_idx < len(cells):
                club_info["goals"] = clean_text(cells[goals_idx].text)
            
            clubs.append(club_info)
    
    return clubs


def extract_national_team(soup: BeautifulSoup) -> List[Dict[str, str]]:
    """Extract the player's national team career from the Wikipedia page."""
    national_teams = []
    
    # Look for the international career section/table
    career_section = find_section(soup, ['International career', 'National team', 'International'])
    if not career_section:
        # If no dedicated section, try to find it in the club career tables
        club_career_tables = soup.find_all('table', {'class': 'wikitable'})
        for table in club_career_tables:
            rows = table.find_all('tr')
            for row in rows:
                cells = row.find_all(['td', 'th'])
                for cell in cells:
                    if cell.text.strip().lower() in ['national team', 'international']:
                        # Found national team data in this table
                        national_team_row = row.find_next('tr')
                        if national_team_row:
                            team_cells = national_team_row.find_all('td')
                            if len(team_cells) >= 3:
                                national_teams.append({
                                    "name": clean_text(team_cells[0].text),
                                    "years": clean_text(team_cells[1].text) if len(team_cells) > 1 else "",
                                    "apps": clean_text(team_cells[2].text) if len(team_cells) > 2 else "",
                                    "goals": clean_text(team_cells[3].text) if len(team_cells) > 3 else ""
                                })
        
        return national_teams
    
    # Find tables in the section
    tables = career_section.find_all('table', {'class': 'wikitable'})
    
    # If no tables found, try to find any wikitable after the section
    if not tables:
        next_section = career_section.find_next('h2')
        if next_section:
            tables = []
            current = career_section.find_next('table', {'class': 'wikitable'})
            while current and (next_section.sourceline is None or current.sourceline < next_section.sourceline):
                tables.append(current)
                current = current.find_next('table', {'class': 'wikitable'})
    
    for table in tables:
        # Check if this table has national team data
        headers = [th.text.strip().lower() for th in table.find_all('th')]
        if not headers:
            continue
        
        # Check if this looks like a national team table
        team_headers = ['team', 'national team', 'country', 'years', 'caps', 'goals']
        if not any(header in ''.join(headers) for header in team_headers):
            continue
        
        # Find the indices for relevant columns
        team_idx = next((i for i, h in enumerate(headers) if 'team' in h or 'country' in h), None)
        years_idx = next((i for i, h in enumerate(headers) if 'years' in h or 'period' in h), None)
        apps_idx = next((i for i, h in enumerate(headers) if 'app' in h or 'caps' in h or 'games' in h), None)
        goals_idx = next((i for i, h in enumerate(headers) if 'goal' in h or 'score' in h), None)
        
        if team_idx is None:
            continue
        
        # Process rows
        for row in table.find_all('tr')[1:]:  # Skip header row
            cells = row.find_all(['td', 'th'])
            if len(cells) <= team_idx:
                continue
            
            # Skip rows that are section headers
            if len(cells) == 1 or (cells[0].name == 'th' and cells[0].get('colspan')):
                continue
            
            team_name = cells[team_idx].text.strip()
            
            # Skip totals or empty rows
            if not team_name or team_name.lower() in ['total', 'career total']:
                continue
            
            team_info = {"name": team_name}
            
            if years_idx is not None and years_idx < len(cells):
                team_info["years"] = clean_text(cells[years_idx].text)
            
            if apps_idx is not None and apps_idx < len(cells):
                team_info["apps"] = clean_text(cells[apps_idx].text)
            
            if goals_idx is not None and goals_idx < len(cells):
                team_info["goals"] = clean_text(cells[goals_idx].text)
            
            national_teams.append(team_info)
    
    return national_teams


def extract_honors(soup: BeautifulSoup) -> List[str]:
    """Extract the player's honors and achievements from the Wikipedia page."""
    honors = []
    
    # Look for the honours section
    honours_section = find_section(soup, ['Honours', 'Honors', 'Achievements', 'Awards'])
    if not honours_section:
        return honors
    
    # Find lists in the section
    lists = honours_section.find_all(['ul', 'dl'])
    
    for lst in lists:
        for item in lst.find_all(['li', 'dd']):
            honor_text = clean_text(item.text)
            if honor_text and len(honor_text) < 100:  # Avoid very long text that's probably not an honor
                honors.append(honor_text)
    
    return honors


def extract_player_image(soup: BeautifulSoup) -> Optional[str]:
    """Extract the player's image URL from the Wikipedia page."""
    infobox = soup.find('table', {'class': 'infobox'})
    if not infobox:
        return None
    
    # Look for the first image in the infobox
    image = infobox.find('img')
    if image and 'src' in image.attrs:
        src = image['src']
        if src.startswith('//'):
            return 'https:' + src
        return src
    
    return None


def find_section(soup: BeautifulSoup, section_titles: List[str]) -> Optional[Tag]:
    """
    Find a section in the Wikipedia page by possible titles.
    
    Args:
        soup: BeautifulSoup object of the page
        section_titles: List of possible section titles
        
    Returns:
        The section tag if found, None otherwise
    """
    for title in section_titles:
        # Look for h2, h3, or h4 headings
        for heading_level in range(2, 5):
            heading_tag = soup.find(f'h{heading_level}', string=lambda text: text and title.lower() in text.lower())
            if heading_tag:
                # Get the content until the next heading of same or higher level
                section_content = Tag(name='div')
                current = heading_tag.next_sibling
                
                while current:
                    if current.name and current.name[0] == 'h' and int(current.name[1]) <= heading_level:
                        break
                    
                    next_element = current.next_sibling
                    section_content.append(current)
                    current = next_element
                
                return section_content
    
    return None


def clean_text(text: str) -> str:
    """Clean text by removing citations, excessive whitespace, etc."""
    if not text:
        return ""
    
    # Remove citations
    text = re.sub(r'\[\d+\]', '', text)
    
    # Remove parenthetical notes
    text = re.sub(r'\([^)]*\)', '', text)
    
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Normalize unicode characters
    text = unicodedata.normalize('NFKC', text)
    
    return text.strip()


def obscure_player_name(career_info: Dict[str, Any], player_name: str) -> Dict[str, Any]:
    """
    Obscure the player's name in the career information.
    
    Args:
        career_info: The player's career information
        player_name: The name of the player to obscure
        
    Returns:
        The career information with the player's name obscured
    """
    if not career_info or not player_name:
        return career_info
    
    # Create a deep copy to avoid modifying the original
    obscured_info = career_info.copy()
    
    # Get all name variants to obscure
    name_variants = generate_name_variants(player_name)
    if "full_name" in obscured_info:
        name_variants.update(generate_name_variants(obscured_info["full_name"]))
    
    # Obscure the full name
    if "full_name" in obscured_info:
        obscured_info["full_name"] = obscure_text(obscured_info["full_name"], name_variants)
    
    # Obscure names in honors
    if "honors" in obscured_info:
        obscured_info["honors"] = [obscure_text(honor, name_variants) for honor in obscured_info["honors"]]
    
    # Obscure any other text fields that might contain the player's name
    for key, value in obscured_info.items():
        if isinstance(value, str) and key not in ["full_name"]:
            obscured_info[key] = obscure_text(value, name_variants)
    
    return obscured_info


def generate_name_variants(name: str) -> Set[str]:
    """
    Generate variations of a player's name for thorough obscuring.
    
    Args:
        name: The player's name
        
    Returns:
        A set of name variations to obscure
    """
    if not name:
        return set()
    
    variants = set()
    name = name.strip()
    
    # Add the full name
    variants.add(name)
    
    # Add lowercase version
    variants.add(name.lower())
    
    # Add name parts
    parts = name.split()
    for part in parts:
        if len(part) > 1:  # Only add parts that are actual names, not initials
            variants.add(part)
            variants.add(part.lower())
    
    # Add first name + last name combination if there are at least 2 parts
    if len(parts) >= 2:
        variants.add(f"{parts[0]} {parts[-1]}")
        variants.add(f"{parts[0]} {parts[-1]}".lower())
    
    # Add common nickname patterns
    if len(parts) >= 2:
        # First name initial + last name
        variants.add(f"{parts[0][0]}. {parts[-1]}")
        variants.add(f"{parts[0][0]}. {parts[-1]}".lower())
        
        # Just last name
        variants.add(parts[-1])
        variants.add(parts[-1].lower())
        
        # Just first name
        variants.add(parts[0])
        variants.add(parts[0].lower())
    
    return variants


def obscure_text(text: str, name_variants: Set[str]) -> str:
    """
    Obscure all occurrences of name variants in a text.
    
    Args:
        text: The text to obscure
        name_variants: Set of name variants to obscure
        
    Returns:
        The text with name variants obscured
    """
    if not text or not name_variants:
        return text
    
    # Sort variants by length (descending) to replace longer variants first
    sorted_variants = sorted(name_variants, key=len, reverse=True)
    
    # Tokenize the text to handle word boundaries properly
    tokens = word_tokenize(text)
    obscured_tokens = []
    
    i = 0
    while i < len(tokens):
        # Try to match multi-token name variants
        matched = False
        for variant in sorted_variants:
            variant_tokens = word_tokenize(variant)
            if len(variant_tokens) > 1 and i + len(variant_tokens) <= len(tokens):
                # Check if the next tokens match the variant
                potential_match = ' '.join(tokens[i:i+len(variant_tokens)])
                if potential_match.lower() == variant.lower():
                    # Replace with obscured version
                    obscured_tokens.append('█' * len(variant_tokens[0]))
                    for j in range(1, len(variant_tokens)):
                        obscured_tokens.append('█' * len(variant_tokens[j]))
                    i += len(variant_tokens)
                    matched = True
                    break
        
        # If no multi-token match, check single token
        if not matched:
            token = tokens[i]
            if any(token.lower() == variant.lower() for variant in sorted_variants):
                obscured_tokens.append('█' * len(token))
            else:
                obscured_tokens.append(token)
            i += 1
    
    # Reconstruct the text with proper spacing
    result = ''
    for j, token in enumerate(obscured_tokens):
        if j > 0 and not (obscured_tokens[j-1].endswith(('.', ',', ':', ';', '!', '?')) or token.startswith(('.', ',', ':', ';', '!', '?'))):
            result += ' '
        result += token
    
    return result
