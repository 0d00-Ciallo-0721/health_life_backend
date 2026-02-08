### 📄 文件: apps/aiservice/utils.py
import base64

def encode_image_to_base64(image_file):
    """
    将 Django 的 UploadedFile 对象转换为 Base64 字符串
    适配 OpenAI/SiliconFlow 的 image_url 格式
    """
    try:
        # 读取文件内容
        image_content = image_file.read()
        # 编码为 base64
        base64_content = base64.b64encode(image_content).decode('utf-8')
        # 拼接前缀 (假设是 jpeg/png，这里做通用处理，模型通常能容错)
        return f"data:image/jpeg;base64,{base64_content}"
    except Exception as e:
        print(f"Image Encode Error: {e}")
        return None