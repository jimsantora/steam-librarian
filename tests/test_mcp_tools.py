#!/usr/bin/env python3
"""Comprehensive test suite for new MCP tools: smart_search, recommend_games, get_library_insights"""

import asyncio
import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime

# Add src to path for imports
if "src" not in sys.path:
    sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


class TestNewMCPTools(unittest.TestCase):
    """Test suite for the new MCP tools"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment"""
        # Set test configuration
        os.environ["DEFAULT_USER"] = "test_user"
        os.environ["DATABASE_URL"] = "sqlite:///:memory:"
        os.environ["DEBUG"] = "false"
    
    def setUp(self):
        """Set up each test"""
        self.mock_context = MagicMock()
        self.mock_context.session = AsyncMock()
        self.mock_context.elicit = AsyncMock()
    
    def test_new_tool_imports(self):
        """Test that new tools can be imported"""
        try:
            from mcp_server import tools
            
            # Verify new tools exist
            new_tools = [
                'smart_search',
                'recommend_games',
                'get_library_insights'
            ]
            
            for tool_name in new_tools:
                self.assertTrue(
                    hasattr(tools, tool_name),
                    f"New tool '{tool_name}' not found in tools module"
                )
                tool_func = getattr(tools, tool_name)
                self.assertTrue(
                    asyncio.iscoroutinefunction(tool_func),
                    f"Tool '{tool_name}' is not an async function"
                )
            
            print("✅ All new tools imported successfully")
            
        except Exception as e:
            self.fail(f"Failed to import new tools: {e}")
    
    @patch('mcp_server.tools.get_db')
    @patch('mcp_server.tools.resolve_user_for_tool')
    def test_smart_search_basic(self, mock_resolve_user, mock_get_db):
        """Test smart_search tool basic functionality"""
        from mcp_server.tools import smart_search
        
        # Mock user resolution
        mock_resolve_user.return_value = {
            "steam_id": "test_steam_id",
            "display_name": "Test User"
        }
        
        # Mock database session
        mock_session = MagicMock()
        mock_get_db.return_value.__enter__.return_value = mock_session
        
        # Mock query results
        mock_game = MagicMock()
        mock_game.name = "Portal 2"
        mock_game.metacritic_score = 95
        mock_game.platforms_windows = True
        mock_game.platforms_mac = True
        mock_game.platforms_linux = True
        mock_game.vr_support = False
        mock_game.short_description = "A puzzle game"
        mock_game.genres = [MagicMock(genre_name="Puzzle")]
        mock_game.categories = []
        mock_game.tags = [MagicMock(tag_name="Co-op")]
        mock_game.reviews = MagicMock()
        
        mock_user_game = MagicMock()
        mock_user_game.playtime_forever = 600
        mock_user_game.playtime_2weeks = 120
        
        mock_query = MagicMock()
        mock_query.join.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        
        # Mock for iteration (smart_search iterates directly)
        mock_limit = MagicMock()
        mock_limit.__iter__ = lambda self: iter([(mock_game, mock_user_game)])
        mock_query.distinct.return_value.limit.return_value = mock_limit
        
        mock_session.query.return_value = mock_query
        
        # Test basic search
        async def test():
            result = await smart_search("Portal", None, "relevance", 10, None, "test_user")
            self.assertIn("Portal 2", result)
            self.assertIn("95/100", result)
            self.assertIn("Puzzle", result)
            self.assertIn("Co-op", result)
            print("✅ smart_search basic test passed")
        
        asyncio.run(test())
    
    @patch('mcp_server.tools.get_db')
    @patch('mcp_server.tools.resolve_user_for_tool')
    def test_smart_search_with_filters(self, mock_resolve_user, mock_get_db):
        """Test smart_search with JSON filters"""
        from mcp_server.tools import smart_search
        
        # Mock user resolution
        mock_resolve_user.return_value = {
            "steam_id": "test_steam_id",
            "display_name": "Test User"
        }
        
        # Mock database session
        mock_session = MagicMock()
        mock_get_db.return_value.__enter__.return_value = mock_session
        
        # Setup mock returns
        mock_game = MagicMock()
        mock_game.name = "Terraria"
        mock_game.metacritic_score = 83
        mock_game.platforms_windows = True
        mock_game.platforms_mac = True
        mock_game.platforms_linux = True
        mock_game.vr_support = False
        mock_game.genres = [MagicMock(genre_name="Action"), MagicMock(genre_name="Adventure")]
        mock_game.categories = [MagicMock(category_name="Single-player")]
        mock_game.tags = [MagicMock(tag_name="Sandbox")]
        
        mock_user_game = MagicMock()
        mock_user_game.playtime_forever = 0  # Unplayed
        mock_user_game.playtime_2weeks = 0
        
        mock_query = MagicMock()
        mock_query.join.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        
        # Mock for iteration 
        mock_limit = MagicMock()
        mock_limit.__iter__ = lambda self: iter([(mock_game, mock_user_game)])
        mock_query.distinct.return_value.limit.return_value = mock_limit
        
        mock_session.query.return_value = mock_query
        
        # Test with filters
        async def test():
            filters = json.dumps({"genres": ["Action"], "playtime": "unplayed"})
            result = await smart_search("sandbox", filters, "metacritic", 10, None, "test_user")
            self.assertIn("Terraria", result)
            self.assertIn("Action", result)
            self.assertIn("🆕", result)  # Unplayed indicator
            print("✅ smart_search with filters test passed")
        
        asyncio.run(test())
    
    @patch('mcp_server.tools.get_db')
    @patch('mcp_server.tools.resolve_user_for_tool')
    def test_smart_search_with_ai_sampling(self, mock_resolve_user, mock_get_db):
        """Test smart_search with AI sampling for natural language"""
        from mcp_server.tools import smart_search
        
        # Mock user resolution
        mock_resolve_user.return_value = {
            "steam_id": "test_steam_id",
            "display_name": "Test User"
        }
        
        # Mock database session
        mock_session = MagicMock()
        mock_get_db.return_value.__enter__.return_value = mock_session
        
        # Mock genre/category/tag queries for AI context
        mock_session.query.return_value.all.return_value = [
            MagicMock(genre_name="Action"),
            MagicMock(genre_name="Casual")
        ]
        
        # Setup mock context with AI response
        mock_ai_response = MagicMock()
        mock_ai_response.content.type = "text"
        mock_ai_response.content.text = json.dumps({
            "genres": ["Casual"],
            "categories": [],
            "tags": ["Relaxing"],
            "mood": "relaxing",
            "time_commitment": "short"
        })
        self.mock_context.session.create_message.return_value = mock_ai_response
        
        # Mock game results
        mock_game = MagicMock()
        mock_game.name = "Stardew Valley"
        mock_game.metacritic_score = 89
        mock_game.platforms_windows = True
        mock_game.platforms_mac = True
        mock_game.platforms_linux = True
        mock_game.vr_support = False
        mock_game.genres = [MagicMock(genre_name="Casual")]
        mock_game.categories = []
        mock_game.tags = [MagicMock(tag_name="Relaxing")]
        
        mock_user_game = MagicMock()
        mock_user_game.playtime_forever = 3600
        mock_user_game.playtime_2weeks = 0
        
        mock_query = MagicMock()
        mock_query.join.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        
        # Mock for iteration
        mock_limit = MagicMock()
        mock_limit.__iter__ = lambda self: iter([(mock_game, mock_user_game)])
        mock_limit.all.return_value = [(mock_game, mock_user_game)]  # Also support .all()
        mock_query.distinct.return_value.limit.return_value = mock_limit
        
        mock_session.query.return_value = mock_query
        
        # Test with natural language
        async def test():
            result = await smart_search("something relaxing", None, "relevance", 10, self.mock_context, "test_user")
            self.assertIn("Stardew Valley", result)
            self.assertIn("Casual", result)
            print("✅ smart_search with AI sampling test passed")
        
        asyncio.run(test())
    
    @patch('mcp_server.tools.get_db')
    @patch('mcp_server.tools.resolve_user_for_tool')
    def test_recommend_games_family(self, mock_resolve_user, mock_get_db):
        """Test recommend_games with family context"""
        from mcp_server.tools import recommend_games
        
        # Mock user resolution
        mock_resolve_user.return_value = {
            "steam_id": "test_steam_id",
            "display_name": "Test User"
        }
        
        # Mock database session
        mock_session = MagicMock()
        mock_get_db.return_value.__enter__.return_value = mock_session
        
        # Mock family-friendly games
        mock_game = MagicMock()
        mock_game.name = "Minecraft"
        mock_game.esrb_rating = "E10+"
        mock_game.pegi_rating = "7"
        mock_game.genres = [MagicMock(genre_name="Adventure")]
        mock_game.categories = [MagicMock(category_name="Family Sharing")]
        
        mock_user_game = MagicMock()
        mock_user_game.playtime_forever = 1200
        
        mock_query = MagicMock()
        mock_query.join.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        
        # Mock for iteration
        mock_limit = MagicMock()
        mock_limit.__iter__ = lambda self: iter([(mock_game, mock_user_game)])
        mock_limit.all.return_value = [(mock_game, mock_user_game)]  # Also support .all()
        mock_query.distinct.return_value.limit.return_value = mock_limit
        
        mock_session.query.return_value = mock_query
        
        # Test family recommendations
        async def test():
            params = json.dumps({"age": 8, "players": 2})
            result = await recommend_games("family", params, True, None, "test_user")
            self.assertIn("Minecraft", result)
            self.assertIn("E10+", result)
            print("✅ recommend_games family context test passed")
        
        asyncio.run(test())
    
    @patch('mcp_server.tools.get_db')
    @patch('mcp_server.tools.resolve_user_for_tool')
    def test_recommend_games_with_elicitation(self, mock_resolve_user, mock_get_db):
        """Test recommend_games with elicitation for missing parameters"""
        from mcp_server.tools import recommend_games
        
        # Mock user resolution
        mock_resolve_user.return_value = {
            "steam_id": "test_steam_id",
            "display_name": "Test User"
        }
        
        # Mock database session
        mock_session = MagicMock()
        mock_get_db.return_value.__enter__.return_value = mock_session
        
        # Mock elicitation response
        mock_elicit_result = MagicMock()
        mock_elicit_result.action = "accept"
        mock_elicit_result.data = MagicMock()
        mock_elicit_result.data.dict.return_value = {
            "age": 10,
            "players": 1,
            "content_concerns": ["violence"]
        }
        self.mock_context.elicit.return_value = mock_elicit_result
        
        # Mock game results
        mock_game = MagicMock()
        mock_game.name = "Terraria"
        mock_game.esrb_rating = "T"
        mock_game.pegi_rating = "12"
        mock_game.genres = []
        mock_game.categories = []
        
        mock_user_game = MagicMock()
        
        mock_query = MagicMock()
        mock_query.join.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        
        # Mock for iteration
        mock_limit = MagicMock()
        mock_limit.__iter__ = lambda self: iter([(mock_game, mock_user_game)])
        mock_limit.all.return_value = [(mock_game, mock_user_game)]  # Also support .all()
        mock_query.distinct.return_value.limit.return_value = mock_limit
        
        mock_session.query.return_value = mock_query
        
        # Test with elicitation
        async def test():
            result = await recommend_games("family", None, True, self.mock_context, "test_user")
            self.assertIn("Terraria", result)
            # Verify elicitation was called
            self.mock_context.elicit.assert_called_once()
            print("✅ recommend_games with elicitation test passed")
        
        asyncio.run(test())
    
    @patch('mcp_server.tools.get_db')
    @patch('mcp_server.tools.resolve_user_for_tool')
    def test_recommend_unplayed_gems(self, mock_resolve_user, mock_get_db):
        """Test recommend_games for unplayed gems"""
        from mcp_server.tools import recommend_games
        
        # Mock user resolution
        mock_resolve_user.return_value = {
            "steam_id": "test_steam_id",
            "display_name": "Test User"
        }
        
        # Mock database session
        mock_session = MagicMock()
        mock_get_db.return_value.__enter__.return_value = mock_session
        
        # Mock high-rated unplayed games
        mock_game = MagicMock()
        mock_game.name = "Hades"
        mock_game.metacritic_score = 93
        mock_game.short_description = "A rogue-like dungeon crawler"
        mock_game.genres = [MagicMock(genre_name="Action"), MagicMock(genre_name="Indie")]
        mock_game.reviews = MagicMock()
        mock_game.reviews.review_summary = "Overwhelmingly Positive"
        
        mock_user_game = MagicMock()
        mock_user_game.playtime_forever = 0  # Unplayed
        
        mock_query = MagicMock()
        mock_query.join.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.options.return_value = mock_query
        mock_query.order_by.return_value.limit.return_value.all.return_value = [(mock_game, mock_user_game)]
        
        mock_session.query.return_value = mock_query
        
        # Test unplayed gems
        async def test():
            result = await recommend_games("unplayed_gems", None, True, None, "test_user")
            self.assertIn("Hades", result)
            self.assertIn("93/100", result)
            self.assertIn("Overwhelmingly Positive", result)
            print("✅ recommend_games unplayed_gems test passed")
        
        asyncio.run(test())
    
    @patch('mcp_server.tools.get_db')
    @patch('mcp_server.tools.resolve_user_for_tool')
    def test_get_library_insights_patterns(self, mock_resolve_user, mock_get_db):
        """Test get_library_insights with patterns analysis"""
        from mcp_server.tools import get_library_insights
        
        # Mock user resolution
        mock_resolve_user.return_value = {
            "steam_id": "test_steam_id",
            "display_name": "Test User"
        }
        
        # Mock database session
        mock_session = MagicMock()
        mock_get_db.return_value.__enter__.return_value = mock_session
        
        # Mock user games with rich data
        mock_user_games = []
        for i in range(10):
            ug = MagicMock()
            ug.playtime_forever = i * 100
            ug.playtime_2weeks = 60 if i < 2 else 0
            
            game = MagicMock()
            game.name = f"Game {i}"
            game.genres = [MagicMock(genre_name="Action" if i % 2 == 0 else "RPG")]
            game.tags = []
            game.developers = [MagicMock(developer_name=f"Dev {i % 3}")]
            
            ug.game = game
            mock_user_games.append(ug)
        
        mock_query = MagicMock()
        mock_query.options.return_value = mock_query
        mock_query.filter.return_value.all.return_value = mock_user_games
        
        mock_session.query.return_value = mock_query
        
        # Test pattern analysis
        async def test():
            result = await get_library_insights("patterns", None, "all", None, "test_user")
            self.assertIn("Gaming Pattern Analysis", result)
            self.assertIn("Library Overview", result)
            self.assertIn("Favorite Genres", result)
            self.assertIn("Developer Loyalty", result)
            print("✅ get_library_insights patterns test passed")
        
        asyncio.run(test())
    
    @patch('mcp_server.tools.get_db')
    @patch('mcp_server.tools.resolve_user_for_tool')
    def test_get_library_insights_value(self, mock_resolve_user, mock_get_db):
        """Test get_library_insights with value analysis"""
        from mcp_server.tools import get_library_insights
        
        # Mock user resolution
        mock_resolve_user.return_value = {
            "steam_id": "test_steam_id",
            "display_name": "Test User"
        }
        
        # Mock database session
        mock_session = MagicMock()
        mock_get_db.return_value.__enter__.return_value = mock_session
        
        # Mock user games for value analysis
        mock_user_games = []
        
        # High value game
        ug1 = MagicMock()
        ug1.playtime_forever = 6000  # 100 hours
        ug1.playtime_2weeks = 120
        ug1.game = MagicMock()
        ug1.game.name = "The Witcher 3"
        ug1.game.metacritic_score = 92
        ug1.game.reviews = MagicMock()
        mock_user_games.append(ug1)
        
        # Low value game
        ug2 = MagicMock()
        ug2.playtime_forever = 90  # 1.5 hours
        ug2.playtime_2weeks = 0
        ug2.game = MagicMock()
        ug2.game.name = "Abandoned Game"
        ug2.game.metacritic_score = 65
        ug2.game.reviews = MagicMock()
        mock_user_games.append(ug2)
        
        mock_query = MagicMock()
        mock_query.options.return_value = mock_query
        mock_query.filter.return_value.all.return_value = mock_user_games
        
        mock_session.query.return_value = mock_query
        
        # Test value analysis
        async def test():
            result = await get_library_insights("value", None, "all", None, "test_user")
            self.assertIn("Library Value Analysis", result)
            self.assertIn("Best Value Games", result)
            self.assertIn("The Witcher 3", result)
            self.assertIn("100.0 hours", result)
            print("✅ get_library_insights value test passed")
        
        asyncio.run(test())
    
    @patch('mcp_server.tools.get_db')
    @patch('mcp_server.tools.resolve_user_for_tool')
    def test_get_library_insights_with_ai(self, mock_resolve_user, mock_get_db):
        """Test get_library_insights with AI interpretation"""
        from mcp_server.tools import get_library_insights
        
        # Mock user resolution
        mock_resolve_user.return_value = {
            "steam_id": "test_steam_id",
            "display_name": "Test User"
        }
        
        # Mock database session
        mock_session = MagicMock()
        mock_get_db.return_value.__enter__.return_value = mock_session
        
        # Mock user games
        mock_user_games = []
        for i in range(5):
            ug = MagicMock()
            ug.playtime_forever = 1000
            ug.playtime_2weeks = 100 if i == 0 else 0
            ug.game = MagicMock()
            ug.game.name = f"Game {i}"
            ug.game.genres = [MagicMock(genre_name="RPG")]
            ug.game.tags = []
            ug.game.developers = [MagicMock(developer_name="BioWare")]
            mock_user_games.append(ug)
        
        mock_query = MagicMock()
        mock_query.options.return_value = mock_query
        mock_query.filter.return_value.all.return_value = mock_user_games
        
        mock_session.query.return_value = mock_query
        
        # Mock AI response
        mock_ai_response = MagicMock()
        mock_ai_response.content.type = "text"
        mock_ai_response.content.text = "You're a dedicated RPG fan who values story-driven experiences."
        self.mock_context.session.create_message.return_value = mock_ai_response
        
        # Test with AI insights
        async def test():
            result = await get_library_insights("patterns", None, "all", self.mock_context, "test_user")
            self.assertIn("Gaming Pattern Analysis", result)
            self.assertIn("AI Insights", result)
            self.assertIn("RPG fan", result)
            print("✅ get_library_insights with AI test passed")
        
        asyncio.run(test())


def run_new_tool_tests():
    """Run all new tool tests and return results"""
    print("\n🚀 Testing New MCP Tools (smart_search, recommend_games, get_library_insights)")
    print("=" * 70)
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestNewMCPTools)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 70)
    print(f"📊 New Tool Test Results:")
    print(f"  Tests run: {result.testsRun}")
    print(f"  Failures: {len(result.failures)}")
    print(f"  Errors: {len(result.errors)}")
    print(f"  Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    
    if result.wasSuccessful():
        print("\n✅ All new tool tests passed!")
        return 0
    else:
        print("\n❌ Some new tool tests failed")
        for failure in result.failures:
            print(f"\nFailed: {failure[0]}")
            print(failure[1])
        for error in result.errors:
            print(f"\nError: {error[0]}")
            print(error[1])
        return 1


if __name__ == "__main__":
    sys.exit(run_new_tool_tests())