import os
from fastapi import FastAPI, HTTPException, Form
from pydantic import BaseModel
from typing import List
from playwright.sync_api import sync_playwright

app = FastAPI(title="E-Kurier L4H2 Live Scraper & Test Agent", version="0.3.3")

EKURIER_USER = os.getenv("EKURIER_USER", "asmaa10.logistik@gmail.com")
EKURIER_PASS = os.getenv("EKURIER_PASS", "kP4100UY")

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
    return {"message": "E-Kurier Live Agent is running with robust login selectors!"}

@app.get("/api/loads", response_model=LoadsResponse)
def get_live_filtered_loads():
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage"]
            )
            context = browser.new_context(ignore_https_errors=True)
            page = context.new_page()
            
            # الانتقال إلى صفحة تسجيل الدخول
            page.goto("https://panel.e-kurier.com.pl/login", timeout=60000)
            
            # محاولة إيجاد حقل البريد الإلكتروني بعدة طرق مرنة (بواسطة type أو name أو placeholder)
            email_input = page.locator("input[type='email'], input[name='email'], input[id*='email']").first
            email_input.wait_for(state="visible", timeout=15000)
            email_input.fill(EKURIER_USER)
            
            # إيجاد حقل كلمة المرور بشكل مرن
            password_input = page.locator("input[type='password'], input[name='password'], input[id*='password']").first
            password_input.fill(EKURIER_PASS)
            
            # الضغط على زر تسجيل الدخول
            submit_btn = page.locator("button[type='submit'], input[type='submit'], button:has-text('Log in'), button:has-text('Zaloguj')").first
            submit_btn.click()
            
            page.wait_for_load_state("networkidle", timeout=30000)
            
            # التقاط حالة النجاح بعد تسجيل الدخول
            live_loads = [
                LoadItem(origin="[تم تسجيل الدخول بنجاح]", destination="جاري سحب الجداول الحية", weight="---", vehicle_match="Fiat Ducato L4H2")
            ]
            
            browser.close()
            
            return LoadsResponse(
                status="success_logged_in",
                vehicle="Fiat Ducato L4H2",
                loads_count=len(live_loads),
                loads=live_loads
            )
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Playwright Login Error: {str(e)}")

@app.post("/api/temporary-select-load")
def temporary_select_load(load_id: int = Form(...)):
    return {
        "status": "test_simulation_success",
        "selected_load_id": load_id,
        "message": f"🧪 [وضع تجريبي آمن]: تم استلام طلبك للحمولة رقم ({load_id}) بنجاح، ولن يتم إجراء أي حجز حقيقي على الموقع حالياً."
    }
