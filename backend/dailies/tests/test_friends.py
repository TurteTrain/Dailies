from django.contrib.auth.models import User
from django.db import IntegrityError, transaction
from django.test import TestCase

from dailies.models import Friendship


class FriendsApiTests(TestCase):
    def setUp(self):
        self.alice = User.objects.create_user("alice", password="pw-12345-x")
        self.bob = User.objects.create_user("Bob", password="pw-12345-x")
        self.cara = User.objects.create_user("cara", password="pw-12345-x")

    def as_user(self, user):
        self.client.force_login(user)

    def send(self, username):
        return self.client.post("/api/friends/request", {"username": username},
                                content_type="application/json")

    def accept(self, request_id):
        return self.client.post("/api/friends/accept", {"request_id": request_id},
                                content_type="application/json")

    def test_requires_login(self):
        self.assertEqual(self.client.get("/api/friends").status_code, 403)
        self.assertEqual(self.send("bob").status_code, 403)
        self.assertEqual(self.accept(1).status_code, 403)

    def test_send_request_shows_up_on_both_sides(self):
        self.as_user(self.alice)
        r = self.send("bob")
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.json()["status"], "pending")
        self.assertEqual([e["username"] for e in r.json()["outgoing"]], ["Bob"])
        self.as_user(self.bob)
        data = self.client.get("/api/friends").json()
        self.assertEqual([e["username"] for e in data["incoming"]], ["alice"])
        self.assertEqual(data["friends"], [])

    def test_username_lookup_ignores_case(self):
        self.as_user(self.alice)
        self.assertEqual(self.send("  BOB ").status_code, 201)

    def test_accept_makes_friendship_mutual(self):
        self.as_user(self.alice)
        self.send("bob")
        self.as_user(self.bob)
        rid = self.client.get("/api/friends").json()["incoming"][0]["id"]
        r = self.accept(rid)
        self.assertEqual(r.status_code, 200)
        self.assertEqual([e["username"] for e in r.json()["friends"]], ["alice"])
        self.assertEqual(r.json()["incoming"], [])
        self.as_user(self.alice)
        data = self.client.get("/api/friends").json()
        self.assertEqual([e["username"] for e in data["friends"]], ["Bob"])
        self.assertEqual(data["outgoing"], [])

    def test_only_the_receiver_can_accept(self):
        self.as_user(self.alice)
        self.send("bob")
        rid = Friendship.objects.get().id
        self.assertEqual(self.accept(rid).status_code, 404)      # sender can't accept own request
        self.as_user(self.cara)
        self.assertEqual(self.accept(rid).status_code, 404)      # a third user can't either
        self.assertEqual(Friendship.objects.get().status, Friendship.PENDING)

    def test_cannot_accept_twice(self):
        self.as_user(self.alice)
        self.send("bob")
        rid = Friendship.objects.get().id
        self.as_user(self.bob)
        self.assertEqual(self.accept(rid).status_code, 200)
        self.assertEqual(self.accept(rid).status_code, 404)

    def test_bad_requests(self):
        self.as_user(self.alice)
        self.assertEqual(self.send("").status_code, 400)
        self.assertEqual(self.send("nobody").status_code, 404)
        self.assertEqual(self.send("ALICE").status_code, 400)
        self.assertEqual(Friendship.objects.count(), 0)

    def test_duplicate_request_and_existing_friend(self):
        self.as_user(self.alice)
        self.send("bob")
        self.assertEqual(self.send("bob").status_code, 409)
        self.as_user(self.bob)
        rid = Friendship.objects.get().id
        self.accept(rid)
        self.assertEqual(self.send("alice").status_code, 409)    # already friends, from either side
        self.as_user(self.alice)
        self.assertEqual(self.send("bob").status_code, 409)
        self.assertEqual(Friendship.objects.count(), 1)

    def test_request_back_auto_accepts(self):
        self.as_user(self.alice)
        self.send("bob")
        self.as_user(self.bob)
        r = self.send("alice")                                   # Bob also asks Alice
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["status"], "accepted")
        self.assertEqual(Friendship.objects.count(), 1)
        self.assertEqual(Friendship.objects.get().status, Friendship.ACCEPTED)

    def test_lists_are_sorted_and_private(self):
        self.as_user(self.cara)
        self.send("bob"); self.send("alice")
        self.as_user(self.alice)
        self.assertEqual(self.client.get("/api/friends").json()["incoming"][0]["username"], "cara")
        self.as_user(self.bob)
        self.accept(Friendship.objects.get(to_user=self.bob).id)
        self.as_user(self.alice)
        self.accept(Friendship.objects.get(to_user=self.alice).id)
        self.as_user(self.cara)
        names = [e["username"] for e in self.client.get("/api/friends").json()["friends"]]
        self.assertEqual(names, ["alice", "Bob"])

    def test_response_exposes_only_usernames_and_ids(self):
        self.as_user(self.alice)
        entry = self.send("bob").json()["outgoing"][0]
        self.assertEqual(set(entry), {"id", "user_id", "username"})

    def test_deleting_a_user_removes_their_friendships(self):
        self.as_user(self.alice)
        self.send("bob")
        self.bob.delete()
        self.assertEqual(Friendship.objects.count(), 0)

    def test_db_rejects_duplicate_and_self_rows(self):
        Friendship.objects.create(from_user=self.alice, to_user=self.bob)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Friendship.objects.create(from_user=self.alice, to_user=self.bob)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Friendship.objects.create(from_user=self.alice, to_user=self.alice)


