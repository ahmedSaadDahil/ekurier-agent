import os
from flask import Flask, request, jsonify
from twilio.twiml.messaging_response import MessagingResponse
from google import genai
from google.genai import types

app = Flask(__name__)

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

HARETH_WHATSAPP_NUMBER = "whatsapp:+4917656970147"

@app.route("/whatsapp", methods=["POST"])
def whatsapp_webhook():
    incoming_msg = request.form.get("Body", "").strip()
    sender = request.form.get("From", "")
    resp = MessagingResponse()
    reply = resp.message()

    if not incoming_msg:
        reply.body("أهلاً بك يا أبو شهاب")
        return str(resp)

    if not GEMINI_API_KEY:
        reply.body("مفتاح الـ API غير مضبوط")
        return str(resp)

    if sender == HARETH_WHATSAPP_NUMBER:
        system_instruction = (
            "أنت مساعد نظام نقل مخصص حصرياً لأخيك حارث. مهامك ثابتة ومحصورة في إدارة شحنات وحمولات "
            "سيارة Fiat Ducato (L3H2/L4H2). نطاق أسعار الشحن لديك بين 1.00 إلى 1.30 يورو لكل كيلومتر. "
            "كن دقيقاً، مختصراً، ومباشراً في تفاصيل الحمولات وعمليات الحجز."
        )
    else:
        system_instruction = (
            "أنت مساعد شخصي ذكي وشامل لأحمد (أبو شهاب). يمكنك الإجابة على أي سؤال يطلبه، "
            "سواء في البرمجة، التحليل، الأفكار، أو أي استفسار عام."
        )

    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=incoming_msg,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.7,
            ),
        )
        
        if response and response.text:
            reply.body(response.text)
        else:
            reply.body("عذراً يا أبو شهاب، لم أتمكن من صياغة الإجابة.")
            
    except Exception as e:
        print(f"Error occurred: {str(e)}")
        reply.body("حدث خطأ في الاتصال بالنموذج.")

    return str(resp)

@app.route("/api/loads", methods=["GET"])
def get_hareth_loads():
    try:
        loads_list = [
            {
                "id": 1,
                "origin": "ميونخ (Munich)",
                "destination": "برلين (Berlin)",
                "weight": "1200 كغ",
                "distance_km": 580.0,
                "floor_price": round(580.0 * 1.3 * 1.2, 2),
                "vehicle_match": "Fiat Ducato L4H2"
            },
            {
                "id": 2,
                "origin": "فرانكفورت (Frankfurt)",
                "destination": "هامبورغ (Hamburg)",
                "weight": "950 كغ",
                "distance_km": 490.0,
                "floor_price": round(490.0 * 1.3 * 1.2, 2),
                "vehicle_match": "Fiat Ducato L4H2"
            },
            {
                "id": 3,
                "origin": "شتوتغارت (Stuttgart)",
                "destination": "كولونيا (Cologne)",
                "weight": "1100 كغ",
                "distance_km": 360.0,
                "floor_price": round(360.0 * 1.3 * 1.2, 2),
                "vehicle_match": "Fiat Ducato L4H2"
            }
        ]
        return jsonify({
            "status": "success",
            "driver": "حارث",
            "vehicle": "Fiat Ducato L4H2",
            "loads": loads_list
        }), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/", methods=["GET"])
def home_root():
    return jsonify({"status": "online", "message": "E-Kurier Clean Server Agent is running successfully!"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
