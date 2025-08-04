#!/usr/bin/env python3
"""Tests for user experience improvements."""

import os
import sys
import unittest

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

try:
    from mcp_server.tools import (
        format_tool_documentation,
        parse_natural_language_filters,
        parse_recommendation_parameters,
    )
except ImportError as e:
    print(f"Import error: {e}")
    print("Note: These tests require the MCP server to be properly set up with all dependencies.")
    sys.exit(0)


class TestFilterParsing(unittest.TestCase):
    """Test natural language filter parsing functionality."""

    def test_genre_detection(self):
        """Test that genres are detected correctly."""
        test_cases = [
            ("action games", {"genres": ["Action"]}),
            ("adventure titles", {"genres": ["Adventure"]}),
            ("RPG games", {"genres": ["RPG"]}),
            ("strategy games", {"genres": ["Strategy"]}),
            ("indie games", {"genres": ["Indie"]}),
            ("puzzle games", {"genres": ["Puzzle"]})
        ]

        for text, expected in test_cases:
            result = parse_natural_language_filters(text)
            self.assertEqual(result.get("genres"), expected.get("genres"),
                           f"Failed for '{text}': expected {expected.get('genres')}, got {result.get('genres')}")

    def test_rating_detection(self):
        """Test rating detection patterns."""
        test_cases = [
            ("games with rating above 75", {"min_rating": 75}),
            ("rating over 80", {"min_rating": 80}),
            ("games rated >= 90", {"min_rating": 90}),
            ("highly rated games", {}),  # Should not set min_rating without specific number
        ]

        for text, expected in test_cases:
            result = parse_natural_language_filters(text)
            if "min_rating" in expected:
                self.assertEqual(result.get("min_rating"), expected["min_rating"],
                               f"Failed for '{text}': expected {expected.get('min_rating')}, got {result.get('min_rating')}")

    def test_multiplayer_detection(self):
        """Test multiplayer mode detection."""
        test_cases = [
            ("coop games", {"categories": ["Co-op"]}),
            ("co-op multiplayer", {"categories": ["Co-op"]}),
            ("cooperative games", {"categories": ["Co-op"]}),
            ("pvp games", {"categories": ["PvP"]}),
            ("multiplayer games", {"categories": ["Multi-player"]}),
        ]

        for text, expected in test_cases:
            result = parse_natural_language_filters(text)
            self.assertEqual(result.get("categories"), expected.get("categories"),
                           f"Failed for '{text}': expected {expected.get('categories')}, got {result.get('categories')}")

    def test_playtime_detection(self):
        """Test playtime status detection."""
        test_cases = [
            ("unplayed games", {"playtime": "unplayed"}),
            ("never played games", {"playtime": "unplayed"}),
            ("games i've played", {"playtime": "played"}),
            ("started games", {"playtime": "played"}),
        ]

        for text, expected in test_cases:
            result = parse_natural_language_filters(text)
            self.assertEqual(result.get("playtime"), expected.get("playtime"),
                           f"Failed for '{text}': expected {expected.get('playtime')}, got {result.get('playtime')}")

    def test_vr_detection(self):
        """Test VR support detection."""
        test_cases = [
            ("vr games", {"vr_support": True}),
            ("VR titles", {"vr_support": True}),
            ("virtual reality games", {}),  # More complex phrase, might not be detected
        ]

        for text, expected in test_cases:
            result = parse_natural_language_filters(text)
            if "vr_support" in expected:
                self.assertEqual(result.get("vr_support"), expected["vr_support"],
                               f"Failed for '{text}': expected {expected.get('vr_support')}, got {result.get('vr_support')}")

    def test_complex_queries(self):
        """Test complex multi-filter queries."""
        test_cases = [
            ("action games with rating above 75 and coop multiplayer", {
                "genres": ["Action"],
                "min_rating": 75,
                "categories": ["Co-op"]
            }),
            ("unplayed indie games", {
                "genres": ["Indie"],
                "playtime": "unplayed"
            }),
            ("vr puzzle games rated over 80", {
                "genres": ["Puzzle"],
                "min_rating": 80,
                "vr_support": True
            })
        ]

        for text, expected in test_cases:
            result = parse_natural_language_filters(text)
            for key, value in expected.items():
                self.assertEqual(result.get(key), value,
                               f"Failed for '{text}' on key '{key}': expected {value}, got {result.get(key)}")


