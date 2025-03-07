"""
Utility functions for working with email signatures.
"""
import logging
import traceback
from bs4 import BeautifulSoup
import requests
import base64
import os
from flask import url_for, current_app

from models import EmailSignature
from utils.database import session_scope
from utils.gmail_integration import convert_image_urls_to_data_urls

logger = logging.getLogger(__name__)

def fix_all_signatures():
    """
    Fix all email signatures in the database by converting any image URLs to data URLs.
    This ensures that all images will be properly embedded in emails.
    
    Returns:
        dict: A summary of the operation
    """
    try:
        with session_scope() as session:
            signatures = session.query(EmailSignature).all()
            
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
                        # Convert all image URLs to data URLs
                        fixed_content = convert_image_urls_to_data_urls(signature.content)
                        signature.content = fixed_content
                        fixed_count += 1
                    else:
                        skipped_count += 1
                
                except Exception as e:
                    logger.error(f"Error fixing signature {signature.id}: {str(e)}")
                    logger.error(traceback.format_exc())
                    error_count += 1
            
            # Commit all changes
            if fixed_count > 0:
                session.commit()
            
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

def fix_user_signatures(user_id):
    """
    Fix all email signatures for a specific user by converting any image URLs to data URLs.
    
    Args:
        user_id (str): The user ID whose signatures should be fixed
        
    Returns:
        dict: A summary of the operation
    """
    try:
        with session_scope() as session:
            signatures = session.query(EmailSignature).filter_by(user_id=user_id).all()
            
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
                        # Convert all image URLs to data URLs
                        fixed_content = convert_image_urls_to_data_urls(signature.content)
                        signature.content = fixed_content
                        fixed_count += 1
                    else:
                        skipped_count += 1
                
                except Exception as e:
                    logger.error(f"Error fixing signature {signature.id}: {str(e)}")
                    logger.error(traceback.format_exc())
                    error_count += 1
            
            # Commit all changes
            if fixed_count > 0:
                session.commit()
            
            return {
                'total': len(signatures),
                'fixed': fixed_count,
                'skipped': skipped_count,
                'errors': error_count
            }
    
    except Exception as e:
        logger.error(f"Error fixing signatures for user {user_id}: {str(e)}")
        logger.error(traceback.format_exc())
        return {
            'error': str(e),
            'total': 0,
            'fixed': 0,
            'skipped': 0,
            'errors': 0
        } 