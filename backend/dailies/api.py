from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Count, Q
from django.http import JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie
from django.utils import timezone
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from .models import Friendship, Listen
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

@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def delete_user(request):
    request.user.delete()
    logout(request)
    return Response(status=204)

@api_view(["DELETE"])
@permission_classes([IsAdminUser])
def delete_admin(request):
    target = get_object_or_404(User, id=request.data.get("user_id"))
    if target.is_staff:
        return Response({"error": "cannot delete admin accounts in this way."}, status=403)
    target.delete()
    return Response(status=204)


# ---- Friends ----------------------------------------------------------------------------
# Friendships are mutual and found by username. A request is a pending Friendship row;
# accepting it makes the friendship mutual. One row per pair, whichever way it was sent.

def _pair(a, b):
    """The Friendship row between two users, in either direction (or None)."""
    return Friendship.objects.filter(
        Q(from_user=a, to_user=b) | Q(from_user=b, to_user=a)).first()

def _friends_payload(user):
    rows = Friendship.objects.filter(Q(from_user=user) | Q(to_user=user)).select_related(
        "from_user", "to_user")
    friends, incoming, outgoing = [], [], []
    for f in rows:
        other = f.to_user if f.from_user_id == user.id else f.from_user
        entry = {"id": f.id, "user_id": other.id, "username": other.username}
        if f.status == Friendship.ACCEPTED:
            friends.append(entry)
        elif f.to_user_id == user.id:
            incoming.append(entry)
        else:
            outgoing.append(entry)
    for group in (friends, incoming, outgoing):
        group.sort(key=lambda e: e["username"].lower())
    return {"friends": friends, "incoming": incoming, "outgoing": outgoing}

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def friends(request):
    return Response(_friends_payload(request.user))

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def friend_request(request):
    username = str(request.data.get("username", "")).strip()
    if not username:
        return Response({"error": "Enter a username."}, status=400)
    target = User.objects.filter(username__iexact=username).first()
    if target is None:
        return Response({"error": f"No user named {username}."}, status=404)
    if target.id == request.user.id:
        return Response({"error": "You can't add yourself."}, status=400)

    with transaction.atomic():
        existing = _pair(request.user, target)
        if existing is not None:
            if existing.status == Friendship.ACCEPTED:
                return Response({"error": f"You and {target.username} are already friends."}, status=409)
            if existing.from_user_id == request.user.id:
                return Response({"error": f"You already sent {target.username} a request."}, status=409)
            # They already asked us: sending a request back means yes.
            existing.status = Friendship.ACCEPTED
            existing.save(update_fields=["status"])
            return Response({"status": "accepted", **_friends_payload(request.user)})
        Friendship.objects.create(from_user=request.user, to_user=target)
    return Response({"status": "pending", **_friends_payload(request.user)}, status=201)

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def friend_accept(request):
    # Only the person the request was sent to can accept it, and only while it is pending.
    f = Friendship.objects.filter(id=request.data.get("request_id"), to_user=request.user,
                                  status=Friendship.PENDING).first()
    if f is None:
        return Response({"error": "That friend request no longer exists."}, status=404)
    f.status = Friendship.ACCEPTED
    f.save(update_fields=["status"])
    return Response(_friends_payload(request.user))
