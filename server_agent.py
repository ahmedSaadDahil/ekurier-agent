import os
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from google import genai

app = Flask(__name__)

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

@app.route("/whatsapp", methods=["POST"])
def whatsapp_webhook():
    incoming_msg = request.form.get("Body", "").strip()
    resp = MessagingResponse()
    reply = resp.message()

    if not incoming_msg:
        reply.body("أهلاً بك يا أبو شهاب")
        return str(resp)

    if not GEMINI_API_KEY:
        reply.body("مفتاح الـ API غير مضبوط")
        return str(resp)

    try:
        # استخدام الحزمة والموديل الرسمي الموثق في جوجل
        client = genai.Client(api_key=GEMINI_API_KEY)
        response = client.interactions.create(
            model="gemini-3.8-flash",
            input=incoming_msg
        )
        
        if response and response.output_text:
            reply.body(response.output_text)
        else:
            reply.body("عذراً، لم أتمكن من صياغة الإجابة.")
            
    except Exception as e:
        reply.body("حدث خطأ في النظام.")

    return str(resp)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
