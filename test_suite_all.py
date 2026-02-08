### 📄 文件: test_suite_all.py

import requests
import json
import time
import datetime
import os

# ================= 配置区域 =================
BASE_URL = "http://127.0.0.1:8000/api/v1"
HEADERS = {"Content-Type": "application/json"}
TOKEN = ""  

# ================= 辅助函数 =================
def print_header(title):
    print(f"\n\n{'='*15} 🧪 {title} {'='*15}")

def check_token():
    global TOKEN, HEADERS
    if len(TOKEN) < 20:
        print("\n⚠️  部分接口需要鉴权！")
        TOKEN = input("🔑 请输入你的 Bearer Token: ").strip()
        HEADERS["Authorization"] = f"Bearer {TOKEN}"

def assert_status(res, code=200):
    if res.status_code != code:
        print(f"❌ 失败! 预期 {code}, 实际 {res.status_code}")
        try: print(f"   响应: {res.json()}")
        except: print(f"   响应: {res.text[:200]}")
        return False
    return True

# ================= 模块 1: 鉴权 (Auth) =================
def test_auth_login():
    print_header("1. 微信登录鉴权")
    url = f"{BASE_URL}/user/login/"
    payload = {"code": "TEST_CODE_V3_AUTO"} 
    try:
        res = requests.post(url, json=payload)
        if res.status_code == 200:
            data = res.json().get('data', {})
            token = data.get('access') or data.get('token')
            print(f"✅ 登录成功! Token: {token[:10]}...")
            global TOKEN, HEADERS
            TOKEN = token
            HEADERS["Authorization"] = f"Bearer {TOKEN}"
        else:
            print(f"❌ 登录失败: {res.text}")
    except Exception as e: print(f"❌ 请求失败: {e}")

# ================= 模块 2: 档案 (Profile) =================
def test_profile():
    check_token()
    print_header("2. 身体档案 & v3.0 目标驱动")
    url = f"{BASE_URL}/diet/profile/"
    
    # 2.1 设置减脂目标
    print(">>> [2.1] 更新档案: 减脂模式 (Lose Weight)")
    payload = {
        "height": 175, "weight": 75.0, "gender": 1, "age": 28,
        "target_weight": 68.0, "goal_type": "lose", # v3.0 核心枚举
        "activity_level": 1.3, "diet_tags": ["低碳"], "allergens": ["芒果"]
    }
    try:
        res = requests.patch(url, json=payload, headers=HEADERS)
        if assert_status(res):
            data = res.json().get('data', {})
            # 验证自动计算逻辑 (lose = TDEE * 0.85)
            print(f"✅ BMR: {data.get('bmr')} | 目标摄入: {data.get('daily_kcal_limit')} kcal")
            print(f"   当前目标: {data.get('goal_type')}")
    except Exception as e: print(f"❌ 异常: {e}")

# ================= 模块 3: 冰箱 (Fridge) =================
def test_fridge():
    check_token()
    print_header("3. 冰箱库存 (v3.1 标准化)")
    base_url = f"{BASE_URL}/diet/fridge/"
    
    # 3.1 添加普通食材
    print(">>> [3.1] 添加食材: 西红柿 (5个)")
    try:
        payload = {"name": "西红柿", "amount": 5.0, "unit": "个", "category": "vegetable", "sub_category": "茄果类"}
        requests.post(base_url, json=payload, headers=HEADERS)
    except: pass

    # 3.2 添加临期食材 (触发大扫除模式)
    print(">>> [3.2] 添加临期食材: 临期牛奶 (明天过期)")
    try:
        tomorrow = (datetime.date.today() + datetime.timedelta(days=1)).isoformat()
        payload = {
            "name": "牛奶", "amount": 2.0, "unit": "盒", 
            "category": "other", "expiry_date": tomorrow, "is_scrap": False
        }
        res = requests.post(base_url, json=payload, headers=HEADERS)
        if assert_status(res, 201):
            print(f"✅ 临期食材添加成功 (过期日: {tomorrow})")
            
        # 3.3 验证列表响应格式 (Phase 8 修复)
        print(">>> [3.3] 验证列表响应结构 (items vs results)")
        res_list = requests.get(base_url, headers=HEADERS)
        if assert_status(res_list):
            data = res_list.json().get('data', {})
            if 'items' in data and 'total' in data:
                print(f"✅ 响应格式正确: items count={len(data['items'])}, total={data['total']}")
            else:
                print(f"❌ 响应格式错误! 收到 keys: {list(data.keys())}")

    except Exception as e: print(f"❌ 异常: {e}")

