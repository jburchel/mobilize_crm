#!/usr/bin/env python3
"""
Route Verification Script

This script scans template files for url_for references and verifies that the
referenced routes actually exist in the Flask application.

Usage:
    python verify_routes.py

Output:
    List of potential route mismatches or confirmation that all routes are valid
"""

import os
import re
import importlib
import sys
from collections import defaultdict

# Directories to scan
TEMPLATE_DIR = 'templates'
ROUTES_DIR = 'routes'

def extract_routes_from_blueprints():
    """Extract all route functions from blueprint files."""
    routes = {}
    blueprint_pattern = re.compile(r'(\w+)_bp\s*=\s*Blueprint\(')
    route_pattern = re.compile(r'@(\w+)_bp\.route\([\'"].*[\'"]\).*\ndef\s+(\w+)\(')
    
    for filename in os.listdir(ROUTES_DIR):
        if filename.endswith('.py'):
            filepath = os.path.join(ROUTES_DIR, filename)
            with open(filepath, 'r') as f:
                content = f.read()
                
                # Find blueprint name
                blueprint_match = blueprint_pattern.search(content)
                if blueprint_match:
                    blueprint_name = blueprint_match.group(1) + '_bp'
                    
                    # Find all route functions
                    for match in route_pattern.finditer(content):
                        bp_name = match.group(1) + '_bp'
                        if bp_name == blueprint_name:
                            route_name = match.group(2)
                            routes[f"{blueprint_name}.{route_name}"] = filepath
    
    return routes

def extract_url_for_from_templates():
    """Extract all url_for references from template files."""
    url_for_pattern = re.compile(r'url_for\([\'"](\w+\.\w+)[\'"]')
    references = defaultdict(list)
    
    for root, _, files in os.walk(TEMPLATE_DIR):
        for filename in files:
            if filename.endswith('.html'):
                filepath = os.path.join(root, filename)
                with open(filepath, 'r') as f:
                    content = f.read()
                    
                    # Find all url_for references
                    for match in url_for_pattern.finditer(content):
                        route_ref = match.group(1)
                        references[route_ref].append(filepath)
    
    return references

def main():
    print("Verifying routes in templates against blueprint definitions...")
    
    # Extract routes and references
    defined_routes = extract_routes_from_blueprints()
    template_references = extract_url_for_from_templates()
    
    # Check for mismatches
    mismatches = []
    for route_ref, files in template_references.items():
        if route_ref not in defined_routes:
            mismatches.append((route_ref, files))
    
    # Report results
    if mismatches:
        print("\n❌ Found potential route mismatches:")
        for route_ref, files in mismatches:
            print(f"\n  Route '{route_ref}' referenced in:")
            for file in files:
                print(f"    - {file}")
            
            # Suggest possible correct routes
            bp_name, func_name = route_ref.split('.')
            suggestions = []
            for defined_route in defined_routes:
                if defined_route.startswith(bp_name):
                    suggestions.append(defined_route)
            
            if suggestions:
                print("  Possible correct routes:")
                for suggestion in suggestions[:5]:  # Limit to 5 suggestions
                    print(f"    - {suggestion}")
        
        print("\nPlease fix these mismatches before deployment.")
        return 1
    else:
        print("\n✅ All template route references match defined routes.")
        return 0

if __name__ == "__main__":
    sys.exit(main()) 