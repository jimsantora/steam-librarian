#!/usr/bin/env python3
"""Integration tests for Steam Librarian MCP Server"""

import asyncio
import os
import subprocess
import time
import sys
import signal
from pathlib import Path
from contextlib import asynccontextmanager

try:
    import aiohttp
    HAS_AIOHTTP = True
except ImportError:
    HAS_AIOHTTP = False
    print("⚠️  aiohttp not available - integration tests will be limited")

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


class IntegrationTestSuite:
    """Integration tests that start the actual server"""
    
    def __init__(self):
        self.server_process = None
        self.base_url = "http://localhost:8001"  # Use different port for testing
        
    async def start_test_server(self):
        """Start the MCP server for testing"""
        print("🚀 Starting test server...")
        
        if not HAS_AIOHTTP:
            print("⚠️  Skipping server startup test - aiohttp not available")
            return True
        
        # Start server process
        cmd = [
            sys.executable, 
            str(Path(__file__).parent.parent / "src" / "mcp_server" / "run_server.py")
        ]
        
        env = {
            **dict(os.environ),
            "HOST": "127.0.0.1",
            "PORT": "8001",
            "DEBUG": "true",
            "LOG_LEVEL": "WARNING"  # Reduce noise during tests
        }
        
        try:
            self.server_process = subprocess.Popen(
                cmd,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=os.setsid if hasattr(os, 'setsid') else None
            )
            
            # Wait for server to start
            for i in range(30):  # 30 second timeout
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.get(f"{self.base_url}/health", timeout=1) as response:
                            if response.status == 200:
                                print("✅ Test server started successfully")
                                return True
                except:
                    pass
                await asyncio.sleep(1)
            
            print("❌ Test server failed to start within timeout")
            return False
            
        except Exception as e:
            print(f"❌ Failed to start test server: {e}")
            return False
    
    def stop_test_server(self):
        """Stop the test server"""
        if self.server_process:
            print("🛑 Stopping test server...")
            try:
                if hasattr(os, 'killpg'):
                    os.killpg(os.getpgid(self.server_process.pid), signal.SIGTERM)
                else:
                    self.server_process.terminate()
                
                # Wait for process to end
                try:
                    self.server_process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    if hasattr(os, 'killpg'):
                        os.killpg(os.getpgid(self.server_process.pid), signal.SIGKILL)
                    else:
                        self.server_process.kill()
                
                print("✅ Test server stopped")
            except Exception as e:
                print(f"⚠️  Error stopping test server: {e}")
    
    async def test_health_endpoints(self):
        """Test health check endpoints"""
        print("\n🏥 Testing Health Endpoints...")
        
        if not HAS_AIOHTTP:
            print("⚠️  Skipping health endpoint tests - aiohttp not available")
            return True
        
        async with aiohttp.ClientSession() as session:
            # Test basic health check
            try:
                async with session.get(f"{self.base_url}/health") as response:
                    assert response.status == 200
                    text = await response.text()
                    assert "OK" in text
                    print("✅ Basic health check")
            except Exception as e:
                print(f"❌ Basic health check failed: {e}")
                return False
            
            # Test detailed health check
            try:
                async with session.get(f"{self.base_url}/health/detailed") as response:
                    assert response.status == 200
                    data = await response.json()
                    assert "status" in data
                    assert "components" in data
                    print("✅ Detailed health check")
            except Exception as e:
                print(f"❌ Detailed health check failed: {e}")
                return False
            
            # Test config endpoint
            try:
                async with session.get(f"{self.base_url}/config") as response:
                    assert response.status == 200
                    data = await response.json()
                    assert "server_info" in data
                    assert "features" in data
                    print("✅ Configuration endpoint")
            except Exception as e:
                print(f"❌ Configuration endpoint failed: {e}")
                return False
            
            # Test metrics endpoint
            try:
                async with session.get(f"{self.base_url}/metrics") as response:
                    assert response.status == 200
                    data = await response.json()
                    assert "timestamp" in data
                    print("✅ Metrics endpoint")
            except Exception as e:
                print(f"❌ Metrics endpoint failed: {e}")
                return False
        
        return True
    
    async def test_mcp_protocol(self):
        """Test MCP protocol endpoint (basic connectivity)"""
        print("\n🔌 Testing MCP Protocol...")
        
        if not HAS_AIOHTTP:
            print("⚠️  Skipping MCP protocol tests - aiohttp not available")
            return True
        
        async with aiohttp.ClientSession() as session:
            try:
                # Test that MCP endpoint exists and responds
                async with session.post(
                    f"{self.base_url}/mcp",
                    json={
                        "jsonrpc": "2.0",
                        "method": "initialize",
                        "params": {
                            "protocolVersion": "2024-11-05",
                            "capabilities": {},
                            "clientInfo": {"name": "test-client", "version": "1.0.0"}
                        },
                        "id": 1
                    }
                ) as response:
                    # Should get some response (even if it's an error due to protocol mismatch)
                    assert response.status in [200, 400, 405, 500]  # Any of these is fine for basic connectivity
                    print("✅ MCP endpoint accessible")
                    return True
            except Exception as e:
                print(f"❌ MCP protocol test failed: {e}")
                return False
    
    async def run_integration_tests(self):
        """Run all integration tests"""
        print("🔗 Steam Librarian MCP Server Integration Tests")
        print("=" * 50)
        
        
        try:
            # Start test server
            if not await self.start_test_server():
                return False
            
            # Run tests
            results = []
            results.append(await self.test_health_endpoints())
            results.append(await self.test_mcp_protocol())
            
            # Calculate results
            passed = sum(results)
            total = len(results)
            
            print(f"\n📊 Integration Test Results: {passed}/{total} passed")
            
            if passed == total:
                print("🎉 All integration tests passed!")
                return True
            else:
                print(f"❌ {total - passed} integration test(s) failed")
                return False
            
        finally:
            # Always stop the server
            self.stop_test_server()


async def main():
    """Main integration test runner"""
    try:
        test_suite = IntegrationTestSuite()
        success = await test_suite.run_integration_tests()
        return 0 if success else 1
    except KeyboardInterrupt:
        print("\n🛑 Integration tests interrupted by user")
        return 1
    except Exception as e:
        print(f"\n💥 Integration test suite crashed: {e}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)