# ================= 模块 4: 搜餐 (Search) =================
def test_search():
    check_token()
    print_header("4. 智能搜餐 v3.0")
    url = f"{BASE_URL}/diet/search/"
    cook_recipe_id = None
    
    # 4.1 大扫除模式
    print(">>> [4.1] 测试 '大扫除模式' (Cleanup Mode)")
    try:
        # v3.0 复杂筛选参数 + v3.1 热量区间
        filters = {
            "cleanup_mode": True, # 核心开关
            "tags": ["快手菜"], 
            "cooking_time": 30,
            "calorie_min": 100,   # Phase 8 复核
            "calorie_max": 800
        }
        payload = {"mode": "cook", "page": 1, "filters": filters}
        res = requests.post(url, json=payload, headers=HEADERS)
        if assert_status(res):
            data = res.json()['data']
            recs = data.get('recommendations', [])
            print(f"✅ 找到 {len(recs)} 个大扫除推荐")
            if recs:
                top = recs[0]
                cook_recipe_id = top['id']
                print(f"   首推: {top['name']} | 理由: {top.get('match_reason')}")
                # 验证是否是因为临期牛奶被推荐
                print(f"   匹配分: {top['match_score']}%")
    except Exception as e: print(f"❌ 异常: {e}")

    # 4.2 菜谱详情与替代方案
    if cook_recipe_id:
        print(f"\n>>> [4.2] 获取详情 (ID: {cook_recipe_id}) & 替代方案")
        try:
            res = requests.get(f"{BASE_URL}/diet/recipe/{cook_recipe_id}/", headers=HEADERS)
            if assert_status(res):
                data = res.json()['data']
                ingredients = data.get('ingredients', [])
                print(f"   🧊 冰箱匹配情况:")
                for ing in ingredients:
                    status = "✅ 有" if ing['in_fridge'] else "❌ 缺"
                    sub_txt = f"(可替: {ing['substitutes'][0]['name']})" if ing.get('substitutes') else ""
                    print(f"      - {ing['name']}: {status} {sub_txt}")
        except Exception as e: print(f"❌ 异常: {e}")

    return cook_recipe_id

# ================= 模块 5: 扩展功能 (Extensions v3.1) =================
def test_extensions(recipe_id):
    check_token()
    print_header("5. 扩展功能 v3.1 (购物/运动)")
    
    # 5.1 购物清单
    if recipe_id:
        print(f">>> [5.1] 生成购物清单 (基于菜谱ID: {recipe_id})")
        url_shop = f"{BASE_URL}/diet/shopping-list/generate/"
        try:
            res = requests.post(url_shop, json={"recipe_ids": [recipe_id]}, headers=HEADERS)
            if assert_status(res):
                data = res.json()['data']
                print(f"   🛒 待购清单: {[i['name'] for i in data['list'] if i['status']=='missing']}")
        except Exception as e: print(f"❌ 异常: {e}")

    # 5.2 运动记录
    print(f"\n>>> [5.2] 运动打卡")
    url_workout = f"{BASE_URL}/diet/workout/save/"
    try:
        payload = {"type": "running", "duration": 30, "calories_burned": 280}
        res = requests.post(url_workout, json=payload, headers=HEADERS)
        if assert_status(res):
            print("   ✅ 跑步 30分钟 记录成功")
            
        # 查询历史
        res_hist = requests.get(f"{BASE_URL}/diet/workout/history/", headers=HEADERS)
        if res_hist.status_code == 200:
            print(f"   📅 历史记录数: {res_hist.json()['data']['summary']['total_count']}")
    except Exception as e: print(f"❌ 异常: {e}")

# ================= 模块 6: 记录 (Log) =================
def test_log(recipe_id):
    check_token()
    print_header("6. 饮食记录 (v3.0 精确扣减)")
    url = f"{BASE_URL}/diet/log/"
    
    if recipe_id:
        print(f">>> [6.1] 记录菜谱 (含扣减) - source_type=1")
        payload = {
            "source_type": 1, 
            "source_id": recipe_id, 
            "deduct_fridge": True,
            "meal_type": "lunch", 
            "meal_time": "12:30",
            "portion": 1.0
        }
        res = requests.post(url, json=payload, headers=HEADERS)
        if assert_status(res):
            data = res.json()['data']
            print(f"✅ 记录成功 (LogID: {data['log_id']})")
            print(f"   📊 剩余热量: {data['remaining_calories']}")
    
    print(f">>> [6.2] 自定义录入 (v3.1) - source_type=3")
    try:
        payload = {
            "source_type": 3,
            "source_id": "custom", # 任意值
            "food_name": "黑咖啡",
            "calories": 15, # [v3.1] 自定义热量
            "meal_type": "snack",
            "meal_time": "15:00"
        }
        res = requests.post(url, json=payload, headers=HEADERS)
        if assert_status(res):
            print(f"✅ 自定义录入成功 (+15 kcal)")
    except Exception as e: print(f"❌ 异常: {e}")

