from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db.models import Count
from django.http import JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from .models import Listen
from .rewind import get_daily_rewind
from datetime import date
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

def user_payload(u):
    return {"id": u.id, "username": u.username, "is_staff": u.is_staff,
            "spotify_connected": hasattr(u, "spotify")}

@ensure_csrf_cookie
def csrf(request):                       # React calls this once to get the CSRF cookie
    return JsonResponse({"detail": "ok"})

@api_view(["POST"])
@permission_classes([AllowAny])
def register(request):
    username = str(request.data.get("username", "")).strip()
    password = str(request.data.get("password", ""))
    if not username or not password:
        return Response({"error": "Username and password are required."}, status=400)
    if User.objects.filter(username__iexact=username).exists():
        return Response({"error": "That username is taken."}, status=409)
    try:
        validate_password(password)
    except ValidationError as e:
        return Response({"error": " ".join(e.messages)}, status=400)
    user = User.objects.create_user(username=username, password=password)
    login(request, user)
    return Response(user_payload(user), status=201)

@api_view(["POST"])
@permission_classes([AllowAny])
def login_view(request):
    user = authenticate(request, username=request.data.get("username", ""),
                        password=request.data.get("password", ""))
    if user is None:
        return Response({"error": "Invalid username or password."}, status=401)
    login(request, user)
    return Response(user_payload(user))

@api_view(["POST"])
@permission_classes([AllowAny])
def logout_view(request):
    logout(request)
    return Response(status=204)

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me(request):
    return Response(user_payload(request.user))

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def my_listens(request):
    sp = getattr(request.user, "spotify", None)
    if sp is None:
        return Response({"connected": False, "total": 0, "listens": []})
    qs = Listen.objects.filter(user=sp).select_related("track").order_by("-played_at")
    return Response({"connected": True, "total": qs.count(),
                     "listens": [{"played_at": l.played_at, "track": l.track.name,
                                  "artist": l.track.artist} for l in qs[:100]]})

@api_view(["GET"])
@permission_classes([IsAdminUser])       # non-admins get 403
def admin_users(request):
    users = User.objects.annotate(listen_count=Count("spotify__listen")).order_by("id")
    return Response([{**user_payload(u), "listen_count": u.listen_count} for u in users])

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def rewind(request):
    tz_name = request.query_params.get("tz", "UTC")
    try:
        tz = ZoneInfo(tz_name)
    except (ZoneInfoNotFoundError, ValueError):
        return Response({"error": f"Unknown timezone: {tz_name}"}, status=400)
    raw = request.query_params.get("date")
    if raw:
        try:
            day = date.fromisoformat(raw)
        except ValueError:
            return Response({"error": "date must be a real date in YYYY-MM-DD format."}, status=400)
    else:
        day = timezone.now().astimezone(tz).date()
    sp = getattr(request.user, "spotify", None)
    if sp is None:
        return Response({"connected": False})
    return Response({"connected": True, **get_daily_rewind(sp, day, tz_name)})
