from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.conf import settings
from django.utils import timezone
from functools import wraps
import json

from .models import AutoCamServer, AutoCamCommand, CarState
from .permissions import is_broadcast_team

STALE_CAR_SECONDS = 30
COMMAND_RATE_LIMIT_SECONDS = 3
VALID_CAMERA_IDS = set(range(10))
SESSION_LIVE_SECONDS = 60
SESSION_EXPIRE_MINUTES = 5


def require_autocam_token(view_func):
    """Validates the shared secret sent by the AutoCam app."""
    @wraps(view_func)
    def wrapped(request, *args, **kwargs):
        token = getattr(settings, 'AUTOCAM_API_TOKEN', '')
        if token:
            if request.headers.get('X-AutoCam-Token', '') != token:
                return JsonResponse({'error': 'Unauthorized'}, status=401)
        return view_func(request, *args, **kwargs)
    return wrapped


def require_autocam_control(view_func):
    """Login required, then broadcast-team gate."""
    @wraps(view_func)
    @login_required
    def wrapped(request, *args, **kwargs):
        if not is_broadcast_team(request.user):
            return JsonResponse({'error': 'Forbidden'}, status=403)
        return view_func(request, *args, **kwargs)
    return wrapped


def _clean_stale_cars(server):
    stale_threshold = timezone.now() - timezone.timedelta(seconds=STALE_CAR_SECONDS)
    CarState.objects.filter(server=server, updated_at__lt=stale_threshold).delete()


def _expire_dead_sessions():
    """Delete auto-registered sessions that have gone silent for too long."""
    cutoff = timezone.now() - timezone.timedelta(minutes=SESSION_EXPIRE_MINUTES)
    AutoCamServer.objects.filter(is_auto_registered=True, last_seen__lt=cutoff).delete()
    AutoCamServer.objects.filter(is_auto_registered=True, last_seen__isnull=True).delete()


def _live_sessions():
    cutoff = timezone.now() - timezone.timedelta(seconds=SESSION_LIVE_SECONDS)
    return AutoCamServer.objects.filter(is_active=True, last_seen__gte=cutoff)



@login_required
def autocam_control(request, server_id=None):
    if not is_broadcast_team(request.user):
        raise PermissionDenied

    _expire_dead_sessions()

    if server_id is None:
        # Session picker
        sessions = _live_sessions().order_by('-last_seen')
        if sessions.count() == 1:
            return redirect('autocam:control_server', server_id=sessions.first().id)
        return render(request, 'autocam/sessions.html', {'sessions': sessions})

    server = get_object_or_404(AutoCamServer, id=server_id, is_active=True)
    _clean_stale_cars(server)

    cars = CarState.objects.filter(server=server, is_connected=True).order_by('position', 'car_id')
    all_live = _live_sessions().order_by('-last_seen')

    return render(request, 'autocam/control.html', {
        'server': server,
        'sessions': all_live,
        'cars': cars,
    })


@require_autocam_control
@require_http_methods(["POST"])
def focus_car(request, server_id):
    try:
        server = get_object_or_404(AutoCamServer, id=server_id, is_active=True)
        data = json.loads(request.body)
        car_id = data.get('car_id')

        if car_id is None or not isinstance(car_id, int) or car_id < 0 or car_id > 255:
            return JsonResponse({'success': False, 'error': 'Invalid car_id'}, status=400)

        car = CarState.objects.filter(server=server, car_id=car_id, is_connected=True).first()
        if not car:
            return JsonResponse({'success': False, 'error': f'Car {car_id} not found or not connected'}, status=404)

        recent_cutoff = timezone.now() - timezone.timedelta(seconds=COMMAND_RATE_LIMIT_SECONDS)
        if AutoCamCommand.objects.filter(server=server, command='focus_car', is_executed=False, created_at__gte=recent_cutoff).exists():
            return JsonResponse({'success': False, 'error': 'Too many requests, please wait'}, status=429)

        command = AutoCamCommand.objects.create(server=server, command='focus_car', car_id=car_id)
        return JsonResponse({'success': True, 'command_id': command.id, 'car_id': car_id, 'driver_name': car.driver_name, 'override_duration': 30})

    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_autocam_control
@require_http_methods(["POST"])
def set_camera(request, server_id):
    try:
        server = get_object_or_404(AutoCamServer, id=server_id, is_active=True)
        data = json.loads(request.body)
        camera_id = data.get('camera_id')

        if camera_id is None:
            return JsonResponse({'success': False, 'error': 'camera_id is required'}, status=400)
        try:
            camera_id = int(camera_id)
        except (TypeError, ValueError):
            return JsonResponse({'success': False, 'error': 'camera_id must be an integer'}, status=400)
        if camera_id not in VALID_CAMERA_IDS:
            return JsonResponse({'success': False, 'error': 'camera_id must be 0-9'}, status=400)

        recent_cutoff = timezone.now() - timezone.timedelta(seconds=COMMAND_RATE_LIMIT_SECONDS)
        if AutoCamCommand.objects.filter(server=server, command='set_camera', is_executed=False, created_at__gte=recent_cutoff).exists():
            return JsonResponse({'success': False, 'error': 'Too many requests, please wait'}, status=429)

        command = AutoCamCommand.objects.create(server=server, command='set_camera', camera_id=camera_id)
        return JsonResponse({'success': True, 'command_id': command.id, 'camera_id': camera_id, 'override_duration': 30})

    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_autocam_control
