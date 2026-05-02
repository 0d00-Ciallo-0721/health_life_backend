from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from apps.users.models import Profile, UserFollow


User = get_user_model()


class WeChatLoginTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    @patch("apps.common.utils.WeChatService.get_openid", return_value={"openid": "openid_1", "session_key": "session"})
    def test_wechat_login_returns_access_and_refresh_tokens(self, mocked_get_openid):
        response = self.client.post("/api/v1/users/login/", {"code": "valid-code"}, format="json")

        self.assertEqual(response.status_code, 200)
        payload = response.json()["data"]
        self.assertIn("access_token", payload)
        self.assertIn("refresh_token", payload)
        self.assertEqual(payload["user_id"], User.objects.get(openid="openid_1").id)
        mocked_get_openid.assert_called_once_with("valid-code")


class UserFollowTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.follower = User.objects.create_user(username="follower", password="pass123456")
        self.followed = User.objects.create_user(username="followed", password="pass123456")
        Profile.objects.create(user=self.follower)
        Profile.objects.create(user=self.followed)
        self.client.force_authenticate(self.follower)

    def test_follow_and_unfollow_user(self):
        follow_response = self.client.post(f"/api/v1/users/{self.followed.id}/follow/")
        self.assertEqual(follow_response.status_code, 200)
        self.assertTrue(UserFollow.objects.filter(follower=self.follower, followed=self.followed).exists())

        unfollow_response = self.client.delete(f"/api/v1/users/{self.followed.id}/follow/")
        self.assertEqual(unfollow_response.status_code, 200)
        self.assertFalse(UserFollow.objects.filter(follower=self.follower, followed=self.followed).exists())


class UserAccountDeletionTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="delete-me", password="pass123456")
        self.other = User.objects.create_user(username="keep-me", password="pass123456")
        Profile.objects.create(user=self.user)
        Profile.objects.create(user=self.other)
        UserFollow.objects.create(follower=self.user, followed=self.other)
        UserFollow.objects.create(follower=self.other, followed=self.user)
        self.client.force_authenticate(self.user)

    @patch("apps.diet.models.mongo.community.Comment")
    @patch("apps.diet.models.mongo.community.CommunityFeed")
    def test_delete_current_user_removes_account_and_related_rows(self, mocked_feed, mocked_comment):
        mocked_feed.objects.filter.return_value = []
        user_id = self.user.id

        response = self.client.delete("/api/v1/users/me/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["code"], 200)
        self.assertFalse(User.objects.filter(id=user_id).exists())
        self.assertFalse(Profile.objects.filter(user_id=user_id).exists())
        self.assertFalse(
            UserFollow.objects.filter(follower_id=user_id).exists()
            or UserFollow.objects.filter(followed_id=user_id).exists()
        )
        self.assertTrue(User.objects.filter(id=self.other.id).exists())
        mocked_comment.objects.filter.assert_called_with(user_id=user_id)
