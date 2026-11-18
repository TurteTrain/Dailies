from datetime import datetime, timezone as dt_tz

from django.contrib.auth.models import User
from django.test import TestCase

from dailies.models import (Artist, Friendship, Group, GroupMembership, Listen, SpotifyUser, Track)


def utc(y, m, d, h=0, mi=0):
    return datetime(y, m, d, h, mi, tzinfo=dt_tz.utc)


class GroupBase(TestCase):
    def setUp(self):
        mk = lambda n: User.objects.create_user(n, password="pw-12345-x")
        self.owner, self.ann, self.ben, self.cy = mk("owner"), mk("Ann"), mk("ben"), mk("cy")
        self.sp = {u.username: SpotifyUser.objects.create(account=u, spotify_id=u.username, refresh_token="x")
                   for u in (self.owner, self.ann, self.ben)}      # cy has no Spotify
        self.client.force_login(self.owner)

    def login(self, user):
        self.client.force_login(user)

    def post(self, url, body=None):
        return self.client.post(url, body or {}, content_type="application/json")

    def create(self, name="Road trip", usernames=()):
        r = self.post("/api/groups", {"name": name, "usernames": list(usernames)})
        return r

    def join(self, group_id, user, when=None):
        """Invite `user` and accept the invitation, optionally pinning joined_at."""
        self.login(self.owner)
        self.post(f"/api/groups/{group_id}/invite", {"usernames": [user.username]})
        m = GroupMembership.objects.get(group_id=group_id, user=user)
        self.login(user)
        self.post("/api/groups/invites/accept", {"invite_id": m.id})
        if when:
            GroupMembership.objects.filter(pk=m.pk).update(joined_at=when)
        self.login(self.owner)


class CreateAndListTests(GroupBase):
    def test_requires_login(self):
        self.client.logout()
        self.assertEqual(self.client.get("/api/groups").status_code, 403)
        self.assertEqual(self.create().status_code, 403)

    def test_group_of_one_is_allowed_and_owner_joins_immediately(self):
        r = self.create("Solo")
        self.assertEqual(r.status_code, 201)
        d = r.json()
        self.assertEqual((d["name"], d["member_count"], d["is_owner"]), ("Solo", 1, True))
        self.assertEqual([m["username"] for m in d["members"]], ["owner"])
        m = GroupMembership.objects.get()
        self.assertEqual(m.status, GroupMembership.MEMBER)
        self.assertIsNotNone(m.joined_at)

    def test_invitees_are_pending_until_they_accept(self):
        d = self.create("Trio", ["ann", "BEN"]).json()
        self.assertEqual(d["member_count"], 1)                       # invitees aren't members yet
        self.assertEqual([p["username"] for p in d["pending"]], ["Ann", "ben"])
        self.login(self.ann)
        data = self.client.get("/api/groups").json()
        self.assertEqual(data["groups"], [])
        self.assertEqual([(i["group_name"], i["invited_by"]) for i in data["invites"]], [("Trio", "owner")])

    def test_accepting_makes_them_a_member_and_counts_them(self):
        gid = self.create("Trio", ["ann", "ben"]).json()["id"]
        self.login(self.ann)
        inv = self.client.get("/api/groups").json()["invites"][0]
        r = self.post("/api/groups/invites/accept", {"invite_id": inv["id"]})
        self.assertEqual(r.status_code, 200)
        g = r.json()["groups"][0]
        self.assertEqual((g["id"], g["member_count"], g["is_owner"]), (gid, 2, False))
        self.assertEqual(r.json()["invites"], [])
        self.assertIsNotNone(GroupMembership.objects.get(group_id=gid, user=self.ann).joined_at)
        self.assertEqual(self.post("/api/groups/invites/accept", {"invite_id": inv["id"]}).status_code, 404)

    def test_declining_removes_the_invite_and_nothing_else(self):
        gid = self.create("Trio", ["ann"]).json()["id"]
        self.login(self.ann)
        inv = self.client.get("/api/groups").json()["invites"][0]
        r = self.post("/api/groups/invites/decline", {"invite_id": inv["id"]})
        self.assertEqual((r.json()["groups"], r.json()["invites"]), ([], []))
        self.assertFalse(GroupMembership.objects.filter(group_id=gid, user=self.ann).exists())
        self.assertTrue(Group.objects.filter(id=gid).exists())

    def test_cannot_answer_someone_elses_invite(self):
        self.create("Trio", ["ann"])
        inv_id = GroupMembership.objects.get(user=self.ann).id
        self.login(self.ben)
        self.assertEqual(self.post("/api/groups/invites/accept", {"invite_id": inv_id}).status_code, 404)
        self.assertEqual(self.post("/api/groups/invites/decline", {"invite_id": inv_id}).status_code, 404)
        self.assertEqual(GroupMembership.objects.get(user=self.ann).status, GroupMembership.INVITED)

    def test_names_need_not_be_unique(self):
        self.create("Same"); self.create("Same")
        self.login(self.ann)
        self.create("Same")
        self.assertEqual(Group.objects.filter(name="Same").count(), 3)

    def test_name_validation(self):
        self.assertEqual(self.create("   ").status_code, 400)
        self.assertEqual(self.create("x" * 51).status_code, 400)
        self.assertEqual(self.create("x" * 50).status_code, 201)
        self.assertEqual(self.create("  Padded  ").json()["name"], "Padded")

    def test_unknown_username_creates_nothing(self):
        r = self.create("Trio", ["ann", "ghost", "phantom"])
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json()["error"], "No users named ghost, phantom.")
        self.assertEqual((Group.objects.count(), GroupMembership.objects.count()), (0, 0))

    def test_duplicates_and_self_in_invite_list_are_ignored(self):
        d = self.create("Trio", ["ANN", "ann", "Ann", "owner"]).json()
        self.assertEqual([p["username"] for p in d["pending"]], ["Ann"])
        self.assertEqual(GroupMembership.objects.filter(user=self.owner).count(), 1)

    def test_bad_usernames_payload(self):
        for bad in ("ann", [1, 2], {"a": 1}):
            r = self.post("/api/groups", {"name": "X", "usernames": bad})
            self.assertEqual(r.status_code, 400)
        self.assertEqual(self.post("/api/groups", {"name": "X", "usernames": [f"u{i}" for i in range(51)]}).status_code, 400)

    def test_list_only_shows_my_groups_sorted_with_counts(self):
        self.create("beta", ["ann"]); self.create("Alpha")
        self.login(self.ann)
        self.create("Ann's own")
        self.login(self.owner)
        names = [(g["name"], g["member_count"], g["is_owner"]) for g in self.client.get("/api/groups").json()["groups"]]
        self.assertEqual(names, [("Alpha", 1, True), ("beta", 1, True)])


