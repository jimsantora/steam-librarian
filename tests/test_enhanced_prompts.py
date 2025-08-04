#!/usr/bin/env python3
"""Test enhanced MCP prompts with proper annotations and argument handling."""

import sys
import unittest
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp.server.fastmcp.prompts import base
from mcp.types import Annotations, ResourceLink, TextContent


class TestEnhancedPrompts(unittest.TestCase):
    """Test cases for enhanced MCP prompts with annotations and proper structure."""

    def test_text_content_with_annotations(self):
        """Test that TextContent with annotations works correctly."""
        content = TextContent(
            type="text",
            text="Test message with annotations",
            annotations=Annotations(audience=["user"], priority=0.9)
        )

        # Verify structure
        self.assertEqual(content.type, "text")
        self.assertEqual(content.text, "Test message with annotations")
        self.assertIsNotNone(content.annotations)
        self.assertEqual(content.annotations.audience, ["user"])
        self.assertEqual(content.annotations.priority, 0.9)

    def test_fastmcp_message_accepts_text_content(self):
        """Test that FastMCP base messages accept TextContent with annotations."""
        content = TextContent(
            type="text",
            text="Test message",
            annotations=Annotations(audience=["user"], priority=0.8)
        )

        # Create FastMCP message
        message = base.UserMessage(content)

        # Verify message structure
        self.assertEqual(message.role, "user")
        self.assertEqual(message.content, content)
        self.assertEqual(message.content.text, "Test message")
        self.assertEqual(message.content.annotations.priority, 0.8)

    def test_resource_link_structure(self):
        """Test that ResourceLink structure is correct for prompts."""
        resource = ResourceLink(
            type="resource_link",
            uri="library://games/unplayed",
            name="unplayed_games",
            description="Test unplayed games resource",
            mimeType="application/json"
        )

        # Verify structure
        self.assertEqual(str(resource.uri), "library://games/unplayed")
        self.assertEqual(resource.name, "unplayed_games")
        self.assertEqual(resource.description, "Test unplayed games resource")
        self.assertEqual(resource.mimeType, "application/json")
        self.assertEqual(resource.type, "resource_link")

        # Test it works in FastMCP message
        message = base.UserMessage(resource)
        self.assertEqual(message.role, "user")
        self.assertEqual(message.content, resource)

    def test_annotation_compliance(self):
        """Test that annotations follow MCP specification."""
        # Test valid audience values
        valid_audiences = [["user"], ["assistant"], ["user", "assistant"]]
        for audience in valid_audiences:
            with self.subTest(audience=audience):
                annotation = Annotations(audience=audience, priority=0.5)
                self.assertEqual(annotation.audience, audience)

        # Test priority range
        valid_priorities = [0.0, 0.5, 1.0]
        for priority in valid_priorities:
            with self.subTest(priority=priority):
                annotation = Annotations(audience=["user"], priority=priority)
                self.assertEqual(annotation.priority, priority)

    def test_prompt_message_structure(self):
        """Test that our prompt messages follow proper MCP structure."""
        # Create a sample prompt message like our enhanced prompts
        messages = [
            base.UserMessage(
                TextContent(
                    type="text",
                    text="I need games suitable for my 8-year-old child.",
                    annotations=Annotations(audience=["user"], priority=0.9)
                )
            ),
            base.AssistantMessage(
                TextContent(
                    type="text",
                    text="I'll find age-appropriate games using our family-safe filtering system.",
                    annotations=Annotations(audience=["assistant"], priority=0.8)
                )
            ),
            base.UserMessage(
                ResourceLink(
                    type="resource_link",
                    uri="library://games/unplayed",
                    name="unplayed_games",
                    description="Your highly-rated unplayed games",
                    mimeType="application/json"
                )
            )
        ]

        # Verify message structure
        self.assertEqual(len(messages), 3)

        # First message - user with text content
        self.assertEqual(messages[0].role, "user")
        self.assertIsInstance(messages[0].content, TextContent)
        self.assertEqual(messages[0].content.annotations.audience, ["user"])

        # Second message - assistant with text content
        self.assertEqual(messages[1].role, "assistant")
        self.assertIsInstance(messages[1].content, TextContent)
        self.assertEqual(messages[1].content.annotations.audience, ["assistant"])

        # Third message - user with resource link
        self.assertEqual(messages[2].role, "user")
        self.assertIsInstance(messages[2].content, ResourceLink)

    def test_priority_ordering(self):
        """Test that priority annotations work as expected."""
        high_priority = TextContent(
            type="text",
            text="High priority message",
            annotations=Annotations(audience=["user"], priority=0.9)
        )

        medium_priority = TextContent(
            type="text",
            text="Medium priority message",
            annotations=Annotations(audience=["assistant"], priority=0.5)
        )

        low_priority = TextContent(
            type="text",
            text="Low priority message",
            annotations=Annotations(audience=["assistant"], priority=0.1)
        )

        # Verify priority values
        self.assertGreater(high_priority.annotations.priority, medium_priority.annotations.priority)
        self.assertGreater(medium_priority.annotations.priority, low_priority.annotations.priority)

    def test_prompt_argument_structure(self):
        """Test understanding of how FastMCP should handle prompt arguments."""
        # Test that our enhanced prompts have proper docstring argument documentation
        # This helps FastMCP auto-generate PromptArgument objects

        def sample_prompt(child_age: int = 8, game_type: str = "family") -> list[base.Message]:
            """Sample prompt for testing.
            
            Args:
                child_age: Age of the child in years (default: 8)
                game_type: Type of games to recommend (default: "family")
            """
            return []

        # Verify function has proper signature and docstring
        import inspect
        sig = inspect.signature(sample_prompt)

        # Check parameters
        self.assertIn('child_age', sig.parameters)
        self.assertIn('game_type', sig.parameters)
        self.assertEqual(sig.parameters['child_age'].default, 8)
        self.assertEqual(sig.parameters['game_type'].default, "family")

        # Check docstring format
        self.assertIn("Args:", sample_prompt.__doc__)
        self.assertIn("child_age:", sample_prompt.__doc__)
        self.assertIn("game_type:", sample_prompt.__doc__)

    def test_enhanced_prompt_integration(self):
        """Test that enhanced prompt structure integrates properly."""
        # Simulate our enhanced prompt structure
        def enhanced_family_games(child_age: int = 8) -> list[base.Message]:
            """Get age-appropriate game recommendations for family gaming.
            
            Args:
                child_age: Age of the child in years (used for ESRB/PEGI rating filtering, default: 8)
            """
            return [
                base.UserMessage(
                    TextContent(
                        type="text",
                        text=f"I need games suitable for my {child_age}-year-old child. What do you recommend?",
                        annotations=Annotations(audience=["user"], priority=0.9)
                    )
                ),
                base.AssistantMessage(
                    TextContent(
                        type="text",
                        text=f"I'll find age-appropriate games for a {child_age}-year-old using our family-safe filtering system.",
                        annotations=Annotations(audience=["assistant"], priority=0.8)
                    )
                )
            ]

        # Test prompt execution
        messages = enhanced_family_games(10)

        self.assertEqual(len(messages), 2)
        self.assertIn("10-year-old", messages[0].content.text)
        self.assertIn("10-year-old", messages[1].content.text)

        # Verify annotations are preserved
        self.assertEqual(messages[0].content.annotations.audience, ["user"])
        self.assertEqual(messages[1].content.annotations.audience, ["assistant"])


def main():
    """Run the enhanced prompt tests."""
    unittest.main(verbosity=2)


if __name__ == "__main__":
    main()
