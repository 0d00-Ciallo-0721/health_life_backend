### 📄 文件: apps/aiservice/services.py
from openai import OpenAI
import json
import os
from .utils import encode_image_to_base64

# 建议放入 settings.py 或 .env，这里暂时硬编码方便你测试
API_KEY = "sk-pqovdrehlnwxfmhgmhgifwaaxreddhemoaxmecxbhexgtbuf"
BASE_URL = "https://api.siliconflow.cn/v1"
# 使用 Qwen3-VL 思考版
MODEL_NAME = "Qwen/Qwen3-VL-235B-A22B-Thinking" 

class AIService:
    client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

    @staticmethod
    def _clean_json_response(content):
        """清洗模型返回的 Markdown 代码块，提取纯 JSON"""
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]
        return content.strip()

    @staticmethod
    def recognize_food(image_file):
        """
        [功能 1] 拍图识热量
        """
        base64_image = encode_image_to_base64(image_file)
        if not base64_image:
            return {"error": "图片处理失败"}

        system_prompt = """
        你是一个专业的营养师和食物分析AI。
        请识别图片中的食物，并估算其热量和营养成分。
        必须严格按照 JSON 格式返回，不要包含任何思考过程或额外文字。
        JSON 格式要求:
        {
            "food_name": "食物名称",
            "calories": 整数(千卡),
            "nutrition": {
                "carbohydrates": 整数(克),
                "protein": 整数(克),
                "fat": 整数(克)
            },
            "description": "简短的营养评价(30字以内)"
        }
        如果无法识别食物，返回 {"error": "无法识别"}。
        """

        try:
            response = AIService.client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": [
                        {"type": "text", "text": "请分析这张图片中的食物。"},
                        {"type": "image_url", "image_url": {"url": base64_image}}
                    ]}
                ],
                temperature=0.1, # 低温度保证格式稳定
                max_tokens=1024
            )
            
            raw_content = response.choices[0].message.content
            print(f"AI Raw Response: {raw_content}") # Debug用
            
            json_str = AIService._clean_json_response(raw_content)
            return json.loads(json_str)

        except Exception as e:
            print(f"AI Service Error: {e}")
            return {"error": "AI 服务暂时不可用"}

    @staticmethod
    def get_nutrition_advice(user_profile, today_intake, today_calories):
        """
        [功能 2] AI 营养师建议
        """
        # 1. 构建上下文
        goal_text = {"lose": "减脂", "gain": "增肌", "maintain": "保持健康"}.get(user_profile.goal_type, "健康")
        
        intake_desc = ""
        if not today_intake:
            intake_desc = "用户今天还没有记录任何饮食。"
        else:
            intake_desc = "用户今天吃了: " + ", ".join([f"{log.food_name}({log.calories}kcal)" for log in today_intake])

        # 2. 构建 Prompt
        system_prompt = f"""
        你是一位贴心的私人AI营养师。
        用户信息:
        - 目标: {goal_text}
        - 每日热量预算: {user_profile.daily_kcal_limit} kcal
        - 今日已摄入: {today_calories} kcal
        
        今日饮食记录:
        {intake_desc}
        
        请根据以上信息，给出一段专业的饮食建议。
        要求:
        1. 语气亲切、鼓励为主。
        2. 如果摄入过低，提醒按时吃饭；如果超标，建议如何补救（如运动）。
        3. 针对 {goal_text} 目标给出具体建议（如“晚餐建议多吃蛋白质”）。
        4. 字数控制在 150 字以内。
        """

        try:
            response = AIService.client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": "你是有用的营养助手。"},
                    {"role": "user", "content": system_prompt}
                ],
                temperature=0.7, # 稍微高一点，让回复更自然
                max_tokens=1024,
                # enable_thinking=True # 默认就是True，不需要显式设置
            )
            
            return response.choices[0].message.content

        except Exception as e:
            print(f"AI Advice Error: {e}")
            return "AI 营养师正在休息，请稍后再试。"