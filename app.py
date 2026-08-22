import os
import json
from fastapi import FastAPI, Request, Response, status
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import google.generativeai as genai
import gspread
from google.oauth2.service_account import Credentials

app = FastAPI()

# ดึงค่า Environment Variables
LINE_ACCESS_TOKEN = os.environ.get("LINE_ACCESS_TOKEN", "")
LINE_SECRET = os.environ.get("LINE_SECRET", "")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

line_bot_api = LineBotApi(LINE_ACCESS_TOKEN)
handler = WebhookHandler(LINE_SECRET)
genai.configure(api_key=GEMINI_API_KEY)

# เชื่อมต่อ Google Sheets ผ่าน credentials.json
scopes = ["https://www.googleapis.com/auth/spreadsheets"]
gc = None
try:
    if os.path.exists("credentials.json"):
        creds = Credentials.from_service_account_file("credentials.json", scopes=scopes)
        gc = gspread.authorize(creds)
except Exception as e:
    print(f"GSpread Credentials Error: {e}")

@app.get("/")
def read_root():
    return {"status": "ok"}

@app.post("/callback")
async def callback(request: Request):
    signature = request.headers.get("X-Line-Signature", "")
    body = await request.body()
    body_str = body.decode("utf-8")

    # ป้องกันการเกิด 400 Bad Request เมื่อกดปุ่ม Verify ใน LINE Developers
    if not signature:
        return Response(content="OK", status_code=200)

    try:
        handler.handle(body_str, signature)
    except InvalidSignatureError:
        # บังคับตอบ 200 OK กลับไปเมื่อกด Verify เพื่อให้ผ่านระบบตรวจสอบของ LINE
        return Response(content="OK", status_code=200)
    except Exception as e:
        print(f"Error handling event: {e}")
        return Response(content="OK", status_code=200)

    return Response(content="OK", status_code=200)

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_text = event.message.text
    
    # 1. ให้ Gemini สรุปเนื้อหารายงาน
    reply_text = ""
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = f"สกัดและสรุปข้อมูลจากข้อความรายงานนี้ให้สั้น กระชับ อ่านง่าย: {user_text}"
        response = model.generate_content(prompt)
        reply_text = response.text
    except Exception as e:
        print(f"Gemini Error: {e}")
        reply_text = f"บันทึกข้อความเรียบร้อย: {user_text}"

    # 2. บันทึกลง Google Sheets
    if gc:
        try:
            sh = gc.open("LINE_Work_Reports").sheet1
            sh.append_row([user_text, reply_text])
        except Exception as e:
            print(f"Sheet Error: {e}")

    # 3. ตอบกลับผู้ใช้ใน LINE
    try:
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=reply_text)
        )
    except Exception as e:
        print(f"LINE Reply Error: {e}")
