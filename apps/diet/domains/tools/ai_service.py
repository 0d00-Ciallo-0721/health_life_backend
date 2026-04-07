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
                        # [核心修改]: 补全标准的 Data URI Base64 前缀，修复大模型接口因解析图片失败导致的 500 崩溃
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
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
        


    @staticmethod
    def generate_real_time_advice(context):
        prompt = f"""
        作为专业AI私人营养师，请根据用户的当前上下文提供一条实时饮食或健康建议。
        用户上下文信息：{context}
        要求：
        1. 语气亲切、专业、具有鼓励性。
        2. 简明扼要，控制在50字左右，直接给出结论。
        """
        try:
            client = AIService.get_client()
            response = client.chat.completions.create(
                model=settings.SILICONFLOW_MODEL,
                messages=[
                    {"role": "system", "content": "你是一位专业的健康和营养顾问。"},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=100
            )
            return {"advice": response.choices[0].message.content.strip()}
        except Exception as e:
            return {"error": f"实时建议生成失败: {str(e)}"}

    # [新增] AI 智能问答 (支持多轮上下文拼接)
    @staticmethod
    def chat_with_ai(question, context_messages=None):
        if context_messages is None:
            context_messages = []
            
        # 1. 植入系统基础人设
        messages = [{"role": "system", "content": "你是一位专业的私人营养师，请为用户解答健康、饮食和运动方面的问题。"}]
        
        # 2. 追加历史上下文记录 (需前端传入 [{"role": "user/assistant", "content": "..."}] 格式)
        messages.extend(context_messages)
        
        # 3. 追加当前用户的最新提问
        messages.append({"role": "user", "content": question})

        try:
            client = AIService.get_client()
            response = client.chat.completions.create(
                model=settings.SILICONFLOW_MODEL,
                messages=messages,
                max_tokens=800
            )
            return {"answer": response.choices[0].message.content.strip()}
        except Exception as e:
            return {"error": f"AI问答交互失败: {str(e)}"}        
        
    # [新增] AI 智能问答 (支持 Server-Sent Events 流式输出)
    @staticmethod
    def chat_with_ai_stream(question, context_messages=None):
        if context_messages is None:
            context_messages = []
            
        messages = [{"role": "system", "content": "你是一位专业的私人营养师，请为用户解答健康、饮食和运动方面的问题。"}]
        messages.extend(context_messages)
        messages.append({"role": "user", "content": question})

        try:
            client = AIService.get_client()
            response = client.chat.completions.create(
                model=settings.SILICONFLOW_MODEL,
                messages=messages,
                max_tokens=800,
                stream=True  # [核心修改] 开启流式响应
            )
            
            for chunk in response:
                if chunk.choices and len(chunk.choices) > 0:
                    delta_content = chunk.choices[0].delta.content
                    if delta_content:
                        # 构造前端约定的 JSON 结构并转为 SSE 格式
                        data_str = json.dumps({"delta": delta_content}, ensure_ascii=False)
                        yield f"data: {data_str}\n\n"
            
            # 流式传输结束标识
            yield "data: [DONE]\n\n"
            
        except Exception as e:
            # 捕获异常也需以 SSE 格式通知前端
            error_str = json.dumps({"error": f"AI问答交互失败: {str(e)}"}, ensure_ascii=False)
            yield f"data: {error_str}\n\n"

    # [新增] 食材智能识别 (专门用于冰箱录入)
    @staticmethod
    def recognize_ingredient(image_file):
        """
        识别基础食材并返回适合存入冰箱的结构化数据
        """
        try:
            base64_image = encode_image_to_base64(image_file)
        except Exception as e:
            return {"error": f"图片编码异常: {str(e)}"}

        if not base64_image:
            return {"error": "图片处理失败(base64生成为空)"}

        prompt = """
        作为专业食材识别AI，请识别图片中的主要生鲜食材。
        请只返回合法的JSON格式，不要有多余的文字、Markdown标记或解释。
        
        JSON返回结构必须如下：
        {
            "name": "食材名称(如西红柿、牛肉)",
            "category": "食材分类(只能从以下枚举中选一：vegetable, fruit, meat, seafood, dairy, grain, seasoning, other)",
            "amount_unit": "推荐的计量单位(如：个、克、升、把、条)"
        }
        """

        try:
            client = AIService.get_client()
            response = client.chat.completions.create(
                model=settings.SILICONFLOW_MODEL,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                        ]
                    }
                ],
                max_tokens=300
            )
            content = response.choices[0].message.content
            cleaned = AIService._clean_json_response(content)
            return json.loads(cleaned)
        except json.JSONDecodeError:
            return {"error": "AI返回的数据格式无法解析"}
        except Exception as e:
            return {"error": f"食材识别接口调用失败: {str(e)}"}

    # [新增] 健康预警生成
    @staticmethod
    def generate_health_warnings(profile, recent_logs_summary):
        """
        根据用户最近饮食与档案，生成健康预警
        recent_logs_summary: 汇总的近期饮食数据字符串，用于 prompt 注入
        """
        prompt = f"""
        作为专业AI营养师，请基于以下用户近期（近3天）的饮食情况，发现其中的不健康趋势，并给出1到2条预警。
        如果没有大问题，可以不返回预警或返回一条温和的建议。
        
        用户身体档案：目标【{getattr(profile, 'goal_type', '健康')}】，每日目标热量【{getattr(profile, 'daily_kcal_limit', 2000)}】大卡
        近期饮食总结：
        {recent_logs_summary}
        
        必须严格按照JSON数组格式返回，格式如下：
        [
            {{
                "id": 1,
                "title": "预警短标题(如:碳水连续超标)",
                "desc": "详细的预警或建议说明",
                "level": "warning" 或 "danger" 或 "info"
            }}
        ]
        """
        
        try:
            client = AIService.get_client()
            response = client.chat.completions.create(
                model=settings.SILICONFLOW_MODEL,
                messages=[
                    {"role": "system", "content": "你是一位敏锐的临床营养师。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=500
            )
            content = response.choices[0].message.content
            cleaned = AIService._clean_json_response(content)
            return json.loads(cleaned)
        except Exception as e:
            # 降级处理
            return []

    # [新增] 环保低碳建议生成
    @staticmethod
    def generate_carbon_suggestions(recent_logs_summary):
        """
        生成环保建议
        """
        prompt = f"""
        作为提倡低碳环保的公共营养师，请根据用户的饮食情况给出2条环保低碳饮食建议。
        例如：如肉类过多可建议多食植物蛋白，如餐食量大可建议光盘行动。
        
        近期饮食总结：
        {recent_logs_summary}
        
        必须返回纯JSON数组，格式如下：
        [
            {{
                "title": "建议标题",
                "desc": "具体说明"
            }}
        ]
        """
        try:
            client = AIService.get_client()
            response = client.chat.completions.create(
                model=settings.SILICONFLOW_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.5,
                max_tokens=400
            )
            content = response.choices[0].message.content
            cleaned = AIService._clean_json_response(content)
            res = json.loads(cleaned)
            if not isinstance(res, list) or len(res) == 0:
                raise ValueError("Format error")
            return res
        except Exception:
            return [{"title": "多吃植物蛋白", "desc": "饮食中增加豆制品不仅健康，更能大幅减少碳足迹。"}, {"title": "光盘行动", "desc": "减少厨余垃圾是降低个人碳排放的最直接方式。"}]

    # [新增] 补救方案智能分诊
    @staticmethod
    def triage_symptoms(action_text, custom_keywords, available_remedies_json):
        """
        传入用户自然语言描述的症状与关键词，以及数据库支持的 remedies，让 AI 返回匹配的 ID
        """
        # 组合用户多维度的诉求
        symptoms_parts = []
        if action_text:
            symptoms_parts.append(f"用户近期行为描述：{action_text}")
        if custom_keywords and isinstance(custom_keywords, list) and len(custom_keywords) > 0:
            symptoms_parts.append(f"用户补充关键词/体征：{', '.join(custom_keywords)}")
            
        symptoms_text = "\n".join(symptoms_parts) if symptoms_parts else "身体不适，需要饮食补救。"

        prompt = f"""
        你是一个专业的临床与营养学健康顾问。用户正在寻找缓解身体不适的饮食补救方案。
        用户的具体诉求是：
        "{symptoms_text}"

        数据库中目前可用的补救方案列表如下（JSON）：
        {available_remedies_json}

        请选择 1 至 3 个最对症的方案，并给出推荐理由。
        严格返回纯JSON对象，格式要求如下：
        {{
            "matched_symptoms": ["提取出的核心症状1(简短)", "核心症状2"],
            "recommended_solutions": [
                {{
                    "remedy_id": 对应方案的整数ID,
                    "reason": "你推荐这个方案的医学或营养学解释（简短，50字内，语气专业且具有同理心）"
                }}
            ]
        }}
        """
        
        try:
            client = AIService.get_client()
            response = client.chat.completions.create(
                model=settings.SILICONFLOW_MODEL,
                messages=[
                    {"role": "system", "content": "你是一位敏锐且专业的健康分诊AI。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3, # 降低发散，提高匹配准确度
                max_tokens=600
            )
            content = response.choices[0].message.content
            cleaned = AIService._clean_json_response(content)
            return json.loads(cleaned)
        except Exception as e:
            print(f"❌ AI Triage Error: {e}")
            # 返回兼容格式的外壳，防止前端崩溃
            return {"matched_symptoms": ["系统判断异常降级"], "recommended_solutions": []}