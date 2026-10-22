import os, secrets
from urllib.parse import urlencode
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import redirect
from . import spotify
from .models import SpotifyUser

REDIRECT_URI = os.environ["SPOTIFY_REDIRECT_URI"]

def login(request):
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
    if request.GET.get("state") != request.session.get("oauth_state"):
        return HttpResponseBadRequest("State mismatch")
    if "code" not in request.GET:
        return HttpResponseBadRequest("Login was denied")
    tokens = spotify.exchange_code(request.GET["code"], REDIRECT_URI)
    me = spotify.get_me(tokens["access_token"])
    SpotifyUser.objects.update_or_create(
        spotify_id=me["id"],
        defaults={"refresh_token": tokens["refresh_token"]},
    )
    return HttpResponse("Connected! Your listening history will start being collected.")
