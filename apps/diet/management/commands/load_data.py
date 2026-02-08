import json
import os
from django.core.management.base import BaseCommand
from django.conf import settings
from apps.diet.models import Recipe, Restaurant

class Command(BaseCommand):
    help = '清洗并导入菜谱和商家数据 (适配 v3.1 架构)'

    def handle(self, *args, **options):
        # 1. 导入商家数据
        json_path = os.path.join(settings.BASE_DIR, 'food_data_1767266333.json')
        
        if os.path.exists(json_path):
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    res_data = json.load(f)
                    count = 0
                    for item in res_data.get('data', []):
                        lng, lat = map(float, item['location'].split(','))
                        Restaurant.objects(amap_id=item['id']).update_one(
                            set__name=item['name'],
                            set__location=[lng, lat],
                            set__type=item['type'],
                            set__address=item['address'],
                            set__rating=float(item.get('rating', 0) or 0),
                            set__cost=float(item.get('cost', 0) or 0),
                            set__photos=item.get('photos', []),
                            upsert=True
                        )
                        count += 1
                self.stdout.write(self.style.SUCCESS(f'✅ 成功导入 {count} 条商家数据'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'❌ 商家导入失败: {str(e)}'))
        else:
            self.stdout.write(self.style.WARNING('⚠️ 未找到商家 JSON 文件，跳过。'))

        # 2. 导入菜谱示例
        sample_recipe = {
            "name": "红烧滩羊肉",
            "recipeIngredient": ["1kg羊肉", "5片姜", "3瓣蒜"],
            "ingredients_search": ["羊肉", "姜", "蒜"],
            "recipeInstructions": ["滩羊肉在姜水里焯3分钟", "切块慢炖"],
            "keywords": ["宁夏", "硬菜"],
            "calories": 450,
            "difficulty": "困难",
            "cooking_time": 60
        }
        
        try:
            Recipe.objects(name=sample_recipe['name']).update_one(
                set__recipeIngredient=sample_recipe['recipeIngredient'],
                set__ingredients_search=sample_recipe['ingredients_search'],
                set__recipeInstructions=sample_recipe['recipeInstructions'],
                set__keywords=sample_recipe['keywords'],
                set__calories=sample_recipe['calories'],
                set__difficulty=sample_recipe['difficulty'],
                set__cooking_time=sample_recipe['cooking_time'],
                upsert=True
            )
            self.stdout.write(self.style.SUCCESS('✅ 成功导入菜谱示例数据'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ 菜谱导入失败: {str(e)}'))