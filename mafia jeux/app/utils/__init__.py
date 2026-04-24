"""
Utility functions for Mafia Online
"""

import string
import random
from datetime import datetime, timedelta
from functools import wraps
from flask import session, redirect, url_for, flash
import json

def generate_room_code(length=8):
    """Generate unique room code"""
    characters = string.ascii_uppercase + string.digits
    return ''.join(random.choice(characters) for _ in range(length))

def validate_username(username):
    """Validate username"""
    if not username or not isinstance(username, str):
        return False, "اسم المستخدم مطلوب"

    username = username.strip()

    if len(username) < 2:
        return False, "اسم المستخدم يجب أن يكون على الأقل حرفين"

    if len(username) > 50:
        return False, "اسم المستخدم طويل جداً"

    # Check for valid characters (Arabic, English, numbers, spaces, hyphens)
    if not all(c.isalnum() or c in ' \u0600-\u06FF-' for c in username):
        return False, "اسم المستخدم يحتوي على أحرف غير مسموحة"

    return True, ""

def validate_room_code(code):
    """Validate room code"""
    if not code or not isinstance(code, str):
        return False, "رمز الغرفة مطلوب"

    code = code.strip().upper()

    if len(code) != 8:
        return False, "رمز الغرفة يجب أن يكون 8 أحرف"

    if not all(c in string.ascii_uppercase + string.digits for c in code):
        return False, "رمز الغرفة يجب أن يحتوي على أحرف وأرقام فقط"

    return True, code

def get_current_player():
    """Get current player from session"""
    from app.models import get_player_by_session
    session_id = session.get('session_id')
    if not session_id:
        return None
    return get_player_by_session(session_id)

def require_player(f):
    """Decorator to require authenticated player"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        player = get_current_player()
        if not player:
            flash('يجب تسجيل الدخول أولاً', 'error')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function

def require_host(f):
    """Decorator to require room host"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        player = get_current_player()
        if not player or not player.is_host:
            flash('غير مصرح لك بهذا الإجراء', 'error')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function

def calculate_vote_results(votes):
    """Calculate voting results"""
    vote_counts = {}
    for vote in votes:
        target_id = vote.target_id
        vote_counts[target_id] = vote_counts.get(target_id, 0) + 1

    if not vote_counts:
        return None, {}

    # Find player(s) with most votes
    max_votes = max(vote_counts.values())
    top_voted = [pid for pid, count in vote_counts.items() if count == max_votes]

    # If tie, return None (no elimination)
    if len(top_voted) > 1:
        return None, vote_counts

    return top_voted[0], vote_counts

def distribute_roles(players, settings):
    """Distribute roles randomly among players"""
    if not players or len(players) < settings.min_players:
        return False

    # Define available roles
    roles = []

    # Mafia roles
    roles.extend(['mafia_boss'] + ['mafia_member'] * (settings.mafia_count - 1))

    # Citizen roles
    roles.extend(['doctor'] * settings.doctor_count)
    roles.extend(['police'] * settings.police_count)
    roles.extend(['sheikh'] * settings.sheikh_count)
    roles.extend(['sniper'] * settings.sniper_count)

    # Fill remaining with citizens
    remaining = len(players) - len(roles)
    roles.extend(['citizen'] * remaining)

    # Shuffle roles
    random.shuffle(roles)

    # Assign roles to players
    for i, player in enumerate(players):
        if i < len(roles):
            player.role = roles[i]
            player.role_description = get_role_description(roles[i])

    return True

def get_role_description(role):
    """Get role description in Arabic"""
    descriptions = {
        'mafia_boss': 'زعيم المافيا - تقود المافيا وتختار الضحية كل ليلة',
        'mafia_member': 'عضو في المافيا - تساعد في قتل المواطنين',
        'doctor': 'الطبيب - تحمي شخصاً واحداً من القتل كل ليلة',
        'police': 'المحقق - تحقق من هوية شخص واحد كل ليلة',
        'sheikh': 'الشيخ - تحصل على معلومات خاصة من النظام',
        'sniper': 'القناص - تملك فرصة قتل واحدة فقط',
        'citizen': 'مواطن عادي - تعتمد على التحليل والتصويت'
    }
    return descriptions.get(role, 'دور غير معروف')

def check_win_condition(room):
    """Check if game has ended and who won"""
    alive_players = room.get_alive_players()
    mafia_players = room.get_mafia_players()
    citizen_players = room.get_citizen_players()

    # Mafia wins if mafia count >= citizens count
    if len([p for p in mafia_players if p.is_alive]) >= len([p for p in citizen_players if p.is_alive]):
        return 'mafia'

    # Citizens win if all mafia are dead
    if not any(p.is_alive for p in mafia_players):
        return 'citizens'

    return None  # Game continues

def format_time_remaining(seconds):
    """Format time remaining in readable format"""
    if seconds <= 0:
        return "انتهى الوقت"

    minutes = seconds // 60
    remaining_seconds = seconds % 60

    if minutes > 0:
        return f"{minutes}:{remaining_seconds:02d}"
    else:
        return f"{remaining_seconds} ثانية"

def log_game_event(room, event_type, event_data=None, round_number=0, phase=None):
    """Log game event"""
    from app.models import GameLog
    log = GameLog(
        room_id=room.id,
        event_type=event_type,
        event_data=event_data,
        round_number=round_number,
        phase=phase
    )
    from app import db
    db.session.add(log)
    db.session.commit()

def get_room_statistics(room):
    """Get room statistics"""
    total_players = len(room.players)
    alive_players = len(room.get_alive_players())
    mafia_count = len([p for p in room.get_mafia_players() if p.is_alive])
    citizen_count = len([p for p in room.get_citizen_players() if p.is_alive])

    return {
        'total_players': total_players,
        'alive_players': alive_players,
        'mafia_count': mafia_count,
        'citizen_count': citizen_count,
        'dead_players': total_players - alive_players
    }
