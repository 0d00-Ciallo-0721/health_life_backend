from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import resolve
from django.utils import timezone
from rest_framework.test import APIClient

from apps.admin_management.models import AuditLog
from apps.diet.domains.community.services import CommunityService
from apps.diet.domains.discovery.recommendation_service import RecommendationService
from apps.diet.domains.discovery.wheel_engine import WheelEngine
from apps.diet.domains.gamification.services import GamificationService
from apps.diet.domains.tools.ai_service import AIService
from apps.diet.models.mysql.gamification import (
    Achievement,
    ChallengeTask,
    Remedy,
    UserChallengeProgress,
    UserFeaturedBadge,
)
from apps.diet.models.mysql.journal import DailyIntake, WaterIntake
from apps.diet.models.mysql.preference import UserPreference
from apps.users.models import Profile


User = get_user_model()


class FakeCommunityFeed:
    def __init__(self, likes_count=0, report_count=0):
        self.likes_count = likes_count
        self.report_count = report_count

    def update(self, **kwargs):
        self.likes_count += kwargs.get("inc__likes_count", 0)
        self.likes_count -= kwargs.get("dec__likes_count", 0)
        self.report_count += kwargs.get("inc__report_count", 0)

    def reload(self):
        return None


class DietFeatureTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="diet-user", password="pass123456")
        Profile.objects.create(user=self.user, water_goal_ml=2000, water_goal_cups=8)
        self.client.force_authenticate(self.user)

    @override_settings(AMAP_WEB_KEY="", ENABLE_LBS_MOCK_FALLBACK=False)
    def test_lbs_returns_empty_list_when_mock_fallback_disabled(self):
        response = self.client.get("/api/v1/diet/shopping-list/stores/?lat=39.9&lng=116.3")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"], [])

    @patch("apps.diet.domains.preferences.services.PreferenceService.get_favorites", side_effect=RuntimeError("boom"))
    def test_favorite_list_returns_500_on_service_error(self, mocked_get_favorites):
        response = self.client.get("/api/v1/diet/favorites/")

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json()["code"], 500)
        mocked_get_favorites.assert_called_once()

    def test_remedy_favorite_persists_with_user_preference(self):
        remedy = Remedy.objects.create(scenario="overeat", title="补救", desc="desc")

        response = self.client.post("/api/v1/diet/remedy/favorite/", {"remedy_id": remedy.id}, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            UserPreference.objects.filter(
                user=self.user,
                target_id=str(remedy.id),
                target_type="remedy",
                action="like",
            ).exists()
        )

    def test_profile_serializer_returns_real_featured_badges(self):
        achievement = Achievement.objects.create(code="A1", title="成就", desc="desc")
        UserFeaturedBadge.objects.create(user=self.user, achievement=achievement, sort_order=0)

        response = self.client.get("/api/v1/users/profile/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["data"]["featured_badges"]), 1)

    def test_diet_profile_returns_frontend_optional_display_fields(self):
        response = self.client.get("/api/v1/diet/profile/")

        self.assertEqual(response.status_code, 200)
        payload = response.json()["data"]
        for field in [
            "follow_count",
            "fans_count",
            "like_count",
            "badges",
            "featured_badges",
            "water_goal_ml",
        ]:
            self.assertIn(field, payload)

    def test_water_stats_use_ml_fields(self):
        admin = User.objects.create_superuser(username="admin", password="pass123456", email="admin@example.com")
        Profile.objects.create(user=admin, water_goal_ml=2000, water_goal_cups=8)
        WaterIntake.objects.create(
            user=self.user,
            date=timezone.now().date(),
            total_ml=2100,
            manual_ml=2100,
            food_ml=0,
        )
        self.client.force_authenticate(admin)

        response = self.client.get("/api/admin/v1/business/stats/journal/")

        self.assertEqual(response.status_code, 200)
        water_stats = response.json()["data"]["water_stats"]
        self.assertEqual(water_stats["completed_users"], 1)
        self.assertEqual(water_stats["total_ml_drank"], 2100)

    def test_carbon_achievements_do_not_return_mock_defaults(self):
        response = self.client.get("/api/v1/diet/carbon/achievements/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"], [])

    def test_carbon_weekly_uses_real_offsets_without_mock_fillers(self):
        response = self.client.get("/api/v1/diet/carbon/footprint/weekly/")

        self.assertEqual(response.status_code, 200)
        payload = response.json()["data"]
        self.assertEqual(payload["total_saved"], 0.0)
        self.assertEqual(len(payload["daily_data"]), 7)
        self.assertTrue(all(item["val"] == 0 for item in payload["daily_data"]))

    def test_diet_log_detail_supports_get_patch_delete_contract(self):
        record = DailyIntake.objects.create(
            user=self.user,
            source_type=3,
            source_id="",
            food_name="旧食物",
            meal_time="lunch",
            calories=100,
            macros={"protein": 1},
        )

        detail_response = self.client.get(f"/api/v1/diet/log/{record.id}/")
        self.assertEqual(detail_response.status_code, 200)
        self.assertEqual(detail_response.json()["data"]["food_name"], "旧食物")

        patch_response = self.client.patch(
            f"/api/v1/diet/log/{record.id}/",
            {"food_name": "新食物", "calories": 180, "meal_time": "dinner"},
            format="json",
        )
        self.assertEqual(patch_response.status_code, 200)
        self.assertEqual(patch_response.json()["data"]["food_name"], "新食物")
        self.assertEqual(patch_response.json()["data"]["calories"], 180)

        delete_response = self.client.delete(f"/api/v1/diet/log/{record.id}/")
        self.assertEqual(delete_response.status_code, 200)
        self.assertFalse(DailyIntake.objects.filter(id=record.id).exists())

    def test_collaborative_scores_exclude_current_user_items(self):
        behavior_map = {
            1: {"recipe_a", "recipe_b"},
            2: {"recipe_a", "recipe_c"},
            3: {"recipe_b", "recipe_d"},
            4: {"recipe_x"},
        }

        scores = RecommendationService._compute_collaborative_scores(1, behavior_map)

        self.assertNotIn("recipe_a", scores)
        self.assertNotIn("recipe_b", scores)
        self.assertGreater(scores["recipe_c"], 0)
        self.assertGreater(scores["recipe_d"], 0)

    @patch("apps.diet.api.v1.discovery.RecommendationService.get_recommendations")
    def test_search_accepts_strategy_and_returns_algorithm_fields(self, mocked_recommend):
        mocked_recommend.return_value = [
            {
                "id": "recipe_1",
                "name": "热门菜谱",
                "match_score": 88,
                "score": 91.5,
                "recommend_type": "hybrid",
                "algorithm_label": "混合推荐",
            }
        ]

        response = self.client.post(
            "/api/v1/diet/search/",
            {"mode": "cook", "strategy": "hybrid", "page_size": 10},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()["data"]["recommendations"][0]
        self.assertEqual(payload["recommend_type"], "hybrid")
        self.assertEqual(payload["algorithm_label"], "混合推荐")
        mocked_recommend.assert_called_once()
        self.assertEqual(mocked_recommend.call_args.kwargs["strategy"], "hybrid")

    def test_wheel_ranked_candidates_keep_recommendation_metadata(self):
        candidates = []
        seen_ids = set()
        pool = [
            {
                "id": "recipe_1",
                "name": "健康餐",
                "calories": 360,
                "image": "img",
                "difficulty": "简单",
                "cooking_time": 12,
                "recommend_type": "content",
                "algorithm_label": "冰箱食材匹配",
                "score": 87,
            }
        ]

        WheelEngine._pick_ranked_candidates(candidates, seen_ids, pool, count=1, reason="健康轻食")

        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["recommend_type"], "content")
        self.assertEqual(candidates[0]["algorithm_label"], "冰箱食材匹配")
        self.assertEqual(candidates[0]["score"], 87)

    @patch("apps.diet.domains.discovery.wheel_engine.PreferenceSelector.get_blocked_ids", return_value=[])
    @patch("apps.diet.domains.discovery.wheel_engine.RecommendationService.get_recommendations")
    def test_wheel_handles_non_numeric_calories_without_crashing(self, mocked_recommend, mocked_blocked):
        mocked_recommend.return_value = [
            {"id": "recipe_1", "name": "未知热量餐", "calories": None},
            {"id": "recipe_2", "name": "异常热量餐", "calories": "not-a-number"},
        ]
        user = SimpleNamespace(profile=SimpleNamespace(daily_kcal_limit=None, allergens=[]))

        candidates = WheelEngine._get_smart_candidates(user, cuisine=None, flavor=None)

        self.assertEqual(len(candidates), 2)
        self.assertEqual(candidates[0]["id"], "recipe_1")

    @patch("apps.diet.domains.community.services.cache")
    @patch("apps.diet.domains.community.services.CommunityFeed")
    def test_community_like_persists_without_redis(self, mocked_feed_model, mocked_cache):
        mocked_cache.client = None
        feed = FakeCommunityFeed()
        mocked_feed_model.objects.get.return_value = feed

        liked = CommunityService.toggle_like(self.user.id, "feed_1", action="like")
        liked_again = CommunityService.toggle_like(self.user.id, "feed_1", action="like")
        unliked = CommunityService.toggle_like(self.user.id, "feed_1", action="unlike")

        self.assertTrue(liked["is_liked"])
        self.assertEqual(liked["likes_count"], 1)
        self.assertEqual(liked_again["likes_count"], 1)
        self.assertFalse(unliked["is_liked"])
        self.assertEqual(unliked["likes_count"], 0)
        self.assertFalse(
            UserPreference.objects.filter(
                user=self.user,
                target_id="feed_1",
                target_type="feed",
                action="like",
            ).exists()
        )

    @patch("apps.diet.domains.community.services.CommunityFeed")
    def test_community_report_writes_real_audit_log_fields(self, mocked_feed_model):
        feed = FakeCommunityFeed()
        mocked_feed_model.objects.get.return_value = feed

        result = CommunityService.report_feed(self.user.id, "feed_2", "spam")

        self.assertEqual(result["status"], "reported")
        self.assertEqual(feed.report_count, 1)
        log = AuditLog.objects.get(operator=self.user, module="community_report")
        self.assertEqual(log.method, "POST")
        self.assertIn("feed_2", log.path)
        self.assertEqual(log.body["reason"], "spam")

    def test_leaderboard_falls_back_to_mysql_when_redis_unavailable(self):
        task = ChallengeTask.objects.create(
            title="Walk",
            desc="Walk today",
            reward_points=12,
            condition_code="workout",
            is_active=True,
        )
        UserChallengeProgress.objects.create(
            user=self.user,
            challenge=task,
            status="completed",
            progress=100,
            completed_at=timezone.now(),
        )

        rows = GamificationService.get_leaderboard()

        self.assertEqual(rows[0]["user_id"], self.user.id)
        self.assertEqual(rows[0]["score"], 12)

    def test_challenge_check_advances_progress_before_completion(self):
        task = ChallengeTask.objects.create(
            title="Hydrate",
            desc="Drink water",
            reward_points=10,
            condition_code="drink_water",
            is_active=True,
        )
        progress = UserChallengeProgress.objects.create(user=self.user, challenge=task, progress=0)

        result = GamificationService.update_progress(self.user, progress.id, action="check")

        progress.refresh_from_db()
        self.assertEqual(result["status"], "pending")
        self.assertEqual(progress.progress, 1)
        self.assertIsNone(progress.completed_at)

    def test_ai_json_parser_extracts_fenced_json_with_required_keys(self):
        raw = 'text before ```json\n{"food_name":"apple","calories":80,"nutrition":{},"description":"ok"}\n``` text after'

        parsed = AIService._parse_json_response(
            raw,
            expected_type=dict,
            required_keys=["food_name", "calories", "nutrition", "description"],
        )

        self.assertEqual(parsed["food_name"], "apple")

    def test_recommendation_filters_merge_user_blocks_and_allergens(self):
        self.user.profile.allergens = ["peanut"]
        self.user.profile.save(update_fields=["allergens"])
        UserPreference.objects.create(
            user=self.user,
            target_id="recipe_blocked",
            target_type="recipe",
            action="block",
        )

        filters = RecommendationService._prepare_filters(
            self.user,
            {"exclude_ids": ["recipe_existing"], "allergens": ["milk"]},
        )

        self.assertIn("recipe_existing", filters["exclude_ids"])
        self.assertIn("recipe_blocked", filters["exclude_ids"])
        self.assertIn("milk", filters["allergens"])
        self.assertIn("peanut", filters["allergens"])

    def test_recommendation_ignores_invalid_calorie_filters(self):
        query = RecommendationService._recipe_filter_query(
            {"calorie_min": "bad-min", "calorie_max": object()}
        )

        self.assertIsNotNone(query)

    def test_recommendation_returns_demo_items_when_recipe_store_empty(self):
        with patch.object(RecommendationService, "_fallback_recipes", return_value=[]):
            items = RecommendationService.get_recommendations(
                self.user,
                strategy="popular",
                page=1,
                page_size=2,
                filters={},
            )

        self.assertGreater(len(items), 0)
        self.assertTrue(items[0]["id"].startswith("demo_recipe_"))
        self.assertIn("recommend_type", items[0])
        self.assertIn("algorithm_label", items[0])
        self.assertIn("match_reason", items[0])

    def test_legacy_frontend_alias_routes_resolve(self):
        self.assertEqual(resolve("/api/v1/user/login/").url_name, "wechat_login")
        self.assertEqual(resolve("/api/v1/recipe/demo-id/").url_name, "legacy_recipe_detail")
        self.assertEqual(resolve("/api/v1/restaurant/demo-id/").url_name, "legacy_restaurant_detail")
