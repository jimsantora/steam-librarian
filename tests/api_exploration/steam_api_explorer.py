#!/usr/bin/env python3
"""
Steam Store API Explorer

Explores current Steam Store API response structure to identify available fields
for game metadata including controller support, VR support, and Metacritic scores.
Useful for understanding what data can be extracted from the API.
"""

import json
import time

import requests


def get_app_details(appid: int) -> dict | None:
    """Get detailed information about a specific app/game from Store API"""
    url = "https://store.steampowered.com/api/appdetails"
    params = {"appids": appid, "cc": "us", "l": "english"}

    try:
        response = requests.get(url, params=params, timeout=30)

        if response.status_code == 200:
            data = response.json()
            if str(appid) in data and data[str(appid)].get("success"):
                return data[str(appid)]["data"]
        else:
            print(f"Store API returned {response.status_code} for appid {appid}")

    except Exception as e:
        print(f"Error fetching app details for {appid}: {e}")

    return None

def explore_api_fields():
    """Explore current Steam Store API fields for a few popular games"""

    # Test with a few different types of games
    test_games = [
        (440, "Team Fortress 2"),           # Popular F2P game
        (271590, "Grand Theft Auto V"),     # Popular AAA game
        (1245620, "ELDEN RING"),           # Recent popular game
        (1085660, "Destiny 2"),            # Game with VR support
        (250820, "SteamVR")                # VR application
    ]

    for appid, name in test_games:
        print(f"\n{'='*60}")
        print(f"Exploring {name} (AppID: {appid})")
        print(f"{'='*60}")

        app_details = get_app_details(appid)
        if app_details:
            print(f"All available keys: {sorted(app_details.keys())}")

            # Check categories for controller/VR support
            if 'categories' in app_details:
                print("\nCategories:")
                for cat in app_details['categories']:
                    print(f"  ID {cat.get('id', 'N/A')}: {cat.get('description', 'N/A')}")

            # Check platforms
            if 'platforms' in app_details:
                print(f"\nPlatforms: {app_details['platforms']}")

            # Look for any deck/controller/vr related fields
            print("\nSearching for Steam Deck/Controller/VR fields:")
            for key, value in app_details.items():
                if any(keyword in str(key).lower() for keyword in ['deck', 'controller', 'vr', 'steam_deck']):
                    print(f"  {key}: {value}")

            # Check if controller_support field exists
            if 'controller_support' in app_details:
                print(f"\nController Support: {app_details['controller_support']}")

            print(f"\nFull JSON saved to {name.replace(' ', '_').replace(':', '')}_details.json")
            with open(f"{name.replace(' ', '_').replace(':', '')}_details.json", 'w') as f:
                json.dump(app_details, f, indent=2)
        else:
            print(f"Failed to get details for {name}")

        # Rate limiting
        time.sleep(2)

if __name__ == "__main__":
    explore_api_fields()
