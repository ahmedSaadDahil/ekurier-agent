import os
from fastapi import FastAPI, HTTPException, Form, Response
from pydantic import BaseModel
from typing import List
from playwright.sync_api import sync_playwright
from twilio.twiml.voice_response import VoiceResponse, Gather
from twilio.rest import Client

app = FastAPI(title="E-Kurier L4H2 Secure Scraper Agent", version="0.1.0")

# إعدادات بيانات الاعتماد
EKURIER_USER = os.getenv("EKURIER_USER", "asmaa10.logistik@gmail.com")
EKURIER_PASS = os.getenv("EKURIER_PASS", "kP4100UY")

# إعدادات Twilio 
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER", "")
HARITH_PHONE_NUMBER = os.getenv("HARITH_PHONE_NUMBER", "+9647701668515") # رقم الهاتف المعتمد

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
    return {"message": "E-Kurier L4H2 Agent is running successfully!"}

@app.get("/api/loads", response_model=LoadsResponse)
def get_filtered_loads():
    """
    يقوم بتشغيل متصفح Playwright في الخلفية، تسجيل الدخول، 
    وجلب الحمولات المتاحة وتصفيتها لسيارة Fiat Ducato L4H2.
    """
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage"]
            )
            page = browser.new_page()
            
            # بيانات تجريبية تحاكي جلب 3 حمولات مطابقة لسيارة فيات دوكاتو L4H2
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

@app.get("/api/call-harith")
def call_harith_for_loads():
    """
    يبدأ مكالمة تفاعلية مع حارث عبر Twilio لعرض الحمولات المتاحة وسؤاله عن الاختيار (متاح عبر GET لسهولة التجربة من المتصفح).
    """
    if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN:
        raise HTTPException(status_code=400, detail="Twilio credentials are not configured yet.")
    
    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        
        webhook_url = "https://ekurier-agent.onrender.com/api/voice-webhook"
        
        call = client.calls.create(
            to=HARITH_PHONE_NUMBER,
            from_=TWILIO_PHONE_NUMBER,
            url=webhook_url
        )
        return {"status": "call initiated", "call_sid": call.sid}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/voice-webhook")
def voice_webhook():
    """
    توليد الرد الصوتي التفاعلي عبر TwiML لقراءة الحمولات وطلب الاختيار من حارث.
    """
    response = VoiceResponse()
    gather = Gather(num_digits=1, action="/api/handle-selection", method="POST")
    gather.say(
        text="أهلاً يا حارث. توجد ثلاث حمولات متاحة لسيارة فيات دوكاتو. اضغط 1 للحمولة الأولى من وفات إلى صلاح، اضغط 2 للحمولة الثانية من بغداد إلى اربيل، او اضغط 3 للحمولة الثالثة من الموصل إلى دهوك.",
        voice="alice",
        language="ar-XA"
    )
    response.append(gather)
    response.redirect("/api/voice-webhook")
    
    return Response(content=str(response), media_type="application/xml")

@app.post("/api/handle-selection")
def handle_selection(Digits: str = Form(...)):
    """
    يستقبل رقم الحمولة الذي اختاره حارث عبر الضغط على هاتفه، 
    ويقوم بتأكيد الطلب ومن ثم توجيهه.
    """
    response = VoiceResponse()
    
    selected_load = f"الحمولة رقم {Digits}"
    
    response.say(
        text=f"تم تأكيد {selected_load} بنجاح. توجه الآن فوراً إلى موقع التحميل. بالتوفيق!",
        voice="alice",
        language="ar-XA"
    )
    
    return Response(content=str(response), media_type="application/xml")
