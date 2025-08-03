#!/usr/bin/env python3
"""MCP Protocol Compliance Test Suite - validates all MCP features"""

import asyncio
import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock
from typing import Dict, Any, List

# Add src to path for imports
if "src" not in sys.path:
    sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


class TestMCPProtocolCompliance(unittest.TestCase):
    """Test suite for MCP protocol compliance"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment"""
        os.environ["DEFAULT_USER"] = "test_user"
        os.environ["DATABASE_URL"] = "sqlite:///:memory:"
        os.environ["DEBUG"] = "false"
    
    def test_server_initialization(self):
        """Test MCP server initialization"""
        try:
            from mcp_server.server import mcp
            
            # Verify server is initialized
            self.assertIsNotNone(mcp)
            self.assertEqual(mcp.name, "steam-librarian")
            
            # Check server metadata
            self.assertIsNotNone(mcp.description)
            self.assertIn("Steam", mcp.description)
            
            print("✅ MCP server initialization test passed")
            
        except Exception as e:
            self.fail(f"Server initialization failed: {e}")
    
    def test_tool_registration(self):
        """Test that all tools are properly registered with MCP"""
        try:
            from mcp_server.server import mcp
            import mcp_server.tools  # Import to register tools
            
            # Get registered tools
            tools = mcp.tools
            
            # Expected tool names
            expected_tools = [
                'smart_search',
                'recommend_games',
                'get_library_insights',
                'find_games_with_preferences',
                'search_games',
                'generate_recommendation',
                'analyze_library',
                'find_family_games',
                'find_quick_session_games'
            ]
            
            # Check each tool is registered
            for tool_name in expected_tools:
                self.assertIn(
                    tool_name,
                    tools,
                    f"Tool '{tool_name}' not registered with MCP"
                )
            
            print(f"✅ All {len(expected_tools)} tools properly registered")
            
        except Exception as e:
            self.fail(f"Tool registration test failed: {e}")
    
    def test_resource_registration(self):
        """Test that all resources are properly registered with MCP"""
        try:
            from mcp_server.server import mcp
            import mcp_server.resources  # Import to register resources
            
            # Get registered resources
            resources = mcp.resources
            
            # Expected resource patterns
            expected_patterns = [
                'library://games/{game_id}',
                'library://overview',
                'library://users/{user_id}/summary',
                'library://users/{user_id}/games',
                'library://stats/genres',
                'library://stats/categories',
                'library://stats/tags'
            ]
            
            # Check each resource is registered
            for pattern in expected_patterns:
                found = any(pattern in str(r) for r in resources)
                self.assertTrue(
                    found,
                    f"Resource pattern '{pattern}' not registered with MCP"
                )
            
            print(f"✅ All {len(expected_patterns)} resources properly registered")
            
        except Exception as e:
            self.fail(f"Resource registration test failed: {e}")
    
    def test_prompt_registration(self):
        """Test that all prompts are properly registered with MCP"""
        try:
            from mcp_server.server import mcp
            import mcp_server.prompts  # Import to register prompts
            
            # Get registered prompts
            prompts = mcp.prompts
            
            # Expected prompt names
            expected_prompts = [
                'steam-search-help',
                'steam-recommendation-help',
                'steam-filter-help'
            ]
            
            # Check each prompt is registered
            for prompt_name in expected_prompts:
                self.assertIn(
                    prompt_name,
                    prompts,
                    f"Prompt '{prompt_name}' not registered with MCP"
                )
            
            print(f"✅ All {len(expected_prompts)} prompts properly registered")
            
        except Exception as e:
            self.fail(f"Prompt registration test failed: {e}")
    
    def test_completion_registration(self):
        """Test that completions are properly registered with MCP"""
        try:
            from mcp_server.server import mcp
            import mcp_server.completions  # Import to register completions
            
            # Check completion handler is registered
            self.assertTrue(
                hasattr(mcp, 'completion'),
                "MCP server missing completion decorator"
            )
            
            # Verify completion function exists
            from mcp_server.completions import tool_argument_completions
            self.assertTrue(
                asyncio.iscoroutinefunction(tool_argument_completions),
                "Completion handler is not an async function"
            )
            
            print("✅ Completion handler properly registered")
            
        except Exception as e:
            self.fail(f"Completion registration test failed: {e}")
    
    @patch('mcp_server.completions.get_db')
    def test_completion_functionality(self, mock_get_db):
        """Test completion functionality for tool arguments"""
        from mcp_server.completions import tool_argument_completions
        from mcp.types import CompletionArgument, Completion
        
        # Mock database session
        mock_session = MagicMock()
        mock_get_db.return_value.__enter__.return_value = mock_session
        
        # Mock game data for completions
        mock_session.query.return_value.join.return_value.order_by.return_value.limit.return_value.all.return_value = [
            ("Portal 2",),
            ("Terraria",),
            ("Stardew Valley",)
        ]
        
        # Test smart_search query completions
        async def test():
            # Create mock reference with tool name
            ref = MagicMock()
            ref.toolName = "smart_search"
            
            # Test query argument
            arg = CompletionArgument(name="query", value="por")
            
            result = await tool_argument_completions(ref, arg, None)
            
            self.assertIsInstance(result, Completion)
            self.assertIn("Portal 2", result.values)
            
            # Test filter argument
            arg = CompletionArgument(name="filters", value="")
            result = await tool_argument_completions(ref, arg, None)
            
            self.assertIsInstance(result, Completion)
            self.assertTrue(any("genres" in v for v in result.values))
            
            # Test sort_by argument
            arg = CompletionArgument(name="sort_by", value="rel")
            result = await tool_argument_completions(ref, arg, None)
            
            self.assertIsInstance(result, Completion)
            self.assertIn("relevance", result.values)
            
            print("✅ Completion functionality test passed")
        
        asyncio.run(test())
    
    def test_tool_parameters(self):
        """Test that tool parameters are properly defined"""
        try:
            from mcp_server import tools
            import inspect
            
            # Test smart_search parameters
            sig = inspect.signature(tools.smart_search)
            params = sig.parameters
            
            self.assertIn('query', params)
            self.assertIn('filters', params)
            self.assertIn('sort_by', params)
            self.assertIn('limit', params)
            self.assertIn('ctx', params)
            self.assertIn('user', params)
            
            # Test recommend_games parameters
            sig = inspect.signature(tools.recommend_games)
            params = sig.parameters
            
            self.assertIn('context', params)
            self.assertIn('parameters', params)
            self.assertIn('use_play_history', params)
            self.assertIn('ctx', params)
            self.assertIn('user', params)
            
            # Test get_library_insights parameters
            sig = inspect.signature(tools.get_library_insights)
            params = sig.parameters
            
            self.assertIn('analysis_type', params)
            self.assertIn('compare_to', params)
            self.assertIn('time_range', params)
            self.assertIn('ctx', params)
            self.assertIn('user', params)
            
            print("✅ Tool parameters properly defined")
            
        except Exception as e:
            self.fail(f"Tool parameter test failed: {e}")
    
    def test_resource_uri_templates(self):
        """Test that resource URI templates are valid"""
        try:
            from mcp_server import resources
            import re
            
            # Test game details resource
            self.assertTrue(hasattr(resources, 'get_game_details'))
            
            # Test library overview resource
            self.assertTrue(hasattr(resources, 'library_overview'))
            
            # Test user summary resource
            self.assertTrue(hasattr(resources, 'get_user_summary'))
            
            # Test genre stats resource
            self.assertTrue(hasattr(resources, 'get_genre_stats'))
            
            print("✅ Resource URI templates are valid")
            
        except Exception as e:
            self.fail(f"Resource URI template test failed: {e}")
    
    def test_prompt_content(self):
        """Test that prompts return valid content"""
        try:
            from mcp_server import prompts
            
            # Test search help prompt
            result = prompts.steam_search_help()
            self.assertIsInstance(result, str)
            self.assertIn("search", result.lower())
            
            # Test recommendation help prompt
            result = prompts.steam_recommendation_help()
            self.assertIsInstance(result, str)
            self.assertIn("recommendation", result.lower())
            
            # Test filter help prompt
            result = prompts.steam_filter_help()
            self.assertIsInstance(result, str)
            self.assertIn("filter", result.lower())
            
            print("✅ All prompts return valid content")
            
        except Exception as e:
            self.fail(f"Prompt content test failed: {e}")
    
    def test_error_handling(self):
        """Test error handling in MCP tools"""
        from mcp_server.tools import smart_search, recommend_games, get_library_insights
        
        async def test():
            # Test with invalid user
            result = await smart_search("test", user="invalid_user")
            self.assertIn("error", result.lower())
            
            # Test with invalid JSON filters
            result = await smart_search("test", filters="invalid json", user="test_user")
            self.assertIn("invalid", result.lower())
            
            # Test with invalid context
            result = await recommend_games("invalid_context", user="test_user")
            self.assertIn("invalid context", result.lower())
            
            # Test with invalid analysis type
            result = await get_library_insights("invalid_type", user="test_user")
            self.assertIn("invalid analysis type", result.lower())
            
            print("✅ Error handling test passed")
        
        asyncio.run(test())
    
    def test_async_compliance(self):
        """Test that all MCP handlers are async"""
        try:
            from mcp_server import tools, completions
            import inspect
            
            # Check all tool functions are async
            tool_funcs = [
                tools.smart_search,
                tools.recommend_games,
                tools.get_library_insights,
                tools.find_games_with_preferences
            ]
            
            for func in tool_funcs:
                self.assertTrue(
                    asyncio.iscoroutinefunction(func),
                    f"{func.__name__} is not async"
                )
            
            # Check completion handler is async
            self.assertTrue(
                asyncio.iscoroutinefunction(completions.tool_argument_completions),
                "Completion handler is not async"
            )
            
            print("✅ All MCP handlers are properly async")
            
        except Exception as e:
            self.fail(f"Async compliance test failed: {e}")


