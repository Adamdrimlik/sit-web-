"""
Socket.IO event handlers for Mafia Online
"""

import random
from flask import request, session
from flask_socketio import emit, join_room, leave_room, rooms
from app.models import Room, Player, get_room_by_code, get_player_by_session
from app.utils import log_game_event
from app import socketio, db

def register_socket_events(socketio_instance):
    """Register all Socket.IO events"""

    @socketio_instance.on('connect')
    def handle_connect():
        """Handle client connection"""
        print(f"🔌 Client connected: {request.sid}")
        emit('connected', {'status': 'success'})

    @socketio_instance.on('disconnect')
    def handle_disconnect():
        """Handle client disconnection"""
        print(f"🔌 Client disconnected: {request.sid}")

        # Update player connection status
        # Note: This would need session tracking implementation

    @socketio_instance.on('join_waiting_room')
    def handle_join_waiting_room(data):
        """Join waiting room"""
        session_id = data.get('session_id') or session.get('session_id')
        room_code = data.get('room_code')

        if not session_id or not room_code:
            emit('error', {'message': 'بيانات غير مكتملة'})
            return

        player = get_player_by_session(session_id)
        room = get_room_by_code(room_code)

        if not player or not room or player.room_id != room.id:
            emit('error', {'message': 'غير مصرح'})
            return

        # Join Socket.IO room
        join_room(f'room_{room.id}')

        # Send current room data
        players_data = [p.to_dict() for p in room.players]
        emit('room_joined', {
            'room': room.to_dict(),
            'players': players_data
        })

        # Notify others
        emit('player_joined', {
            'player': player.to_dict(),
            'message': f'{player.username} انضم إلى الغرفة'
        }, room=f'room_{room.id}', skip_sid=request.sid)

        # Log event
        log_game_event(room, 'player_joined', {'username': player.username})

    @socketio_instance.on('leave_room')
    def handle_leave_room(data):
        """Leave room"""
        session_id = data.get('session_id') or session.get('session_id')
        room_code = data.get('room_code')

        player = get_player_by_session(session_id)
        room = get_room_by_code(room_code)

        if player and room:
            leave_room(f'room_{room.id}')

            # If player was host, assign new host or close room
            if player.is_host and len(room.players) > 1:
                new_host = next((p for p in room.players if p.id != player.id), None)
                if new_host:
                    new_host.is_host = True
                    db.session.commit()
                    emit('new_host', {
                        'new_host': new_host.to_dict(),
                        'message': f'{new_host.username} أصبح المضيف الجديد'
                    }, room=f'room_{room.id}')

            # Remove player
            db.session.delete(player)
            db.session.commit()

            # Notify others
            emit('player_left', {
                'player_id': player.id,
                'message': f'{player.username} غادر الغرفة'
            }, room=f'room_{room.id}')

            # Log event
            log_game_event(room, 'player_left', {'username': player.username})

    @socketio_instance.on('toggle_ready')
    def handle_toggle_ready(data):
        """Toggle player ready status"""
        session_id = data.get('session_id') or session.get('session_id')
        room_code = data.get('room_code')
        is_ready = data.get('ready', False)

        player = get_player_by_session(session_id)
        room = get_room_by_code(room_code)

        if not player or not room or player.room_id != room.id:
            emit('error', {'message': 'غير مصرح'})
            return

        player.is_ready = is_ready
        db.session.commit()

        emit('player_ready_changed', {
            'player_id': player.id,
            'is_ready': is_ready,
            'message': f'{player.username} {"جاهز" if is_ready else "غير جاهز"}'
        }, room=f'room_{room.id}')

    @socketio_instance.on('start_game')
    def handle_start_game(data):
        """Start the game"""
        session_id = data.get('session_id') or session.get('session_id')
        room_code = data.get('room_code')

        player = get_player_by_session(session_id)
        room = get_room_by_code(room_code)

        if not player or not room or not player.is_host:
            emit('error', {'message': 'غير مصرح'})
            return

        if room.status != 'waiting':
            emit('error', {'message': 'اللعبة قد بدأت بالفعل'})
            return

        if len(room.players) < room.settings.min_players:
            emit('error', {'message': f'يجب أن يكون هناك على الأقل {room.settings.min_players} لاعبين'})
            return

        try:
            from app.utils import distribute_roles
            from datetime import datetime

            # Distribute roles
            distribute_roles(room.players, room.settings)

            # Update room status
            room.status = 'playing'
            room.game_phase = 'role_reveal'
            room.started_at = datetime.utcnow()

            db.session.commit()

            # Send roles to players privately
            for p in room.players:
                emit('game_started', {
                    'role': p.role,
                    'role_description': p.role_description,
                    'message': 'بدأت اللعبة! تحقق من دورك'
                }, room=f'player_{p.id}')

            # Notify room
            emit('game_started_public', {
                'message': 'بدأت اللعبة! تفقد أدواركم'
            }, room=f'room_{room.id}')

            # Log event
            log_game_event(room, 'game_started', {
                'player_count': len(room.players),
                'host': player.username
            })

        except Exception as e:
            db.session.rollback()
            emit('error', {'message': f'خطأ في بدء اللعبة: {str(e)}'})

    @socketio_instance.on('kick_player')
    def handle_kick_player(data):
        """Kick a player from the waiting room"""
        session_id = data.get('session_id') or session.get('session_id')
        room_code = data.get('room_code')
        target_id = data.get('player_id')

        player = get_player_by_session(session_id)
        room = get_room_by_code(room_code)

        if not player or not room or not player.is_host:
            emit('error', {'message': 'غير مصرح'});
            return

        target_player = Player.query.get(target_id)
        if not target_player or target_player.room_id != room.id:
            emit('error', {'message': 'اللاعب غير موجود في الغرفة'});
            return

        target_name = target_player.username
        db.session.delete(target_player)
        db.session.commit()

        emit('player_kicked', {
            'player_id': target_player.id,
            'player_name': target_name
        }, room=f'room_{room.id}')

        log_game_event(room, 'player_kicked', {
            'target': target_name,
            'by': player.username
        })

    @socketio_instance.on('player_action')
    def handle_player_action(data):
        """Handle player actions during game"""
        session_id = data.get('session_id') or session.get('session_id')
        room_code = data.get('room_code')
        action_type = data.get('action_type')
        action_data = data.get('action_data', {})

        player = get_player_by_session(session_id)
        room = get_room_by_code(room_code)

        if not player or not room or player.room_id != room.id:
            emit('error', {'message': 'غير مصرح'})
            return

        if room.status != 'playing':
            emit('error', {'message': 'اللعبة غير نشطة'})
            return

        # Handle different action types
        if action_type == 'vote':
            handle_vote(player, room, action_data)
        elif action_type == 'mafia_kill':
            handle_mafia_kill(player, room, action_data)
        elif action_type == 'doctor_save':
            handle_doctor_save(player, room, action_data)
        elif action_type == 'police_investigate':
            handle_police_investigate(player, room, action_data)
        elif action_type == 'sheikh_hint':
            handle_sheikh_hint(player, room, action_data)

