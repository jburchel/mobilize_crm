#!/usr/bin/env python
import requests
import sys
import re
import time
import argparse

def check_page(url, expected_content=None, timeout=5, retries=3):
    """
    Check if a page is accessible and contains expected content
    
    Args:
        url: URL to check
        expected_content: Content to look for (regex pattern)
        timeout: Request timeout in seconds
        retries: Number of retry attempts
    
    Returns:
        tuple: (success, status_code, has_expected_content)
    """
    for attempt in range(retries):
        try:
            response = requests.get(url, timeout=timeout)
            
            # Check if page is accessible
            if response.status_code == 200:
                # Check for expected content if provided
                if expected_content:
                    has_content = re.search(expected_content, response.text, re.IGNORECASE)
                    return True, response.status_code, bool(has_content)
                return True, response.status_code, True
            else:
                # If not successful and we have more retries, wait and try again
                if attempt < retries - 1:
                    time.sleep(1)
                    continue
                return False, response.status_code, False
                
        except requests.RequestException as e:
            # If not successful and we have more retries, wait and try again
            if attempt < retries - 1:
                time.sleep(1)
                continue
            return False, None, False
    
    return False, None, False

def main():
    parser = argparse.ArgumentParser(description="Check data retrieval from the application")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", 
                        help="Base URL of the application (default: http://127.0.0.1:8000)")
    parser.add_argument("--timeout", type=int, default=5,
                        help="Request timeout in seconds (default: 5)")
    parser.add_argument("--retries", type=int, default=3,
                        help="Number of retry attempts (default: 3)")
    
    args = parser.parse_args()
    
    # Define pages to check
    pages = {
        "People": {
            "url": f"{args.base_url}/people/",
            "expected_content": r"<tr[^>]*>.*?<td[^>]*>.*?</td>.*?</tr>"  # Look for table rows with data
        },
        "Churches": {
            "url": f"{args.base_url}/churches/",
            "expected_content": r"<tr[^>]*>.*?<td[^>]*>.*?</td>.*?</tr>"  # Look for table rows with data
        }
    }
    
    all_success = True
    
    # Check each page
    for page_name, page_info in pages.items():
        print(f"Checking {page_name} page at {page_info['url']}...")
        success, status_code, has_content = check_page(
            page_info['url'], 
            page_info['expected_content'],
            args.timeout,
            args.retries
        )
        
        if success:
            print(f"✅ {page_name} page returned status code {status_code}")
            if has_content:
                print(f"✅ {page_name} page appears to show data")
            else:
                print(f"❌ {page_name} page does not appear to show data")
                all_success = False
        else:
            print(f"❌ {page_name} page check failed with status code {status_code}")
            all_success = False
    
    print("\n✅ Data retrieval check complete." if all_success else "\n❌ Data retrieval check failed.")
    return 0 if all_success else 1

if __name__ == "__main__":
    sys.exit(main()) 