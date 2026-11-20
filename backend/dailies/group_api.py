"""Groups: a named set of users whose listening is combined into one shared rewind.

Roles: the owner (created the group) can invite people and delete the group; other members can
only view the group and leave it. Invitees must accept before they count as members.
Anyone who isn't a member (or an invitee, for their own invite) gets a 404, as if the group
did not exist."""
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Friendship, Group, GroupMembership
from .rewind import get_group_rewind
from .api import rewind_params

MAX_NAME = 50
MAX_INVITES = 50      # per request


def _friend_ids(user):
    rows = Friendship.objects.filter(status=Friendship.ACCEPTED).filter(
        Q(from_user=user) | Q(to_user=user))
    return {f.to_user_id if f.from_user_id == user.id else f.from_user_id for f in rows}


def _member_count(group):
    return group.memberships.filter(status=GroupMembership.MEMBER).count()


def _my_group(user, group_id):
    """The group, but only if `user` is a full member of it."""
    return Group.objects.filter(
        id=group_id, memberships__user=user, memberships__status=GroupMembership.MEMBER).first()


def _groups_payload(user):
    groups = list(Group.objects.filter(
        memberships__user=user, memberships__status=GroupMembership.MEMBER).select_related("owner"))
    counts = dict(GroupMembership.objects
                  .filter(group__in=groups, status=GroupMembership.MEMBER)
                  .values_list("group_id").annotate(n=Count("id")))
    mine = sorted(({"id": g.id, "name": g.name, "member_count": counts.get(g.id, 0),
                    "is_owner": g.owner_id == user.id} for g in groups),
                  key=lambda g: (g["name"].lower(), g["id"]))
    invites = [{"id": m.id, "group_name": m.group.name,
                "invited_by": m.invited_by.username if m.invited_by else None}
               for m in GroupMembership.objects.filter(user=user, status=GroupMembership.INVITED)
               .select_related("group", "invited_by").order_by("-created_at")]
    return {"groups": mine, "invites": invites}


def _detail_payload(group, user):
    friend_ids = _friend_ids(user)
    rows = list(group.memberships.select_related("user").order_by("user__username"))
    entry = lambda m: {"user_id": m.user_id, "username": m.user.username,
                       "is_owner": m.user_id == group.owner_id,
                       "is_friend": m.user_id in friend_ids}
    members = sorted((entry(m) for m in rows if m.status == GroupMembership.MEMBER),
                     key=lambda e: (not e["is_owner"], e["username"].lower()))
    data = {"id": group.id, "name": group.name, "owner": group.owner.username,
            "is_owner": group.owner_id == user.id, "member_count": len(members),
            "members": members}
    if data["is_owner"]:           # only the owner sees who has been invited but not yet joined
        data["pending"] = sorted((entry(m) for m in rows if m.status == GroupMembership.INVITED),
                                 key=lambda e: e["username"].lower())
    return data


def _resolve_usernames(raw):
    """Usernames -> (users, unknown_names, error). Case-insensitive; duplicates collapsed."""
    if raw is None:
        raw = []
    if not isinstance(raw, list) or not all(isinstance(n, str) for n in raw):
        return None, None, "usernames must be a list of usernames."
    names, seen = [], set()
    for n in raw:
        n = n.strip()
        if n and n.lower() not in seen:
            seen.add(n.lower())
            names.append(n)
    if len(names) > MAX_INVITES:
        return None, None, f"You can invite at most {MAX_INVITES} people at a time."
    users, unknown = [], []
    for n in names:
        u = User.objects.filter(username__iexact=n).first()
        (users if u else unknown).append(u or n)
    return users, unknown, None


def _unknown_error(unknown):
    noun = "user" if len(unknown) == 1 else "users"
    return Response({"error": f"No {noun} named {', '.join(unknown)}."}, status=400)


