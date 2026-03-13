import datetime
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone

# 导入 MySQL 模型
from apps.users.models import Profile
from apps.diet.models.mysql.pantry import FridgeItem
from apps.diet.models.mysql.journal import DailyIntake
from apps.diet.models.mysql.gamification import ChallengeTask, UserChallengeProgress, Achievement, UserAchievement

# 导入 MongoDB 模型
from apps.diet.models.mongo.recipe import Recipe
from apps.diet.models.mongo.restaurant import Restaurant
from apps.diet.models.mongo.community import CommunityFeed

User = get_user_model()

class Command(BaseCommand):
    help = '将前端所需的测试 Mock 数据安全导入到指定的测试账号下，并自动适配双库架构'

    def handle(self, *args, **options):
        # 自动抓取数据库中最新注册的一个普通用户（排除掉后台管理员）
        user = User.objects.filter(is_superuser=False).last()
        
        if not user:
            self.stdout.write(self.style.ERROR("❌ 数据库中没有任何小程序用户！请先在微信开发者工具中点击一次【登录】按钮！"))
            return
            
        username = user.username

        self.stdout.write(self.style.WARNING(f"🚀 找到测试用户: {username}，开始疯狂灌入数据..."))
        
        today = timezone.now().date()

        # ==========================================
        # 1. MySQL: 补全个人饮食档案
        # ==========================================
        Profile.objects.update_or_create(
            user=user,
            defaults={
                'gender': 1, 
                'height': 175.0,
                'weight': 70.0,
                'target_weight': 65.0,
                'goal_type': 'lose',           # ✅ 修正：使用正确的枚举值 'lose' (减脂)
                'activity_level': 1.55,        # ✅ 修正：使用中等活动量的标准浮点数 1.55
            }
        )
        self.stdout.write(self.style.SUCCESS("✅ [MySQL] 个人档案 (Profile) 写入成功"))

        # ==========================================
        # 2. MySQL: 填充冰箱食材
        FridgeItem.objects.filter(user=user).delete() # 先清空旧的测试数据
        
        # 👇 这里的 amount_unit 已经改为了 unit，expire_date 改为了 expiry_date
        FridgeItem.objects.create(user=user, name='西兰花', category='vegetable', amount=300, unit='g', expiry_date=today + datetime.timedelta(days=7))
        FridgeItem.objects.create(user=user, name='鸡胸肉', category='meat', amount=2, unit='块', expiry_date=today + datetime.timedelta(days=5))
        
        self.stdout.write(self.style.SUCCESS("✅ [MySQL] 冰箱食材 (FridgeItem) 写入成功"))
        # 3. MySQL: 生成一条今天的饮食记录
        # ==========================================
        DailyIntake.objects.filter(user=user, record_date=today).delete()
        DailyIntake.objects.create(
            user=user,
            record_date=today,
            meal_time='breakfast',
            source_type=3,  # 3表示自定义录入
            food_name='燕麦牛奶',
            calories=280,
            # 将三大营养素封装进 macros 这个 JSON 字段中
            macros={
                "protein": 12.0,
                "fat": 6.0,
                "carbohydrates": 40.0
            }
        )
        
        # 写入一条运动记录 (注意模型名是 WorkoutRecord，字段名是 date, type, calories_burned)
        try:
            from apps.diet.models.mysql.journal import WorkoutRecord
            WorkoutRecord.objects.filter(user=user, date=today).delete()
            WorkoutRecord.objects.create(
                user=user, 
                date=today, 
                type='running', 
                duration=30, 
                calories_burned=260
            )
            self.stdout.write(self.style.SUCCESS("✅ [MySQL] 饮食/运动记录 (Journal) 写入成功"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"⚠️ 运动记录写入失败 (可忽略): {e}"))
        # ==========================================
        # 4. MySQL: 挑战进度与成就获取
        # ==========================================
        task, _ = ChallengeTask.objects.get_or_create(condition_code='log_breakfast', defaults={'title': '连续 7 天记录早餐', 'desc': '养成吃早餐的好习惯', 'reward_points': 50, 'is_active': True})
        UserChallengeProgress.objects.update_or_create(user=user, challenge=task, defaults={'status': 'ongoing', 'progress': 3})

        achieve, _ = Achievement.objects.get_or_create(code='FIRST_LOG', defaults={'title': '初级记录员', 'desc': '完成第一条饮食记录', 'icon': ''})
        UserAchievement.objects.get_or_create(user=user, achievement=achieve)
        self.stdout.write(self.style.SUCCESS("✅ [MySQL] 挑战与成就 (Gamification) 写入成功"))

        # ==========================================
        # 5. MongoDB: 创建精美菜谱 (兼容推荐和大转盘)
        # ==========================================
        recipe = Recipe.objects(name='清炒西兰花鸡胸').first()
        if not recipe:
            recipe = Recipe(
                name='清炒西兰花鸡胸',
                calories=420,
                cooking_time=15,
                difficulty='简单',
                # 我们后端的模型中叫 ingredients_search，所以只保留这个即可
                ingredients_search=['西兰花', '鸡胸肉'],
                keywords=['减脂', '晚餐', '高蛋白'],
                image_url='https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=500&q=80' 
            ).save()
        self.stdout.write(self.style.SUCCESS("✅ [MongoDB] 菜谱数据 (Recipe) 写入成功"))
        # ==========================================
        # 6. MongoDB: 附近轻食餐厅
        # ==========================================
        restaurant = Restaurant.objects(amap_id='mock_shop_001').first()
        if not restaurant:
            restaurant = Restaurant(
                amap_id='mock_shop_001',
                name='轻食之家 (官方测试店)',
                address='XX路 88 号',
                location=[121.470000, 31.230000], # lng, lat
                rating=4.6,
                menu=[{"name": "招牌鸡胸肉沙拉", "price": 28, "calories": 350}]
            ).save()
        self.stdout.write(self.style.SUCCESS("✅ [MongoDB] 餐厅数据 (Restaurant) 写入成功"))

        # ==========================================
        # 7. MongoDB: 发布一条社区动态流
        # ==========================================
        if not CommunityFeed.objects(user_id=user.id, feed_type='post').first():
            CommunityFeed(
                user_id=user.id,
                feed_type='post',
                content='这是我第一天使用 Health Life，用冰箱里的西兰花和鸡胸肉做了一顿减脂餐！坚持打卡！💪',
                likes_count=18,
                comments_count=5,
                created_at=timezone.now()
            ).save()
        self.stdout.write(self.style.SUCCESS("✅ [MongoDB] 社区动态流 (CommunityFeed) 写入成功"))

        # 结束
        self.stdout.write(self.style.WARNING("\n🎉 恭喜！测试数据全部就绪！"))
        self.stdout.write("👉 您现在可以在小程序中打开【我的】、【冰箱】、【首页】、【搜餐】和【社区】页面，所有内容都将丰富起来！")