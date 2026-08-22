import os
from fastapi import FastAPI, Request, Response
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

# ตั้งค่า Gemini API
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# ตั้งค่า Google Sheets จากไฟล์ credentials.json โดยตรง
scopes = ["https://www.googleapis.com/auth/spreadsheets"]
gc = None

if os.path.exists("credentials.json"):
    try:
        creds = Credentials.from_service_account_file("credentials.json", scopes=scopes)
        gc = gspread.authorize(creds)
        print("Google Sheets authorization successful via credentials.json!")
    except Exception as e:
        print(f"GSpread File Error: {e}")
else:
    print("Warning: credentials.json file not found in repository.")

@app.get("/")
def read_root():
    return {"status": "ok"}

@app.post("/callback")
async def callback(request: Request):
    signature = request.headers.get("X-Line-Signature", "")
    body = await request.body()
    body_str = body.decode("utf-8")

    if not signature:
        return Response(content="OK", status_code=200)

    try:
        handler.handle(body_str, signature)
    except InvalidSignatureError:
        return Response(content="OK", status_code=200)
    except Exception as e:
        print(f"Error handling event: {e}")
        return Response(content="OK", status_code=200)

    return Response(content="OK", status_code=200)

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_text = event.message.text
    
    # 1. ให้ Gemini สรุปข้อความ
    reply_text = ""
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = f"ช่วยสรุปรายงานการทำงานนี้ให้อ่านง่าย กระชับ เป็นหัวข้อชัดเจน:\n{user_text}"
        response = model.generate_content(prompt)
        reply_text = response.text
    except Exception as e:
        print(f"Gemini Error: {e}")
        reply_text = f"ได้รับรายงานเรียบร้อยแล้วครับ:\n{user_text}"

    # 2. บันทึกลง Google Sheet
    if gc:
        try:
            sh = gc.open("LINE_Work_Reports").sheet1
            sh.append_row([user_text, reply_text])
            print("Successfully appended to Google Sheet")
        except Exception as e:
            print(f"Sheet Append Error: {e}")
    else:
        print("Google Sheet not configured.")

    # 3. ตอบกลับใน LINE
    try:
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=reply_text)
        )
    except Exception as e:
        print(f"LINE Reply Error: {e}")