class TestMCPDataFlow(unittest.TestCase):
    """Test data flow through MCP protocol layers"""
    
    @patch('mcp_server.tools.get_db')
    @patch('mcp_server.tools.resolve_user_for_tool')
    def test_tool_to_database_flow(self, mock_resolve_user, mock_get_db):
        """Test data flow from tool through database"""
        from mcp_server.tools import smart_search
        
        # Mock user resolution
        mock_resolve_user.return_value = {
            "steam_id": "test_steam_id",
            "display_name": "Test User"
        }
        
        # Track database calls
        db_calls = []
        
        def track_query(*args, **kwargs):
            db_calls.append(('query', args, kwargs))
            mock_query = MagicMock()
            mock_query.join.return_value = mock_query
            mock_query.filter.return_value = mock_query
            mock_query.order_by.return_value = mock_query
            mock_query.distinct.return_value.limit.return_value = []
            return mock_query
        
        mock_session = MagicMock()
        mock_session.query.side_effect = track_query
        mock_get_db.return_value.__enter__.return_value = mock_session
        
        async def test():
            await smart_search("test query", user="test_user")
            
            # Verify database was queried
            self.assertTrue(len(db_calls) > 0, "No database queries made")
            print(f"✅ Tool made {len(db_calls)} database queries")
        
        asyncio.run(test())
    
    @patch('mcp_server.resources.get_db')
    def test_resource_data_serialization(self, mock_get_db):
        """Test that resources properly serialize data to JSON"""
        from mcp_server.resources import library_overview
        
        # Mock database session
        mock_session = MagicMock()
        mock_get_db.return_value.__enter__.return_value = mock_session
        
        # Mock query results
        mock_session.query.return_value.count.return_value = 100
        mock_session.query.return_value.all.return_value = []
        mock_session.query.return_value.filter_by.return_value.all.return_value = []
        
        # Get resource data
        result = library_overview()
        
        # Verify JSON serialization
        self.assertIsInstance(result, str)
        data = json.loads(result)
        self.assertIsInstance(data, dict)
        self.assertIn("overview", data)
        
        print("✅ Resources properly serialize to JSON")
    
    def test_prompt_to_tool_integration(self):
        """Test that prompts provide guidance for tools"""
        from mcp_server.prompts import steam_search_help
        
        help_text = steam_search_help()
        
        # Verify prompt mentions actual tools
        self.assertIn("search", help_text.lower())
        self.assertTrue(
            "smart_search" in help_text or "search" in help_text.lower(),
            "Prompt doesn't reference search functionality"
        )
        
        print("✅ Prompts properly guide tool usage")


def run_protocol_tests():
    """Run all MCP protocol compliance tests"""
    print("\n🔬 Testing MCP Protocol Compliance")
    print("=" * 70)
    
    # Create test suites
    suite = unittest.TestSuite()
    
    # Add compliance tests
    loader = unittest.TestLoader()
    suite.addTests(loader.loadTestsFromTestCase(TestMCPProtocolCompliance))
    suite.addTests(loader.loadTestsFromTestCase(TestMCPDataFlow))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 70)
    print(f"📊 MCP Protocol Test Results:")
    print(f"  Tests run: {result.testsRun}")
    print(f"  Failures: {len(result.failures)}")
    print(f"  Errors: {len(result.errors)}")
    print(f"  Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    
    if result.wasSuccessful():
        print("\n✅ All MCP protocol tests passed!")
        return 0
    else:
        print("\n❌ Some MCP protocol tests failed")
        for failure in result.failures:
            print(f"\nFailed: {failure[0]}")
            print(failure[1])
        for error in result.errors:
            print(f"\nError: {error[0]}")
            print(error[1])
        return 1


if __name__ == "__main__":
    sys.exit(run_protocol_tests())