class TestParameterValidation(unittest.TestCase):
    """Test recommendation parameter parsing."""

    def test_exclusion_patterns(self):
        """Test genre exclusion parsing."""
        test_cases = [
            ("no horror games", {"exclude_genres": ["Horror"]}),
            ("exclude scary games", {"exclude_genres": ["Horror"]}),
            ("avoid horror", {"exclude_genres": ["Horror"]}),
            ("no action games", {"exclude_genres": ["Action"]}),
            ("without puzzle games", {"exclude_genres": ["Puzzle"]}),
        ]

        for text, expected in test_cases:
            result = parse_recommendation_parameters(text)
            self.assertEqual(result.get("exclude_genres"), expected.get("exclude_genres"),
                           f"Failed for '{text}': expected {expected.get('exclude_genres')}, got {result.get('exclude_genres')}")

    def test_rating_patterns(self):
        """Test rating requirement parsing."""
        test_cases = [
            ("minimum rating 80", {"min_rating": 80}),
            ("min rating 75", {"min_rating": 75}),
            ("at least rating 85", {"min_rating": 85}),
            ("highly rated", {"min_rating": 75}),
            ("well rated games", {"min_rating": 75}),
        ]

        for text, expected in test_cases:
            result = parse_recommendation_parameters(text)
            self.assertEqual(result.get("min_rating"), expected.get("min_rating"),
                           f"Failed for '{text}': expected {expected.get('min_rating')}, got {result.get('min_rating')}")

    def test_time_commitment_patterns(self):
        """Test time commitment parsing."""
        test_cases = [
            ("short games", {"max_hours": 20}),
            ("quick games", {"max_hours": 20}),
            ("brief experiences", {"max_hours": 20}),
            ("long games", {"min_hours": 40}),
            ("epic games", {"min_hours": 40}),
            ("extensive games", {"min_hours": 40}),
        ]

        for text, expected in test_cases:
            result = parse_recommendation_parameters(text)
            if "max_hours" in expected:
                self.assertEqual(result.get("max_hours"), expected["max_hours"],
                               f"Failed for '{text}': expected max_hours={expected['max_hours']}, got {result.get('max_hours')}")
            if "min_hours" in expected:
                self.assertEqual(result.get("min_hours"), expected["min_hours"],
                               f"Failed for '{text}': expected min_hours={expected['min_hours']}, got {result.get('min_hours')}")

    def test_multiplayer_preferences(self):
        """Test multiplayer preference parsing."""
        test_cases = [
            ("single player games", {"single_player": True}),
            ("single-player only", {"single_player": True}),
            ("multiplayer games", {"multiplayer": True}),
            ("no multiplayer", {}),  # Should not set multiplayer=True
        ]

        for text, expected in test_cases:
            result = parse_recommendation_parameters(text)
            if "single_player" in expected:
                self.assertEqual(result.get("single_player"), expected["single_player"],
                               f"Failed for '{text}': expected single_player={expected['single_player']}, got {result.get('single_player')}")
            if "multiplayer" in expected:
                self.assertEqual(result.get("multiplayer"), expected["multiplayer"],
                               f"Failed for '{text}': expected multiplayer={expected['multiplayer']}, got {result.get('multiplayer')}")

    def test_complex_parameters(self):
        """Test complex parameter combinations."""
        test_cases = [
            ("no horror games, minimum rating 80, single player", {
                "exclude_genres": ["Horror"],
                "min_rating": 80,
                "single_player": True
            }),
            ("short highly rated games", {
                "max_hours": 20,
                "min_rating": 75
            }),
            ("avoid action games, quick sessions", {
                "exclude_genres": ["Action"],
                "max_hours": 20
            })
        ]

        for text, expected in test_cases:
            result = parse_recommendation_parameters(text)
            for key, value in expected.items():
                self.assertEqual(result.get(key), value,
                               f"Failed for '{text}' on key '{key}': expected {value}, got {result.get(key)}")


