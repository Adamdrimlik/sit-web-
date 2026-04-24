"""
Game routes for Mafia Online
"""

from flask import Blueprint, render_template
from app.utils import get_current_player, require_player
from app.models import get_room_by_code

game_bp = Blueprint('game', __name__)

@game_bp.route('/<room_code>')
@require_player
def game(room_code):
    """Main game interface"""
    player = get_current_player()
    room = get_room_by_code(room_code)

    if not room or player.room_id != room.id:
        return redirect(url_for('main.index'))

    if room.status not in ['playing', 'starting']:
        return redirect(url_for('main.waiting_room', room_code=room_code))

    return render_template('game/index.html', room=room, player=player)

@game_bp.route('/<room_code>/role')
@require_player
def role_reveal(room_code):
    """Role reveal page"""
    player = get_current_player()
    room = get_room_by_code(room_code)

    if not room or player.room_id != room.id:
        return redirect(url_for('main.index'))

    return render_template('game/role.html', room=room, player=player)

@game_bp.route('/<room_code>/night')
@require_player
def night_phase(room_code):
    """Night phase interface"""
    player = get_current_player()
    room = get_room_by_code(room_code)

    if not room or player.room_id != room.id or room.game_phase != 'night':
        return redirect(url_for('game.game', room_code=room_code))

    return render_template('game/night.html', room=room, player=player)

@game_bp.route('/<room_code>/day')
@require_player
def day_phase(room_code):
    """Day phase interface"""
    player = get_current_player()
    room = get_room_by_code(room_code)

    if not room or player.room_id != room.id or room.game_phase != 'day':
        return redirect(url_for('game.game', room_code=room_code))

    return render_template('game/day.html', room=room, player=player)

@game_bp.route('/<room_code>/voting')
@require_player
def voting_phase(room_code):
    """Voting phase interface"""
    player = get_current_player()
    room = get_room_by_code(room_code)

    if not room or player.room_id != room.id or room.game_phase != 'voting':
        return redirect(url_for('game.game', room_code=room_code))

    return render_template('game/voting.html', room=room, player=player)
