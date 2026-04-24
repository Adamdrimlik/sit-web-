"""
API routes for Mafia Online
"""

from flask import Blueprint, request, jsonify
from app.utils import get_current_player, require_player, require_host
from app.models import Room, Player, get_room_by_code
from app import db

api_bp = Blueprint('api', __name__)

@api_bp.route('/room/<room_code>')
def get_room_data(room_code):
    """Get room data"""
    player = get_current_player()
    room = get_room_by_code(room_code)

    if not room or not player or player.room_id != room.id:
        return jsonify({'error': 'Unauthorized'}), 403

    return jsonify({
        'room': room.to_dict(),
        'players': [p.to_dict() for p in room.players],
        'settings': room.settings.__dict__ if room.settings else None,
        'current_player': player.to_dict(include_role=(room.status == 'playing'))
    })

@api_bp.route('/room/<room_code>/players')
def get_room_players(room_code):
    """Get room players"""
    player = get_current_player()
    room = get_room_by_code(room_code)

    if not room or not player or player.room_id != room.id:
        return jsonify({'error': 'Unauthorized'}), 403

    players_data = []
    for p in room.players:
        player_data = p.to_dict(include_role=(room.status == 'playing' and p.id == player.id))
        players_data.append(player_data)

    return jsonify({'players': players_data})

@api_bp.route('/room/<room_code>/settings', methods=['GET', 'POST'])
@require_host
def room_settings(room_code):
    """Get or update room settings"""
    player = get_current_player()
    room = get_room_by_code(room_code)

    if not room or room.host_id != player.id:
        return jsonify({'error': 'Unauthorized'}), 403

    if request.method == 'POST':
        data = request.get_json()
        settings = room.settings

        if not settings:
            from app.models import GameSettings
            settings = GameSettings(room_id=room.id)
            db.session.add(settings)

        # Update settings
        for key, value in data.items():
            if hasattr(settings, key):
                setattr(settings, key, value)

        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'تم حفظ الإعدادات',
            'settings': settings.__dict__
        })

    return jsonify({'settings': room.settings.__dict__ if room.settings else None})

@api_bp.route('/room/<room_code>/kick/<int:player_id>', methods=['POST'])
@require_host
def kick_player(room_code, player_id):
    """Kick player from room"""
    player = get_current_player()
    room = get_room_by_code(room_code)
    target_player = Player.query.get(player_id)

    if not room or room.host_id != player.id:
        return jsonify({'error': 'Unauthorized'}), 403

    if not target_player or target_player.room_id != room.id:
        return jsonify({'error': 'Player not found'}), 404

    if target_player.id == player.id:
        return jsonify({'error': 'Cannot kick yourself'}), 400

    try:
        db.session.delete(target_player)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'تم طرد {target_player.username}'
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@api_bp.route('/player/ready', methods=['POST'])
@require_player
def toggle_ready():
    """Toggle player ready status"""
    player = get_current_player()
    data = request.get_json()
    is_ready = data.get('ready', False)

    player.is_ready = is_ready
    db.session.commit()

    return jsonify({
        'success': True,
        'is_ready': player.is_ready
    })

@api_bp.route('/room/<room_code>/start-game', methods=['POST'])
@require_host
def start_game(room_code):
    """Start the game"""
    player = get_current_player()
    room = get_room_by_code(room_code)

    if not room or room.host_id != player.id:
        return jsonify({'error': 'Unauthorized'}), 403

    if room.status != 'waiting':
        return jsonify({'error': 'Game already started'}), 400

    if len(room.players) < room.settings.min_players:
        return jsonify({
            'error': f'يجب أن يكون هناك على الأقل {room.settings.min_players} لاعبين'
        }), 400

    try:
        from app.utils import distribute_roles, log_game_event
        from datetime import datetime

        # Distribute roles
        if not distribute_roles(room.players, room.settings):
            return jsonify({'error': 'فشل في توزيع الأدوار'}), 500

        # Update room status
        room.status = 'starting'
        room.started_at = datetime.utcnow()

        db.session.commit()

        # Log game start
        log_game_event(room, 'game_started', {
            'player_count': len(room.players),
            'host': player.username
        })

        return jsonify({
            'success': True,
            'message': 'بدأت اللعبة!'
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