class DetailInviteLeaveDeleteTests(GroupBase):
    def setUp(self):
        super().setUp()
        self.gid = self.create("Crew", ["ann"]).json()["id"]
        self.join(self.gid, self.ann)

    def test_members_see_detail_but_outsiders_and_invitees_do_not(self):
        self.login(self.ann)
        d = self.client.get(f"/api/groups/{self.gid}").json()
        self.assertEqual((d["name"], d["owner"], d["member_count"], d["is_owner"]), ("Crew", "owner", 2, False))
        self.assertEqual([m["username"] for m in d["members"]], ["owner", "Ann"])   # owner first
        self.assertNotIn("pending", d)                                              # owner-only
        self.login(self.owner)
        self.post(f"/api/groups/{self.gid}/invite", {"usernames": ["ben"]})
        self.assertEqual(self.client.get(f"/api/groups/{self.gid}").json()["pending"][0]["username"], "ben")
        for outsider in (self.cy, self.ben):                                        # ben is only invited
            self.login(outsider)
            self.assertEqual(self.client.get(f"/api/groups/{self.gid}").status_code, 404)
        self.assertEqual(self.client.get("/api/groups/99999").status_code, 404)

    def test_friends_are_flagged_in_member_lists(self):
        Friendship.objects.create(from_user=self.owner, to_user=self.ann, status=Friendship.ACCEPTED)
        Friendship.objects.create(from_user=self.owner, to_user=self.ben)           # pending: not a friend
        self.post(f"/api/groups/{self.gid}/invite", {"usernames": ["ben"]})
        d = self.client.get(f"/api/groups/{self.gid}").json()
        self.assertEqual({m["username"]: m["is_friend"] for m in d["members"]}, {"owner": False, "Ann": True})
        self.assertFalse(d["pending"][0]["is_friend"])

    def test_owner_can_invite_later_and_skips_people_already_in(self):
        r = self.post(f"/api/groups/{self.gid}/invite", {"usernames": ["ben", "ann", "owner"]})
        self.assertEqual(r.status_code, 200)
        self.assertEqual((r.json()["invited"], r.json()["skipped"]), (["ben"], ["Ann"]))
        self.assertEqual([p["username"] for p in r.json()["group"]["pending"]], ["ben"])
        again = self.post(f"/api/groups/{self.gid}/invite", {"usernames": ["ben"]}).json()
        self.assertEqual((again["invited"], again["skipped"]), ([], ["ben"]))

    def test_invite_errors(self):
        self.assertEqual(self.post(f"/api/groups/{self.gid}/invite", {"usernames": ["ghost"]}).status_code, 400)
        self.assertEqual(self.post(f"/api/groups/{self.gid}/invite", {"usernames": []}).status_code, 400)
        self.assertEqual(GroupMembership.objects.filter(group_id=self.gid).count(), 2)

    def test_only_the_owner_can_invite(self):
        self.login(self.ann)
        self.assertEqual(self.post(f"/api/groups/{self.gid}/invite", {"usernames": ["ben"]}).status_code, 403)
        self.login(self.cy)
        self.assertEqual(self.post(f"/api/groups/{self.gid}/invite", {"usernames": ["ben"]}).status_code, 404)
        self.assertFalse(GroupMembership.objects.filter(user=self.ben).exists())

    def test_member_can_leave_owner_cannot(self):
        self.login(self.ann)
        self.assertEqual(self.post(f"/api/groups/{self.gid}/leave").status_code, 204)
        self.assertEqual(self.client.get("/api/groups").json()["groups"], [])
        self.assertEqual(self.post(f"/api/groups/{self.gid}/leave").status_code, 404)   # no longer a member
        self.login(self.owner)
        self.assertEqual(self.client.get(f"/api/groups/{self.gid}").json()["member_count"], 1)
        r = self.post(f"/api/groups/{self.gid}/leave")
        self.assertEqual(r.status_code, 400)
        self.assertTrue(Group.objects.filter(id=self.gid).exists())

    def test_only_the_owner_can_delete(self):
        self.login(self.ann)
        self.assertEqual(self.client.delete(f"/api/groups/{self.gid}").status_code, 403)
        self.login(self.cy)
        self.assertEqual(self.client.delete(f"/api/groups/{self.gid}").status_code, 404)
        self.assertTrue(Group.objects.filter(id=self.gid).exists())
        self.login(self.owner)
        self.assertEqual(self.client.delete(f"/api/groups/{self.gid}").status_code, 204)
        self.assertEqual((Group.objects.count(), GroupMembership.objects.count()), (0, 0))
        self.login(self.ann)
        self.assertEqual(self.client.get("/api/groups").json()["groups"], [])

    def test_deleting_the_owners_account_deletes_the_group(self):
        self.owner.delete()
        self.assertEqual(Group.objects.count(), 0)

    def test_deleting_a_members_account_drops_only_their_membership(self):
        self.ann.delete()
        self.assertEqual(GroupMembership.objects.filter(group_id=self.gid).count(), 1)


