import requests
from django.conf import settings
from rest_framework.exceptions import AuthenticationFailed

class WeChatService:
    @staticmethod
    def get_openid(code):
        """
        通过前端传来的 code 换取 openid
        参考: https://developers.weixin.qq.com/miniprogram/dev/api-backend/open-api/login/auth.code2Session.html
        """
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

        # 返回 openid 和 session_key (session_key 可存入 Redis 用于解密敏感数据)
        return {
            "openid": data.get("openid"),
            "session_key": data.get("session_key")
        }