def handle_vote(player, room, action_data):
    """Handle voting action"""
    target_id = action_data.get('target_id')
    target_player = Player.query.get(target_id)

    if not target_player or target_player.room_id != room.id or not target_player.is_alive:
        emit('error', {'message': 'هدف غير صحيح'})
        return

    # Record vote
    from app.models import Vote
    vote = Vote(
        room_id=room.id,
        voter_id=player.id,
        target_id=target_id,
        round_number=room.current_round,
        phase='day'
    )
    db.session.add(vote)
    db.session.commit()

    emit('vote_cast', {
        'voter': player.username,
        'target': target_player.username,
        'message': f'{player.username} صوت ضد {target_player.username}'
    }, room=f'room_{room.id}')

def handle_mafia_kill(player, room, action_data):
    """Handle mafia kill action"""
    if not player.role or 'mafia' not in player.role.lower():
        emit('error', {'message': 'غير مصرح'})
        return

    if room.game_phase != 'night':
        emit('error', {'message': 'ليس وقت القتل'})
        return

    target_id = action_data.get('target_id')
    target_player = Player.query.get(target_id)

    if not target_player or not target_player.is_alive:
        emit('error', {'message': 'هدف غير صحيح'})
        return

    # Record kill action (would be processed at end of night)
    # For now, just log it
    log_game_event(room, 'mafia_target_selected', {
        'killer': player.username,
        'target': target_player.username
    })

    emit('action_performed', {
        'action_type': 'mafia_kill',
        'message': 'تم اختيار الهدف'
    }, room=f'player_{player.id}')

def handle_doctor_save(player, room, action_data):
    """Handle doctor save action"""
    if player.role != 'doctor':
        emit('error', {'message': 'غير مصرح'})
        return

    target_id = action_data.get('target_id')
    target_player = Player.query.get(target_id)

    if not target_player or target_player.room_id != room.id:
        emit('error', {'message': 'هدف غير صحيح'})
        return

    log_game_event(room, 'doctor_saved', {
        'doctor': player.username,
        'target': target_player.username
    })

    emit('action_performed', {
        'action_type': 'doctor_save',
        'message': 'تم حماية اللاعب'
    }, room=f'player_{player.id}')

def handle_police_investigate(player, room, action_data):
    """Handle police investigation"""
    if player.role != 'police':
        emit('error', {'message': 'غير مصرح'})
        return

    target_id = action_data.get('target_id')
    target_player = Player.query.get(target_id)

    if not target_player or target_player.room_id != room.id:
        emit('error', {'message': 'هدف غير صحيح'})
        return

    # Determine if target is mafia
    is_mafia = target_player.role and 'mafia' in target_player.role.lower()

    log_game_event(room, 'police_investigated', {
        'police': player.username,
        'target': target_player.username,
        'result': 'mafia' if is_mafia else 'citizen'
    })

    emit('investigation_result', {
        'target': target_player.username,
        'is_mafia': is_mafia,
        'message': f'{target_player.username} {"عضو في المافيا" if is_mafia else "مواطن"}'
    }, room=f'player_{player.id}')

def handle_sheikh_hint(player, room, action_data):
    """Handle sheikh hint request"""
    if player.role != 'sheikh':
        emit('error', {'message': 'غير مصرح'})
        return

    # Generate random hint
    hints = [
        "المافيا نشطة الليلة",
        "هناك شخص يحمي شخص آخر",
        "المحقق يبحث عن الحقيقة",
        "اللعبة ستكون مثيرة اليوم"
    ]

    hint = random.choice(hints)

    log_game_event(room, 'sheikh_hint_received', {
        'sheikh': player.username,
        'hint': hint
    })

    emit('sheikh_hint', {
        'hint': hint,
        'message': f'التلميح: {hint}'
    }, room=f'player_{player.id}')
