from django.core.management.base import BaseCommand
from apps.admin_management.models import Menu
from apps.admin_management.models import Menu, SystemConfig # 🚀 导入 SystemConfig

class Command(BaseCommand):
    help = '初始化后台管理系统菜单'

    def handle(self, *args, **options):
        self.stdout.write("正在初始化菜单数据...")

        # 1. 根菜单：系统管理
        sys_menu, _ = Menu.objects.get_or_create(
            permission_code='system:manage',
            defaults={
                'name': '系统管理',
                'path': '/system',
                'component': 'Layout',
                'icon': 'Setting',
                'sort_order': 99
            }
        )

        # 2. 子菜单：菜单管理
        Menu.objects.get_or_create(
            permission_code='system:menu:list',
            defaults={
                'name': '菜单权限',
                'path': 'menu',
                'component': 'views/system/menu/index',
                'icon': 'Menu',
                'parent': sys_menu,
                'sort_order': 1
            }
        )

        # 3. 子菜单：角色管理
        Menu.objects.get_or_create(
            permission_code='system:role:list',
            defaults={
                'name': '角色管理',
                'path': 'role',
                'component': 'views/system/role/index',
                'icon': 'UserFilled',
                'parent': sys_menu,
                'sort_order': 2
            }
        )

        # 3. 子菜单：操作日志 (sort_order=3)
        Menu.objects.get_or_create(
            permission_code='system:log:list',
            defaults={
                'name': '操作日志',
                'path': 'log',
                'component': 'views/system/log/index',
                'icon': 'Document',
                'parent': sys_menu,
                'sort_order': 3
            }
        )

        # 4. 根菜单：业务管理
        diet_menu, _ = Menu.objects.get_or_create(
            permission_code='diet:manage',
            defaults={
                'name': '健康业务',
                'path': '/diet',
                'component': 'Layout',
                'icon': 'Food',
                'sort_order': 10
            }
        )
        # 4. 子菜单：消息通知
        Menu.objects.get_or_create(
            permission_code='system:notify:list',
            defaults={
                'name': '消息通知',
                'path': 'notification',
                'component': 'views/system/notification/index',
                'icon': 'Bell',
                'parent': sys_menu, # 挂载在 系统管理 下
                'sort_order': 4
            }
        )


        # 5. 子菜单：商家管理
        Menu.objects.get_or_create(
            permission_code='business:restaurant:list',
            defaults={
                'name': '商家管理',
                'path': 'restaurant', # 前端路由路径 apps/business/restaurant/index
                'component': 'views/business/restaurant/index',
                'icon': 'Shop',
                'parent': diet_menu, # 挂载在“健康业务”下
                'sort_order': 11
            }
        )
        
        # 5. 子菜单：参数配置 (加在 消息通知 后面)
        Menu.objects.get_or_create(
            permission_code='system:config:list',
            defaults={
                'name': '参数配置',
                'path': 'config',
                'component': 'views/system/config/index',
                'icon': 'Operation',
                'parent': sys_menu,
                'sort_order': 5
            }
        )

        # 6. 子菜单：任务配置
        Menu.objects.get_or_create(
            permission_code='business:task:list',
            defaults={
                'name': '挑战任务',
                'path': 'gamification/task', # 前端路由路径
                'component': 'views/business/gamification/task',
                'icon': 'Trophy',
                'parent': diet_menu, # 挂载在“健康业务”下
                'sort_order': 12
            }
        )
        # 🚀 6. 预置一些系统参数 (Seed Data)
        configs = [
            {
                'key': 'app_version', 
                'value': '3.1.0', 
                'desc': '小程序当前版本号', 
                'public': True
            },
            {
                'key': 'audit_reward_points', 
                'value': '50', 
                'desc': '发布菜谱审核通过奖励积分', 
                'public': False
            },
            {
                'key': 'support_phone', 
                'value': '400-123-4567', 
                'desc': '客服联系电话', 
                'public': True
            }
        ]
        
        for cfg in configs:
            SystemConfig.objects.get_or_create(
                key=cfg['key'],
                defaults={
                    'value': cfg['value'],
                    'description': cfg['desc'],
                    'is_public': cfg['public']
                }
            )
        # 7. 子菜单：补救方案
        Menu.objects.get_or_create(
            permission_code='business:remedy:list',
            defaults={
                'name': '补救方案',
                'path': 'gamification/remedy',
                'component': 'views/business/gamification/remedy',
                'icon': 'FirstAidKit',
                'parent': diet_menu,
                'sort_order': 13
            }
        )

        self.stdout.write(self.style.SUCCESS('✅ 菜单初始化完成！'))