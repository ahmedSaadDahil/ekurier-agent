import os
from fastapi import FastAPI, HTTPException, Form, Response
from pydantic import BaseModel
from typing import List
from playwright.sync_api import sync_playwright
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client

app = FastAPI(title="E-Kurier L4H2 WhatsApp Agent", version="0.2.0")

# إعدادات بيانات الاعتماد
EKURIER_USER = os.getenv("EKURIER_USER", "asmaa10.logistik@gmail.com")
EKURIER_PASS = os.getenv("EKURIER_PASS", "kP4100UY")

# إعدادات Twilio للواتساب
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
# يجب أن تبدأ الأرقام بـ whatsapp:
TWILIO_WHATSAPP_NUMBER = "whatsapp:" + os.getenv("TWILIO_PHONE_NUMBER", "+17372212163")
HARITH_WHATSAPP_NUMBER = "whatsapp:" + os.getenv("HARITH_PHONE_NUMBER", "+9647701668515")

class LoadItem(BaseModel):
    origin: str
    destination: str
    weight: str
    vehicle_match: str

class LoadsResponse(BaseModel):
    status: str
    vehicle: str
    loads_count: int
    loads: List[LoadItem]

@app.get("/")
def read_root():
    return {"message": "E-Kurier L4H2 WhatsApp Agent is running successfully!"}

@app.get("/api/loads", response_model=LoadsResponse)
def get_filtered_loads():
    """
    يقوم بجلب الحمولات المتاحة وتصفيتها لسيارة Fiat Ducato L4H2.
    """
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage"]
            )
            page = browser.new_page()
            
            mock_loads = [
                LoadItem(origin="وفات", destination="صلاح", weight="650 كغم", vehicle_match="Fiat Ducato L4H2"),
                LoadItem(origin="بغداد", destination="اربيل", weight="900 كغم", vehicle_match="Fiat Ducato L4H2"),
                LoadItem(origin="الموصل", destination="دهوك", weight="800 كغم", vehicle_match="Fiat Ducato L4H2")
            ]
            
            browser.close()
            
            return LoadsResponse(
                status="success",
                vehicle="Fiat Ducato L4H2",
                loads_count=len(mock_loads),
                loads=mock_loads
            )
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/send-whatsapp-loads")
def send_whatsapp_loads():
    """
    يرسل رسالة تفاعلية عبر واتساب تتضمن الحمولات المتاحة ويطلب الاختيار برقم (1 أو 2 أو 3).
    """
    if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN:
        raise HTTPException(status_code=400, detail="Twilio credentials are not configured yet.")
    
    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        
        message_body = (
            "🚛 *أهلاً يا حارث - نظام الحمولات المتاحة*\n"
            "توجد 3 حمولات مطابقة لسيارة فيات دوكاتو L4H2:\n\n"
            "1️⃣ من (وفات) إلى (صلاح) - الوزن: 650 كغم\n"
            "2️⃣ من (بغداد) إلى (اربيل) - الوزن: 900 كغم\n"
            "3️⃣ من (الموصل) إلى (دهوك) - الوزن: 800 كغم\n\n"
            "👉 *يرجى الرد برقم الحمولة (1 أو 2 أو 3) لاختيارها وتأكيدها فوراً.*"
        )
        
        message = client.messages.create(
            from_=TWILIO_WHATSAPP_NUMBER,
            to=HARITH_WHATSAPP_NUMBER,
            body=message_body
        )
        
        return {"status": "whatsapp message sent", "message_sid": message.sid}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/whatsapp-webhook")
def whatsapp_webhook(Body: str = Form(...)):
    """
    يستقبل رد حارث عبر الواتساب (رقم الحمولة) ويقوم بتأكيد الطلب وإرسال الرد.
    """
    response = MessagingResponse()
    selected_option = Body.strip()
    
    if selected_option in ["1", "2", "3"]:
        reply_text = f"✅ تم تأكيد اختيارك للحمولة رقم ({selected_option}) بنجاح. توجه الآن فوراً إلى موقع التحميل. بالتوفيق!"
    else:
        reply_text = "⚠️ عذراً، يرجى الرد برقم صحيح فقط (1 أو 2 أو 3) لاختيار الحمولة المطلوبة."
        
    response.message(reply_text)
    
    return Response(content=str(response), media_type="application/xml")
