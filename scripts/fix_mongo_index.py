import os
import sys
import django

# --- 环境配置 ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'health_life.settings')
django.setup()

from apps.diet.documents import Restaurant

def fix_indices():
    print("🔧 正在检查 MongoDB 索引...")
    
    # 1. 强制创建索引
    try:
        Restaurant.ensure_indexes()
        print("✅ 索引 '2dsphere' 创建/确认成功！")
    except Exception as e:
        print(f"❌ 索引创建失败: {e}")

    # 2. 检查数据量
    count = Restaurant.objects.count()
    print(f"📊 当前商家数据量: {count} 条")
    
    if count == 0:
        print("⚠️ 警告: 数据库中没有商家数据！搜索接口将返回空列表。")
        print("   -> 请先运行商家导入脚本，或者手动插入一条测试数据。")
        insert_dummy_data()

def insert_dummy_data():
    print("🛠️ 正在插入一条测试商家数据...")
    try:
        Restaurant(
            amap_id="TEST_001",
            name="测试健康沙拉店",
            location=[107.484212, 31.210793], # 对应测试脚本的坐标
            type="餐饮服务;轻食;沙拉",
            address="虚拟测试地址",
            rating=4.5,
            photos=["http://dummyimage.com/200x200"]
        ).save()
        print("✅ 测试数据插入成功！")
    except Exception as e:
        print(f"❌ 插入失败: {e}")

if __name__ == "__main__":
    fix_indices()