class GroupRewindTests(GroupBase):
    def setUp(self):
        super().setUp()
        art = Artist.objects.create(artist_id="a1", name="Quiet Hours", genres=["lo-fi"])
        art2 = Artist.objects.create(artist_id="a2", name="Loud Noise", genres=["punk"])
        self.calm = Track.objects.create(track_id="t1", name="Late Library", artist="Quiet Hours",
                                         duration_ms=60000, mood="calm", mood_confidence=0.9)
        self.calm.artists.set([art])
        self.angry = Track.objects.create(track_id="t2", name="Shout", artist="Loud Noise",
                                          duration_ms=60000, mood="angry", mood_confidence=0.9)
        self.angry.artists.set([art2])
        self.gid = self.create("Crew").json()["id"]
        # everyone joins on 2026-11-10 (owner's join time is pinned too)
        GroupMembership.objects.filter(group_id=self.gid, user=self.owner).update(joined_at=utc(2026, 11, 10, 9))
        self.join(self.gid, self.ann, utc(2026, 11, 10, 15))
        self.join(self.gid, self.ben, utc(2026, 11, 10, 15))

    def listen(self, who, track, when):
        Listen.objects.create(user=self.sp[who], track=track, played_at=when)

    def rewind(self, day="2026-11-10", tz="UTC"):
        return self.client.get(f"/api/groups/{self.gid}/rewind?date={day}&tz={tz}")

    def test_combines_every_members_listening(self):
        self.listen("owner", self.calm, utc(2026, 11, 10, 10))
        self.listen("Ann", self.calm, utc(2026, 11, 10, 18))
        self.listen("ben", self.angry, utc(2026, 11, 10, 19))
        self.listen("ben", self.calm, utc(2026, 11, 10, 20))
        d = self.rewind().json()
        self.assertEqual((d["connected"], d["group"], d["member_count"], d["total_plays"]), (True, "Crew", 3, 4))
        self.assertEqual([(t["name"], t["plays"]) for t in d["top_tracks"]], [("Late Library", 3), ("Shout", 1)])
        self.assertEqual([(a["name"], a["plays"]) for a in d["top_artists"]], [("Quiet Hours", 3), ("Loud Noise", 1)])
        self.assertEqual([(g["genre"], g["plays"]) for g in d["top_genres"]], [("lo-fi", 3), ("punk", 1)])
        self.assertEqual(d["mood_of_the_day"], "calm")
        self.assertEqual({m["mood"] for m in d["top_moods"]}, {"calm", "angry"})
        self.assertEqual(d["approx_minutes"], 4)

    def test_only_listening_from_the_join_day_onward_counts(self):
        self.listen("Ann", self.calm, utc(2026, 11, 9, 23, 59))     # day before joining: excluded
        self.listen("Ann", self.angry, utc(2026, 11, 10, 1))        # join day, earlier than join time: included
        self.assertEqual(self.rewind("2026-11-09").json()["total_plays"], 0)
        d = self.rewind("2026-11-10").json()
        self.assertEqual([t["name"] for t in d["top_tracks"]], ["Shout"])
        self.listen("Ann", self.calm, utc(2026, 11, 11, 12))
        self.assertEqual(self.rewind("2026-11-11").json()["total_plays"], 1)

    def test_join_day_uses_the_viewers_timezone(self):
        # Ann joined 2026-11-10 15:00 UTC = 2026-11-11 00:00 in Tokyo, so in Tokyo her join day is the 11th
        self.listen("Ann", self.calm, utc(2026, 11, 10, 10))        # Nov 10 19:00 Tokyo: before her Tokyo join day
        self.assertEqual(self.rewind("2026-11-10", "Asia/Tokyo").json()["total_plays"], 0)
        self.assertEqual(self.rewind("2026-11-10", "UTC").json()["total_plays"], 1)

    def test_can_browse_past_days_unlike_friends(self):
        self.listen("owner", self.calm, utc(2026, 11, 12, 10))
        self.listen("owner", self.angry, utc(2026, 11, 13, 10))
        self.assertEqual(self.rewind("2026-11-12").json()["top_tracks"][0]["name"], "Late Library")
        self.assertEqual(self.rewind("2026-11-13").json()["top_tracks"][0]["name"], "Shout")
        self.assertEqual(self.client.get(f"/api/groups/{self.gid}/rewind").status_code, 200)   # default: today

    def test_pending_invitees_do_not_contribute(self):
        self.post(f"/api/groups/{self.gid}/invite", {"usernames": ["cy"]})
        pending = SpotifyUser.objects.create(account=self.cy, spotify_id="cy", refresh_token="x")
        Listen.objects.create(user=pending, track=self.calm, played_at=utc(2026, 11, 12, 10))
        self.assertEqual(self.rewind("2026-11-12").json()["total_plays"], 0)

    def test_leaving_removes_your_listening_from_the_group(self):
        self.listen("Ann", self.calm, utc(2026, 11, 12, 10))
        self.listen("owner", self.angry, utc(2026, 11, 12, 11))
        self.assertEqual(self.rewind("2026-11-12").json()["total_plays"], 2)
        self.login(self.ann)
        self.post(f"/api/groups/{self.gid}/leave")
        self.login(self.owner)
        d = self.rewind("2026-11-12").json()
        self.assertEqual((d["total_plays"], d["member_count"]), (1, 2))

    def test_rejoining_does_not_bring_back_old_history(self):
        self.listen("Ann", self.calm, utc(2026, 11, 12, 10))
        self.login(self.ann)
        self.post(f"/api/groups/{self.gid}/leave")
        self.join(self.gid, self.ann)                                # rejoins "now" (real clock)
        self.assertEqual(self.rewind("2026-11-12").json()["total_plays"], 0)

    def test_members_without_spotify_are_ignored_and_group_of_one_works(self):
        solo = self.create("Solo").json()["id"]
        r = self.client.get(f"/api/groups/{solo}/rewind?date=2026-11-12&tz=UTC").json()
        self.assertEqual((r["total_plays"], r["member_count"], r["top_tracks"]), (0, 1, []))
        self.login(self.cy)                                           # cy has no Spotify at all
        cy_group = self.create("No music").json()["id"]
        self.assertEqual(self.client.get(f"/api/groups/{cy_group}/rewind").json()["total_plays"], 0)

    def test_only_members_can_see_the_rewind(self):
        for outsider in (self.cy,):
            self.login(outsider)
            self.assertEqual(self.rewind().status_code, 404)
        self.login(self.owner)
        self.post(f"/api/groups/{self.gid}/invite", {"usernames": ["cy"]})
        self.login(self.cy)                                           # invited but not joined
        self.assertEqual(self.rewind().status_code, 404)
        self.client.logout()
        self.assertEqual(self.rewind().status_code, 403)

    def test_does_not_expose_individual_members_listening(self):
        self.listen("Ann", self.calm, utc(2026, 11, 10, 18))
        body = self.rewind().content.decode()
        self.assertNotIn("played_at", body)
        self.assertNotIn('"Ann"', body)

    def test_bad_params(self):
        self.assertEqual(self.client.get(f"/api/groups/{self.gid}/rewind?tz=Mars/Base").status_code, 400)
        self.assertEqual(self.client.get(f"/api/groups/{self.gid}/rewind?date=nope").status_code, 400)
