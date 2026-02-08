from openai import OpenAI
import json
from django.conf import settings
from apps.common.utils import encode_image_to_base64

class AIService:
    _client = None

    @classmethod
    def get_client(cls):
        if not cls._client:
            cls._client = OpenAI(
                api_key=settings.SILICONFLOW_API_KEY,
                base_url=settings.SILICONFLOW_BASE_URL
            )
        return cls._client

    @staticmethod
    def _clean_json_response(content):
        try:
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            return content.strip()
        except IndexError:
            return content

    @staticmethod
    def recognize_food(image_file):
        """
        [功能 1] 拍图识热量 (接入 Qwen-VL)
        """
        # 1. 尝试编码
        try:
            base64_image = encode_image_to_base64(image_file)
        except Exception as e:
            return {"error": f"图片编码异常: {str(e)}"}

        if not base64_image:
            return {"error": "图片处理失败(base64生成为空)，请检查服务端控制台日志"}

        # 2. 准备 Prompt
        system_prompt = """
        你是一个专业的营养师和食物分析AI。
        请识别图片中的食物，并估算其热量和营养成分。
        **必须严格返回纯 JSON 格式**，不要包含任何思考过程或额外文字。
        JSON 格式:
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
        如果无法识别，返回 {"error": "无法识别"}。
        """

        try:
            client = AIService.get_client()
            response = client.chat.completions.create(
                model=settings.SILICONFLOW_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": [
                        {"type": "text", "text": "分析这张图片"},
                        {"type": "image_url", "image_url": {"url": base64_image}}
                    ]}
                ],
                temperature=0.1,
                max_tokens=512
            )
            
            raw_content = response.choices[0].message.content
            # print(f"🤖 AI Raw: {raw_content}") # Debug
            
            json_str = AIService._clean_json_response(raw_content)
            return json.loads(json_str)

        except json.JSONDecodeError:
            return {"error": "AI返回非JSON格式", "raw": raw_content}
        except Exception as e:
            print(f"❌ AI Service Error: {e}")
            return {"error": f"AI服务调用失败: {str(e)}"}

    @staticmethod
    def get_nutrition_advice(profile, today_intake_logs, total_calories):
        """
        [功能 2] AI 营养师建议
        """
        # 1. 数据准备
        goal_map = {"lose": "减脂", "gain": "增肌", "maintain": "保持健康"}
        goal_text = goal_map.get(profile.goal_type, "健康")
        limit = profile.daily_kcal_limit or 2000
        
        intake_desc = "无记录"
        if today_intake_logs:
            # 简化日志，减少 Token 消耗
            intake_desc = ", ".join([f"{log.food_name}({log.calories})" for log in today_intake_logs])

        # 2. 构建 Prompt
        prompt = f"""
        我是你的用户。
        我的档案: 目标[{goal_text}], 预算[{limit}kcal]。
        今日摄入: 总热量[{total_calories}kcal]。
        吃了这些: {intake_desc}。
        
        请作为私人营养师给出建议。
        要求:
        1. 语气亲切。
        2. 结合目标点评今日饮食。
        3. 给出1条具体的补救或优化建议。
        4. 100字以内。
        """

        try:
            client = AIService.get_client()
            response = client.chat.completions.create(
                model=settings.SILICONFLOW_MODEL, # 纯文本任务也可以用 VL 模型，或者换 Qwen2.5-7B
                messages=[
                    {"role": "system", "content": "你是有用的营养助手。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=256
            )
            return response.choices[0].message.content

        except Exception as e:
            print(f"❌ AI Advice Error: {e}")
            return "AI 营养师正在思考人生，请稍后再试。"