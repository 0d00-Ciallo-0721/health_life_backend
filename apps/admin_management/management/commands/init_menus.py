from django.core.management.base import BaseCommand
from apps.admin_management.models import Menu, SystemConfig

class Command(BaseCommand):
    help = '初始化后台管理系统菜单(终极清理 404 修复版)'

    def handle(self, *args, **options):
        self.stdout.write("🧹 正在清空旧的菜单数据，防止历史幽灵路径导致 404...")
        # 🚀 极其关键：一键清空旧的冲突菜单
        Menu.objects.all().delete()  

        self.stdout.write("🚀 正在重新生成精准对齐的菜单结构...")

        # 1. 根菜单：系统管理
        sys_menu = Menu.objects.create(permission_code='system:manage', name='系统管理', path='', icon='Setting', sort_order=90)
        Menu.objects.create(permission_code='system:menu:list', name='菜单权限', path='./pages/system/menu.html', parent=sys_menu, sort_order=1)
        Menu.objects.create(permission_code='system:role:list', name='角色管理', path='./pages/system/role.html', parent=sys_menu, sort_order=2)
        Menu.objects.create(permission_code='system:log:list', name='操作日志', path='./pages/system/logs.html', parent=sys_menu, sort_order=3)
        Menu.objects.create(permission_code='system:notify:list', name='消息通知', path='./pages/system/notifications.html', parent=sys_menu, sort_order=4)
        Menu.objects.create(permission_code='system:config:list', name='参数配置', path='./pages/system/config.html', parent=sys_menu, sort_order=5)

        # 2. 根菜单：业务管理
        biz_menu = Menu.objects.create(permission_code='diet:manage', name='业务管理', path='', icon='Food', sort_order=10)
        Menu.objects.create(permission_code='business:user:list', name='用户管理', path='./pages/business/users.html', parent=biz_menu, sort_order=11)
        Menu.objects.create(permission_code='business:recipe:audit', name='菜谱审核', path='./pages/business/recipes.html', parent=biz_menu, sort_order=12)
        Menu.objects.create(permission_code='business:restaurant:list', name='商家管理', path='./pages/business/restaurants.html', parent=biz_menu, sort_order=13)
        Menu.objects.create(permission_code='business:feed:list', name='社区动态审核', path='./pages/business/feeds.html', parent=biz_menu, sort_order=14)

        # 3. 根菜单：游戏化管理
        game_menu = Menu.objects.create(permission_code='game:manage', name='游戏化管理', path='', icon='Trophy', sort_order=20)
        # 🚀 精准对齐你的实际文件夹 pages/game/
        Menu.objects.create(permission_code='game:achievement:list', name='成就管理', path='./pages/game/achievements.html', parent=game_menu, sort_order=21)
        Menu.objects.create(permission_code='game:challenge:list', name='挑战任务', path='./pages/game/challenges.html', parent=game_menu, sort_order=22)
        Menu.objects.create(permission_code='game:remedy:list', name='补救方案', path='./pages/game/remedies.html', parent=game_menu, sort_order=23)

        # 🚀 预置系统参数 (防止配置表为空时前端报错)
        configs = [
            {'key': 'app_version', 'value': '3.1.0', 'desc': '小程序当前版本号', 'public': True},
            {'key': 'audit_reward_points', 'value': '50', 'desc': '发布菜谱审核通过奖励积分', 'public': False},
            {'key': 'support_phone', 'value': '400-123-4567', 'desc': '客服联系电话', 'public': True}
        ]
        for cfg in configs:
            SystemConfig.objects.get_or_create(
                key=cfg['key'],
                defaults={'value': cfg['value'], 'description': cfg['desc'], 'is_public': cfg['public']}
            )

        self.stdout.write(self.style.SUCCESS('✅ 菜单数据库重建完成！'))