import os, secrets
from urllib.parse import urlencode

import requests
from django.conf import settings
from django.db import IntegrityError
from django.http import HttpResponseBadRequest
from django.shortcuts import redirect

from . import spotify
from .models import SpotifyUser

REDIRECT_URI = os.environ["SPOTIFY_REDIRECT_URI"]


def login(request):
    # Only app users who are already signed in can connect Spotify
    if not request.user.is_authenticated:
        return redirect(f"{settings.FRONTEND_URL}/")
    request.session["oauth_state"] = secrets.token_urlsafe(16)
    params = {
        "client_id": os.environ["SPOTIFY_CLIENT_ID"],
        "response_type": "code",
        "redirect_uri": REDIRECT_URI,
        "scope": "user-read-recently-played",
        "state": request.session["oauth_state"],
    }
    return redirect("https://accounts.spotify.com/authorize?" + urlencode(params))


def callback(request):
    if not request.user.is_authenticated:
        return redirect(f"{settings.FRONTEND_URL}/")
    if request.GET.get("state") != request.session.get("oauth_state"):
        return HttpResponseBadRequest("State mismatch")
    if "code" not in request.GET:
        return HttpResponseBadRequest("Login was denied")

    try:
        tokens = spotify.exchange_code(request.GET["code"], REDIRECT_URI)
        me = spotify.get_me(tokens["access_token"])
    except requests.HTTPError:
        return HttpResponseBadRequest("Spotify rejected the login. Please try again.")

    try:
        SpotifyUser.objects.update_or_create(
            spotify_id=me["id"],
            defaults={"refresh_token": tokens["refresh_token"], "account": request.user},
        )
    except IntegrityError:
        return HttpResponseBadRequest(
            "This Spotify account or this user is already linked to another account.")

    return redirect(f"{settings.FRONTEND_URL}/dashboard")
