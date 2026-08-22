# ใช้ Credentials แบบกำหนดเวลาเผื่อ (Token expiry/clock skew)
from google.auth.transport import requests

try:
    if GOOGLE_CREDENTIALS:
        clean_creds = GOOGLE_CREDENTIALS.strip().strip("'").strip('"')
        creds_dict = json.loads(clean_creds)
        
        # เพิ่มการกำหนด scopes และ request object เพื่อแก้ปัญหา JWT Signature
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        
        # บังคับต่ออายุ/รีเฟรช Token ทันทีเพื่อป้องกันปัญหาเวลาเซิร์ฟเวอร์ไม่ตรง
        auth_request = requests.Request()
        creds.refresh(auth_request)
        
        gc = gspread.authorize(creds)
        print("Google Sheets authorization successful!")
except Exception as e:
    print(f"GSpread Credentials Error: {e}")
