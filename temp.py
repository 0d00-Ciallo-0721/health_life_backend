import os

path = r'c:\Users\zlj\Desktop\health_life_backend\health_life_admin_frontend\assets\js\api.js'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace(
    "const API_BASE_URL = 'http://192.168.170.105:8000/api/admin/v1';",
    "const API_BASE_URL = (window.APP_CONFIG && window.APP_CONFIG.API_BASE_URL) || 'http://127.0.0.1:8000/api/admin/v1';"
)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
print("api.js updated successfully")
