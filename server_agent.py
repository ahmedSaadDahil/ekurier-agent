import os
from flask import Flask, request
from twilio.rest import Client
from google import genai
from google.genai import types

app = Flask(__name__)

# قراءة إعدادات Twilio من متغيرات البيئة بأمان تام
account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
twilio_client = Client(account_sid, auth_token)

# قراءة مفتاح Gemini تلقائيًا من متغيرات البيئة في Render
ai_client = genai.Client()

MY_WHATSAPP_NUMBER = "whatsapp:+9647701668515"  # رقمك الشخصي
HARETH_WHATSAPP_NUMBER = "whatsapp:+4917656970147" # رقم حارث

@app.route("/whatsapp", methods=["POST"])
def whatsapp_reply():
    incoming_msg = request.form.get('Body', '').strip()
    sender = request.form.get('From', '')
    
    print(f"استلام رسالة من {sender}: {incoming_msg}")
    
    if sender == HARETH_WHATSAPP_NUMBER:
        system_instruction = (
            "أنت مساعد نظام نقل مخصص حصرياً لأخيك حارث. مهامك ثابتة ومحصورة في إدارة شحنات وحمولات "
            "سيارة Fiat Ducato (L3H2). نطاق أسعار الشحن لديك بين 1.00 إلى 1.30 يورو لكل كيلومتر. "
            "كن دقيقاً، مختصراً، ومباشراً في تفاصيل الحمولات وعمليات الحجز."
        )
    else:
        system_instruction = (
            "أنت مساعد شخصي ذكي وشامل لأحمد (أبو شهاب). يمكنك الإجابة على أي سؤال يطلبه، "
            "سواء في البرمجة، التحليل، الأفكار، أو أي استفسار عام مستفيداً من قدراتك الكاملة كنموذج ذكاء اصطناعي، "
            "مع الاحتفاظ بالمرونة والذكاء العالي والأسلوب الاحترافي في الحوار."
        )
    
    try:
        response = ai_client.models.generate_content(
            model='gemini-2.5-flash',
            contents=incoming_msg,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.7,
            ),
        )
        ai_reply_text = response.text
    except Exception as e:
        ai_reply_text = "أهلاً بك يا أبو شهاب، أواجه ضغطاً مؤقتاً في معالجة الطلب، يرجى إعادة المحاولة."

    from twilio.twiml.messaging_response import MessagingResponse
    resp = MessagingResponse()
    resp.message(ai_reply_text)
        
    return str(resp)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)