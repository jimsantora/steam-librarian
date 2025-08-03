#!/usr/bin/env python3
"""Full MCP Server Test Suite - Comprehensive testing of all MCP features"""

import asyncio
import json
import os
import sys
import tempfile
import time
import unittest
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List
from unittest.mock import MagicMock, patch

# Add src to path for imports
if "src" not in sys.path:
    sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


class TestReport:
    """Test report generator"""
    
    def __init__(self):
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "sections": {},
            "summary": {
                "total_tests": 0,
                "passed": 0,
                "failed": 0,
                "errors": 0,
                "warnings": []
            }
        }
    
    def add_section(self, name: str, result: unittest.TestResult):
        """Add a test section to the report"""
        self.results["sections"][name] = {
            "tests_run": result.testsRun,
            "failures": len(result.failures),
            "errors": len(result.errors),
            "success_rate": ((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100) if result.testsRun > 0 else 0,
            "details": {
                "failures": [str(f[0]) for f in result.failures],
                "errors": [str(e[0]) for e in result.errors]
            }
        }
        
        # Update summary
        self.results["summary"]["total_tests"] += result.testsRun
        self.results["summary"]["passed"] += (result.testsRun - len(result.failures) - len(result.errors))
        self.results["summary"]["failed"] += len(result.failures)
        self.results["summary"]["errors"] += len(result.errors)
    
    def add_warning(self, warning: str):
        """Add a warning to the report"""
        self.results["summary"]["warnings"].append(warning)
    
    def save(self, filepath: str):
        """Save report to file"""
        with open(filepath, 'w') as f:
            json.dump(self.results, f, indent=2)
    
    def print_summary(self):
        """Print report summary to console"""
        summary = self.results["summary"]
        print("\n" + "=" * 70)
        print("📊 COMPREHENSIVE TEST REPORT")
        print("=" * 70)
        print(f"Timestamp: {self.results['timestamp']}")
        print(f"\nTotal Tests: {summary['total_tests']}")
        print(f"✅ Passed: {summary['passed']}")
        print(f"❌ Failed: {summary['failed']}")
        print(f"⚠️  Errors: {summary['errors']}")
        
        if summary['total_tests'] > 0:
            success_rate = (summary['passed'] / summary['total_tests']) * 100
            print(f"\n🎯 Overall Success Rate: {success_rate:.1f}%")
        
        if summary['warnings']:
            print(f"\n⚠️  Warnings ({len(summary['warnings'])}):")
            for warning in summary['warnings']:
                print(f"  - {warning}")
        
        print("\n📁 Section Results:")
        for section, data in self.results["sections"].items():
            icon = "✅" if data["success_rate"] == 100 else "⚠️" if data["success_rate"] >= 50 else "❌"
            print(f"  {icon} {section}: {data['success_rate']:.1f}% ({data['tests_run']} tests)")


def check_dependencies():
    """Check if required dependencies are available"""
    missing = []
    warnings = []
    
    # Check critical imports
    try:
        import sqlalchemy
    except ImportError:
        missing.append("sqlalchemy")
    
    try:
        import pydantic
    except ImportError:
        missing.append("pydantic")
    
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError:
        missing.append("mcp")
    
    # Check optional dependencies
    try:
        import aiohttp
    except ImportError:
        warnings.append("aiohttp (for HTTP transport)")
    
    # Check database file
    if not os.path.exists("steam_library.db"):
        warnings.append("steam_library.db not found - some tests may fail")
    
    return missing, warnings


def run_comprehensive_tests():
    """Run all MCP server tests comprehensively"""
    print("\n" + "=" * 70)
    print("🚀 STEAM LIBRARIAN MCP SERVER - COMPREHENSIVE TEST SUITE")
    print("=" * 70)
    
    # Check dependencies
    print("\n📦 Checking dependencies...")
    missing, warnings = check_dependencies()
    
    if missing:
        print(f"❌ Missing critical dependencies: {', '.join(missing)}")
        print("Please install them with: pip install -r requirements.txt")
        return 1
    
    if warnings:
        print(f"⚠️  Warnings:")
        for warning in warnings:
            print(f"  - {warning}")
    
    # Initialize report
    report = TestReport()
    for warning in warnings:
        report.add_warning(warning)
    
    # Test sections
    test_sections = [
        ("Core Imports", test_core_imports),
        ("MCP Protocol Compliance", test_protocol_compliance),
        ("New Tools (smart_search, recommend_games, get_library_insights)", test_new_tools),
        ("Legacy Tools", test_legacy_tools),
        ("Resources", test_resources),
        ("Prompts", test_prompts),
        ("Completions", test_completions),
        ("Database Integration", test_database),
        ("Error Handling", test_error_handling),
        ("Performance", test_performance)
    ]
    
    all_passed = True
    
    for section_name, test_func in test_sections:
        print(f"\n{'=' * 70}")
        print(f"🔧 Testing: {section_name}")
        print(f"{'=' * 70}")
        
        try:
            result = test_func()
            report.add_section(section_name, result)
            
            if not result.wasSuccessful():
                all_passed = False
                
        except Exception as e:
            print(f"❌ Section failed with exception: {e}")
            # Create a failed result
            result = unittest.TestResult()
            result.testsRun = 1
            result.errors.append((section_name, str(e)))
            report.add_section(section_name, result)
            all_passed = False
    
    # Save report
    report_dir = Path("agent_output")
    report_dir.mkdir(exist_ok=True)
    report_file = report_dir / f"mcp_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    report.save(str(report_file))
    
    # Print summary
    report.print_summary()
    print(f"\n📄 Detailed report saved to: {report_file}")
    
    # Return status
    if all_passed:
        print("\n🎉 ALL TESTS PASSED!")
        return 0
    else:
        print("\n⚠️  SOME TESTS FAILED - Review the report for details")
        return 1


def test_core_imports() -> unittest.TestResult:
    """Test core imports"""
    from test_mcp_tools import TestMCPTools
    
    suite = unittest.TestSuite()
    suite.addTest(TestMCPTools('test_tool_imports'))
    suite.addTest(TestMCPTools('test_helper_functions'))
    
    runner = unittest.TextTestRunner(verbosity=1)
    return runner.run(suite)


def test_protocol_compliance() -> unittest.TestResult:
    """Test MCP protocol compliance"""
    from test_mcp_protocol import TestMCPProtocolCompliance
    
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestMCPProtocolCompliance)
    
    runner = unittest.TextTestRunner(verbosity=1)
    return runner.run(suite)


