#!/usr/bin/env python3
"""Monitoring and administration tool for Steam Librarian MCP Server"""

import argparse
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import aiohttp

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp_server.config import settings


class ServerMonitor:
    """Monitor and manage the Steam Librarian MCP Server"""

    def __init__(self, host: str = None, port: int = None):
        self.host = host or settings.host
        self.port = port or settings.port
        self.base_url = f"http://{self.host}:{self.port}"

    async def check_health(self, detailed: bool = False) -> dict[str, Any]:
        """Check server health"""
        endpoint = "/health/detailed" if detailed else "/health"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}{endpoint}") as response:
                    if response.content_type == "application/json":
                        return await response.json()
                    else:
                        text = await response.text()
                        return {"status": "healthy" if response.status == 200 else "unhealthy", "message": text, "status_code": response.status}
        except aiohttp.ClientConnectorError:
            return {"status": "unreachable", "message": f"Cannot connect to server at {self.base_url}", "status_code": 0}
        except Exception as e:
            return {"status": "error", "message": str(e), "status_code": 0}

    async def get_config(self) -> dict[str, Any]:
        """Get server configuration"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/config") as response:
                    return await response.json()
        except Exception as e:
            return {"error": str(e)}

    async def get_metrics(self) -> dict[str, Any]:
        """Get server metrics"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/metrics") as response:
                    return await response.json()
        except Exception as e:
            return {"error": str(e)}

    async def list_tools(self) -> dict[str, Any]:
        """List available MCP tools"""
        try:
            # Note: This would require implementing a /tools endpoint or using MCP protocol
            # For now, return a placeholder
            return {"message": "Tool listing requires MCP protocol client"}
        except Exception as e:
            return {"error": str(e)}

    def format_health_status(self, health_data: dict[str, Any]) -> str:
        """Format health status for display"""
        if "status" not in health_data:
            return f"Error: {health_data.get('error', 'Unknown error')}"

        status = health_data["status"]
        if status == "healthy":
            icon = "[HEALTHY]"
        elif status == "unhealthy":
            icon = "[UNHEALTHY]"
        elif status == "unreachable":
            icon = "[UNREACHABLE]"
        else:
            icon = "[UNKNOWN]"

        result = f"{icon} Server Status: {status.upper()}"

        if "timestamp" in health_data:
            result += f"\nTimestamp: {health_data['timestamp']}"

        if "server" in health_data:
            server = health_data["server"]
            result += f"\nServer: {server.get('name', 'unknown')} v{server.get('version', 'unknown')}"
            result += f"\nPID: {server.get('pid', 'unknown')}"

        if "components" in health_data:
            result += "\n\nComponent Status:"
            for name, component in health_data["components"].items():
                comp_status = component.get("status", "unknown")
                comp_icon = "[OK]" if comp_status == "healthy" else "[ERR]"
                result += f"\n  {comp_icon} {name}: {comp_status}"

                if "error" in component:
                    result += f" ({component['error']})"
                elif "count" in component:
                    result += f" ({component['count']} items)"
                elif "user_count" in component:
                    result += f" ({component['user_count']} users)"

        return result

    def format_metrics(self, metrics_data: dict[str, Any]) -> str:
        """Format metrics for display"""
        if "error" in metrics_data:
            return f"Error: {metrics_data['error']}"

        result = "Server Metrics\n"
        result += f"Timestamp: {metrics_data.get('timestamp', 'unknown')}\n"

        if "system" in metrics_data:
            sys_data = metrics_data["system"]
            result += "\nSystem Resources:\n"
            result += f"  CPU: {sys_data.get('cpu_percent', 0):.1f}%\n"
            result += f"  Memory: {sys_data.get('memory_mb', 0):.1f} MB ({sys_data.get('memory_percent', 0):.1f}%)\n"
            result += f"  Threads: {sys_data.get('threads', 0)}\n"
            result += f"  Uptime: {sys_data.get('uptime_seconds', 0):.0f} seconds\n"

        if "cache" in metrics_data:
            cache_data = metrics_data["cache"]
            result += "\nCache:\n"
            result += f"  Size: {cache_data.get('size', 0)}/{cache_data.get('max_size', 0)}\n"
            result += f"  Hit Rate: {cache_data.get('hit_rate', 0):.2f}\n"

        if "database" in metrics_data:
            db_data = metrics_data["database"]
            result += "\nDatabase:\n"
            result += f"  Users: {db_data.get('users', 0)}\n"
            result += f"  Games: {db_data.get('games', 0)}\n"

        return result

    def format_config(self, config_data: dict[str, Any]) -> str:
        """Format configuration for display"""
        if "error" in config_data:
            return f"Error: {config_data['error']}"

        result = "Server Configuration\n"

        if "server_info" in config_data:
            server = config_data["server_info"]
            result += "\nServer Info:\n"
            result += f"  Name: {server.get('name', 'unknown')}\n"
            result += f"  Version: {server.get('version', 'unknown')}\n"
            result += f"  Host: {server.get('host', 'unknown')}:{server.get('port', 'unknown')}\n"
            result += f"  Debug: {server.get('debug', False)}\n"
            result += f"  Log Level: {server.get('log_level', 'unknown')}\n"

        if "features" in config_data:
            result += "\nFeature Flags:\n"
            for feature, enabled in config_data["features"].items():
                icon = "[ON]" if enabled else "[OFF]"
                result += f"  {icon} {feature}\n"

        if "validation" in config_data:
            validation = config_data["validation"]
            result += "\nConfiguration Validation:\n"
            result += f"  Valid: {'[YES]' if validation.get('valid', False) else '[NO]'}\n"

            if validation.get("warnings"):
                result += "  Warnings:\n"
                for warning in validation["warnings"]:
                    result += f"    WARNING: {warning}\n"

            if validation.get("errors"):
                result += "  Errors:\n"
                for error in validation["errors"]:
                    result += f"    ERROR: {error}\n"

        return result


