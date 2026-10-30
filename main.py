import os
from fastapi import FastAPI, HTTPException, Form
from pydantic import BaseModel
from typing import List
from playwright.sync_api import sync_playwright

app = FastAPI(title="E-Kurier L4H2 Dynamic Agent", version="0.4.1")

EKURIER_USER = os.getenv("EKURIER_USER", "asmaa10.logistik@gmail.com")
EKURIER_PASS = os.getenv("EKURIER_PASS", "kP4100UY")

cached_cookies = None

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
    return {"message": "E-Kurier Dynamic Agent is running successfully!"}

def get_logged_in_page(browser):
    global cached_cookies
    context = browser.new_context(ignore_https_errors=True)
    
    # محاولة استخدام الجلسة المحفوظة مسبقاً إن وجدت
    if cached_cookies:
        context.add_cookies(cached_cookies)
        page = context.new_page()
        page.goto("https://panel.e-kurier.com.pl/", timeout=45000)
        if "login" not in page.url:
            return context, page

    # تسجيل الدخول في حال عدم وجود جلسة
    page = context.new_page()
    page.goto("https://panel.e-kurier.com.pl/login", timeout=60000)
    
    # انتظار تحميل العناصر واختيار أول حقلين إدخال بغض النظر عن أسمائها
    page.wait_for_selector("input", timeout=15000)
    inputs = page.query_selector_all("input")
    
    if len(inputs) >= 2:
        # الحقل الأول للبريد الإلكتروني والثاني كلمة المرور
        inputs[0].fill(EKURIER_USER)
        inputs[1].fill(EKURIER_PASS)
    else:
        raise Exception("لم يتم العثور على حقول تسجيل الدخول المطلوبة في الصفحة.")
    
    # البحث عن زر الإرسال أو الضغط على مفتاح Enter
    submit_btn = page.locator("button[type='submit'], input[type='submit'], button").first
    submit_btn.click()
    
    page.wait_for_load_state("networkidle", timeout=30000)
    
    # حفظ الكوكيز للجلسات القادمة
    cached_cookies = context.cookies()
    return context, page

@app.get("/api/loads", response_model=LoadsResponse)
def get_live_filtered_loads():
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage"]
            )
            
            context, page = get_logged_in_page(browser)
            
            live_loads = [
                LoadItem(origin="[تم تسجيل الدخول بنجاح عبر الطريقة الديناميكية]", destination="جاهز لسحب الجداول", weight="---", vehicle_match="Fiat Ducato L4H2")
            ]
            
            browser.close()
            
            return LoadsResponse(
                status="success_dynamic_login",
                vehicle="Fiat Ducato L4H2",
                loads_count=len(live_loads),
                loads=live_loads
            )
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Dynamic Login Error: {str(e)}")

@app.post("/api/temporary-select-load")
def temporary_select_load(load_id: int = Form(...)):
    return {
        "status": "test_simulation_success",
        "selected_load_id": load_id,
        "message": f"🧪 [وضع تجريبي آمن]: تم استلام طلبك للحمولة رقم ({load_id}) بنجاح، ولن يتم إجراء أي حجز حقيقي على الموقع حالياً."
    }
