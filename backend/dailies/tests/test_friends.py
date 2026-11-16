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