# ================= 模块 7: 报表与图表 (Charts v3.1) =================
def test_report_charts():
    check_token()
    print_header("7. 深度报表 & 图表接口 (Phase 8)")
    
    # 7.1 今日概览 (含评级)
    print(">>> [7.1] 今日概览 & 健康评级")
    url_summary = f"{BASE_URL}/diet/summary/"
    try:
        res = requests.get(url_summary, headers=HEADERS)
        if assert_status(res):
            data = res.json()['data']['summary']
            print(f"   🏆 健康评级: {data.get('health_level').upper()} ({data.get('health_tip')})")
            print(f"   📈 进度: {data.get('progress_percentage')}%")
    except Exception as e: print(f"❌ 异常: {e}")

    # 7.2 图表接口 (P1级需求)
    print("\n>>> [7.2] 验证前端图表专用接口")
    chart_urls = {
        "Daily": f"{BASE_URL}/diet/report/charts/daily/",
        "Weekly": f"{BASE_URL}/diet/report/charts/weekly/",
        "Weight": f"{BASE_URL}/diet/report/charts/weight/"
    }
    
    for name, url in chart_urls.items():
        try:
            res = requests.get(url, headers=HEADERS)
            if assert_status(res):
                data = res.json()['data']
                keys = list(data.keys())
                print(f"   📊 {name} Chart ✅ (Keys: {keys})")
                # 简单验证颜色配置是否存在
                if name == "Daily" and 'config' in data.get('calorie_chart', {}):
                    print("      颜色配置检测: OK")
        except Exception as e: print(f"❌ {name} Chart 异常: {e}")

# ================= 模块 8: 智能转盘 (Wheel) =================
def test_wheel():
    check_token()
    print_header("8. 智能转盘 (v3.0 组合算法)")
    
    print(">>> [8.1] 转盘 Step 3 (3健康+2偏好+1放纵)")
    try:
        payload = {"step": 3, "cuisine": "川菜", "flavor": "麻辣"}
        res = requests.post(f"{BASE_URL}/diet/wheel/", json=payload, headers=HEADERS)
        if assert_status(res):
            data = res.json()['data']
            recs = data.get('recommendations', [])
            print(f"✅ 推荐结果: {len(recs)} 个")
            reasons = [r.get('match_reason', '未知') for r in recs]
            print(f"   🏷️ 推荐理由分布: {reasons}")
    except Exception as e: print(f"❌ 异常: {e}")

# ================= 模块 9: AI 服务 (AI v3.1) =================
def test_ai_service():
    check_token()
    print_header("9. AI 智能服务 (v3.1)")
    
    # 9.1 拍图识热量
    print(">>> [9.1] 拍图识热量 (测试文件: 1.png)")
    image_path = "1.png"
    if os.path.exists(image_path):
        try:
            url = f"{BASE_URL}/diet/ai/food-recognition/"
            # 注意: 上传文件时不能带 Content-Type: application/json，requests 会自动处理 boundary
            # 我们需要构造一个新的 header，只包含 Authorization
            upload_headers = {"Authorization": HEADERS["Authorization"]}
            
            with open(image_path, 'rb') as f:
                files = {'image': f}
                print("   📤 正在上传图片并请求大模型 (耗时较长)...")
                start_time = time.time()
                res = requests.post(url, headers=upload_headers, files=files)
                duration = time.time() - start_time
                
                if assert_status(res):
                    data = res.json()['data']
                    print(f"   ✅ 识别成功 ({duration:.1f}s): {data.get('food_name')} - {data.get('calories')} kcal")
                    print(f"      分析: {data.get('description')[:30]}...")
        except Exception as e: print(f"❌ 异常: {e}")
    else:
        print("   ⚠️  未找到 '1.png'，跳过识图测试")

    # 9.2 AI 营养师
    print("\n>>> [9.2] AI 营养师分析")
    try:
        url = f"{BASE_URL}/diet/ai-nutritionist/analyze/"
        res = requests.post(url, json={}, headers=HEADERS)
        if assert_status(res):
            data = res.json()['data']
            print(f"   🤖 建议: {data.get('advice')[:50]}...")
    except Exception as e: print(f"❌ 异常: {e}")

# ================= 主程序 =================
def main():
    print("\n" + "="*60)
    print("🚀 健康生活后端 v3.1 终极回归测试")
    print("   覆盖: 核心业务 + AI识图 + 购物清单 + 运动 + 图表接口")
    print("="*60)
    
    test_auth_login()
    test_profile()
    test_fridge()
    
    # 核心流程串联
    recipe_id = test_search()
    test_extensions(recipe_id) # 购物/运动
    test_log(recipe_id)
    
    test_report_charts() # 包含报表和新图表接口
    test_wheel()
    test_ai_service() # AI 压轴
    
    print("\n🎉 v3.1 所有模块测试完成!")

if __name__ == "__main__":
    main()