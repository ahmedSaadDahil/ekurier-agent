import os
import json
import httpx
from bs4:// ... (باقي المكتبات)

# مسار لتسجيل الدخول التلقائي من السيرفر مباشرة وحفظ الجلسة الحقيقية
@app.route("/api/auto-login", methods=["GET", "POST"])
def server_auto_login():
    try:
        username = os.environ.get("EKURIER_USER")
        password = os.environ.get("EKURIER_PASS")
        
        if not username or not password:
            return jsonify({"status": "error", "message": "بيانات الدخول (EKURIER_USER / EKURIER_PASS) غير مضبوطة في متغيرات البيئة لـ Render"}), 400

        login_url = "https://e-kurier.net/portal/login" # أو رابط صفحة إرسال الفورم للـ Login
        
        with httpx.Client(follow_redirects=True, timeout=30.0) as client:
            # 1. جلب صفحة الدخول لأخذ الـ CSRF Tokens أو الكوكيز الأولية
            resp = client.get(login_url)
            
            # 2. إرسال بيانات الدخول (POST)
            # (ملاحظة: حقول الـ form تعتمد على أسماء الحقول في موقعهم مثل email/password أو username/password)
            payload = {
                "email": username,
                "password": password
            }
            login_resp = client.post(login_url, data=payload)
            
            # استخراج الكوكيز الحقيقية الفعالة بعد نجاح الدخول
            active_cookies = [{"name": name, "value": val} for name, val in client.cookies.items()]
            
            if active_cookies:
                session_payload = {"cookies": active_cookies}
                with open("session.json", "w", encoding="utf-8") as f:
                    json.dump(session_payload, f, ensure_ascii=False, indent=4)
                print("✅ [LOGIN] تم تسجيل الدخول وحفظ الكوكيز الحقيقية بنجاح من السيرفر!")
                return jsonify({"status": "success", "message": "تم تسجيل الدخول بنجاح وتحديث الجلسة", "cookies_count": len(active_cookies)}), 200
            else:
                return jsonify({"status": "error", "message": "فشل استخراج الكوكيز بعد محاولة تسجيل الدخول"}), 400

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
