import argparse
import os
import sys

import django


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "health_life.settings")
django.setup()

from apps.common.utils import AMapService
from apps.diet.models.mongo.restaurant import Restaurant


def parse_args():
    parser = argparse.ArgumentParser(description="Load real restaurants from AMap into MongoDB cache.")
    parser.add_argument("--lng", type=float, required=True, help="Center longitude")
    parser.add_argument("--lat", type=float, required=True, help="Center latitude")
    parser.add_argument("--radius", type=int, default=3000, help="Search radius in meters")
    parser.add_argument("--pages", type=int, default=3, help="How many pages to fetch")
    parser.add_argument("--clear", action="store_true", help="Clear existing restaurant cache before loading")
    return parser.parse_args()


def load_restaurants(lng, lat, radius=3000, pages=3, clear=False):
    if clear:
        deleted = Restaurant.objects.count()
        Restaurant.objects.delete()
        print(f"已清空旧商家数据，共删除 {deleted} 条")

    saved = 0
    skipped = 0

    for page in range(1, pages + 1):
        pois = AMapService.search_nearby_restaurants(lng, lat, radius=radius, page=page)
        if not pois:
            print(f"第 {page} 页没有更多商家数据，停止加载")
            break

        print(f"第 {page} 页获取到 {len(pois)} 条商家")
        for poi in pois:
            amap_id = poi.get("id")
            if not amap_id:
                skipped += 1
                continue

            if Restaurant.objects(amap_id=amap_id).first():
                skipped += 1
                continue

            location = poi.get("location", "")
            try:
                lng_str, lat_str = location.split(",")
                coords = [float(lng_str), float(lat_str)]
            except Exception:
                skipped += 1
                continue

            photos = [item.get("url") for item in poi.get("photos", []) if item.get("url")]
            biz_ext = poi.get("biz_ext") or {}

            try:
                Restaurant(
                    amap_id=amap_id,
                    name=poi.get("name", "未知商家"),
                    location=coords,
                    type=poi.get("type", ""),
                    address=poi.get("address", ""),
                    rating=float(biz_ext.get("rating", 4.0) or 4.0),
                    cost=float(biz_ext.get("cost", 0.0) or 0.0),
                    photos=photos,
                ).save()
                saved += 1
            except Exception as exc:
                skipped += 1
                print(f"跳过商家 {amap_id}: {exc}")

    Restaurant.ensure_indexes()
    total = Restaurant.objects.count()
    print(f"真实商家加载完成，新增 {saved} 条，跳过 {skipped} 条，当前总数 {total}")


if __name__ == "__main__":
    args = parse_args()
    load_restaurants(
        lng=args.lng,
        lat=args.lat,
        radius=args.radius,
        pages=args.pages,
        clear=args.clear,
    )
