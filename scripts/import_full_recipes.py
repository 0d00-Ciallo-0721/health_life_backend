### 📄 文件: scripts/import_full_recipes.py

import os
import sys
import json
import django
import re

# --- 1. 环境配置 ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'health_life.settings')
django.setup()

from apps.diet.documents import Recipe

def clean_ingredient(raw_text):
    """
    清洗食材文本，提取核心词
    例: "1kg羊肉" -> "羊肉"
    例: "半根黄瓜" -> "黄瓜"
    """
    # 去除括号内容 (e.g. "金枪鱼(in spring water)")
    text = re.sub(r'\(.*?\)', '', raw_text)
    text = re.sub(r'（.*?）', '', text)
    
    # 简单的正则提取：去除数字、量词、标点
    # 保留中文、英文
    # 这是一个简化策略，实际 NLP 更复杂
    # 去除常见的量词前缀
    text = re.sub(r'^[\d\.\/]+[g克kg斤两勺颗根个只片瓣块]+', '', text)
    text = re.sub(r'^[适少]量', '', text)
    
    return text.strip()

def import_full_corpus(file_path):
    print(f"🚀 开始导入全量菜谱: {file_path}")
    
    # 自动标签映射
    cuisine_map = {
        "川": "川菜", "麻辣": "川菜", "粤": "粤菜", "湘": "湘菜", "鲁": "鲁菜", 
        "浙": "浙菜", "苏": "苏菜", "闽": "闽菜", "徽": "徽菜",
        "西餐": "西餐", "日式": "日式", "泰式": "泰式",
        "面包": "烘焙", "蛋糕": "烘焙", "曲奇": "烘焙", "吐司": "烘焙",
        "沙拉": "轻食", "减脂": "轻食"
    }

    count = 0
    batch = []
    skipped = 0
    
    # 必须确保文件存在
    if not os.path.exists(file_path):
        print(f"❌ 错误: 找不到文件 {file_path}")
        print(f"   -> 请将 recipe_corpus_full.json 放入项目根目录: {BASE_DIR}")
        return

    try:
        # 清空旧数据 (可选，防止重复)
        print("🧹 正在清空旧的菜谱数据...")
        Recipe.objects.delete()
        print("✅ 旧数据已清空")

        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line: continue
                
                try:
                    data = json.loads(line)
                    
                    # 1. 基础字段
                    name = data.get('name', '')
                    if not name: continue

                    # 2. 标签清洗
                    tags = set(data.get('keywords', []))
                    # 补充标签
                    for key, val in cuisine_map.items():
                        if key in name:
                            tags.add(val)
                    
                    # 3. 食材清洗 (构建搜索索引)
                    raw_ings = data.get('recipeIngredient', [])
                    search_ings = set()
                    for ing in raw_ings:
                        clean = clean_ingredient(ing)
                        if len(clean) > 0:
                            search_ings.add(clean)
                    
                    # 4. 构建对象
                    recipe = Recipe(
                        name=name,
                        dish=data.get('dish', 'Unknown'),
                        description=data.get('description', ''),
                        recipeIngredient=raw_ings, # 原文列表
                        ingredients_search=list(search_ings), # 清洗后的搜索词
                        recipeInstructions=data.get('recipeInstructions', []),
                        keywords=list(tags),
                        # 默认值
                        calories=350, # 原始数据无热量，设默认值
                        difficulty="中等" if len(data.get('recipeInstructions', [])) > 5 else "简单",
                        cooking_time=15
                    )
                    batch.append(recipe)

                    # 5. 批量写入
                    if len(batch) >= 500:
                        Recipe.objects.insert(batch, load_bulk=True)
                        count += len(batch)
                        print(f"   已导入 {count} 条...")
                        batch = []

                except json.JSONDecodeError:
                    skipped += 1
                    continue
                except Exception as e:
                    print(f"⚠️ 跳过一条数据: {e}")
                    skipped += 1
                    continue

        # 写入剩余
        if batch:
            Recipe.objects.insert(batch, load_bulk=True)
            count += len(batch)

        print(f"\n🎉 导入完成！")
        print(f"✅ 成功: {count} 条")
        print(f"⚠️ 跳过: {skipped} 条")
        
    except Exception as e:
        print(f"❌ 发生致命错误: {e}")

if __name__ == "__main__":
    # 默认文件名
    path = os.path.join(BASE_DIR, "recipe_corpus_full.json")
    import_full_corpus(path)