def test_new_tools() -> unittest.TestResult:
    """Test new MCP tools"""
    from test_mcp_new_tools import TestNewMCPTools
    
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestNewMCPTools)
    
    runner = unittest.TextTestRunner(verbosity=1)
    return runner.run(suite)


def test_legacy_tools() -> unittest.TestResult:
    """Test legacy MCP tools"""
    from test_mcp_tools import TestMCPTools
    
    suite = unittest.TestSuite()
    suite.addTest(TestMCPTools('test_search_games_tool'))
    suite.addTest(TestMCPTools('test_analyze_library_tool'))
    suite.addTest(TestMCPTools('test_find_family_games_tool'))
    suite.addTest(TestMCPTools('test_find_quick_session_games_tool'))
    
    runner = unittest.TextTestRunner(verbosity=1)
    return runner.run(suite)


def test_resources() -> unittest.TestResult:
    """Test MCP resources"""
    
    class TestResources(unittest.TestCase):
        @patch('mcp_server.resources.get_db')
        def test_resource_functions(self, mock_get_db):
            """Test resource functions return valid JSON"""
            from mcp_server import resources
            
            # Mock database
            mock_session = MagicMock()
            mock_get_db.return_value.__enter__.return_value = mock_session
            mock_session.query.return_value.count.return_value = 10
            mock_session.query.return_value.all.return_value = []
            mock_session.query.return_value.filter_by.return_value.first.return_value = None
            
            # Test library overview
            result = resources.library_overview()
            self.assertIsInstance(result, str)
            data = json.loads(result)
            self.assertIsInstance(data, dict)
            
            # Test genre stats
            result = resources.get_genre_stats()
            self.assertIsInstance(result, str)
            data = json.loads(result)
            self.assertIsInstance(data, dict)
    
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestResources)
    
    runner = unittest.TextTestRunner(verbosity=1)
    return runner.run(suite)


