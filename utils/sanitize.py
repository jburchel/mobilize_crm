import bleach
from functools import wraps
from flask import request
import json

ALLOWED_TAGS = [
    'a', 'abbr', 'acronym', 'b', 'blockquote', 'code',
    'em', 'i', 'li', 'ol', 'strong', 'ul', 'p', 'br'
]

ALLOWED_ATTRIBUTES = {
    'a': ['href', 'title'],
    'abbr': ['title'],
    'acronym': ['title'],
}

def sanitize_string(text):
    """Sanitize a single string value"""
    if isinstance(text, str):
        return bleach.clean(
            text,
            tags=ALLOWED_TAGS,
            attributes=ALLOWED_ATTRIBUTES,
            strip=True
        )
    return text

def sanitize_dict(data):
    """Recursively sanitize all string values in a dictionary"""
    if isinstance(data, dict):
        return {k: sanitize_dict(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [sanitize_dict(item) for item in data]
    else:
        return sanitize_string(data)

def sanitize_input(f):
    """Decorator to sanitize all incoming request data"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Sanitize form data
        if request.form:
            request.form = sanitize_dict(request.form.to_dict())
            
        # Sanitize JSON data
        if request.is_json:
            try:
                request.json = sanitize_dict(request.get_json())
            except json.JSONDecodeError:
                pass
            
        # Sanitize query parameters
        if request.args:
            request.args = sanitize_dict(request.args.to_dict())
            
        return f(*args, **kwargs)
    return decorated_function