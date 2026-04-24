"""
Main routes for Mafia Online
"""

from flask import Blueprint, render_template, request, session, redirect, url_for, flash, jsonify
from app.utils import get_current_player, require_player, validate_username, validate_room_code
from app.models import Room, Player, create_room_with_settings, get_room_by_code
from app import db
import uuid

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    """Home page"""
    # Initialize session
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
        session.permanent = True

    return render_template('index.html')

@main_bp.route('/create-room', methods=['GET', 'POST'])
def create_room():
    """Create new room"""
    # Initialize session
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())

    if request.method == 'POST':
        data = request.get_json()
        username = data.get('username', '').strip()
        room_name = data.get('room_name', '').strip()

        # Validate username
        is_valid, error_msg = validate_username(username)
        if not is_valid:
            return jsonify({'success': False, 'error': error_msg}), 400

        session_id = session.get('session_id')

        # Check if player already exists
        existing_player = Player.query.filter_by(session_id=session_id).first()
        if existing_player:
            db.session.delete(existing_player)
            db.session.commit()

        try:
            # Create host player
            host_player = Player(
                username=username,
                session_id=session_id,
                is_host=True
            )
            db.session.add(host_player)
            db.session.flush()

            # Create room with settings
            room = create_room_with_settings(host_player, room_name or None)
            host_player.room_id = room.id
            db.session.commit()

            return jsonify({
                'success': True,
                'room_code': room.code,
                'room_id': room.id,
                'message': f'تم إنشاء الغرفة {room.code} بنجاح!'
            })

        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'error': str(e)}), 500

    return render_template('create_room.html')

@main_bp.route('/join-room', methods=['GET', 'POST'])
def join_room():
    """Join existing room"""
    # Initialize session
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())

    if request.method == 'POST':
        data = request.get_json()
        room_code = data.get('room_code', '').strip().upper()
        username = data.get('username', '').strip()

        # Validate inputs
        is_valid_username, username_error = validate_username(username)
        is_valid_code, validated_code = validate_room_code(room_code)

        if not is_valid_username:
            return jsonify({'success': False, 'error': username_error}), 400
        if not is_valid_code:
            return jsonify({'success': False, 'error': validated_code}), 400

        session_id = session.get('session_id')
        room = get_room_by_code(validated_code)

        if not room:
            return jsonify({'success': False, 'error': 'الغرفة غير موجودة'}), 404

        if room.status != 'waiting':
            return jsonify({'success': False, 'error': 'الغرفة قد بدأت اللعب بالفعل'}), 400

        if len(room.players) >= room.settings.max_players:
            return jsonify({'success': False, 'error': 'الغرفة ممتلئة'}), 400

        # Check if player already exists
        existing_player = Player.query.filter_by(session_id=session_id).first()
        if existing_player:
            db.session.delete(existing_player)
            db.session.commit()

        try:
            # Create new player
            player = Player(
                username=username,
                session_id=session_id,
                room_id=room.id,
                is_host=False
            )
            db.session.add(player)
            db.session.commit()

            return jsonify({
                'success': True,
                'room_code': room.code,
                'room_id': room.id,
                'message': f'تم الانضمام إلى الغرفة {room.code} بنجاح!'
            })

        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'error': str(e)}), 500

    return render_template('join_room.html')

@main_bp.route('/room/<room_code>')
@require_player
def waiting_room(room_code):
    """Waiting room"""
    player = get_current_player()
    room = get_room_by_code(room_code)

    if not room or player.room_id != room.id:
        flash('الغرفة غير موجودة أو غير مصرح لك بالدخول', 'error')
        return redirect(url_for('main.index'))

    return render_template('waiting_room.html', room=room, player=player)

@main_bp.route('/game/<room_code>')
@require_player
def game_room(room_code):
    """Game room"""
    player = get_current_player()
    room = get_room_by_code(room_code)

    if not room or player.room_id != room.id:
        flash('الغرفة غير موجودة أو غير مصرح لك بالدخول', 'error')
        return redirect(url_for('main.index'))

    if room.status not in ['playing', 'starting']:
        return redirect(url_for('main.waiting_room', room_code=room_code))

    return render_template('game_room.html', room=room, player=player)

# Error handlers
@main_bp.errorhandler(404)
def not_found(error):
    return 'الصفحة غير موجودة', 404

@main_bp.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return 'حدث خطأ داخلي في الخادم', 500
