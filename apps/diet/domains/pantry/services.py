from django.db import transaction
from apps.diet.models import FridgeItem
from apps.common.utils import normalize_ingredient_name

class PantryService:
    @staticmethod
    def sync_fridge(user, operation, items):
        """全量同步/覆盖冰箱库存"""
        if operation == 'override':
            with transaction.atomic():
                FridgeItem.objects.filter(user=user).delete()
                bulk = [
                    FridgeItem(
                        user=user, 
                        name=i.get('name'), 
                        amount=i.get('amount', 1), 
                        unit=i.get('unit', '个'), 
                        category=i.get('category'),
                        sub_category=i.get('sub_category'),
                        expiry_date=i.get('expiry_date'),
                        is_scrap=i.get('is_scrap', False)
                    ) for i in items
                ]
                FridgeItem.objects.bulk_create(bulk)
            return len(bulk)
        return 0

    @staticmethod
    def deduct_inventory(user, ingredients_needed, portion=1.0):
        """
        [核心解耦] 扣减库存逻辑
        ingredients_needed: 归一化后的食材名称列表 ['西红柿', '鸡蛋']
        portion: 份数
        """
        if not ingredients_needed:
            return

        user_fridge_items = FridgeItem.objects.filter(user=user)
        
        # 预加载到内存以减少数据库查询次数
        # 转换为字典列表以便操作: {'西红柿': [item1, item2]}
        stock_map = {}
        for item in user_fridge_items:
            std_name = normalize_ingredient_name(item.name)
            if std_name not in stock_map:
                stock_map[std_name] = []
            stock_map[std_name].append(item)

        # 执行扣减
        for ing_std_name in ingredients_needed:
            matched_items = stock_map.get(ing_std_name, [])
            if not matched_items:
                continue

            # 简单的数量扣减逻辑：假设每份菜消耗 1.0 个单位
            # 实际生产中可能需要基于 recipeIngredient 的具体数值解析
            needed_amount = 1.0 * portion 
            
            # 先进先出 (FIFO): 优先扣减最早入库的
            matched_items.sort(key=lambda x: x.created_at)
            
            for target_item in matched_items:
                if needed_amount <= 0: 
                    break
                
                current_stock = target_item.amount
                if current_stock > needed_amount:
                    target_item.amount -= needed_amount
                    target_item.save()
                    needed_amount = 0
                else:
                    needed_amount -= current_stock
                    target_item.delete()