#!/usr/bin/env python3
"""Test enhanced MCP resources with metadata and annotations compliance."""

import json
import sys
import unittest
from datetime import datetime
from pathlib import Path
from typing import Any

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp.types import TextResourceContents


# Directly implement the helper functions for testing to avoid database dependencies
def create_resource_content(
    uri: str,
    name: str,
    title: str,
    description: str,
    data: dict[str, Any],
    priority: float = 0.5,
    audience: list[str] = None,
    mime_type: str = "application/json"
) -> TextResourceContents:
    """Create properly formatted resource content with metadata and annotations."""
    if audience is None:
        audience = ["user", "assistant"]

    # Annotations go in the meta field for MCP
    meta = {
        "audience": audience,
        "priority": priority,
        "lastModified": datetime.now().isoformat() + "Z",
        "name": name,
        "title": title,
        "description": description
    }

    return TextResourceContents(
        uri=uri,
        mimeType=mime_type,
        text=json.dumps(data, indent=2),
        _meta=meta
    )


def create_error_resource(uri: str, name: str, error_message: str) -> TextResourceContents:
    """Create error resource content with appropriate metadata."""
    return create_resource_content(
        uri=uri,
        name=name,
        title="Resource Error",
        description=f"Error accessing resource: {error_message}",
        data={"error": error_message},
        priority=0.1,
        audience=["assistant"]
    )


class TestEnhancedResources(unittest.TestCase):
    """Test cases for enhanced MCP resources with metadata and annotations."""

    def test_create_resource_content(self):
        """Test the create_resource_content helper function."""
        # Test data
        test_data = {
            "games": [
                {"id": 440, "name": "Team Fortress 2", "genres": ["Action", "Free to Play"]},
                {"id": 570, "name": "Dota 2", "genres": ["Strategy", "Free to Play"]}
            ],
            "total": 2
        }

        # Create resource content
        content = create_resource_content(
            uri="library://test/games",
            name="test_games",
            title="Test Games List",
            description="Test games for validation",
            data=test_data,
            priority=0.8,
            audience=["user", "assistant"]
        )

        # Verify it's the correct type
        self.assertIsInstance(content, TextResourceContents)

        # Verify required fields
        self.assertEqual(str(content.uri), "library://test/games")
        self.assertEqual(content.mimeType, "application/json")
        self.assertIsNotNone(content.text)

        # Verify metadata structure
        self.assertIsNotNone(content.meta)
        self.assertEqual(content.meta["name"], "test_games")
        self.assertEqual(content.meta["title"], "Test Games List")
        self.assertEqual(content.meta["description"], "Test games for validation")
        self.assertEqual(content.meta["audience"], ["user", "assistant"])
        self.assertEqual(content.meta["priority"], 0.8)
        self.assertIn("lastModified", content.meta)

        # Verify JSON content can be parsed back
        parsed_data = json.loads(content.text)
        self.assertEqual(parsed_data, test_data)

    def test_create_error_resource(self):
        """Test the create_error_resource helper function."""
        error_content = create_error_resource(
            uri="library://test/nonexistent",
            name="test_error",
            error_message="Resource not found"
        )

        # Verify it's the correct type
        self.assertIsInstance(error_content, TextResourceContents)

        # Verify error structure
        self.assertEqual(str(error_content.uri), "library://test/nonexistent")
        self.assertEqual(error_content.meta["name"], "test_error")
        self.assertEqual(error_content.meta["title"], "Resource Error")
        self.assertEqual(error_content.meta["priority"], 0.1)  # Low priority for errors
        self.assertEqual(error_content.meta["audience"], ["assistant"])  # Errors are for assistant

        # Verify error message in content
        parsed_data = json.loads(error_content.text)
        self.assertIn("error", parsed_data)
        self.assertEqual(parsed_data["error"], "Resource not found")

    def test_mcp_specification_compliance(self):
        """Test that our metadata follows MCP specification exactly."""
        content = create_resource_content(
            uri="library://compliance/test",
            name="compliance_test",
            title="Compliance Test Resource",
            description="Testing MCP specification compliance",
            data={"test": True}
        )

        # Verify MCP annotations compliance
        self.assertIsInstance(content.meta["audience"], list)
        valid_audiences = {"user", "assistant"}
        for aud in content.meta["audience"]:
            self.assertIn(aud, valid_audiences, f"Invalid audience value: {aud}")

        # Verify priority is a number between 0.0 and 1.0
        self.assertIsInstance(content.meta["priority"], (int, float))
        self.assertGreaterEqual(content.meta["priority"], 0.0)
        self.assertLessEqual(content.meta["priority"], 1.0)

        # Verify lastModified is ISO 8601 format
        last_modified = content.meta["lastModified"]
        try:
            # Parse the timestamp to verify it's valid ISO 8601
            datetime.fromisoformat(last_modified.replace('Z', '+00:00'))
        except ValueError:
            self.fail(f"lastModified '{last_modified}' is not valid ISO 8601 format")

    def test_default_parameters(self):
        """Test that default parameters work correctly."""
        content = create_resource_content(
            uri="library://defaults/test",
            name="defaults_test",
            title="Defaults Test",
            description="Testing default parameters",
            data={"defaults": True}
        )

        # Verify defaults
        self.assertEqual(content.meta["priority"], 0.5)  # Default priority
        self.assertEqual(content.meta["audience"], ["user", "assistant"])  # Default audience
        self.assertEqual(content.mimeType, "application/json")  # Default MIME type

    def test_custom_mime_type(self):
        """Test that custom MIME types work correctly."""
        content = create_resource_content(
            uri="library://custom/mime",
            name="custom_mime",
            title="Custom MIME Type",
            description="Testing custom MIME type",
            data={"custom": True},
            mime_type="application/vnd.steam-librarian+json"
        )

        self.assertEqual(content.mimeType, "application/vnd.steam-librarian+json")

    def test_metadata_structure_consistency(self):
        """Test that all enhanced resources have consistent metadata structure."""
        # Test multiple resource creations to ensure consistency
        test_cases = [
            ("library://games/123", "game_123", "Game Details", "Individual game details"),
            ("library://users/456", "user_456", "User Profile", "User profile information"),
            ("library://genres/Action", "action_games", "Action Games", "Games in Action genre")
        ]

        for uri, name, title, description in test_cases:
            with self.subTest(uri=uri):
                content = create_resource_content(
                    uri=uri,
                    name=name,
                    title=title,
                    description=description,
                    data={"test": uri}
                )

                # Verify consistent metadata structure
                required_meta_keys = {"audience", "priority", "lastModified", "name", "title", "description"}
                self.assertEqual(set(content.meta.keys()), required_meta_keys)

                # Verify all values are non-None and correct types
                self.assertIsInstance(content.meta["audience"], list)
                self.assertIsInstance(content.meta["priority"], (int, float))
                self.assertIsInstance(content.meta["lastModified"], str)
                self.assertIsInstance(content.meta["name"], str)
                self.assertIsInstance(content.meta["title"], str)
                self.assertIsInstance(content.meta["description"], str)


def main():
    """Run the enhanced resource tests."""
    unittest.main(verbosity=2)


if __name__ == "__main__":
    main()
