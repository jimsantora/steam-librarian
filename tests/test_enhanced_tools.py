#!/usr/bin/env python3
"""Test enhanced MCP tools with proper input/output schemas and structured responses."""

import sys
import unittest
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp.types import Annotations, CallToolResult, TextContent, ToolAnnotations


class TestEnhancedTools(unittest.TestCase):
    """Test cases for enhanced MCP tools with structured responses and proper annotations."""

    def test_call_tool_result_structure(self):
        """Test that CallToolResult follows MCP specification structure."""
        # Test successful result with structured content
        result = CallToolResult(
            content=[
                TextContent(
                    type="text",
                    text="Test tool result",
                    annotations=Annotations(audience=["user"], priority=0.9)
                )
            ],
            structuredContent={"games": [{"name": "Portal", "score": 95}], "total": 1},
            isError=False
        )

        # Verify structure
        self.assertIsInstance(result.content, list)
        self.assertEqual(len(result.content), 1)
        self.assertIsInstance(result.content[0], TextContent)
        self.assertEqual(result.content[0].type, "text")
        self.assertEqual(result.content[0].text, "Test tool result")

        # Verify annotations
        self.assertIsNotNone(result.content[0].annotations)
        self.assertEqual(result.content[0].annotations.audience, ["user"])
        self.assertEqual(result.content[0].annotations.priority, 0.9)

        # Verify structured content
        self.assertIsNotNone(result.structuredContent)
        self.assertIn("games", result.structuredContent)
        self.assertIn("total", result.structuredContent)
        self.assertEqual(result.structuredContent["total"], 1)

        # Verify error flag
        self.assertFalse(result.isError)

    def test_call_tool_result_error(self):
        """Test that CallToolResult properly handles error responses."""
        error_result = CallToolResult(
            content=[
                TextContent(
                    type="text",
                    text="User error: No default user configured",
                    annotations=Annotations(audience=["assistant"], priority=0.9)
                )
            ],
            isError=True
        )

        # Verify error structure
        self.assertTrue(error_result.isError)
        self.assertEqual(error_result.content[0].text, "User error: No default user configured")
        self.assertEqual(error_result.content[0].annotations.audience, ["assistant"])

    def test_tool_annotations_structure(self):
        """Test that ToolAnnotations follow MCP specification."""
        annotations = ToolAnnotations(
            title="Advanced Game Discovery",
            readOnlyHint=True,
            idempotentHint=True,
            destructiveHint=False
        )

        # Verify annotation structure
        self.assertEqual(annotations.title, "Advanced Game Discovery")
        self.assertTrue(annotations.readOnlyHint)
        self.assertTrue(annotations.idempotentHint)
        self.assertFalse(annotations.destructiveHint)

    def test_text_content_with_annotations(self):
        """Test that TextContent with annotations works correctly in tool results."""
        content = TextContent(
            type="text",
            text="Enhanced tool response with proper annotations",
            annotations=Annotations(
                audience=["user", "assistant"],
                priority=0.8
            )
        )

        # Verify content structure
        self.assertEqual(content.type, "text")
        self.assertEqual(content.text, "Enhanced tool response with proper annotations")

        # Verify annotations
        self.assertIsNotNone(content.annotations)
        self.assertEqual(content.annotations.audience, ["user", "assistant"])
        self.assertEqual(content.annotations.priority, 0.8)

    def test_structured_content_format(self):
        """Test that structured content follows expected patterns."""
        # Test search results structure
        search_results = {
            "results": [
                {
                    "name": "Portal",
                    "metacritic": 95,
                    "platforms": {"windows": True, "mac": False, "linux": False, "vr": False},
                    "playtime": 12.5,
                    "recent_playtime": 0,
                    "genres": ["Puzzle", "Platformer"],
                    "tags": ["Great Soundtrack", "Atmospheric"]
                }
            ],
            "query": "portal",
            "filters": {},
            "sort_by": "relevance",
            "total": 1,
            "limited": False
        }

        # Verify structure
        self.assertIn("results", search_results)
        self.assertIn("query", search_results)
        self.assertIn("total", search_results)
        self.assertIsInstance(search_results["results"], list)
        self.assertEqual(search_results["total"], 1)

        # Verify game structure
        game = search_results["results"][0]
        required_fields = ["name", "metacritic", "platforms", "playtime", "genres"]
        for field in required_fields:
            self.assertIn(field, game)

    def test_error_handling_patterns(self):
        """Test various error handling patterns for tools."""
        # Test user resolution error
        user_error = CallToolResult(
            content=[
                TextContent(
                    type="text",
                    text="User error: No default user configured",
                    annotations=Annotations(audience=["assistant"], priority=0.9)
                )
            ],
            isError=True
        )

        # Test JSON parsing error
        json_error = CallToolResult(
            content=[
                TextContent(
                    type="text",
                    text="Invalid filters format. Please provide valid JSON.",
                    annotations=Annotations(audience=["assistant"], priority=0.8)
                )
            ],
            isError=True
        )

        # Test empty results (not an error)
        empty_results = CallToolResult(
            content=[
                TextContent(
                    type="text",
                    text="No games found matching 'nonexistent'",
                    annotations=Annotations(audience=["assistant"], priority=0.7)
                )
            ],
            structuredContent={"results": [], "query": "nonexistent", "filters": {}, "total": 0},
            isError=False
        )

        # Verify error patterns
        self.assertTrue(user_error.isError)
        self.assertTrue(json_error.isError)
        self.assertFalse(empty_results.isError)  # Empty results are not errors

        # Verify all have proper annotations
        for result in [user_error, json_error, empty_results]:
            self.assertIsNotNone(result.content[0].annotations)
            self.assertIn("assistant", result.content[0].annotations.audience)

    def test_audience_targeting(self):
        """Test that audience targeting works correctly for different content types."""
        # User-facing content (high priority)
        user_content = TextContent(
            type="text",
            text="Here are your search results:",
            annotations=Annotations(audience=["user"], priority=0.9)
        )

        # Assistant-facing content (medium priority)
        assistant_content = TextContent(
            type="text",
            text="Query processed successfully",
            annotations=Annotations(audience=["assistant"], priority=0.6)
        )

        # Mixed audience content (high priority)
        mixed_content = TextContent(
            type="text",
            text="Game recommendation results with detailed analysis",
            annotations=Annotations(audience=["user", "assistant"], priority=0.8)
        )

        # Verify audience targeting
        self.assertEqual(user_content.annotations.audience, ["user"])
        self.assertEqual(assistant_content.annotations.audience, ["assistant"])
        self.assertEqual(mixed_content.annotations.audience, ["user", "assistant"])

        # Verify priority ordering
        self.assertGreater(user_content.annotations.priority, assistant_content.annotations.priority)
        self.assertGreater(mixed_content.annotations.priority, assistant_content.annotations.priority)

    def test_structured_vs_unstructured_content(self):
        """Test the relationship between structured and unstructured content."""
        # Tool result with both structured and unstructured content
        result = CallToolResult(
            content=[
                TextContent(
                    type="text",
                    text="Found 3 games matching your criteria:\n• Portal (95/100)\n• Portal 2 (95/100)\n• Half-Life 2 (96/100)",
                    annotations=Annotations(audience=["user"], priority=0.9)
                )
            ],
            structuredContent={
                "results": [
                    {"name": "Portal", "score": 95},
                    {"name": "Portal 2", "score": 95},
                    {"name": "Half-Life 2", "score": 96}
                ],
                "total": 3
            },
            isError=False
        )

        # Verify both content types are present
        self.assertIsNotNone(result.content)
        self.assertIsNotNone(result.structuredContent)

        # Verify structured content matches unstructured count
        text_mentions = result.content[0].text.count("•")
        structured_count = len(result.structuredContent["results"])
        self.assertEqual(text_mentions, structured_count)
        self.assertEqual(result.structuredContent["total"], 3)


def main():
    """Run the enhanced tools tests."""
    unittest.main(verbosity=2)


if __name__ == "__main__":
    main()