@require_http_methods(["POST"])
def clear_override(request, server_id):
    try:
        server = get_object_or_404(AutoCamServer, id=server_id, is_active=True)
        command = AutoCamCommand.objects.create(server=server, command='clear_override')
        return JsonResponse({'success': True, 'command_id': command.id})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_autocam_control
@require_http_methods(["GET"])
def get_cars_json(request, server_id):
    try:
        server = get_object_or_404(AutoCamServer, id=server_id, is_active=True)
        _clean_stale_cars(server)
        cars = CarState.objects.filter(server=server, is_connected=True).order_by('position', 'car_id')
        return JsonResponse({
            'success': True,
            'server_name': server.name,
            'is_live': server.is_live,
            'cars': [{
                'car_id': car.car_id,
                'driver_name': car.driver_name,
                'car_model': car.car_model,
                'position': car.position,
                'lap_count': car.lap_count,
                'last_lap_time': car.last_lap_time,
                'is_in_pits': car.is_in_pits,
            } for car in cars],
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@csrf_exempt
@require_autocam_token
@require_http_methods(["POST"])
def register_session(request):
    """Called by AutoCam on startup. Creates a live session, returns its ID."""
    try:
        _expire_dead_sessions()

        data = json.loads(request.body)
        server_name = str(data.get('server_name') or '').strip()[:200]
        server_ip   = str(data.get('server_ip')   or '').strip()[:100]
        track_name  = str(data.get('track_name')  or '').strip()[:200]
        session_label = str(data.get('session_label') or '').strip()[:50]

        display_name = server_name or track_name or 'AutoCam Session'
        if track_name and server_name and track_name != server_name:
            display_name = f"{server_name} – {track_name}"

        server = AutoCamServer.objects.create(
            name=display_name,
            host=server_ip,
            track_name=track_name,
            session_label=session_label,
            is_active=True,
            is_auto_registered=True,
            last_seen=timezone.now(),
        )

        return JsonResponse({'success': True, 'session_id': server.id})

    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@csrf_exempt
@require_autocam_token
@require_http_methods(["POST"])
def deregister_session(request, server_id):
    """Called by AutoCam on shutdown. Removes the session."""
    try:
        try:
            server = AutoCamServer.objects.get(id=server_id)
            if server.is_auto_registered:
                server.delete()
            else:
                server.is_active = False
                server.save(update_fields=['is_active'])
        except AutoCamServer.DoesNotExist:
            pass
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@csrf_exempt
@require_autocam_token
@require_http_methods(["GET"])
def get_command(request, server_id):
    try:
        server = get_object_or_404(AutoCamServer, id=server_id)
        server.last_seen = timezone.now()
        server.save(update_fields=['last_seen'])

        # Expire stale pending commands
        stale_cutoff = timezone.now() - timezone.timedelta(seconds=10)
        AutoCamCommand.objects.filter(server=server, is_executed=False, created_at__lt=stale_cutoff).update(
            is_executed=True, executed_at=timezone.now()
        )

        command = AutoCamCommand.objects.filter(server=server, is_executed=False).order_by('-created_at').first()
        if command:
            response_data = {
                'has_command': True,
                'id': command.id,
                'command': command.command,
                'car_id': command.car_id,
                'camera_id': command.camera_id,
                'timestamp': command.created_at.timestamp(),
            }
            command.mark_executed()
            return JsonResponse(response_data)

        return JsonResponse({'has_command': False, 'timestamp': timezone.now().timestamp()})

    except Exception as e:
        return JsonResponse({'has_command': False, 'error': str(e)}, status=500)


@csrf_exempt
@require_autocam_token
@require_http_methods(["POST"])
def update_car_state(request, server_id):
    try:
        server = get_object_or_404(AutoCamServer, id=server_id)
        data = json.loads(request.body)
        cars_data = data.get('cars', [])

        if not isinstance(cars_data, list) or len(cars_data) > 100:
            return JsonResponse({'success': False, 'error': 'Invalid cars data'}, status=400)

        for car_data in cars_data:
            car_id = car_data.get('car_id')
            if not isinstance(car_id, int) or car_id < 0 or car_id > 255:
                continue
            CarState.objects.update_or_create(
                server=server,
                car_id=car_id,
                defaults={
                    'driver_name': str(car_data.get('driver_name', ''))[:200],
                    'car_model':   str(car_data.get('car_model', ''))[:200],
                    'is_connected': bool(car_data.get('is_connected', True)),
                    'position':    car_data.get('position'),
                    'lap_count':   int(car_data.get('lap_count', 0)),
                    'last_lap_time': car_data.get('last_lap_time'),
                    'is_in_pits':  bool(car_data.get('is_in_pits', False)),
                }
            )

        valid_ids = [c['car_id'] for c in cars_data if isinstance(c.get('car_id'), int) and 0 <= c['car_id'] <= 255]
        CarState.objects.filter(server=server).exclude(car_id__in=valid_ids).update(is_connected=False)

        return JsonResponse({'success': True, 'cars_updated': len(cars_data)})

    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
