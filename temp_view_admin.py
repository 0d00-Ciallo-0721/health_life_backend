import os, sqlite3, json

db_path = r'C:\Users\zlj\Desktop\health_life_backend\health_life_backend_dj\db.sqlite3'
if not os.path.exists(db_path):
    print('❌ 数据库文件不存在:', db_path)
else:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    # 选取管理员或超级管理员账户
    cur.execute("SELECT id, username, is_staff, is_superuser, password FROM auth_user WHERE is_staff=1 OR is_superuser=1")
    rows = cur.fetchall()
    if rows:
        print('🔐 管理员账户信息:')
        for r in rows:
            uid, username, is_staff, is_superuser, pwd_hash = r
            print(f'  id={uid}, username={username}, staff={bool(is_staff)}, super={bool(is_superuser)}')
            print(f'  password_hash={pwd_hash}')
    else:
        print('⚠️ 未找到管理员账户')
    conn.close()
