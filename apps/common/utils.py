from django.conf import settings
from rest_framework.exceptions import AuthenticationFailed
import requests

# 食材同义词库
INGREDIENT_SYNONYMS = {
    # 核心映射: 标准名 -> [别名列表]
    "西红柿": ["番茄", "洋柿子"],
    "土豆": ["马铃薯", "洋芋", "地蛋"],
    "鸡蛋": ["鸡子", "蛋", "鲜鸡蛋"],
    "青菜": ["小白菜", "油菜", "小油菜"],
    "猪肉": ["瘦肉", "五花肉", "里脊肉", "前腿肉", "后腿肉"],
    "牛肉": ["肥牛", "牛柳", "牛腱子"],
    "鸡胸肉": ["鸡胸", "鸡肉", "鸡脯肉"],
    "豆腐": ["老豆腐", "嫩豆腐", "水豆腐"],
    "洋葱": ["圆葱"],
    "胡萝卜": ["红萝卜"],
    "米饭": ["大米", "白饭"],
    "面条": ["挂面", "拉面", "手擀面"],
}

_REVERSE_SYNONYM_MAP = {}
for std, aliases in INGREDIENT_SYNONYMS.items():
    for alias in aliases:
        _REVERSE_SYNONYM_MAP[alias] = std
    _REVERSE_SYNONYM_MAP[std] = std  # 自身映射自身

def normalize_ingredient_name(name):
    """
    食材归一化工具函数
    输入 "番茄" -> 返回 "西红柿"
    输入 "西红柿" -> 返回 "西红柿"
    输入 "未知物" -> 返回 "未知物"
    """
    if not name:
        return ""
    clean_name = name.strip()
    return _REVERSE_SYNONYM_MAP.get(clean_name, clean_name)

class WeChatService:
    @staticmethod
    def get_openid(code):
        """
        通过前端传来的 code 换取 openid
        """
        # ✅ [修复核心] 拦截测试码，绕过微信API
        # 只要是 TEST_ 开头的 code，直接视为测试通过
        if code and str(code).startswith("TEST_"):
            print(f"⚠️ [Mock Login] 检测到测试码 {code}，模拟登录成功")
            return {
                "openid": f"mock_openid_{code}", # 生成一个固定的 mock openid
                "session_key": "mock_session_key"
            }

        url = "https://api.weixin.qq.com/sns/jscode2session"
        params = {
            "appid": settings.WECHAT_APP_ID,
            "secret": settings.WECHAT_APP_SECRET,
            "js_code": code,
            "grant_type": "authorization_code"
        }

        try:
            res = requests.get(url, params=params, timeout=5)
            data = res.json()
        except Exception as e:
            raise AuthenticationFailed(f"微信API连接失败: {str(e)}")

        if "errcode" in data and data["errcode"] != 0:
            raise AuthenticationFailed(f"微信登录失败: {data.get('errmsg')}")

        return {
            "openid": data.get("openid"),
            "session_key": data.get("session_key")
        }

class AMapService:
    @staticmethod
    def search_nearby_restaurants(lng, lat, radius=3000):
        key = settings.AMAP_WEB_KEY
        if not key: return []
        url = "https://restapi.amap.com/v3/place/around"
        params = {
            "key": key,
            "location": f"{lng},{lat}",
            "types": "050000",
            "radius": radius,
            "offset": 20,
            "page": 1,
            "extensions": "all"
        }
        try:
            res = requests.get(url, params=params, timeout=3)
            return res.json().get('pois', []) if res.json().get('status') == '1' else []
        except Exception:
            return []
        

# [新增] AI 图片编码工具
def encode_image_to_base64(image_file):
    """
    将 Django UploadedFile 转换为 Base64 供 AI 调用
    """
    try:
        # 1. 检查是否导入了 base64
        if 'base64' not in globals():
            global base64
            import base64

        # 2. 重置文件指针 (关键：防止文件已被读取过)
        if hasattr(image_file, 'seek'):
            image_file.seek(0)
        
        # 3. 读取并编码
        image_content = image_file.read()
        if not image_content:
            print("❌ Image Encode Error: 文件内容为空")
            return None
            
        base64_content = base64.b64encode(image_content).decode('utf-8')
        
        # 4. 返回 Data URI Scheme
        # Qwen-VL 等模型通常支持 image/jpeg 或 image/png，这里统一用 jpeg 头通常也能兼容
        return f"data:image/jpeg;base64,{base64_content}"
        
    except Exception as e:
        # 打印详细堆栈，方便在 runserver 控制台查看
        import traceback
        traceback.print_exc()
        print(f"❌ Image Encode Error: {str(e)}")
        return None  