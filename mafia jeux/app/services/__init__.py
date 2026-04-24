"""
Game services for Mafia Online
"""

from app.models import Room, Player, GameLog, Vote
from app.utils import check_win_condition, log_game_event
from app import db
from datetime import datetime
import random

class GameService:
    """Service class for game logic"""

    @staticmethod
    def start_game(room):
        """Start the game for a room"""
        if room.status != 'waiting':
            return False, "اللعبة قد بدأت بالفعل"

        if len(room.players) < room.settings.min_players:
            return False, f"يجب أن يكون هناك على الأقل {room.settings.min_players} لاعبين"

        try:
            from app.utils import distribute_roles

            # Distribute roles
            distribute_roles(room.players, room.settings)

            # Update room status
            room.status = 'playing'
            room.game_phase = 'role_reveal'
            room.started_at = datetime.utcnow()
            room.current_round = 1

            db.session.commit()

            # Log game start
            log_game_event(room, 'game_started', {
                'player_count': len(room.players),
                'round': 1
            })

            return True, "بدأت اللعبة بنجاح"

        except Exception as e:
            db.session.rollback()
            return False, str(e)

    @staticmethod
    def end_night_phase(room):
        """Process night phase results"""
        if room.game_phase != 'night':
            return False, "ليس وقت الليل"

        try:
            # Get mafia targets
            mafia_votes = Vote.query.filter_by(
                room_id=room.id,
                round_number=room.current_round,
                phase='night'
            ).all()

            # Calculate most voted target
            from app.utils import calculate_vote_results
            killed_player_id, vote_counts = calculate_vote_results(mafia_votes)

            killed_player = None
            if killed_player_id:
                killed_player = Player.query.get(killed_player_id)

                # Check if doctor saved the player
                doctor_saves = GameLog.query.filter_by(
                    room_id=room.id,
                    event_type='doctor_saved',
                    round_number=room.current_round
                ).all()

                saved = False
                for save_log in doctor_saves:
                    if save_log.event_data.get('target') == killed_player.username:
                        saved = True
                        break

                if not saved:
                    killed_player.is_alive = False
                    log_game_event(room, 'player_killed', {
                        'player': killed_player.username,
                        'round': room.current_round
                    })

            # Move to day phase
            room.game_phase = 'day'
            room.day_number += 1
            db.session.commit()

            return True, {
                'killed_player': killed_player.username if killed_player and not saved else None,
                'saved': saved if killed_player else False
            }

        except Exception as e:
            db.session.rollback()
            return False, str(e)

    @staticmethod
    def end_day_phase(room):
        """Process day phase voting results"""
        if room.game_phase != 'day':
            return False, "ليس وقت النهار"

        try:
            # Get day votes
            day_votes = Vote.query.filter_by(
                room_id=room.id,
                round_number=room.current_round,
                phase='day'
            ).all()

            # Calculate voting results
            from app.utils import calculate_vote_results
            eliminated_player_id, vote_counts = calculate_vote_results(day_votes)

            eliminated_player = None
            if eliminated_player_id:
                eliminated_player = Player.query.get(eliminated_player_id)
                eliminated_player.is_alive = False

                log_game_event(room, 'player_eliminated', {
                    'player': eliminated_player.username,
                    'votes': vote_counts.get(eliminated_player_id, 0),
                    'round': room.current_round
                })

            # Check win condition
            winner = check_win_condition(room)
            if winner:
                room.status = 'finished'
                room.winner_team = winner
                room.finished_at = datetime.utcnow()

                log_game_event(room, 'game_ended', {
                    'winner': winner,
                    'round': room.current_round
                })

            # Move to night phase
            room.game_phase = 'night'
            room.night_number += 1
            room.current_round += 1
            db.session.commit()

            return True, {
                'eliminated_player': eliminated_player.username if eliminated_player else None,
                'vote_counts': vote_counts,
                'game_ended': winner is not None,
                'winner': winner
            }

        except Exception as e:
            db.session.rollback()
            return False, str(e)

    @staticmethod
    def get_game_state(room, player=None):
        """Get current game state for a room"""
        alive_players = room.get_alive_players()
        game_stats = {
            'total_players': len(room.players),
            'alive_players': len(alive_players),
            'dead_players': len(room.players) - len(alive_players),
            'current_round': room.current_round,
            'game_phase': room.game_phase,
            'mafia_count': len([p for p in alive_players if p.get_team() == 'mafia']),
            'citizen_count': len([p for p in alive_players if p.get_team() == 'citizens'])
        }

        if player:
            game_stats['player_role'] = player.role
            game_stats['player_team'] = player.get_team()
            game_stats['is_alive'] = player.is_alive

        return game_stats

class RoomService:
    """Service class for room management"""

    @staticmethod
    def create_room(host_player, room_name=None, settings=None):
        """Create a new room with settings"""
        from app.models import create_room_with_settings

        room = create_room_with_settings(host_player, room_name)

        if settings:
            # Update room settings
            for key, value in settings.items():
                if hasattr(room.settings, key):
                    setattr(room.settings, key, value)
            db.session.commit()

        log_game_event(room, 'room_created', {
            'host': host_player.username,
            'room_name': room_name
        })

        return room

    @staticmethod
    def get_room_info(room_code):
        """Get room information"""
        from app.models import get_room_by_code
        room = get_room_by_code(room_code)

        if not room:
            return None

        return {
            'code': room.code,
            'name': room.name,
            'status': room.status,
            'player_count': len(room.players),
            'max_players': room.settings.max_players if room.settings else 15,
            'host': room.host.username if room.host else None,
            'created_at': room.created_at.isoformat(),
            'settings': room.settings.__dict__ if room.settings else None
        }

class PlayerService:
    """Service class for player management"""

    @staticmethod
    def update_player_stats(player, game_result):
        """Update player statistics after game"""
        player.games_played += 1

        if game_result == player.get_team():
            player.games_won += 1
            if game_result == 'mafia':
                player.mafia_wins += 1
            else:
                player.citizen_wins += 1

        db.session.commit()

    @staticmethod
    def get_player_stats(player):
        """Get player statistics"""
        return {
            'games_played': player.games_played,
            'games_won': player.games_won,
            'win_rate': (player.games_won / player.games_played * 100) if player.games_played > 0 else 0,
            'mafia_wins': player.mafia_wins,
            'citizen_wins': player.citizen_wins
        }
