from django.core.cache import cache
from apps.diet.models import Restaurant
from apps.common.utils import AMapService

class LBSService:
    @staticmethod
    def get_recommendations(lng, lat, radius=3000):
        results = []
        geo_key = f"lbs_v1:{round(lng, 2)}_{round(lat, 2)}"
        
        cached = cache.get(geo_key)
        if cached: return cached

        try:
            # 1. 查 Mongo 缓存
            shops = list(Restaurant.objects(
                location__near=[lng, lat],
                location__max_distance=radius
            ).limit(15))
            
            # 2. 如果不足，查高德 API 并入库
            if len(shops) < 5:
                raw_pois = AMapService.search_nearby_restaurants(lng, lat, radius)
                for poi in raw_pois:
                    try:
                        if Restaurant.objects(amap_id=poi['id']).count() > 0: continue
                        loc_str = poi.get('location', '0,0').split(',')
                        coords = [float(loc_str[0]), float(loc_str[1])]
                        photos = [p.get('url') for p in poi.get('photos', []) if p.get('url')]
                        
                        shop = Restaurant(
                            amap_id=poi['id'], name=poi['name'], location=coords,
                            type=poi.get('type', ''), address=poi.get('address', ''),
                            rating=float(poi['biz_ext'].get('rating', 4.0)) if poi.get('biz_ext') else 4.0,
                            photos=photos
                        )
                        shop.save()
                        shops.append(shop)
                    except Exception: continue

            # 3. 格式化输出
            for s in shops:
                est_cals = 600
                s_type = str(s.type or "")
                health_light = "yellow"
                if "轻食" in s_type or "沙拉" in s_type: 
                    est_cals = 400; health_light = "green"
                elif "快餐" in s_type or "汉堡" in s_type: 
                    est_cals = 800; health_light = "red"
                elif est_cals < 600: 
                    health_light = "green"
                
                score_map = {"green": 90, "yellow": 70, "red": 50}
                results.append({
                    "id": s.amap_id, "name": s.name, "address": s.address,
                    "rating": s.rating, "image": s.photos[0] if s.photos else "",
                    "estimated_calories": est_cals,
                    "health_light": health_light,
                    "health_score": score_map.get(health_light, 70),
                })
            
            if results: cache.set(geo_key, results, timeout=3600)
            return results
        except Exception:
            return []