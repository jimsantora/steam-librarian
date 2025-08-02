#!/usr/bin/env python3
"""
Steam Tags Extractor

Extracts user-generated tags from Steam store pages by parsing the HTML.
This uses the official Steam store pages which contain tag data embedded in the HTML.
"""

import requests
import re
import time
from typing import List, Dict, Optional

class SteamTagsExtractor:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
        })
        self.rate_limit_delay = 1.0  # Seconds between requests
        self.last_request_time = 0

    def _rate_limit(self):
        """Implement rate limiting to be respectful to Steam's servers"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.rate_limit_delay:
            time.sleep(self.rate_limit_delay - time_since_last)
        self.last_request_time = time.time()

    def get_game_tags(self, app_id: int) -> Optional[List[str]]:
        """
        Extract user-generated tags for a specific Steam game.
        
        Args:
            app_id: Steam application ID
            
        Returns:
            List of tag strings, or None if extraction failed
        """
        self._rate_limit()
        
        url = f"https://store.steampowered.com/app/{app_id}/"
        
        try:
            response = self.session.get(url, timeout=30)
            
            if response.status_code != 200:
                print(f"Failed to get page for app {app_id}: status {response.status_code}")
                return None
                
            return self._extract_tags_from_html(response.text)
            
        except Exception as e:
            print(f"Error fetching tags for app {app_id}: {e}")
            return None

    def _extract_tags_from_html(self, html_content: str) -> List[str]:
        """
        Extract tags from Steam store page HTML.
        
        Args:
            html_content: Raw HTML content from Steam store page
            
        Returns:
            List of tag strings
        """
        tags = []
        
        # Pattern to match the tag links within the popular_tags section
        # Looking for: <a href="..." class="app_tag" ...>Tag Name</a>
        pattern = r'<a[^>]+class="app_tag"[^>]*>(.*?)</a>'
        
        matches = re.findall(pattern, html_content, re.DOTALL | re.IGNORECASE)
        
        for match in matches:
            # Clean up the tag text (remove extra whitespace and newlines)
            tag = re.sub(r'\s+', ' ', match.strip())
            if tag and tag != '+':  # Skip the '+' button
                tags.append(tag)
        
        return tags

    def test_tag_extraction(self):
        """Test tag extraction on a few popular games"""
        test_games = [
            (440, "Team Fortress 2"),
            (271590, "Grand Theft Auto V"),
            (1245620, "ELDEN RING"),
            (3224770, "Horse Life: Adventures"),  # The game from your example
            (1085660, "Destiny 2"),
        ]
        
        print("Testing Steam tag extraction...\n")
        
        for app_id, name in test_games:
            print(f"{'='*60}")
            print(f"Testing: {name} (App ID: {app_id})")
            print(f"{'='*60}")
            
            tags = self.get_game_tags(app_id)
            
            if tags:
                print(f"Found {len(tags)} tags:")
                for i, tag in enumerate(tags, 1):
                    print(f"  {i:2d}. {tag}")
                    
                # Show some interesting tags
                interesting_tags = []
                for tag in tags:
                    if any(keyword in tag.lower() for keyword in 
                          ['roguelike', 'roguelite', 'arcade', 'puzzle', 'card', 'strategy']):
                        interesting_tags.append(tag)
                
                if interesting_tags:
                    print(f"\nInteresting gameplay tags: {', '.join(interesting_tags)}")
                        
            else:
                print("No tags found or extraction failed")
            
            print()

if __name__ == "__main__":
    extractor = SteamTagsExtractor()
    extractor.test_tag_extraction()