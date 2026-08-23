import os
import re

for f in ['frontend/app.js', 'frontend/analytics.js']:
    with open(f, 'r', encoding='utf-8') as file:
        content = file.read()
    
    # Comment out login redirects
    content = re.sub(r"window\.location\.href\s*=\s*'login\.html';", "// window.location.href = 'login.html';", content)
    content = re.sub(r'window\.location\.href\s*=\s*"login\.html";', '// window.location.href = "login.html";', content)
    
    # Mock token
    content = content.replace("localStorage.getItem('recoverai_token')", "'dummy_token_bypass'")
    
    with open(f, 'w', encoding='utf-8') as file:
        file.write(content)

# Update backend auth to bypass token check
auth_path = 'backend/auth.py'
with open(auth_path, 'r', encoding='utf-8') as file:
    auth_content = file.read()

# Replace get_current_user implementation
new_get_current_user = """async def get_current_user(db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == "admin").first()
    if not user:
        user = User(id=1, username="admin")
    return user
"""
# Find the start of get_current_user
auth_content = re.sub(r"async def get_current_user\(.*?\n(?:    .*\n)*", new_get_current_user, auth_content, flags=re.MULTILINE)

with open(auth_path, 'w', encoding='utf-8') as file:
    file.write(auth_content)
