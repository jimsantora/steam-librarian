#!/usr/bin/env python3
"""Server health and startup testing for Steam Librarian MCP Server"""

import asyncio
import os
import signal
import subprocess
import sys
from pathlib import Path

try:
    import aiohttp
    HAS_AIOHTTP = True
except ImportError:
    HAS_AIOHTTP = False


class ServerHealthTests:
    """Simple server health and startup testing"""

    def __init__(self, port=8001):
        self.server_process = None
        self.base_url = f"http://localhost:{port}"
        self.port = port

    async def start_test_server(self):
        """Start the MCP server for testing"""
        print("🚀 Starting test server...")

        if not HAS_AIOHTTP:
            print("⚠️  aiohttp not available - skipping server startup test")
            return False

        # Start server process
        cmd = [
            sys.executable,
            str(Path(__file__).parent.parent / "src" / "mcp_server" / "run_server.py")
        ]

        env = {
            **dict(os.environ),
            "MCP_HOST": "127.0.0.1",
            "MCP_PORT": str(self.port),
            "DEBUG": "false"  # Reduce noise during tests
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
            for i in range(20):  # 20 second timeout
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.get(f"{self.base_url}/health", timeout=2) as response:
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
        print("🏥 Testing Health Endpoints...")

        if not HAS_AIOHTTP:
            print("⚠️  Skipping health endpoint tests - aiohttp not available")
            return False

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
                    print("✅ Detailed health check")
            except Exception as e:
                print(f"❌ Detailed health check failed: {e}")
                return False

        return True

    async def test_mcp_endpoint_accessibility(self):
        """Test that MCP endpoint is accessible"""
        print("🔌 Testing MCP Endpoint...")

        if not HAS_AIOHTTP:
            print("⚠️  Skipping MCP endpoint test - aiohttp not available")
            return False

        async with aiohttp.ClientSession() as session:
            try:
                # Test that MCP endpoint exists and responds
                async with session.post(
                    f"{self.base_url}/mcp",
                    json={
                        "jsonrpc": "2.0",
                        "method": "initialize",
                        "params": {
                            "protocolVersion": "2025-06-18",
                            "capabilities": {},
                            "clientInfo": {"name": "test-client", "version": "1.0.0"}
                        },
                        "id": 1
                    }
                ) as response:
                    # Should get some response (even if it's an error due to protocol mismatch)
                    assert response.status in [200, 400, 405, 500]
                    print("✅ MCP endpoint accessible")
                    return True
            except Exception as e:
                print(f"❌ MCP endpoint test failed: {e}")
                return False

    async def run_all_tests(self):
        """Run all server health tests"""
        print("🔗 Steam Librarian MCP Server Health Tests")
        print("=" * 50)

        if not HAS_AIOHTTP:
            print("⚠️  aiohttp not available - most tests will be skipped")
            print("   Install with: pip install aiohttp")
            return False

        try:
            # Start test server
            if not await self.start_test_server():
                return False

            # Run health tests
            health_ok = await self.test_health_endpoints()
            mcp_ok = await self.test_mcp_endpoint_accessibility()

            success = health_ok and mcp_ok

            if success:
                print("\n✅ All server health tests passed!")
            else:
                print("\n❌ Some server health tests failed")

            return success

        finally:
            # Always stop the server
            self.stop_test_server()


async def main():
    """Main test runner"""
    tester = ServerHealthTests()
    success = await tester.run_all_tests()
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