def _invite(group, inviter, users):
    """Create invitations; returns (invited_usernames, skipped_usernames)."""
    invited, skipped = [], []
    for u in users:
        if u.id == inviter.id:
            continue
        _, created = GroupMembership.objects.get_or_create(
            group=group, user=u, defaults={"status": GroupMembership.INVITED, "invited_by": inviter})
        (invited if created else skipped).append(u.username)     # skipped = already in / invited
    return invited, skipped


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def groups(request):
    if request.method == "GET":
        return Response(_groups_payload(request.user))

    name = str(request.data.get("name", "")).strip()
    if not name:
        return Response({"error": "Give your group a name."}, status=400)
    if len(name) > MAX_NAME:
        return Response({"error": f"Group names can be at most {MAX_NAME} characters."}, status=400)
    users, unknown, error = _resolve_usernames(request.data.get("usernames"))
    if error:
        return Response({"error": error}, status=400)
    if unknown:
        return _unknown_error(unknown)       # nothing is created if any username is wrong

    with transaction.atomic():
        group = Group.objects.create(name=name, owner=request.user)
        # The owner is in straight away; everyone else has to accept.
        GroupMembership.objects.create(group=group, user=request.user,
                                       status=GroupMembership.MEMBER, joined_at=timezone.now())
        _invite(group, request.user, users)
    return Response(_detail_payload(group, request.user), status=201)


@api_view(["GET", "DELETE"])
@permission_classes([IsAuthenticated])
def group_detail(request, group_id):
    group = _my_group(request.user, group_id)
    if group is None:
        return Response({"error": "Group not found."}, status=404)
    if request.method == "DELETE":
        if group.owner_id != request.user.id:
            return Response({"error": "Only the owner can delete this group."}, status=403)
        group.delete()
        return Response(status=204)
    return Response(_detail_payload(group, request.user))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def group_invite(request, group_id):
    group = _my_group(request.user, group_id)
    if group is None:
        return Response({"error": "Group not found."}, status=404)
    if group.owner_id != request.user.id:
        return Response({"error": "Only the owner can invite people."}, status=403)
    users, unknown, error = _resolve_usernames(request.data.get("usernames"))
    if error:
        return Response({"error": error}, status=400)
    if not users and not unknown:
        return Response({"error": "Enter at least one username."}, status=400)
    if unknown:
        return _unknown_error(unknown)
    with transaction.atomic():
        invited, skipped = _invite(group, request.user, users)
    return Response({"invited": invited, "skipped": skipped,
                     "group": _detail_payload(group, request.user)})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def group_leave(request, group_id):
    group = _my_group(request.user, group_id)
    if group is None:
        return Response({"error": "Group not found."}, status=404)
    if group.owner_id == request.user.id:
        return Response({"error": "Owners can't leave their group. Delete it instead."}, status=400)
    group.memberships.filter(user=request.user).delete()
    return Response(status=204)


def _pending_invite(request):
    return GroupMembership.objects.filter(
        id=request.data.get("invite_id"), user=request.user,
        status=GroupMembership.INVITED).first()


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def invite_accept(request):
    m = _pending_invite(request)
    if m is None:
        return Response({"error": "That invitation no longer exists."}, status=404)
    m.status = GroupMembership.MEMBER
    m.joined_at = timezone.now()             # history before this moment never counts for the group
    m.save(update_fields=["status", "joined_at"])
    return Response(_groups_payload(request.user))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def invite_decline(request):
    m = _pending_invite(request)
    if m is None:
        return Response({"error": "That invitation no longer exists."}, status=404)
    m.delete()
    return Response(_groups_payload(request.user))


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def group_rewind(request, group_id):
    group = _my_group(request.user, group_id)
    if group is None:
        return Response({"error": "Group not found."}, status=404)
    tz_name, day, error = rewind_params(request)
    if error:
        return error
    return Response({"connected": True, "group": group.name,
                     "member_count": _member_count(group),
                     **get_group_rewind(group, day, tz_name)})