async def main():
    """Main monitoring function"""
    parser = argparse.ArgumentParser(description="Steam Librarian MCP Server Monitor")
    parser.add_argument("--host", default=settings.host, help="Server host")
    parser.add_argument("--port", type=int, default=settings.port, help="Server port")
    parser.add_argument("--interval", type=int, default=5, help="Monitoring interval in seconds")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Health check command
    health_parser = subparsers.add_parser("health", help="Check server health")
    health_parser.add_argument("--detailed", action="store_true", help="Get detailed health information")

    # Config command
    subparsers.add_parser("config", help="Show server configuration")

    # Metrics command
    subparsers.add_parser("metrics", help="Show server metrics")

    # Monitor command (continuous monitoring)
    monitor_parser = subparsers.add_parser("monitor", help="Continuous monitoring")
    monitor_parser.add_argument("--format", choices=["text", "json"], default="text", help="Output format")

    # Status command (all info at once)
    subparsers.add_parser("status", help="Show complete server status")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    monitor = ServerMonitor(args.host, args.port)

    if args.command == "health":
        health_data = await monitor.check_health(detailed=args.detailed)
        print(monitor.format_health_status(health_data))  # noqa: T201

    elif args.command == "config":
        config_data = await monitor.get_config()
        print(monitor.format_config(config_data))  # noqa: T201

    elif args.command == "metrics":
        metrics_data = await monitor.get_metrics()
        print(monitor.format_metrics(metrics_data))  # noqa: T201

    elif args.command == "status":
        print("Fetching complete server status...\n")  # noqa: T201

        health_data = await monitor.check_health(detailed=True)
        print(monitor.format_health_status(health_data))  # noqa: T201
        print("\n" + "=" * 60 + "\n")  # noqa: T201

        metrics_data = await monitor.get_metrics()
        print(monitor.format_metrics(metrics_data))  # noqa: T201
        print("\n" + "=" * 60 + "\n")  # noqa: T201

        config_data = await monitor.get_config()
        print(monitor.format_config(config_data))  # noqa: T201

    elif args.command == "monitor":
        print(f"Starting continuous monitoring (interval: {args.interval}s)")  # noqa: T201
        print("Press Ctrl+C to stop\n")  # noqa: T201

        try:
            while True:
                if args.format == "json":
                    health_data = await monitor.check_health(detailed=True)
                    metrics_data = await monitor.get_metrics()

                    output = {"timestamp": datetime.now().isoformat(), "health": health_data, "metrics": metrics_data}
                    print(json.dumps(output, indent=2))  # noqa: T201
                else:
                    print(f"Monitor Update - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")  # noqa: T201

                    health_data = await monitor.check_health()
                    print(monitor.format_health_status(health_data))  # noqa: T201

                    print("\n" + "-" * 40 + "\n")  # noqa: T201

                await asyncio.sleep(args.interval)

        except KeyboardInterrupt:
            print("\nMonitoring stopped")  # noqa: T201


if __name__ == "__main__":
    asyncio.run(main())
