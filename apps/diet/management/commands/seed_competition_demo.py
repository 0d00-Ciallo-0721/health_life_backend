import datetime
import random

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone
from mongoengine.errors import MongoEngineException

from apps.diet.models.mongo.community import Comment, CommunityFeed
from apps.diet.models.mongo.recipe import Recipe
from apps.diet.models.mongo.restaurant import Restaurant
from apps.diet.models.mysql.gamification import (
    Achievement,
    ChallengeTask,
    Remedy,
    UserAchievement,
    UserChallengeProgress,
    UserFeaturedBadge,
    UserRemedyPlan,
)
from apps.diet.models.mysql.journal import DailyIntake, WaterEvent, WaterIntake, WeightRecord, WorkoutRecord
from apps.diet.models.mysql.pantry import FridgeItem
from apps.diet.models.mysql.preference import UserPreference
from apps.users.models import Profile


User = get_user_model()


class Command(BaseCommand):
    help = "Seed enough contest demo data for frontend, backend admin, recommendation and reports."

    def add_arguments(self, parser):
        parser.add_argument("--users", type=int, default=20)
        parser.add_argument("--recipes", type=int, default=50)
        parser.add_argument("--restaurants", type=int, default=20)

    def handle(self, *args, **options):
        users = self._seed_users(options["users"])
        main_user = users[0]
        self._seed_profile_and_journal(main_user)
        self._seed_gamification(main_user)

        recipes = self._seed_mongo_recipes(options["recipes"])
        restaurants = self._seed_mongo_restaurants(options["restaurants"])
        self._seed_preferences_and_feeds(users, recipes, restaurants)

        self.stdout.write(self.style.SUCCESS("Competition demo data is ready."))
        self.stdout.write(
            f"users={len(users)}, recipes={len(recipes)}, restaurants={len(restaurants)}, main_user={main_user.username}"
        )

    def _seed_users(self, count):
        users = []
        goals = ["lose", "maintain", "gain"]
        for index in range(1, count + 1):
            user, _ = User.objects.get_or_create(
                username=f"demo_user_{index:02d}",
                defaults={
                    "nickname": f"演示用户{index:02d}",
                    "email": f"demo_user_{index:02d}@example.com",
                },
            )
            user.set_password("DemoPass123")
            user.nickname = f"演示用户{index:02d}"
            user.save()
            Profile.objects.update_or_create(
                user=user,
                defaults={
                    "gender": 1 if index % 2 else 2,
                    "height": 165 + index % 15,
                    "weight": 55 + index % 25,
                    "age": 19 + index % 10,
                    "goal_type": goals[index % len(goals)],
                    "activity_level": 1.2 + (index % 4) * 0.15,
                    "diet_tags": ["高蛋白", "低脂"] if index % 2 else ["家常", "清淡"],
                    "allergens": ["花生"] if index % 7 == 0 else [],
                    "water_goal_ml": 1800 + (index % 4) * 200,
                    "water_goal_cups": 8,
                },
            )
            users.append(user)
        return users

    def _seed_profile_and_journal(self, user):
        today = timezone.now().date()
        ingredients = [
            ("西兰花", "vegetable", 300, "g"),
            ("鸡胸肉", "meat", 2, "块"),
            ("番茄", "vegetable", 4, "个"),
            ("鸡蛋", "dairy", 10, "个"),
            ("牛肉", "meat", 500, "g"),
            ("虾仁", "seafood", 300, "g"),
            ("豆腐", "dairy", 2, "盒"),
            ("菠菜", "vegetable", 250, "g"),
            ("胡萝卜", "vegetable", 5, "根"),
            ("燕麦", "grain", 600, "g"),
            ("牛奶", "dairy", 2, "L"),
            ("苹果", "fruit", 6, "个"),
            ("米饭", "grain", 1, "kg"),
            ("洋葱", "vegetable", 3, "个"),
            ("青椒", "vegetable", 5, "个"),
            ("土豆", "vegetable", 5, "个"),
            ("三文鱼", "seafood", 2, "块"),
            ("紫薯", "grain", 6, "个"),
            ("黄瓜", "vegetable", 4, "根"),
            ("生菜", "vegetable", 2, "颗"),
        ]
        FridgeItem.objects.filter(user=user).delete()
        for index, (name, category, amount, unit) in enumerate(ingredients):
            FridgeItem.objects.create(
                user=user,
                name=name,
                category=category,
                amount=amount,
                unit=unit,
                quantity=f"{amount}{unit}",
                expiry_date=today + datetime.timedelta(days=2 + index % 8),
                is_scrap=index % 6 == 0,
            )

        DailyIntake.objects.filter(user=user).delete()
        WorkoutRecord.objects.filter(user=user).delete()
        WeightRecord.objects.filter(user=user).delete()
        WaterIntake.objects.filter(user=user).delete()
        meals = [
            ("breakfast", "燕麦牛奶", 320, {"carbohydrates": 45, "protein": 14, "fat": 8}),
            ("lunch", "鸡胸肉西兰花饭", 520, {"carbohydrates": 58, "protein": 38, "fat": 12}),
            ("dinner", "番茄豆腐汤", 360, {"carbohydrates": 30, "protein": 22, "fat": 10}),
            ("snack", "苹果酸奶", 180, {"carbohydrates": 28, "protein": 7, "fat": 3}),
        ]
        for day_offset in range(14):
            record_date = today - datetime.timedelta(days=day_offset)
            for meal_time, food_name, calories, macros in meals:
                item = DailyIntake.objects.create(
                    user=user,
                    meal_time=meal_time,
                    source_type=3,
                    food_name=f"{food_name}{day_offset + 1}",
                    calories=calories + (day_offset % 3) * 25,
                    macros=macros,
                )
                DailyIntake.objects.filter(pk=item.pk).update(record_date=record_date)
            WorkoutRecord.objects.create(
                user=user,
                type="running" if day_offset % 2 else "cycling",
                duration=25 + day_offset % 5 * 5,
                calories_burned=180 + day_offset % 6 * 20,
                date=record_date,
            )
            WeightRecord.objects.create(user=user, date=record_date, weight=68.0 - day_offset * 0.05, bmi=22.0)
            water = WaterIntake.objects.create(
                user=user,
                date=record_date,
                total_ml=1800 + (day_offset % 4) * 150,
                manual_ml=1600 + (day_offset % 4) * 150,
                food_ml=200,
            )
            WaterEvent.objects.create(intake=water, ml=300, source="manual", note="demo")

    def _seed_gamification(self, user):
        scenarios = ["overeat", "stay_up", "miss_workout", "low_water", "constipation", "hangover"]
        for index in range(1, 21):
            task, _ = ChallengeTask.objects.update_or_create(
                condition_code=f"demo_task_{index:02d}",
                defaults={
                    "title": f"健康挑战{index:02d}",
                    "desc": f"完成第{index:02d}项健康生活挑战",
                    "reward_points": 10 + index,
                    "task_type": "daily" if index % 2 else "weekly",
                    "is_active": True,
                },
            )
            UserChallengeProgress.objects.update_or_create(
                user=user,
                challenge=task,
                defaults={"status": "completed" if index % 3 == 0 else "pending", "progress": index % 5},
            )

            achievement, _ = Achievement.objects.update_or_create(
                code=f"DEMO_ACH_{index:02d}",
                defaults={
                    "title": f"健康成就{index:02d}",
                    "desc": f"达成第{index:02d}项健康目标",
                    "category": "daily" if index % 2 else "special",
                    "rarity": ["common", "rare", "epic"][index % 3],
                    "points": 5 + index,
                },
            )
            UserAchievement.objects.get_or_create(user=user, achievement=achievement)
            if index <= 5:
                UserFeaturedBadge.objects.update_or_create(
                    user=user, achievement=achievement, defaults={"sort_order": index}
                )

            remedy, _ = Remedy.objects.get_or_create(
                scenario=scenarios[index % len(scenarios)],
                title=f"补救方案{index:02d}",
                defaults={
                    "desc": f"针对健康场景的第{index:02d}条补救建议",
                    "points_cost": 5 + index,
                    "order": index,
                },
            )
            UserRemedyPlan.objects.get_or_create(user=user, remedy=remedy)

    def _seed_mongo_recipes(self, count):
        recipes = []
        cuisines = ["川菜", "粤菜", "湘菜", "日式", "西餐", "家常", "减脂", "高蛋白"]
        ingredients = ["鸡胸肉", "西兰花", "番茄", "鸡蛋", "牛肉", "虾仁", "豆腐", "菠菜", "米饭", "燕麦"]
        try:
            for index in range(1, count + 1):
                name = f"演示健康菜谱{index:02d}"
                recipe = Recipe.objects(name=name).first()
                if not recipe:
                    recipe = Recipe(name=name)
                recipe.description = f"适合比赛演示的健康菜谱{index:02d}"
                recipe.recipeIngredient = random.sample(ingredients, 4)
                recipe.ingredients_search = recipe.recipeIngredient
                recipe.recipeInstructions = ["准备食材", "低油烹饪", "装盘享用"]
                recipe.keywords = [cuisines[index % len(cuisines)], "健康", "推荐"]
                recipe.image_url = f"https://picsum.photos/seed/health-recipe-{index}/600/400"
                recipe.calories = 260 + index * 8
                recipe.cooking_time = 10 + index % 25
                recipe.difficulty = ["简单", "中等", "进阶"][index % 3]
                recipe.nutrition = {"carb": 30 + index % 20, "protein": 18 + index % 12, "fat": 8 + index % 8}
                recipe.status = 1
                recipe.save()
                recipes.append(recipe)
        except MongoEngineException as exc:
            self.stdout.write(self.style.WARNING(f"Mongo recipe seed skipped: {exc}"))
        return recipes

    def _seed_mongo_restaurants(self, count):
        restaurants = []
        try:
            for index in range(1, count + 1):
                amap_id = f"demo_restaurant_{index:02d}"
                restaurant = Restaurant.objects(amap_id=amap_id).first()
                if not restaurant:
                    restaurant = Restaurant(amap_id=amap_id)
                restaurant.name = f"健康轻食餐厅{index:02d}"
                restaurant.address = f"大学城健康路{index:02d}号"
                restaurant.location = [121.40 + index * 0.001, 31.20 + index * 0.001]
                restaurant.type = "轻食/健康餐"
                restaurant.rating = round(4.0 + (index % 10) * 0.08, 1)
                restaurant.cost = 20 + index
                restaurant.photos = [f"https://picsum.photos/seed/restaurant-{index}/600/400"]
                restaurant.menu = [
                    {"name": "鸡胸肉能量碗", "price": 28 + index % 5, "calories": 420},
                    {"name": "低脂沙拉", "price": 22 + index % 6, "calories": 330},
                ]
                restaurant.save()
                restaurants.append(restaurant)
        except MongoEngineException as exc:
            self.stdout.write(self.style.WARNING(f"Mongo restaurant seed skipped: {exc}"))
        return restaurants

    def _seed_preferences_and_feeds(self, users, recipes, restaurants):
        if not recipes:
            return
        UserPreference.objects.filter(target_id__in=[str(recipe.id) for recipe in recipes]).delete()
        for user_index, user in enumerate(users):
            for recipe in recipes[user_index : user_index + 5]:
                UserPreference.objects.get_or_create(
                    user=user,
                    target_id=str(recipe.id),
                    target_type="recipe",
                    action="like" if user_index % 2 else "save",
                )
            for recipe in recipes[user_index : user_index + 3]:
                item = DailyIntake.objects.create(
                    user=user,
                    meal_time="lunch",
                    source_type=1,
                    source_id=str(recipe.id),
                    food_name=recipe.name,
                    calories=getattr(recipe, "calories", 350),
                    macros={"carbohydrates": 45, "protein": 25, "fat": 10},
                )
                DailyIntake.objects.filter(pk=item.pk).update(record_date=timezone.now().date())

        try:
            CommunityFeed.objects(content__startswith="比赛演示动态").delete()
            for index, user in enumerate(users[:20], start=1):
                feed = CommunityFeed(
                    user_id=user.id,
                    content=f"比赛演示动态{index:02d}：今天完成健康饮食打卡，推荐菜谱很实用。",
                    images=[f"https://picsum.photos/seed/feed-{index}/600/400"],
                    feed_type="recipe",
                    target_id=str(recipes[index % len(recipes)].id),
                    likes_count=10 + index,
                    comments_count=index % 6,
                    created_at=timezone.now() - datetime.timedelta(hours=index),
                ).save()
                Comment(feed_id=feed, user_id=user.id, content="演示评论：看起来很健康。").save()
        except MongoEngineException as exc:
            self.stdout.write(self.style.WARNING(f"Mongo community seed skipped: {exc}"))
