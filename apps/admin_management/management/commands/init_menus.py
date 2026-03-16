from django.core.management.base import BaseCommand
from apps.admin_management.models import Menu, SystemConfig

class Command(BaseCommand):
    help = '初始化后台管理系统菜单(适配原生HTML+Iframe架构)'

    def handle(self, *args, **options):
        self.stdout.write("正在更新菜单路径数据...")

        # 1. 根菜单：系统管理
        sys_menu, _ = Menu.objects.update_or_create(
            permission_code='system:manage',
            defaults={
                'name': '系统管理',
                'path': '',  # 根菜单不需要路径
                'icon': 'Setting',
                'sort_order': 99
            }
        )

        # 2. 根菜单：业务管理
        biz_menu, _ = Menu.objects.update_or_create(
            permission_code='diet:manage',
            defaults={
                'name': '健康业务',
                'path': '',  # 根菜单不需要路径
                'icon': 'Food',
                'sort_order': 10
            }
        )

        # ================= 业务管理子菜单 =================
        # 补充缺失的用户管理
        Menu.objects.update_or_create(
            permission_code='business:user:list',
            defaults={'name': '用户管理', 'path': './pages/business/users.html', 'parent': biz_menu, 'sort_order': 11}
        )
        
        # 补充缺失的菜谱审核
        Menu.objects.update_or_create(
            permission_code='business:recipe:audit',
            defaults={'name': '菜谱审核', 'path': './pages/business/recipes.html', 'parent': biz_menu, 'sort_order': 12}
        )

        Menu.objects.update_or_create(
            permission_code='business:restaurant:list',
            defaults={'name': '商家管理', 'path': './pages/business/restaurants.html', 'parent': biz_menu, 'sort_order': 13}
        )

        Menu.objects.update_or_create(
            permission_code='business:task:list',
            defaults={'name': '挑战任务', 'path': './pages/business/tasks.html', 'parent': biz_menu, 'sort_order': 14}
        )

        Menu.objects.update_or_create(
            permission_code='business:remedy:list',
            defaults={'name': '补救方案', 'path': './pages/business/remedies.html', 'parent': biz_menu, 'sort_order': 15}
        )

        # ================= 系统管理子菜单 =================
        Menu.objects.update_or_create(
            permission_code='system:menu:list',
            defaults={'name': '菜单权限', 'path': './pages/system/menu.html', 'parent': sys_menu, 'sort_order': 1}
        )

        Menu.objects.update_or_create(
            permission_code='system:role:list',
            defaults={'name': '角色管理', 'path': './pages/system/role.html', 'parent': sys_menu, 'sort_order': 2}
        )

        Menu.objects.update_or_create(
            permission_code='system:log:list',
            defaults={'name': '操作日志', 'path': './pages/system/logs.html', 'parent': sys_menu, 'sort_order': 3}
        )

        Menu.objects.update_or_create(
            permission_code='system:notify:list',
            defaults={'name': '消息通知', 'path': './pages/system/notifications.html', 'parent': sys_menu, 'sort_order': 4}
        )

        Menu.objects.update_or_create(
            permission_code='system:config:list',
            defaults={'name': '参数配置', 'path': './pages/system/config.html', 'parent': sys_menu, 'sort_order': 5}
        )
        
        # 🚀 [新增] 成就字典管理菜单
        Menu.objects.update_or_create(
            permission_code='business:achievement:list',
            defaults={
                'name': '成就管理', 
                'path': './pages/business/achievements.html', 
                'parent': biz_menu, 
                'sort_order': 60
            }
        )

        # 🚀 [新增] 社区动态审核菜单
        Menu.objects.update_or_create(
            permission_code='business:feed:list',
            defaults={
                'name': '社区动态审核', 
                'path': './pages/business/feeds.html', 
                'parent': biz_menu, 
                'sort_order': 70
            }
        )

        # ================= [新增] 领域模块菜单配置 =================

        # 🚀 [新增] 游戏化管理 (顶级菜单)
        game_menu, _ = Menu.objects.update_or_create(
            permission_code='game:manage',
            defaults={
                'name': '游戏化管理',
                'path': '',
                'icon': 'Trophy',
                'sort_order': 20
            }
        )
        Menu.objects.update_or_create(permission_code='game:achievement:list', defaults={'name': '成就管理', 'path': './pages/game/achievements.html', 'parent': game_menu, 'sort_order': 21})
        Menu.objects.update_or_create(permission_code='game:challenge:list', defaults={'name': '挑战任务管理', 'path': './pages/game/challenges.html', 'parent': game_menu, 'sort_order': 22})
        Menu.objects.update_or_create(permission_code='game:remedy:list', defaults={'name': '补救方案管理', 'path': './pages/game/remedies.html', 'parent': game_menu, 'sort_order': 23})

        # 🚀 [新增] 社区与社交管理 (顶级菜单)
        social_menu, _ = Menu.objects.update_or_create(
            permission_code='social:manage',
            defaults={
                'name': '社区与社交管理',
                'path': '',
                'icon': 'ChatDotRound',
                'sort_order': 30
            }
        )
        Menu.objects.update_or_create(permission_code='social:feed:list', defaults={'name': '动态流审核', 'path': './pages/social/feeds.html', 'parent': social_menu, 'sort_order': 31})
        Menu.objects.update_or_create(permission_code='social:follow:list', defaults={'name': '用户关注关系查询', 'path': './pages/social/follows.html', 'parent': social_menu, 'sort_order': 32})

        # 🚀 [新增] 日志与健康管理 (顶级菜单)
        health_menu, _ = Menu.objects.update_or_create(
            permission_code='health:manage',
            defaults={
                'name': '日志与健康管理',
                'path': '',
                'icon': 'DataLine',
                'sort_order': 40
            }
        )
        Menu.objects.update_or_create(permission_code='health:water:list', defaults={'name': '饮水记录聚合', 'path': './pages/health/water.html', 'parent': health_menu, 'sort_order': 41})
        Menu.objects.update_or_create(permission_code='health:intake:list', defaults={'name': '体重/摄入聚合视图', 'path': './pages/health/intake.html', 'parent': health_menu, 'sort_order': 42})


        # 🚀 预置一些系统参数 (保持不变)
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

        self.stdout.write(self.style.SUCCESS('✅ 菜单路径修正及初始化完成！'))