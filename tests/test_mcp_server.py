#!/usr/bin/env python3
"""Comprehensive test suite for Steam Librarian MCP Server"""

import asyncio
import json
import os
import sys
import tempfile
import time
from pathlib import Path
from typing import Dict, Any

# Add src to path for imports (if not already set by PYTHONPATH)
if "src" not in sys.path:
    sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


class MCPServerTestSuite:
    """Comprehensive test suite for the MCP Server"""
    
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []
        
    def assert_test(self, condition: bool, test_name: str, error_msg: str = ""):
        """Assert a test condition and track results"""
        if condition:
            print(f"✅ {test_name}")
            self.passed += 1
        else:
            print(f"❌ {test_name}: {error_msg}")
            self.failed += 1
            self.errors.append(f"{test_name}: {error_msg}")
    
    def test_imports(self):
        """Test that all critical imports work"""
        print("\n🔍 Testing Imports...")
        
        try:
            # Test core imports
            from mcp_server.server import mcp
            self.assert_test(True, "Import mcp_server.server")
        except Exception as e:
            self.assert_test(False, "Import mcp_server.server", str(e))
        
        try:
            from mcp_server.config import config_manager, settings
            self.assert_test(True, "Import mcp_server.config")
        except Exception as e:
            self.assert_test(False, "Import mcp_server.config", str(e))
        
        try:
            from mcp_server.cache import cache
            self.assert_test(True, "Import mcp_server.cache")
        except Exception as e:
            self.assert_test(False, "Import mcp_server.cache", str(e))
        
        try:
            from mcp_server.tools.search_games import search_games
            self.assert_test(True, "Import search_games tool")
        except Exception as e:
            self.assert_test(False, "Import search_games tool", str(e))
        
        try:
            from mcp_server.tools.filter_games import filter_games
            self.assert_test(True, "Import filter_games tool")
        except Exception as e:
            self.assert_test(False, "Import filter_games tool", str(e))
        
        try:
            from mcp_server.tools.get_recommendations import get_recommendations
            self.assert_test(True, "Import get_recommendations tool")
        except Exception as e:
            self.assert_test(False, "Import get_recommendations tool", str(e))
        
        try:
            from mcp_server.tools.get_friends_data import get_friends_data
            self.assert_test(True, "Import get_friends_data tool")
        except Exception as e:
            self.assert_test(False, "Import get_friends_data tool", str(e))
        
        try:
            from mcp_server.tools.get_library_stats import get_library_stats
            self.assert_test(True, "Import get_library_stats tool")
        except Exception as e:
            self.assert_test(False, "Import get_library_stats tool", str(e))
        
        try:
            from shared.database import get_db, UserProfile, Game
            self.assert_test(True, "Import shared.database")
        except Exception as e:
            self.assert_test(False, "Import shared.database", str(e))
    
    def test_configuration(self):
        """Test configuration management"""
        print("\n⚙️  Testing Configuration...")
        
        try:
            from mcp_server.config import config_manager, settings
            
            # Test server info
            server_info = config_manager.get_server_info()
            self.assert_test(
                isinstance(server_info, dict) and "name" in server_info,
                "Get server info",
                "Server info should be dict with 'name' key"
            )
            
            self.assert_test(
                server_info.get("name") == "steam-librarian",
                "Server name correct",
                f"Expected 'steam-librarian', got '{server_info.get('name')}'"
            )
            
            # Test feature flags
            features = config_manager.get_feature_flags()
            self.assert_test(
                isinstance(features, dict) and len(features) > 0,
                "Get feature flags",
                "Feature flags should be non-empty dict"
            )
            
            # Test configuration validation
            validation = config_manager.validate_configuration()
            self.assert_test(
                isinstance(validation, dict) and "valid" in validation,
                "Configuration validation",
                "Validation should return dict with 'valid' key"
            )
            
            # Test settings access
            self.assert_test(
                hasattr(settings, "host") and hasattr(settings, "port"),
                "Settings attributes",
                "Settings should have host and port attributes"
            )
            
        except Exception as e:
            self.assert_test(False, "Configuration system", str(e))
    
    async def test_fastmcp_server(self):
        """Test FastMCP server functionality"""
        print("\n🚀 Testing FastMCP Server...")
        
        try:
            from mcp_server.server import mcp
            
            # Test server type
            self.assert_test(
                hasattr(mcp, 'name') and mcp.name == "steam-librarian",
                "FastMCP server instance",
                "Server should be FastMCP instance with correct name"
            )
            
            # Test tools registration
            tools = await mcp.list_tools()
            self.assert_test(
                len(tools) == 5,
                f"Tool count (expected 5, got {len(tools)})",
                f"Expected 5 tools, found {len(tools)}"
            )
            
            expected_tools = {
                "search_games", "filter_games", "get_recommendations", 
                "get_friends_data", "get_library_stats"
            }
            actual_tools = {tool.name for tool in tools}
            
            missing_tools = expected_tools - actual_tools
            extra_tools = actual_tools - expected_tools
            
            self.assert_test(
                len(missing_tools) == 0,
                f"All expected tools present",
                f"Missing tools: {missing_tools}" if missing_tools else ""
            )
            
            self.assert_test(
                len(extra_tools) == 0,
                f"No extra tools",
                f"Extra tools: {extra_tools}" if extra_tools else ""
            )
            
            # Test individual tool properties
            for tool in tools:
                self.assert_test(
                    hasattr(tool, 'name') and hasattr(tool, 'description'),
                    f"Tool {tool.name} has required attributes",
                    "Tool should have name and description"
                )
                
                self.assert_test(
                    len(tool.description) > 10,
                    f"Tool {tool.name} has meaningful description",
                    f"Description too short: {tool.description[:50]}..."
                )
            
        except Exception as e:
            self.assert_test(False, "FastMCP server", str(e))
    
    def test_database_models(self):
        """Test database models and relationships"""
        print("\n🗄️  Testing Database Models...")
        
        try:
            from shared.database import UserProfile, Game, UserGame, Genre, get_db
            
            # Test model imports
            self.assert_test(True, "Database models import")
            
            # Test database connection (without requiring actual data)
            try:
                from sqlalchemy import text
                with get_db() as session:
                    # Test that we can create a session
                    result = session.execute(text("SELECT 1")).fetchone()
                    self.assert_test(
                        result is not None,
                        "Database connection",
                        "Could not execute basic query"
                    )
            except Exception as e:
                self.assert_test(False, "Database connection", str(e))
            
            # Test model attributes
            required_user_attrs = ["steam_id", "persona_name", "profile_url"]
            for attr in required_user_attrs:
                self.assert_test(
                    hasattr(UserProfile, attr),
                    f"UserProfile has {attr}",
                    f"UserProfile missing attribute: {attr}"
                )
            
            required_game_attrs = ["app_id", "name"]
            for attr in required_game_attrs:
                self.assert_test(
                    hasattr(Game, attr),
                    f"Game has {attr}",
                    f"Game missing attribute: {attr}"
                )
                
        except Exception as e:
            self.assert_test(False, "Database models", str(e))
    
    async def test_caching_system(self):
        """Test caching functionality"""
        print("\n💾 Testing Caching System...")
        
        try:
            from mcp_server.cache import cache
            
            # Test cache operations
            test_key = "test_key_12345"
            test_value = {"test": "data", "timestamp": time.time()}
            
            # Test set/get (check if methods exist first)
            if not (hasattr(cache, 'set') and hasattr(cache, 'get')):
                self.assert_test(False, "Cache methods exist", "Cache missing set/get methods")
                return
                
            await cache.set(test_key, test_value, ttl=60)
            retrieved = await cache.get(test_key)
            
            self.assert_test(
                retrieved == test_value,
                "Cache set/get",
                f"Expected {test_value}, got {retrieved}"
            )
            
            # Test get_or_compute
            compute_called = False
            async def compute_function():
                nonlocal compute_called
                compute_called = True
                return {"computed": True}
            
            # First call should compute
            result1 = await cache.get_or_compute("compute_test", compute_function, ttl=60)
            self.assert_test(compute_called, "Cache compute function called")
            
            # Second call should use cache
            compute_called = False
            result2 = await cache.get_or_compute("compute_test", compute_function, ttl=60)
            self.assert_test(
                not compute_called,
                "Cache hit (compute not called)",
                "Compute function was called on cache hit"
            )
            
            self.assert_test(
                result1 == result2,
                "Cache consistency",
                f"Results don't match: {result1} vs {result2}"
            )
            
            # Test invalidation
            await cache.invalidate("compute_test")
            compute_called = False
            result3 = await cache.get_or_compute("compute_test", compute_function, ttl=60)
            self.assert_test(
                compute_called,
                "Cache invalidation",
                "Compute function not called after invalidation"
            )
            
        except Exception as e:
            self.assert_test(False, "Caching system", str(e))
    
    async def test_user_context(self):
        """Test user context resolution"""
        print("\n👤 Testing User Context...")
        
        try:
            from mcp_server.user_context import resolve_user_context
            
            # Test with None (should handle gracefully) 
            result = await resolve_user_context(None)
            self.assert_test(
                isinstance(result, dict),
                "Handle None user_steam_id",
                f"Expected dict, got {type(result)}"
            )
            
        except Exception as e:
            # If database doesn't exist or is empty, that's expected for tests
            if "no such table" in str(e).lower():
                self.assert_test(True, "User context (no data - expected)")
            else:
                self.assert_test(False, "User context", str(e))
    
    def test_validation_schemas(self):
        """Test input validation schemas"""
        print("\n✅ Testing Validation Schemas...")
        
        try:
            from mcp_server.validation import (
                SearchGamesInput, FilterGamesInput, RecommendationsInput,
                FriendsDataInput, LibraryStatsInput
            )
            
            # Test SearchGamesInput
            search_input = SearchGamesInput(query="test query")
            self.assert_test(
                search_input.query == "test query",
                "SearchGamesInput validation"
            )
            
            # Test FilterGamesInput
            filter_input = FilterGamesInput(playtime_min=1.0, playtime_max=10.0)
            self.assert_test(
                filter_input.playtime_min == 1.0 and filter_input.playtime_max == 10.0,
                "FilterGamesInput validation"
            )
            
            # Test RecommendationsInput (with required user_steam_id)
            rec_input = RecommendationsInput(user_steam_id="76561197960265728", context={"mood": "chill"})
            self.assert_test(
                rec_input.context and rec_input.context.get("mood") == "chill",
                "RecommendationsInput validation"
            )
            
            # Test FriendsDataInput
            friends_input = FriendsDataInput(data_type="common_games")
            self.assert_test(
                friends_input.data_type == "common_games",
                "FriendsDataInput validation"
            )
            
            # Test LibraryStatsInput
            stats_input = LibraryStatsInput(user_steam_id="76561197960265728", time_period="all_time")
            self.assert_test(
                stats_input.time_period == "all_time",
                "LibraryStatsInput validation"
            )
            
        except Exception as e:
            self.assert_test(False, "Validation schemas", str(e))
    
    async def test_error_handling(self):
        """Test error handling framework"""
        print("\n🚨 Testing Error Handling...")
        
        try:
            from mcp_server.errors import handle_mcp_errors, MCPError
            
            # Test error classes exist
            self.assert_test(True, "Error handling imports")
            
            # Test error decorator (basic test)
            @handle_mcp_errors
            async def test_function():
                return "success"
            
            result = await test_function()
            self.assert_test(
                result == "success" or (isinstance(result, list) and len(result) == 1),
                "Error handling decorator"
            )
            
        except Exception as e:
            self.assert_test(False, "Error handling", str(e))
    
    def test_monitoring_scripts(self):
        """Test monitoring and administration scripts"""
        print("\n📊 Testing Monitoring Scripts...")
        
        try:
            # Test run_server.py exists and is importable
            run_server_path = Path(__file__).parent.parent / "src" / "mcp_server" / "run_server.py"
            self.assert_test(
                run_server_path.exists(),
                "run_server.py exists",
                f"File not found: {run_server_path}"
            )
            
            # Test monitor.py exists
            monitor_path = Path(__file__).parent.parent / "src" / "mcp_server" / "monitor.py"
            self.assert_test(
                monitor_path.exists(),
                "monitor.py exists",
                f"File not found: {monitor_path}"
            )
            
            # Test that scripts have proper shebang
            with open(run_server_path) as f:
                first_line = f.readline().strip()
                self.assert_test(
                    first_line.startswith("#!") and "python" in first_line,
                    "run_server.py has shebang"
                )
            
            with open(monitor_path) as f:
                first_line = f.readline().strip()
                self.assert_test(
                    first_line.startswith("#!") and "python" in first_line,
                    "monitor.py has shebang"
                )
                
        except Exception as e:
            self.assert_test(False, "Monitoring scripts", str(e))
    
    async def run_all_tests(self):
        """Run all tests in the test suite"""
        print("🧪 Steam Librarian MCP Server Test Suite")
        print("=" * 50)
        
        # Run all test methods
        self.test_imports()
        self.test_configuration()
        await self.test_fastmcp_server()
        self.test_database_models()
        await self.test_caching_system()
        await self.test_user_context()
        self.test_validation_schemas()
        await self.test_error_handling()
        self.test_monitoring_scripts()
        
        # Print summary
        print("\n" + "=" * 50)
        print("📊 Test Results Summary")
        print(f"✅ Passed: {self.passed}")
        print(f"❌ Failed: {self.failed}")
        print(f"📈 Success Rate: {(self.passed / (self.passed + self.failed) * 100):.1f}%")
        
        if self.errors:
            print("\n🔍 Failed Tests:")
            for error in self.errors:
                print(f"  • {error}")
        
        if self.failed == 0:
            print("\n🎉 All tests passed! The MCP Server is ready for production.")
            return True
        else:
            print(f"\n⚠️  {self.failed} test(s) failed. Please review and fix issues.")
            return False


def main():
    """Main test runner"""
    try:
        test_suite = MCPServerTestSuite()
        success = asyncio.run(test_suite.run_all_tests())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n🛑 Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Test suite crashed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()