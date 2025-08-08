#!/usr/bin/env python3
"""
Version synchronization script for Steam Librarian.

This script ensures all components maintain synchronized versions:
- MCP Server, Tools Server, Fetcher Module, Helm Chart
"""

import os
import re
import sys
from pathlib import Path

# Colors for output
class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    NC = '\033[0m'  # No Color

# File paths relative to project root
VERSION_FILES = {
    'mcp_server': 'src/mcp_server/__init__.py',
    'tools_server': 'src/oops_all_tools/__init__.py',
    'fetcher': 'src/fetcher/__init__.py',
    'helm_chart': 'deploy/helm/steam-librarian/Chart.yaml'
}

def get_project_root():
    """Get the project root directory."""
    return Path(__file__).parent.parent

def get_python_version(file_path):
    """Extract version from Python __init__.py files."""
    try:
        with open(file_path, 'r') as f:
            content = f.read()
            match = re.search(r'__version__ = ["\']([^"\']+)["\']', content)
            return match.group(1) if match else None
    except FileNotFoundError:
        return None

def get_helm_versions(file_path):
    """Extract version and appVersion from Helm Chart.yaml."""
    try:
        with open(file_path, 'r') as f:
            content = f.read()
            version_match = re.search(r'^version: (.+)$', content, re.MULTILINE)
            app_version_match = re.search(r'^appVersion: ["\']([^"\']+)["\']', content, re.MULTILINE)
            return (
                version_match.group(1) if version_match else None,
                app_version_match.group(1) if app_version_match else None
            )
    except FileNotFoundError:
        return None, None

def update_python_version(file_path, new_version):
    """Update Python __version__ in file."""
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        
        new_content = re.sub(
            r'__version__ = ["\'][^"\']+["\']',
            f'__version__ = "{new_version}"',
            content
        )
        
        with open(file_path, 'w') as f:
            f.write(new_content)
        
        return True
    except Exception as e:
        print(f"{Colors.RED}Error updating {file_path}: {e}{Colors.NC}")
        return False

def update_helm_versions(file_path, new_version):
    """Update both version and appVersion in Helm Chart.yaml."""
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        
        new_content = re.sub(r'^version: .+$', f'version: {new_version}', content, flags=re.MULTILINE)
        new_content = re.sub(r'^appVersion: .+$', f'appVersion: "{new_version}"', new_content, flags=re.MULTILINE)
        
        with open(file_path, 'w') as f:
            f.write(new_content)
        
        return True
    except Exception as e:
        print(f"{Colors.RED}Error updating {file_path}: {e}{Colors.NC}")
        return False

def main():
    """Main version synchronization logic."""
    print(f"{Colors.BLUE}🔍 Checking version synchronization...{Colors.NC}")
    
    project_root = get_project_root()
    os.chdir(project_root)
    
    # Collect all current versions
    versions = {}
    
    # Python modules
    for name, path in VERSION_FILES.items():
        if name == 'helm_chart':
            continue
        version = get_python_version(path)
        if version:
            versions[name] = version
            print(f"  {name.replace('_', ' ').title()}: {Colors.YELLOW}{version}{Colors.NC}")
    
    # Helm chart
    helm_version, helm_app_version = get_helm_versions(VERSION_FILES['helm_chart'])
    if helm_version and helm_app_version:
        versions['helm_version'] = helm_version
        versions['helm_app_version'] = helm_app_version
        print(f"  Helm Chart: {Colors.YELLOW}{helm_version}{Colors.NC} (appVersion: {Colors.YELLOW}{helm_app_version}{Colors.NC})")
    
    # Check for mismatches
    all_versions = list(versions.values())
    unique_versions = list(set(all_versions))
    
    if len(unique_versions) <= 1:
        print(f"{Colors.GREEN}✅ All components are synchronized{Colors.NC}")
        return 0
    
    # Find the latest version (semantic versioning)
    def version_key(v):
        try:
            return tuple(map(int, v.split('.')))
        except:
            return (0, 0, 0)
    
    latest_version = max(unique_versions, key=version_key)
    print(f"{Colors.YELLOW}⚠️  Version mismatch detected!{Colors.NC}")
    print(f"{Colors.BLUE}🎯 Synchronizing to latest version: {Colors.GREEN}{latest_version}{Colors.NC}")
    
    # Update all components
    updated = []
    
    for name, path in VERSION_FILES.items():
        if name == 'helm_chart':
            if helm_version != latest_version or helm_app_version != latest_version:
                if update_helm_versions(path, latest_version):
                    print(f"{Colors.GREEN}  ✓ Updated {path}{Colors.NC}")
                    updated.append(path)
        else:
            current_version = versions.get(name)
            if current_version != latest_version:
                if update_python_version(path, latest_version):
                    print(f"{Colors.GREEN}  ✓ Updated {path}{Colors.NC}")
                    updated.append(path)
    
    if updated:
        print(f"{Colors.GREEN}✅ Version synchronization complete!{Colors.NC}")
        # Stage the updated files for commit
        os.system(f"git add {' '.join(updated)}")
        return 0
    else:
        print(f"{Colors.RED}❌ Version synchronization failed{Colors.NC}")
        return 1

if __name__ == "__main__":
    sys.exit(main())