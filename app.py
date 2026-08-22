import os
import json
from fastapi import FastAPI, Request, HTTPException
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import google.generativeai as genai
import gspread
from google.oauth2.service_account import Credentials

app = FastAPI()

# ดึงค่า Environment Variables
LINE_ACCESS_TOKEN = os.environ.get("LINE_ACCESS_TOKEN")
LINE_SECRET = os.environ.get("LINE_SECRET")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

line_bot_api = LineBotApi(LINE_ACCESS_TOKEN)
handler = WebhookHandler(LINE_SECRET)
genai.configure(api_key=GEMINI_API_KEY)

# เชื่อมต่อ Google Sheets ผ่าน credentials.json
scopes = ["https://www.googleapis.com/auth/spreadsheets"]
creds = Credentials.from_service_account_file("credentials.json", scopes=scopes)
gc = gspread.authorize(creds)

@app.get("/")
def read_root():
    return {"status": "ok"}

@app.post("/callback")
async def callback(request: Request):
    signature = request.headers.get("X-Line-Signature", "")
    body = await request.body()
    try:
        handler.handle(body.decode("utf-8"), signature)
    except InvalidSignatureError:
        raise HTTPException(status_code=400, detail="Invalid signature")
    return "OK"

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_text = event.message.text
    
    # ส่งข้อความไปให้ Gemini สรุปข้อมูล
    model = genai.GenerativeModel('gemini-1.5-flash')
    prompt = f"สกัดข้อมูลจากข้อความรายงานนี้เป็น JSON มี key คือ 'date_time', 'location', 'task', 'status': {user_text}"
    
    try:
        response = model.generate_content(prompt)
        # บันทึกลง Google Sheets
        sh = gc.open("LINE_Work_Reports").sheet1
        sh.append_row([user_text, response.text])
        reply_msg = f"บันทึกข้อมูลเรียบร้อยแล้วครับ:\n{response.text}"
    except Exception as e:
        reply_msg = f"บันทึกข้อมูลเรียบร้อย (Raw text): {user_text}"
        try:
            sh = gc.open("LINE_Work_Reports").sheet1
            sh.append_row([user_text])
        except:
            pass

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply_msg)
    )
