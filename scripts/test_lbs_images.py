import os
import sys
import django
import json

# --- 1. 初始化 Django 环境 ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'health_life.settings')
django.setup()

from apps.diet.models import Restaurant
from apps.common.utils import AMapService

def test_level_2_mongo_data():
    print("\n" + "="*50)
    print("🟡 层次 2: MongoDB 真实数据探查 (Database Layer)")
    print("="*50)
    
    # 获取最近入库的 5 个商家
    shops = Restaurant.objects.order_by('-cached_at').limit(5)
    
    if not shops:
        print("❌ MongoDB restaurant_cache 集合为空，没有数据。")
        return

    for shop in shops:
        print(f"🏪 商家: {shop.name} (AMap ID: {shop.amap_id})")
        photos = shop.photos
        if not photos:
            print("   ❌ 图片状态: 空数组 [] (库里完全没图)")
        else:
            print(f"   ✅ 图片状态: 包含 {len(photos)} 张图")
            print(f"   🖼️ 首图 URL: {photos[0]}")
        print("-" * 30)


def test_level_3_amap_api():
    print("\n" + "="*50)
    print("🟢 层次 3: 高德 API 原始数据探查 (Source Layer)")
    print("="*50)
    
    # 设定一个测试坐标 (例如：北京王府井 或 你们的主测试区域)
    # 请确保该坐标附近有正常营业的餐厅
    test_lng = 116.411136
    test_lat = 39.911048
    radius = 3000
    
    print(f"📡 正在调用高德 API... 坐标: [{test_lng}, {test_lat}], 半径: {radius}m")
    
    try:
        raw_pois = AMapService.search_nearby_restaurants(test_lng, test_lat, radius)
        print(f"✅ 成功获取到 {len(raw_pois)} 条 POI 数据\n")
        
        # 只检查前 3 条 POI 的图片数据
        for poi in raw_pois[:3]:
            print(f"📍 POI 名称: {poi.get('name')}")
            
            raw_photos = poi.get('photos', [])
            if not raw_photos:
                print("   ❌ 高德 API 响应: photos 字段为空 [] 或不存在")
            else:
                print(f"   ✅ 高德 API 响应: 包含 photos 数组 (长度: {len(raw_photos)})")
                # 打印第一张图的具体结构，确认 url 字段是否存在
                first_photo = raw_photos[0]
                print(f"   📦 原始照片节点: {json.dumps(first_photo, ensure_ascii=False)}")
                if first_photo.get('url'):
                    print(f"   🔗 成功提取 URL: {first_photo.get('url')}")
                else:
                    print("   ⚠️ 警告: photos 数组存在，但内部没有 'url' 字段！")
            print("-" * 30)
            
    except Exception as e:
        print(f"❌ 高德 API 调用失败，请检查 utils.py 中的实现或网络/Key 设置: {e}")

if __name__ == "__main__":
    test_level_2_mongo_data()
    test_level_3_amap_api()
    print("\n🎉 排查脚本执行完毕。")