class FriendRewindTests(TestCase):
    def setUp(self):
        from datetime import timedelta
        from django.utils import timezone
        from dailies.models import Artist, Listen, SpotifyUser, Track
        self.me = User.objects.create_user("me", password="pw-12345-x")
        self.pal = User.objects.create_user("pal", password="pw-12345-x")
        self.stranger = User.objects.create_user("stranger", password="pw-12345-x")
        self.asked = User.objects.create_user("asked", password="pw-12345-x")
        Friendship.objects.create(from_user=self.me, to_user=self.pal, status=Friendship.ACCEPTED)
        Friendship.objects.create(from_user=self.asked, to_user=self.me)          # still pending

        artist = Artist.objects.create(artist_id="ar1", name="Quiet Hours", genres=["lo-fi"])
        track = Track.objects.create(track_id="t1", name="Late Library", artist="Quiet Hours",
                                     duration_ms=180000, mood="calm", mood_confidence=0.9)
        track.artists.set([artist])
        old = Track.objects.create(track_id="t0", name="Last Week Song", artist="Quiet Hours",
                                   duration_ms=180000)
        old.artists.set([artist])
        now = timezone.now()
        self.sp = {u.username: SpotifyUser.objects.create(account=u, spotify_id=u.username,
                                                          refresh_token="x")
                   for u in (self.pal, self.stranger, self.asked)}
        Listen.objects.create(user=self.sp["pal"], track=track, played_at=now)
        Listen.objects.create(user=self.sp["pal"], track=old, played_at=now - timedelta(days=3))
        Listen.objects.create(user=self.sp["stranger"], track=track, played_at=now)
        self.client.force_login(self.me)

    def get(self, user, query=""):
        return self.client.get(f"/api/friends/{user.id}/rewind{query}")

    def test_friend_summary_for_today(self):
        r = self.get(self.pal)
        self.assertEqual(r.status_code, 200)
        d = r.json()
        self.assertTrue(d["connected"])
        self.assertEqual(d["username"], "pal")
        self.assertEqual(d["total_plays"], 1)                       # last week's play is not included
        self.assertEqual([t["name"] for t in d["top_tracks"]], ["Late Library"])
        self.assertEqual([a["name"] for a in d["top_artists"]], ["Quiet Hours"])
        self.assertEqual([g["genre"] for g in d["top_genres"]], ["lo-fi"])
        self.assertEqual(d["mood_of_the_day"], "calm")

    def test_works_from_either_side_of_the_friendship(self):
        self.client.force_login(self.pal)
        self.assertEqual(self.get(self.me).status_code, 200)        # me has no Spotify -> connected False
        self.assertFalse(self.get(self.me).json()["connected"])

    def test_non_friends_and_pending_and_unknown_all_get_the_same_404(self):
        bodies = set()
        for target_id in (self.stranger.id, self.asked.id, self.me.id, 999999):
            r = self.client.get(f"/api/friends/{target_id}/rewind")
            self.assertEqual(r.status_code, 404)
            bodies.add(r.content)
        self.assertEqual(len(bodies), 1)

    def test_cannot_choose_a_past_day(self):
        past = (self.get(self.pal, "?date=2020-01-01").json())
        self.assertEqual(past["total_plays"], 1)                    # date parameter is ignored
        self.assertNotEqual(past["date"], "2020-01-01")

    def test_only_aggregated_fields_are_returned(self):
        d = self.get(self.pal).json()
        self.assertEqual(set(d), {"connected", "username", "date", "timezone", "total_plays",
                                  "approx_minutes", "top_tracks", "top_artists", "top_genres",
                                  "mood_of_the_day"})
        self.assertNotIn("played_at", self.get(self.pal).content.decode())
        self.assertEqual(set(d["top_tracks"][0]), {"track_id", "name", "artist", "plays"})

    def test_friend_without_spotify_is_not_connected(self):
        Friendship.objects.create(from_user=self.me, to_user=self.stranger, status=Friendship.ACCEPTED)
        self.sp["stranger"].delete()
        self.assertEqual(self.get(self.stranger).json(), {"connected": False, "username": "stranger"})

    def test_read_only_and_login_required(self):
        self.assertEqual(self.client.post(f"/api/friends/{self.pal.id}/rewind").status_code, 405)
        self.assertEqual(self.client.delete(f"/api/friends/{self.pal.id}/rewind").status_code, 405)
        self.client.logout()
        self.assertEqual(self.get(self.pal).status_code, 403)

    def test_bad_timezone_is_rejected(self):
        self.assertEqual(self.get(self.pal, "?tz=Mars/Base").status_code, 400)