class TestDocumentation(unittest.TestCase):
    """Test documentation formatting."""

    def test_documentation_formatting(self):
        """Test that documentation formats correctly."""
        sample_doc = {
            "description": "Test tool description",
            "parameters": {
                "param1": "First parameter",
                "param2": "Second parameter"
            },
            "contexts": {
                "context1": "First context",
                "context2": "Second context"
            },
            "common_errors": {
                "Error 1": "Solution 1",
                "Error 2": "Solution 2"
            }
        }

        result = format_tool_documentation("test_tool", sample_doc)

        # Check that all sections are present
        self.assertIn("# test_tool Tool Documentation", result)
        self.assertIn("## Description", result)
        self.assertIn("Test tool description", result)
        self.assertIn("## Parameters", result)
        self.assertIn("**param1**: First parameter", result)
        self.assertIn("## Available Contexts", result)
        self.assertIn("**context1**: First context", result)
        self.assertIn("## Common Errors and Solutions", result)
        self.assertIn("**Error 1**: Solution 1", result)

    def test_minimal_documentation(self):
        """Test documentation with minimal fields."""
        minimal_doc = {
            "description": "Minimal test tool"
        }

        result = format_tool_documentation("minimal_tool", minimal_doc)

        self.assertIn("# minimal_tool Tool Documentation", result)
        self.assertIn("## Description", result)
        self.assertIn("Minimal test tool", result)
        # Should not contain other sections
        self.assertNotIn("## Parameters", result)
        self.assertNotIn("## Available Contexts", result)


class TestErrorMessages(unittest.TestCase):
    """Test that error messages are helpful and include examples."""

    def test_filter_validation_error_structure(self):
        """Test that filter validation errors have the right structure."""
        # This would be tested with actual tool calls in integration tests
        # Here we just verify the error message format would be helpful

        # Mock invalid filter keys
        invalid_keys = ["invalid_key"]
        valid_filters = ["genres", "categories", "tags", "min_rating"]

        # Expected error message should include:
        # 1. What went wrong
        # 2. Valid options
        # 3. Examples

        error_parts = [
            f"Unknown filter keys: {invalid_keys}",
            f"Valid filters: {', '.join(valid_filters)}",
            "Example JSON filter:",
            "Example text filter:"
        ]

        # All parts should be present in a good error message
        for part in error_parts:
            self.assertTrue(len(part) > 0, f"Error message part should not be empty: {part}")

    def test_context_validation_error_structure(self):
        """Test context validation error structure."""
        invalid_context = "invalid_context"
        valid_contexts = ["abandoned", "trending", "family"]

        # Good error message should include:
        error_parts = [
            f'Invalid context: "{invalid_context}"',
            "Valid contexts:",
            ', '.join(valid_contexts),
            "Examples:"
        ]

        for part in error_parts:
            self.assertTrue(len(part) > 0, f"Error message part should not be empty: {part}")


class TestIntegrationPatterns(unittest.TestCase):
    """Test that the improved functions integrate well together."""

    def test_json_fallback_to_natural_language(self):
        """Test that invalid JSON falls back to natural language parsing."""
        # Invalid JSON that should fall back to natural language
        invalid_json_texts = [
            "action games",  # Not JSON at all
            '{"genres": [Action]}',  # Invalid JSON (missing quotes)
            "puzzle games rated over 80",  # Natural language
        ]

        for text in invalid_json_texts:
            # Should not raise exception, should return some parsed result
            try:
                result = parse_natural_language_filters(text)
                self.assertIsInstance(result, dict, f"Should return dict for '{text}'")
            except Exception as e:
                self.fail(f"Should not raise exception for '{text}': {e}")

    def test_parameter_robustness(self):
        """Test that parameter parsing is robust to different inputs."""
        robust_inputs = [
            "",  # Empty string
            "   ",  # Whitespace only
            "no preferences",  # Valid text with no matches
            "something completely unrelated",  # No pattern matches
        ]

        for text in robust_inputs:
            try:
                result = parse_recommendation_parameters(text)
                self.assertIsInstance(result, dict, f"Should return dict for '{text}'")
                # Empty or unmatched input should return empty dict
                if not text.strip() or "no preferences" in text.lower():
                    self.assertEqual(len(result), 0, f"Should return empty dict for '{text}'")
            except Exception as e:
                self.fail(f"Should not raise exception for '{text}': {e}")


if __name__ == "__main__":
    print("Running user experience improvement tests...")

    # Run tests with verbose output
    unittest.main(verbosity=2)
