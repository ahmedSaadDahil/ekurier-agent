import os
from fastapi import FastAPI, HTTPException
import requests
from bs4 import BeautifulSoup

app = FastAPI(title="E-Kurier L4H2 Secure Scraper Agent")

# قراءة بيانات الدخول من متغيرات النظام الآمنة (التي سنضبطها في السحابة لاحقاً)
EKURIER_USER = os.getenv("EKURIER_USER", "user_placeholder")
EKURIER_PASS = os.getenv("EKURIER_PASS", "pass_placeholder")

@app.get("/api/loads")
def get_filtered_loads():
    session = requests.Session()
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        # الخطوة 1: محاولة تسجيل الدخول (سنتأكد من رابط الـ Login الفعلي للموقع لاحقاً)
        login_url = "https://e-kurier.net/login" # مثال لصفحة الدخول
        login_data = {
            "username": EKURIER_USER,
            "password": EKURIER_PASS
        }
        
        # إرسال طلب تسجيل الدخول وحفظ الجلسة
        # response_login = session.post(login_url, data=login_data, headers=headers, timeout=10)
        
        # الخطوة 2: جلب صفحة الحمولات بعد تسجيل الدخول
        loads_url = "https://e-kurier.net/"
        response = session.get(loads_url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            raise HTTPException(status_code=500, detail="فشل الاتصال بموقع الشحنات")

        soup = BeautifulSoup(response.text, 'html.parser')
        
        # قائمة لتخزين الحمولات المفلترة لسيارة L4H2
        filtered_loads = []
        
        # (ملاحظة: هنا سنقوم بربط محددات الـ HTML الدقيقة لجدول الشحنات في الموقع واستبعاد الفئات الكبيرة LKW)
        # كنموذج تجريبي أولي يضمن عمل الـ API بنجاح:
        dummy_loads = [
            {"origin": "برلين", "destination": "ميونخ", "weight": "650 كيلو", "vehicle_match": "Fiat Ducato L4H2 مناسب جداً"},
            {"origin": "كولونيا", "destination": "فرانكفورت", "weight": "900 كيلو", "vehicle_match": "Fiat Ducato L4H2 مناسب ضمن الحد الأقصى"}
        ]

        return {
            "status": "success",
            "vehicle": "Fiat Ducato L4H2",
            "loads_count": len(dummy_loads),
            "loads": dummy_loads
        }

    except Exception as e:
        return {
            "status": "error",
            "loads": [],
            "message": str(e)
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)