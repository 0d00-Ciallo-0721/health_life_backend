import os
import sys
import django

# --- 环境配置 ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'health_life.settings')
django.setup()

from apps.diet.documents import Restaurant

def reset_data():
    print("🧹 正在清理旧的商家数据...")
    # 1. 删除所有旧数据 (防止格式错误的数据残留)
    Restaurant.objects.delete()
    print("✅ 旧数据已清空！")

    print("🌱 正在插入标准格式的测试数据...")
    # 2. 插入几条标准数据 (注意 location 是列表 [lng, lat])
    shops = [
        {
            "amap_id": "TEST_001",
            "name": "必胜客(文理学院店)",
            "location": [107.484212, 31.210793], # ✅ 必须是列表
            "type": "餐饮服务;西餐;披萨",
            "address": "南滨路三段406号",
            "rating": 4.8,
            "photos": ["http://dummyimage.com/200x200"]
        },
        {
            "amap_id": "TEST_002",
            "name": "轻食主义沙拉",
            "location": [107.485000, 31.210500],
            "type": "餐饮服务;轻食;沙拉",
            "address": "学府花园A栋",
            "rating": 4.5,
            "photos": []
        }
    ]

    for shop_data in shops:
        try:
            Restaurant(**shop_data).save()
        except Exception as e:
            print(f"❌ 插入失败: {e}")

    print(f"🎉 数据重置完成！当前商家数量: {Restaurant.objects.count()}")
    
    # 3. 重建索引 (防止索引失效)
    try:
        Restaurant.ensure_indexes()
        print("✅ 地理索引已确认")
    except Exception as e:
        print(f"⚠️ 索引警告: {e}")

if __name__ == "__main__":
    reset_data()