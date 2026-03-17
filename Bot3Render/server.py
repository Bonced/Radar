"""
Flask web server with REST API endpoints
Serves the web interface and handles threat data
"""
from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
import time
import os
from database import db, get_all_cities
from parser import parse_threat_message

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'your-secret-key-change-this-in-production')
CORS(app)  # Enable CORS for all routes

# Register admin blueprint
from admin import admin_bp
app.register_blueprint(admin_bp)

# Request rate limiting
request_log = {}
MAX_REQUESTS_PER_MINUTE = 30


def rate_limit_check(identifier: str) -> bool:
    """Simple rate limiting"""
    current_time = time.time()
    
    # Clean old entries
    request_log[identifier] = [
        t for t in request_log.get(identifier, [])
        if current_time - t < 60
    ]
    
    # Check limit
    if len(request_log.get(identifier, [])) >= MAX_REQUESTS_PER_MINUTE:
        return False
    
    # Add new request
    if identifier not in request_log:
        request_log[identifier] = []
    request_log[identifier].append(current_time)
    
    return True


@app.route('/')
def index():
    """Serve the main map interface"""
    return render_template('index.html')


@app.route('/api/threats', methods=['GET'])
def get_threats():
    """
    GET /api/threats - Retrieve recent threats
    Query params:
        - limit: max number of threats (default 100)
        - active_only: only threats from last hour (default false)
    """
    try:
        limit = int(request.args.get('limit', 100))
        active_only = request.args.get('active_only', 'false').lower() == 'true'
        
        if active_only:
            threats = db.get_active_threats()[:limit]
        else:
            threats = db.get_threats(limit)
        
        return jsonify({
            'success': True,
            'count': len(threats),
            'threats': threats
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/report', methods=['POST'])
def report_threat():
    """
    POST /api/report - Report a new threat
    Body: JSON with threat data or raw message
    """
    # Rate limiting
    client_ip = request.remote_addr
    if not rate_limit_check(client_ip):
        return jsonify({
            'success': False,
            'error': 'Rate limit exceeded'
        }), 429
    
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400
        
        # If raw message is provided, parse it
        if 'raw_message' in data and 'threat_type' not in data:
            parsed = parse_threat_message(
                data['raw_message'],
                data.get('source_channel')
            )
            if not parsed:
                return jsonify({
                    'success': False,
                    'error': 'Failed to parse message'
                }), 400
            threat_data = parsed
        else:
            threat_data = data
        
        # Add threat to database
        added = db.add_threat(threat_data)
        
        if added:
            return jsonify({
                'success': True,
                'message': 'Threat added successfully'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Duplicate threat (already reported)'
            })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/statistics', methods=['GET'])
def get_statistics():
    """GET /api/statistics - Get database statistics"""
    try:
        stats = db.get_statistics()
        return jsonify({
            'success': True,
            'statistics': stats
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/cities', methods=['GET'])
def get_cities():
    """GET /api/cities - Get all tracked cities with coordinates"""
    try:
        cities = get_all_cities()
        return jsonify({
            'success': True,
            'cities': cities
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/health', methods=['GET'])
def health_check():
    """GET /api/health - Health check endpoint"""
    stats = db.get_statistics()
    return jsonify({
        'status': 'online',
        'timestamp': time.time(),
        'total_threats': stats['total_threats'],
        'active_threats': stats['active_threats']
    })


@app.errorhandler(404)
def not_found(e):
    """Handle 404 errors"""
    return jsonify({
        'success': False,
        'error': 'Endpoint not found'
    }), 404


@app.errorhandler(500)
def internal_error(e):
    """Handle 500 errors"""
    return jsonify({
        'success': False,
        'error': 'Internal server error'
    }), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000, debug=True)
