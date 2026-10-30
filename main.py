import os
import json
from fastapi import FastAPI, HTTPException, Form
from pydantic import BaseModel
from typing import List
from playwright.sync_api import sync_playwright

app = FastAPI(title="E-Kurier Session File Agent", version="0.5.1")

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
    return {"message": "E-Kurier Session File Agent is running successfully!"}

@app.get("/api/loads", response_model=LoadsResponse)
def get_live_filtered_loads():
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-blink-features=AutomationControlled"
                ]
            )
            
            storage_state_path = "session.json"
            context_args = {
                "ignore_https_errors": True,
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                "viewport": {"width": 1920, "height": 1080}
            }
            
            if os.path.exists(storage_state_path):
                context_args["storage_state"] = storage_state_path
            
            context = browser.new_context(**context_args)
            page = context.new_page()
            
            # الانتقال المباشر إلى الموقع مستخدماً الكوكيز المحقونة
            page.goto("https://www.e-kurier.net/", timeout=60000, wait_until="domcontentloaded")
            
            current_url = page.url
            if "login" in current_url or "password" in current_url:
                browser.close()
                raise HTTPException(
                    status_code=400, 
                    detail=f"تنبيه: الجلسة تتطلب مصادقة (رابط الانتقال: {current_url})."
                )
            
            live_loads = [
                LoadItem(origin="[تم حقن session.json ونجح الاتصال]", destination="جاهز لقراءة جدول الحمولات", weight="---", vehicle_match="Fiat Ducato L4H2")
            ]
            
            browser.close()
            
            return LoadsResponse(
                status="success_session_file",
                vehicle="Fiat Ducato L4H2",
                loads_count=len(live_loads),
                loads=live_loads
            )
            
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Session File Error: {str(e)}")

@app.post("/api/temporary-select-load")
def temporary_select_load(load_id: int = Form(...)):
    return {
        "status": "test_simulation_success",
        "selected_load_id": load_id,
        "message": f"🧪 [وضع تجريبي آمن]: تم استلام طلبك للحمولة رقم ({load_id}) بنجاح."
    }
