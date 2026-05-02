from types import SimpleNamespace

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.admin_management.models import AdminRole, Menu
from apps.admin_management.permissions import IsGameAdmin, RBACPermission
from apps.diet.models.mysql.gamification import ChallengeTask, Remedy
from apps.diet.models.mysql.journal import WaterIntake
from apps.users.models import Profile, UserFollow


User = get_user_model()


class AdminManagementTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def create_staff_user_with_perm(self, username, permission_code):
        return self.create_staff_user_with_perms(username, [permission_code])

    def create_staff_user_with_perms(self, username, permission_codes):
        user = User.objects.create_user(
            username=username,
            password="pass123456",
            is_staff=True,
        )
        Profile.objects.create(user=user, water_goal_ml=2000, water_goal_cups=8)
        role = AdminRole.objects.create(role_name=f"role-{username}", role_key=f"role_{username}")
        role.users.add(user)
        for permission_code in permission_codes:
            menu = Menu.objects.create(
                name=f"menu-{permission_code}",
                icon="Shield",
                path=f"/{permission_code}/",
                component="demo/component",
                permission_code=permission_code,
            )
            role.menus.add(menu)
        return user

    def test_admin_login_returns_access_token_alias(self):
        User.objects.create_user(username="staff-login", password="pass123456", is_staff=True)

        response = self.client.post(
            "/api/admin/v1/auth/login/",
            {"username": "staff-login", "password": "pass123456"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()["data"]
        self.assertIn("token", payload)
        self.assertIn("access_token", payload)
        self.assertEqual(payload["token"], payload["access_token"])

    def test_journal_stats_api_view_accepts_method_based_rbac(self):
        admin = self.create_staff_user_with_perm("health-admin", "health:manage")
        self.client.force_authenticate(admin)
        WaterIntake.objects.create(user=admin, date=timezone.now().date(), total_ml=2250, manual_ml=2250, food_ml=0)

        response = self.client.get("/api/admin/v1/business/stats/journal/")

        self.assertEqual(response.status_code, 200)
        water_stats = response.json()["data"]["water_stats"]
        self.assertEqual(water_stats["total_ml_drank"], 2250)
        self.assertEqual(water_stats["total_cups_drank"], 9.0)

    def test_social_follow_anomaly_returns_frontend_friendly_fields(self):
        admin = self.create_staff_user_with_perm("social-admin", "social:monitor")
        target = User.objects.create_user(username="target-user", password="pass123456")
        follower = User.objects.create_user(username="follower-user", password="pass123456")
        Profile.objects.create(user=target)
        Profile.objects.create(user=follower)
        UserFollow.objects.create(follower=follower, followed=target)
        self.client.force_authenticate(admin)

        response = self.client.get("/api/admin/v1/social/follows/anomaly/")

        self.assertEqual(response.status_code, 200)
        row = response.json()["data"][0]
        self.assertEqual(row["user_id"], target.id)
        self.assertEqual(row["username"], target.username)
        self.assertIn("recent_followers_gained", row)
        self.assertIn("risk_level", row)
        self.assertIn("detected_at", row)

    def test_game_challenge_list_supports_search_and_task_type_filter(self):
        admin = self.create_staff_user_with_perm("game-admin", "game:manage")
        self.client.force_authenticate(admin)
        ChallengeTask.objects.create(
            title="Daily Run",
            desc="Daily cardio task",
            task_type="daily",
            reward_points=10,
            condition_code="workout",
            is_active=True,
        )
        ChallengeTask.objects.create(
            title="Weekly Yoga",
            desc="Weekly yoga task",
            task_type="weekly",
            reward_points=20,
            condition_code="stretch",
            is_active=True,
        )

        response = self.client.get("/api/admin/v1/game/challenges/?search=Daily&task_type=daily")

        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["title"], "Daily Run")
        self.assertEqual(data[0]["description"], "Daily cardio task")

    def test_game_challenge_create_accepts_frontend_description_field(self):
        admin = self.create_staff_user_with_perm("game-admin-create", "game:manage")
        self.client.force_authenticate(admin)

        response = self.client.post(
            "/api/admin/v1/game/challenges/",
            {
                "title": "Hydrate Today",
                "task_type": "daily",
                "reward_points": 15,
                "condition_code": "drink_water",
                "description": "Drink enough water today",
                "is_active": True,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()["data"]
        self.assertEqual(payload["description"], "Drink enough water today")
        self.assertEqual(ChallengeTask.objects.get(title="Hydrate Today").desc, "Drink enough water today")

    def test_game_remedy_create_accepts_frontend_fields(self):
        admin = self.create_staff_user_with_perm("game-remedy-admin", "game:manage")
        self.client.force_authenticate(admin)

        response = self.client.post(
            "/api/admin/v1/game/remedies/",
            {
                "scenario": "low_water",
                "title": "补水提醒",
                "description": "先补 500ml 温水并暂停含糖饮料",
                "points_cost": 12,
                "order": 1,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()["data"]
        self.assertEqual(payload["scenario"], "low_water")
        self.assertEqual(payload["description"], "先补 500ml 温水并暂停含糖饮料")
        self.assertEqual(payload["points_cost"], 12)
        remedy = Remedy.objects.get(title="补水提醒")
        self.assertEqual(remedy.desc, "先补 500ml 温水并暂停含糖饮料")
        self.assertEqual(remedy.points_cost, 12)

    def test_role_api_accepts_frontend_name_and_description_fields(self):
        admin = self.create_staff_user_with_perms("role-admin", ["system:role:add", "system:role:list"])
        self.client.force_authenticate(admin)

        create_response = self.client.post(
            "/api/admin/v1/system/roles/",
            {"name": "内容审核员", "description": "content_reviewer", "menus": []},
            format="json",
        )

        self.assertEqual(create_response.status_code, 201)
        payload = create_response.json()["data"]
        self.assertEqual(payload["name"], "内容审核员")
        self.assertEqual(payload["description"], "content_reviewer")

        list_response = self.client.get("/api/admin/v1/system/roles/")
        self.assertEqual(list_response.status_code, 200)
        self.assertTrue(any(item["name"] == "内容审核员" for item in list_response.json()["data"]))

    def test_notification_api_maps_public_type_for_frontend(self):
        admin = self.create_staff_user_with_perms("notify-admin", ["system:notify:add", "system:notify:list"])
        self.client.force_authenticate(admin)

        create_response = self.client.post(
            "/api/admin/v1/system/notifications/",
            {"title": "系统公告", "content": "维护通知", "type": "public"},
            format="json",
        )

        self.assertEqual(create_response.status_code, 201)
        self.assertEqual(create_response.json()["data"]["type"], "public")

        list_response = self.client.get("/api/admin/v1/system/notifications/")
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(list_response.json()["data"][0]["type"], "public")

    def test_restaurant_create_accepts_avg_price_without_location(self):
        admin = self.create_staff_user_with_perm("restaurant-admin", "business:restaurant:add")
        self.client.force_authenticate(admin)

        response = self.client.post(
            "/api/admin/v1/business/restaurants/",
            {"name": "轻食餐厅", "address": "上海", "avg_price": 42},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()["data"]
        self.assertEqual(payload["avg_price"], 42.0)
        self.assertEqual(payload["location"], [0.0, 0.0])

    def test_audit_log_serializer_exposes_request_path_alias(self):
        admin = self.create_staff_user_with_perm("log-admin", "system:log:list")
        self.client.force_authenticate(admin)
        self.client.post(
            "/api/admin/v1/auth/login/",
            {"username": "no-user", "password": "no-pass"},
            format="json",
        )

        response = self.client.get("/api/admin/v1/system/logs/")

        self.assertEqual(response.status_code, 200)
        if response.json()["data"]:
            self.assertIn("request_path", response.json()["data"][0])

    def test_rbac_denies_unmapped_action_when_perms_map_exists(self):
        admin = self.create_staff_user_with_perm("role-reader", "system:role:list")
        request = SimpleNamespace(user=admin, method="GET")
        view = SimpleNamespace(action="retrieve", perms_map={"list": "system:role:list"})

        allowed = RBACPermission().has_permission(request, view)

        self.assertFalse(allowed)

    def test_game_admin_keeps_module_permission_for_mapped_actions(self):
        admin = self.create_staff_user_with_perm("game-module-admin", "game:manage")
        request = SimpleNamespace(user=admin, method="GET")
        view = SimpleNamespace(action="list", perms_map={"list": "game:challenge:list"})

        allowed = IsGameAdmin().has_permission(request, view)

        self.assertTrue(allowed)
