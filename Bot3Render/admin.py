"""
Admin panel for managing the userbot
Password-protected interface for adding/removing channels
"""
from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
from functools import wraps
import os
import json

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# Admin password from environment variable
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'admin123')  # Change this!

# File to store channel list
CHANNELS_FILE = 'monitored_channels.json'


def load_channels():
    """Load channels from file"""
    try:
        if os.path.exists(CHANNELS_FILE):
            with open(CHANNELS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []
    except:
        return []


def save_channels(channels):
    """Save channels to file"""
    try:
        with open(CHANNELS_FILE, 'w', encoding='utf-8') as f:
            json.dump(channels, f, ensure_ascii=False, indent=2)
        return True
    except:
        return False


def login_required(f):
    """Decorator to require admin login"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return redirect(url_for('admin.login'))
        return f(*args, **kwargs)
    return decorated_function


@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Admin login page"""
    if request.method == 'POST':
        password = request.form.get('password', '')
        
        if password == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            session.permanent = True
            return redirect(url_for('admin.panel'))
        else:
            return render_template('admin_login.html', error='Неверный пароль')
    
    # If already logged in, redirect to panel
    if session.get('admin_logged_in'):
        return redirect(url_for('admin.panel'))
    
    return render_template('admin_login.html')


@admin_bp.route('/logout')
def logout():
    """Logout admin"""
    session.pop('admin_logged_in', None)
    return redirect(url_for('admin.login'))


@admin_bp.route('/panel')
@login_required
def panel():
    """Admin control panel"""
    channels = load_channels()
    
    # Get userbot status
    from userbot import userbot
    
    userbot_status = {
        'running': userbot.client is not None and userbot.client.is_connected() if userbot.client else False,
        'channels_active': len(userbot.channel_entities) if hasattr(userbot, 'channel_entities') else 0
    }
    
    # Get database stats
    from database import db
    stats = db.get_statistics()
    
    return render_template('admin_panel.html', 
                         channels=channels,
                         userbot_status=userbot_status,
                         stats=stats)


@admin_bp.route('/api/channels', methods=['GET'])
@login_required
def get_channels():
    """Get list of monitored channels"""
    channels = load_channels()
    return jsonify({'success': True, 'channels': channels})


@admin_bp.route('/api/channels/add', methods=['POST'])
@login_required
def add_channel():
    """Add a channel to monitor"""
    data = request.get_json()
    channel = data.get('channel', '').strip()
    
    if not channel:
        return jsonify({'success': False, 'error': 'Channel name required'})
    
    # Validate format
    if not (channel.startswith('@') or channel.startswith('-100') or channel.lstrip('-').isdigit()):
        return jsonify({'success': False, 'error': 'Invalid format. Use @username or -1001234567890'})
    
    channels = load_channels()
    
    if channel in channels:
        return jsonify({'success': False, 'error': 'Channel already exists'})
    
    channels.append(channel)
    
    if save_channels(channels):
        # Update environment variable for userbot
        update_monitored_channels(channels)
        return jsonify({'success': True, 'message': 'Channel added. Restart required.'})
    else:
        return jsonify({'success': False, 'error': 'Failed to save'})


@admin_bp.route('/api/channels/remove', methods=['POST'])
@login_required
def remove_channel():
    """Remove a channel from monitoring"""
    data = request.get_json()
    channel = data.get('channel', '').strip()
    
    channels = load_channels()
    
    if channel not in channels:
        return jsonify({'success': False, 'error': 'Channel not found'})
    
    channels.remove(channel)
    
    if save_channels(channels):
        update_monitored_channels(channels)
        return jsonify({'success': True, 'message': 'Channel removed. Restart required.'})
    else:
        return jsonify({'success': False, 'error': 'Failed to save'})


def update_monitored_channels(channels):
    """Update MONITORED_CHANNELS in userbot"""
    # This updates the runtime list
    # Note: Full restart needed for changes to take effect
    from userbot import userbot
    if userbot:
        userbot.monitored_channels = channels


@admin_bp.route('/api/userbot/status', methods=['GET'])
@login_required
def userbot_status():
    """Get userbot status"""
    from userbot import userbot, userbot_stats
    
    status = {
        'connected': userbot.client.is_connected() if userbot.client else False,
        'channels_active': len(userbot.channel_entities) if hasattr(userbot, 'channel_entities') else 0,
        'stats': userbot_stats
    }
    
    return jsonify({'success': True, 'status': status})
