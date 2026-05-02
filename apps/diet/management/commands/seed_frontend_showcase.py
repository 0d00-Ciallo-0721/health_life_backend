import datetime
import random

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone
from mongoengine.errors import MongoEngineException

from apps.diet.models.mongo.community import Comment, CommunityFeed
from apps.diet.models.mongo.recipe import Recipe
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
from apps.users.models import Profile, UserFollow


User = get_user_model()


class Command(BaseCommand):
    help = "Seed frontend showcase data into the test database."

    def add_arguments(self, parser):
        parser.add_argument("--users", type=int, default=20, help="Total showcase users to prepare.")
        parser.add_argument("--days", type=int, default=14, help="Journal days for each target user.")
        parser.add_argument(
            "--include-existing-users",
            action="store_true",
            default=True,
            help="Also seed data for users already in the database.",
        )

    def handle(self, *args, **options):
        user_count = max(options["users"], 1)
        days = max(options["days"], 7)

        users = self._prepare_users(user_count)
        if options["include_existing_users"]:
            users = self._merge_existing_users(users)

        challenges = self._seed_challenges()
        achievements = self._seed_achievements()
        remedies = self._seed_remedies()

        for index, user in enumerate(users):
            self._seed_profile(user, index)
            self._seed_fridge(user, index)
            self._seed_journal(user, index, days)
            self._seed_user_gamification(user, index, challenges, achievements, remedies)

        self._seed_follow_graph(users)
        self._seed_recipe_preferences(users)
        self._seed_community(users)

        self.stdout.write(self.style.SUCCESS("Frontend showcase data seeded."))
        self.stdout.write(
            "users={users}, challenges={challenges}, achievements={achievements}, remedies={remedies}".format(
                users=len(users),
                challenges=ChallengeTask.objects.count(),
                achievements=Achievement.objects.count(),
                remedies=Remedy.objects.count(),
            )
        )

    def _prepare_users(self, count):
        users = []
        for index in range(1, count + 1):
            username = f"showcase_user_{index:02d}"
            user, _ = User.objects.get_or_create(
                username=username,
                defaults={
                    "nickname": f"演示用户{index:02d}",
                    "email": f"{username}@example.com",
                    "openid": f"showcase_openid_{index:02d}",
                },
            )
            user.nickname = user.nickname or f"演示用户{index:02d}"
            user.email = user.email or f"{username}@example.com"
            if not user.openid:
                user.openid = f"showcase_openid_{index:02d}"
            user.set_password("DemoPass123")
            user.save()
            users.append(user)
        return users

    def _merge_existing_users(self, seeded_users):
        user_map = {user.id: user for user in seeded_users}
        for user in User.objects.all().order_by("id"):
            user_map.setdefault(user.id, user)
        return list(user_map.values())

    def _seed_profile(self, user, index):
        goals = ["lose", "maintain", "gain"]
        profile, _ = Profile.objects.get_or_create(user=user)
        profile.gender = 1 if index % 2 == 0 else 2
        profile.height = 162 + index % 18
        profile.weight = 54 + index % 24
        profile.age = 19 + index % 12
        profile.goal_type = goals[index % len(goals)]
        profile.target_weight = round(profile.weight - 2.5, 1) if profile.goal_type == "lose" else profile.weight
        profile.activity_level = 1.2 + (index % 4) * 0.15
        profile.diet_tags = ["高蛋白", "低脂"] if index % 2 == 0 else ["清淡", "高纤维"]
        profile.allergens = ["花生"] if index % 8 == 0 else []
        profile.signature = f"演示账号{index + 1}：坚持记录饮食和运动。"
        profile.water_goal_ml = 1800 + (index % 5) * 150
        profile.water_goal_cups = max(1, round(profile.water_goal_ml / 250))
        profile.save()

        user.nickname = user.nickname or f"演示用户{index + 1:02d}"
        user.avatar = user.avatar or f"https://api.dicebear.com/7.x/thumbs/svg?seed=health-{index + 1}"
        user.save(update_fields=["nickname", "avatar"])

    def _seed_fridge(self, user, user_index):
        today = timezone.now().date()
        items = [
            ("鸡胸肉", "meat", 2, "块"),
            ("西兰花", "vegetable", 300, "g"),
            ("番茄", "vegetable", 4, "个"),
            ("鸡蛋", "protein", 8, "个"),
            ("豆腐", "protein", 2, "盒"),
            ("虾仁", "seafood", 300, "g"),
            ("燕麦", "grain", 500, "g"),
            ("牛奶", "dairy", 2, "L"),
            ("苹果", "fruit", 5, "个"),
            ("生菜", "vegetable", 2, "颗"),
            ("胡萝卜", "vegetable", 5, "根"),
            ("紫薯", "grain", 4, "个"),
            ("三文鱼", "seafood", 2, "块"),
            ("黄瓜", "vegetable", 4, "根"),
            ("糙米", "grain", 1, "kg"),
            ("酸奶", "dairy", 4, "杯"),
            ("玉米", "grain", 4, "根"),
            ("牛油果", "fruit", 2, "个"),
            ("菌菇", "vegetable", 250, "g"),
            ("藜麦", "grain", 400, "g"),
        ]
        for index, (name, category, amount, unit) in enumerate(items):
            item = FridgeItem.objects.filter(user=user, name=name).first()
            if not item:
                item = FridgeItem(user=user, name=name)
            item.category = category
            item.amount = amount
            item.unit = unit
            item.quantity = f"{amount}{unit}"
            item.expiry_date = today + datetime.timedelta(days=1 + (index + user_index) % 9)
            item.is_scrap = index % 7 == 0
            item.save()

    def _seed_journal(self, user, user_index, days):
        today = timezone.now().date()
        DailyIntake.objects.filter(user=user, food_name__startswith="演示-").delete()
        WorkoutRecord.objects.filter(user=user, type__startswith="demo_").delete()

        meals = [
            ("breakfast", "演示-燕麦牛奶水果杯", 310, {"carbohydrates": 45, "protein": 13, "fat": 7}),
            ("lunch", "演示-鸡胸肉西兰花糙米饭", 520, {"carbohydrates": 58, "protein": 39, "fat": 12}),
            ("dinner", "演示-番茄豆腐菌菇汤", 360, {"carbohydrates": 28, "protein": 22, "fat": 10}),
            ("snack", "演示-酸奶苹果坚果", 190, {"carbohydrates": 24, "protein": 8, "fat": 6}),
        ]
        workout_types = ["demo_running", "demo_cycling", "demo_yoga", "demo_strength"]

        for day_offset in range(days):
            record_date = today - datetime.timedelta(days=day_offset)
            for meal_time, food_name, calories, macros in meals:
                record = DailyIntake.objects.create(
                    user=user,
                    meal_time=meal_time,
                    source_type=3,
                    source_id="",
                    food_name=f"{food_name}-{day_offset + 1}",
                    calories=calories + ((day_offset + user_index) % 4) * 18,
                    macros=macros,
                )
                DailyIntake.objects.filter(pk=record.pk).update(record_date=record_date)

            WorkoutRecord.objects.create(
                user=user,
                type=workout_types[(day_offset + user_index) % len(workout_types)],
                duration=20 + (day_offset % 5) * 6,
                calories_burned=140 + ((day_offset + user_index) % 6) * 25,
                date=record_date,
            )

            weight = round(64.5 - day_offset * 0.04 + (user_index % 6) * 0.6, 1)
            WeightRecord.objects.update_or_create(
                user=user,
                date=record_date,
                defaults={"weight": weight, "bmi": round(weight / 1.7 / 1.7, 1)},
            )

            total_ml = 1700 + ((day_offset + user_index) % 5) * 180
            water, _ = WaterIntake.objects.update_or_create(
                user=user,
                date=record_date,
                defaults={"total_ml": total_ml, "manual_ml": total_ml - 250, "food_ml": 250},
            )
            WaterEvent.objects.filter(intake=water, note__startswith="demo").delete()
            for event_index, ml in enumerate([300, 250, 350, 400]):
                WaterEvent.objects.create(
                    intake=water,
                    ml=ml,
                    source="manual",
                    note=f"demo water event {event_index + 1}",
                )

    def _seed_challenges(self):
        definitions = [
            ("log_breakfast", "早餐打卡", "记录一次营养早餐", 10, "daily"),
            ("log_dinner", "晚餐清淡", "记录一次清淡晚餐", 10, "daily"),
            ("workout", "今日运动", "完成一次运动记录", 15, "daily"),
            ("no_sugar", "少糖一天", "一天内避免高糖饮品和甜点", 18, "daily"),
        ]
        for index in range(5, 21):
            definitions.append(
                (
                    f"showcase_task_{index:02d}",
                    f"健康挑战{index:02d}",
                    f"完成第{index:02d}项健康生活任务",
                    8 + index,
                    "weekly" if index % 3 == 0 else "daily",
                )
            )

        tasks = []
        for condition_code, title, desc, reward, task_type in definitions:
            task, _ = ChallengeTask.objects.update_or_create(
                condition_code=condition_code,
                defaults={
                    "title": title,
                    "desc": desc,
                    "reward_points": reward,
                    "task_type": task_type,
                    "is_active": True,
                },
            )
            tasks.append(task)
        return tasks

    def _seed_achievements(self):
        definitions = [
            ("carbon_low_day", "低碳饮食日", "当日饮食碳足迹保持在较低水平", "🌱", "daily", "rare", 20),
            ("carbon_week_saver", "绿色一周", "连续记录一周低碳饮食和运动", "🌍", "weekly", "epic", 60),
            ("carbon_sport_offset", "运动抵消达人", "通过运动形成可感知的碳抵消", "🚴", "special", "rare", 35),
        ]
        for index in range(4, 24):
            definitions.append(
                (
                    f"showcase_ach_{index:02d}",
                    f"健康成就{index:02d}",
                    f"完成第{index:02d}个健康管理里程碑",
                    "🏅",
                    ["daily", "weekly", "monthly", "special"][index % 4],
                    ["common", "rare", "epic"][index % 3],
                    5 + index,
                )
            )

        achievements = []
        for code, title, desc, icon, category, rarity, points in definitions:
            achievement, _ = Achievement.objects.update_or_create(
                code=code,
                defaults={
                    "title": title,
                    "desc": desc,
                    "icon": icon,
                    "category": category,
                    "rarity": rarity,
                    "points": points,
                },
            )
            achievements.append(achievement)
        return achievements

    def _seed_remedies(self):
        scenarios = ["overeat", "stay_up", "miss_workout", "low_water", "constipation", "hangover"]
        remedies = []
        for index in range(1, 25):
            scenario = scenarios[index % len(scenarios)]
            remedy, _ = Remedy.objects.update_or_create(
                scenario=scenario,
                title=f"演示补救方案{index:02d}",
                defaults={
                    "desc": f"针对{scenario}场景的饮食、饮水、运动与作息补救建议，适合比赛演示。",
                    "points_cost": 5 + index,
                    "order": index,
                },
            )
            remedies.append(remedy)
        return remedies

    def _seed_user_gamification(self, user, user_index, challenges, achievements, remedies):
        for index, task in enumerate(challenges):
            status = "completed" if (index + user_index) % 3 == 0 else "pending"
            progress = 100 if status == "completed" else (index + user_index) % 70
            UserChallengeProgress.objects.update_or_create(
                user=user,
                challenge=task,
                defaults={
                    "status": status,
                    "progress": progress,
                    "completed_at": timezone.now() - datetime.timedelta(days=index % 10)
                    if status == "completed"
                    else None,
                },
            )

        unlocked = achievements[: 8 + user_index % 6]
        for achievement in unlocked:
            UserAchievement.objects.get_or_create(user=user, achievement=achievement)

        UserFeaturedBadge.objects.filter(user=user).delete()
        for sort_order, achievement in enumerate(unlocked[:3]):
            UserFeaturedBadge.objects.update_or_create(
                user=user,
                achievement=achievement,
                defaults={"sort_order": sort_order},
            )

        for remedy in remedies[user_index % 5 : user_index % 5 + 6]:
            UserRemedyPlan.objects.get_or_create(user=user, remedy=remedy)
            UserPreference.objects.get_or_create(
                user=user,
                target_id=str(remedy.id),
                target_type="remedy",
                action="like",
            )

    def _seed_follow_graph(self, users):
        if len(users) < 2:
            return
        for index, user in enumerate(users):
            for offset in (1, 2, 3):
                followed = users[(index + offset) % len(users)]
                if followed.id != user.id:
                    UserFollow.objects.get_or_create(follower=user, followed=followed)

    def _seed_recipe_preferences(self, users):
        try:
            recipes = list(Recipe.objects(status=1).limit(50))
        except MongoEngineException as exc:
            self.stdout.write(self.style.WARNING(f"Mongo recipe preferences skipped: {exc}"))
            return
        if not recipes:
            return

        for user_index, user in enumerate(users):
            for recipe in recipes[user_index : user_index + 6]:
                UserPreference.objects.get_or_create(
                    user=user,
                    target_id=str(recipe.id),
                    target_type="recipe",
                    action="like" if user_index % 2 else "save",
                )

    def _seed_community(self, users):
        try:
            CommunityFeed.objects(content__startswith="演示-").delete()
            for index, user in enumerate(users[:30], start=1):
                feed_type = ["post", "meal", "sport"][index % 3]
                sport_info = {}
                if feed_type == "sport":
                    sport_info = {
                        "type": "running",
                        "duration": 30 + index % 20,
                        "calories_burned": 180 + index * 4,
                        "distance_km": round(3.0 + index * 0.15, 1),
                    }
                feed = CommunityFeed(
                    user_id=user.id,
                    content=f"演示-健康动态{index:02d}：今天完成饮食记录、饮水打卡和运动计划。",
                    images=[f"https://picsum.photos/seed/showcase-feed-{index}/600/400"],
                    feed_type=feed_type,
                    target_id="",
                    sport_info=sport_info,
                    likes_count=8 + index,
                    comments_count=2 + index % 5,
                    save_count=index % 4,
                    created_at=timezone.now() - datetime.timedelta(hours=index),
                ).save()
                for comment_index in range(1, 4):
                    Comment(
                        feed_id=feed,
                        user_id=users[(index + comment_index) % len(users)].id,
                        content=f"演示评论{comment_index}：这个健康计划很适合展示。",
                    ).save()
        except MongoEngineException as exc:
            self.stdout.write(self.style.WARNING(f"Mongo community seed skipped: {exc}"))