def test_prompts() -> unittest.TestResult:
    """Test MCP prompts"""
    
    class TestPrompts(unittest.TestCase):
        def test_prompt_functions(self):
            """Test prompt functions return valid strings"""
            from mcp_server import prompts
            
            # Test all prompt functions
            result = prompts.steam_search_help()
            self.assertIsInstance(result, str)
            self.assertTrue(len(result) > 0)
            
            result = prompts.steam_recommendation_help()
            self.assertIsInstance(result, str)
            self.assertTrue(len(result) > 0)
            
            result = prompts.steam_filter_help()
            self.assertIsInstance(result, str)
            self.assertTrue(len(result) > 0)
    
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestPrompts)
    
    runner = unittest.TextTestRunner(verbosity=1)
    return runner.run(suite)


def test_completions() -> unittest.TestResult:
    """Test MCP completions"""
    from test_mcp_protocol import TestMCPProtocolCompliance
    
    suite = unittest.TestSuite()
    suite.addTest(TestMCPProtocolCompliance('test_completion_functionality'))
    
    runner = unittest.TextTestRunner(verbosity=1)
    return runner.run(suite)


def test_database() -> unittest.TestResult:
    """Test database integration"""
    
    class TestDatabase(unittest.TestCase):
        def test_database_models(self):
            """Test database models are properly defined"""
            from shared.database import Game, UserGame, Genre, Category, Tag, UserProfile
            
            # Test model attributes
            self.assertTrue(hasattr(Game, 'app_id'))
            self.assertTrue(hasattr(Game, 'name'))
            self.assertTrue(hasattr(UserGame, 'steam_id'))
            self.assertTrue(hasattr(UserGame, 'playtime_forever'))
            self.assertTrue(hasattr(Genre, 'genre_name'))
            self.assertTrue(hasattr(Category, 'category_name'))
            self.assertTrue(hasattr(Tag, 'tag_name'))
            self.assertTrue(hasattr(UserProfile, 'steam_id'))
        
        @patch('shared.database.create_engine')
        def test_database_connection(self, mock_create_engine):
            """Test database connection handling"""
            from shared.database import get_db
            
            mock_engine = MagicMock()
            mock_create_engine.return_value = mock_engine
            
            with get_db() as session:
                self.assertIsNotNone(session)
    
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestDatabase)
    
    runner = unittest.TextTestRunner(verbosity=1)
    return runner.run(suite)


def test_error_handling() -> unittest.TestResult:
    """Test error handling"""
    from test_mcp_protocol import TestMCPProtocolCompliance
    
    suite = unittest.TestSuite()
    suite.addTest(TestMCPProtocolCompliance('test_error_handling'))
    
    runner = unittest.TextTestRunner(verbosity=1)
    return runner.run(suite)


def test_performance() -> unittest.TestResult:
    """Test performance characteristics"""
    
    class TestPerformance(unittest.TestCase):
        @patch('mcp_server.tools.get_db')
        @patch('mcp_server.tools.resolve_user_for_tool')
        def test_tool_response_time(self, mock_resolve_user, mock_get_db):
            """Test that tools respond within acceptable time"""
            from mcp_server.tools import smart_search
            
            # Mock setup
            mock_resolve_user.return_value = {"steam_id": "test", "display_name": "Test"}
            mock_session = MagicMock()
            mock_get_db.return_value.__enter__.return_value = mock_session
            mock_query = MagicMock()
            mock_query.join.return_value = mock_query
            mock_query.filter.return_value = mock_query
            mock_query.order_by.return_value = mock_query
            mock_query.distinct.return_value.limit.return_value = []
            mock_session.query.return_value = mock_query
            
            async def test():
                start = time.time()
                await smart_search("test", user="test_user")
                elapsed = time.time() - start
                
                # Should respond within 1 second for mock data
                self.assertLess(elapsed, 1.0, f"Tool took {elapsed:.2f}s to respond")
            
            asyncio.run(test())
    
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestPerformance)
    
    runner = unittest.TextTestRunner(verbosity=1)
    return runner.run(suite)


if __name__ == "__main__":
    sys.exit(run_comprehensive_tests())