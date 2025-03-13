#!/usr/bin/env python3
"""
Script to fix email signatures by converting image URLs to data URLs.
This ensures that all images in signatures will be properly embedded in emails.

Usage:
    python fix_signatures.py [--user USER_ID]

Options:
    --user USER_ID    Fix signatures for a specific user only
"""

import os
import sys
import argparse
import logging
from bs4 import BeautifulSoup
import requests
import base64
import traceback
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add the current directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Create database engine - use explicit path to instance folder
engine = create_engine('sqlite:///instance/mobilize_crm.db')
Session = sessionmaker(bind=engine)

@contextmanager
def session_scope():
    """Provide a transactional scope around a series of operations."""
    session = Session()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

def convert_image_urls_to_data_urls(html_content):
    """
    Convert all image URLs in HTML content to data URLs.
    This ensures that images are embedded directly in the email and will display properly.
    
    Args:
        html_content: HTML content containing image tags
        
    Returns:
        HTML content with image URLs converted to data URLs
    """
    if not html_content:
        return html_content
        
    soup = BeautifulSoup(html_content, 'html.parser')
    img_tags = soup.find_all('img')
    
    for img in img_tags:
        src = img.get('src')
        if not src:
            continue
            
        # Skip if it's already a data URL
        if src.startswith('data:'):
            continue
            
        try:
            # Handle relative URLs
            if src.startswith('/'):
                # For development environment
                src = f"http://127.0.0.1:8000{src}"
                    
            # Download the image
            response = requests.get(src, stream=True)
            if response.status_code == 200:
                # Determine content type
                content_type = response.headers.get('Content-Type', 'image/jpeg')
                
                # Convert to base64
                img_data = base64.b64encode(response.content).decode('utf-8')
                
                # Create data URL
                data_url = f"data:{content_type};base64,{img_data}"
                
                # Replace the src attribute
                img['src'] = data_url
                logger.info(f"Converted image URL to data URL: {src[:30]}...")
            else:
                logger.warning(f"Failed to download image from {src}: {response.status_code}")
        except Exception as e:
            logger.error(f"Error converting image URL to data URL: {str(e)}")
            logger.error(traceback.format_exc())
    
    return str(soup)

def fix_signatures(user_id=None):
    """
    Fix email signatures by converting image URLs to data URLs.
    
    Args:
        user_id: Optional user ID to fix signatures for a specific user only
        
    Returns:
        dict: A summary of the operation
    """
    from models import EmailSignature
    
    try:
        with session_scope() as session:
            # Query signatures
            if user_id:
                signatures = session.query(EmailSignature).filter_by(user_id=user_id).all()
                logger.info(f"Found {len(signatures)} signatures for user {user_id}")
            else:
                signatures = session.query(EmailSignature).all()
                logger.info(f"Found {len(signatures)} signatures total")
            
            fixed_count = 0
            error_count = 0
            skipped_count = 0
            
            for signature in signatures:
                try:
                    if not signature.content:
                        skipped_count += 1
                        continue
                    
                    # Check if the signature contains any non-data URL images
                    soup = BeautifulSoup(signature.content, 'html.parser')
                    img_tags = soup.find_all('img')
                    
                    needs_fixing = False
                    for img in img_tags:
                        src = img.get('src')
                        if src and not src.startswith('data:'):
                            needs_fixing = True
                            break
                    
                    if needs_fixing:
                        logger.info(f"Fixing signature {signature.id} for user {signature.user_id}")
                        # Convert all image URLs to data URLs
                        fixed_content = convert_image_urls_to_data_urls(signature.content)
                        signature.content = fixed_content
                        fixed_count += 1
                    else:
                        logger.debug(f"Signature {signature.id} doesn't need fixing")
                        skipped_count += 1
                
                except Exception as e:
                    logger.error(f"Error fixing signature {signature.id}: {str(e)}")
                    logger.error(traceback.format_exc())
                    error_count += 1
            
            # Commit all changes
            if fixed_count > 0:
                # No need to explicitly commit as session_scope will do it
                logger.info(f"Committed changes for {fixed_count} signatures")
            
            return {
                'total': len(signatures),
                'fixed': fixed_count,
                'skipped': skipped_count,
                'errors': error_count
            }
    
    except Exception as e:
        logger.error(f"Error fixing signatures: {str(e)}")
        logger.error(traceback.format_exc())
        return {
            'error': str(e),
            'total': 0,
            'fixed': 0,
            'skipped': 0,
            'errors': 0
        }

def main():
    """Main entry point for the script"""
    parser = argparse.ArgumentParser(description='Fix email signatures by converting image URLs to data URLs')
    parser.add_argument('--user', help='Fix signatures for a specific user only')
    args = parser.parse_args()
    
    # Fix signatures
    result = fix_signatures(args.user)
    
    # Print summary
    print("\nSignature Fix Summary:")
    print(f"Total signatures: {result.get('total', 0)}")
    print(f"Fixed: {result.get('fixed', 0)}")
    print(f"Skipped: {result.get('skipped', 0)}")
    print(f"Errors: {result.get('errors', 0)}")
    
    if 'error' in result:
        print(f"Error: {result['error']}")
        return 1
    
    return 0

if __name__ == '__main__':
    sys.exit(main()) 