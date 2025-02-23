from flask import Blueprint, jsonify
import os

auth_api = Blueprint('auth_api', __name__)

@auth_api.route('/api/auth/config')
def get_oauth_config():
    return jsonify({
        'clientId': os.getenv('GOOGLE_CLIENT_ID'),
    })