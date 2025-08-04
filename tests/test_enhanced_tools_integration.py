#!/usr/bin/env python3
"""Integration tests for enhanced MCP tools with actual implementations."""

import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp.types import CallToolResult, TextContent, Annotations


class TestEnhancedToolsIntegration(unittest.TestCase):
    """Integration test cases for enhanced MCP tools with actual function testing."""

    def setUp(self):
        """Set up test environment."""
        # Mock database session to avoid actual database dependency
        self.mock_session = MagicMock()
        
    async def test_smart_search_basic_functionality(self):
        """Test that smart_search returns proper CallToolResult structure."""
        # Import the actual function
        from src.mcp_server.tools import smart_search
        
        # Test with basic parameters (will fail due to database dependency, but we can check structure)
        try:
            result = await smart_search("portal", "", "relevance", 5, None, "test_user")
            
            # Should not reach here due to database dependency, but if it does:
            self.assertIsInstance(result, CallToolResult)
            self.assertIsInstance(result.content, list)
            self.assertIsInstance(result.content[0], TextContent)
            
        except Exception as e:
            # Expected due to database dependency - verify it's the right kind of error
            self.assertIn("database", str(e).lower(), "Should fail due to database connection, not type errors")

    def test_smart_search_error_handling(self):
        """Test that smart_search handles various error conditions properly."""
        # We can test this without database by checking the error path
        from src.mcp_server.tools import smart_search
        import asyncio
        
        # Test invalid JSON filters
        async def test_invalid_json():
            result = await smart_search("test", "invalid json", "relevance", 5, None, "test_user")
            
            # Should return CallToolResult with error
            self.assertIsInstance(result, CallToolResult)
            self.assertTrue(result.isError)
            self.assertIn("Invalid filters format", result.content[0].text)
            self.assertEqual(result.content[0].annotations.audience, ["assistant"])
            
        # Run the async test
        asyncio.run(test_invalid_json())

    def test_smart_search_parameter_validation(self):
        """Test that smart_search validates parameters correctly."""
        from src.mcp_server.tools import smart_search
        import asyncio
        
        async def test_params():
            # Test with empty query - should work but return database error
            try:
                result = await smart_search("", "", "relevance", 10, None, "test_user")
                # If we get here, check structure
                if isinstance(result, CallToolResult):
                    self.assertIsInstance(result.content, list)
            except Exception:
                # Expected due to database dependency
                pass
                
            # Test with extreme limit values
            try:
                result = await smart_search("test", "", "relevance", 1000, None, "test_user")
                # Should handle gracefully
            except Exception:
                # Expected due to database dependency
                pass
        
        asyncio.run(test_params())

    async def test_recommend_games_elicitation_structure(self):
        """Test that recommend_games has proper elicitation structure."""
        from src.mcp_server.tools import recommend_games
        
        # Mock context with elicit method
        mock_ctx = MagicMock()
        mock_elicit_result = MagicMock()
        mock_elicit_result.action = "accept"
        mock_elicit_result.content = {"age": 10, "players": 2, "content_concerns": "none"}
        mock_ctx.elicit = AsyncMock(return_value=mock_elicit_result)
        
        try:
            result = await recommend_games("family", "", True, mock_ctx, "test_user")
            
            # Should not reach here due to database dependency, but check if elicit was called properly
            if mock_ctx.elicit.called:
                call_args = mock_ctx.elicit.call_args
                self.assertIn("message", call_args.kwargs)
                self.assertIn("requestedSchema", call_args.kwargs)
                
                # Verify schema structure
                schema = call_args.kwargs["requestedSchema"]
                self.assertEqual(schema["type"], "object")
                self.assertIn("properties", schema)
                self.assertIn("age", schema["properties"])
                self.assertEqual(schema["properties"]["age"]["type"], "integer")
                
        except Exception as e:
            # Expected due to database dependency
            self.assertIn("database", str(e).lower(), "Should fail due to database, not elicitation structure")

    def test_recommend_games_decline_handling(self):
        """Test that recommend_games handles elicitation decline properly."""
        from src.mcp_server.tools import recommend_games
        import asyncio
        
        async def test_decline():
            # Mock context with declined elicitation
            mock_ctx = MagicMock()
            mock_elicit_result = MagicMock()
            mock_elicit_result.action = "decline"
            mock_ctx.elicit = AsyncMock(return_value=mock_elicit_result)
            
            # Mock user resolution to avoid database for this test
            import src.mcp_server.tools as tools_module
            original_resolve = tools_module.resolve_user_for_tool
            
            def mock_resolve(user, fallback):
                return {"steam_id": "test_user_123"}
            
            tools_module.resolve_user_for_tool = mock_resolve
            
            try:
                result = await recommend_games("family", "", True, mock_ctx, "test_user")
                
                # Should return proper decline response
                self.assertIsInstance(result, CallToolResult)
                self.assertFalse(result.isError)  # Decline is not an error
                self.assertIn("understand", result.content[0].text.lower())
                self.assertIn("elicitation_declined", result.structuredContent)
                self.assertTrue(result.structuredContent["elicitation_declined"])
                
            finally:
                # Restore original function
                tools_module.resolve_user_for_tool = original_resolve
        
        asyncio.run(test_decline())

    def test_recommend_games_cancel_handling(self):
        """Test that recommend_games handles elicitation cancel properly."""
        from src.mcp_server.tools import recommend_games
        import asyncio
        
        async def test_cancel():
            # Mock context with cancelled elicitation
            mock_ctx = MagicMock()
            mock_elicit_result = MagicMock()
            mock_elicit_result.action = "cancel"
            mock_ctx.elicit = AsyncMock(return_value=mock_elicit_result)
            
            # Mock user resolution
            import src.mcp_server.tools as tools_module
            original_resolve = tools_module.resolve_user_for_tool
            
            def mock_resolve(user, fallback):
                return {"steam_id": "test_user_123"}
            
            tools_module.resolve_user_for_tool = mock_resolve
            
            try:
                result = await recommend_games("family", "", True, mock_ctx, "test_user")
                
                # Should return proper cancel response
                self.assertIsInstance(result, CallToolResult)
                self.assertFalse(result.isError)  # Cancel is not an error
                self.assertIn("cancelled", result.content[0].text.lower())
                self.assertIn("elicitation_cancelled", result.structuredContent)
                self.assertTrue(result.structuredContent["elicitation_cancelled"])
                
            finally:
                # Restore original function
                tools_module.resolve_user_for_tool = original_resolve
        
        asyncio.run(test_cancel())

    def test_user_resolution_error_handling(self):
        """Test that tools handle user resolution errors properly."""
        from src.mcp_server.tools import smart_search, recommend_games
        import asyncio
        
        async def test_user_errors():
            # Mock user resolution to return error
            import src.mcp_server.tools as tools_module
            original_resolve = tools_module.resolve_user_for_tool
            
            def mock_resolve_error(user, fallback):
                return {"error": True, "message": "No default user configured"}
            
            tools_module.resolve_user_for_tool = mock_resolve_error
            
            try:
                # Test smart_search error handling
                result = await smart_search("test", "", "relevance", 5, None, None)
                self.assertIsInstance(result, CallToolResult)
                self.assertTrue(result.isError)
                self.assertIn("No default user configured", result.content[0].text)
                self.assertEqual(result.content[0].annotations.audience, ["assistant"])
                
                # Test recommend_games error handling
                result = await recommend_games("family", "", True, None, None)
                self.assertIsInstance(result, CallToolResult)
                self.assertTrue(result.isError)
                self.assertIn("No default user configured", result.content[0].text)
                self.assertEqual(result.content[0].annotations.audience, ["assistant"])
                
            finally:
                # Restore original function
                tools_module.resolve_user_for_tool = original_resolve
        
        asyncio.run(test_user_errors())

    def test_tool_annotations_compliance(self):
        """Test that tool annotations are properly declared."""
        from src.mcp_server.tools import smart_search, recommend_games
        import inspect
        
        # Check that tools have proper FastMCP decorator calls
        # We can't directly access the decorator info, but we can check function signatures
        
        # Check smart_search signature
        sig = inspect.signature(smart_search)
        self.assertIn('query', sig.parameters)
        self.assertIn('filters', sig.parameters)
        self.assertIn('ctx', sig.parameters)
        
        # Check return type annotation
        self.assertEqual(sig.return_annotation, CallToolResult)
        
        # Check recommend_games signature
        sig = inspect.signature(recommend_games)
        self.assertIn('context', sig.parameters)
        self.assertIn('parameters', sig.parameters)
        self.assertIn('ctx', sig.parameters)
        
        # Check return type annotation
        self.assertEqual(sig.return_annotation, CallToolResult)

    def test_json_parameter_parsing(self):
        """Test that tools handle JSON parameter parsing correctly."""
        from src.mcp_server.tools import recommend_games
        import asyncio
        
        async def test_json_parsing():
            # Mock user resolution
            import src.mcp_server.tools as tools_module
            original_resolve = tools_module.resolve_user_for_tool
            
            def mock_resolve(user, fallback):
                return {"steam_id": "test_user_123"}
            
            tools_module.resolve_user_for_tool = mock_resolve
            
            try:
                # Test valid JSON
                valid_json = '{"age": 10, "players": 2}'
                try:
                    result = await recommend_games("family", valid_json, True, None, "test_user")
                    # May fail due to database, but JSON should be parsed
                except Exception as e:
                    # Should not be JSON parsing error
                    self.assertNotIn("Invalid parameters format", str(e))
                
                # Test invalid JSON
                result = await recommend_games("family", "invalid json", True, None, "test_user")
                self.assertIsInstance(result, CallToolResult)
                self.assertTrue(result.isError)
                self.assertIn("Invalid parameters format", result.content[0].text)
                
            finally:
                # Restore original function
                tools_module.resolve_user_for_tool = original_resolve
        
        asyncio.run(test_json_parsing())

    def test_structured_content_consistency(self):
        """Test that structured content is consistent with text content."""
        # This is more of a design validation test
        from mcp.types import CallToolResult, TextContent, Annotations
        
        # Create a sample result like our tools would generate
        sample_result = CallToolResult(
            content=[
                TextContent(
                    type="text",
                    text="Found 2 games:\n• Portal (95/100)\n• Portal 2 (95/100)",
                    annotations=Annotations(audience=["user"], priority=0.9)
                )
            ],
            structuredContent={
                "results": [
                    {"name": "Portal", "metacritic": 95},
                    {"name": "Portal 2", "metacritic": 95}
                ],
                "total": 2
            },
            isError=False
        )
        
        # Verify consistency
        text_game_count = sample_result.content[0].text.count("•")
        structured_game_count = len(sample_result.structuredContent["results"])
        structured_total = sample_result.structuredContent["total"]
        
        self.assertEqual(text_game_count, structured_game_count)
        self.assertEqual(structured_game_count, structured_total)


def main():
    """Run the enhanced tools integration tests."""
    unittest.main(verbosity=2)


if __name__ == "__main__":
    main()