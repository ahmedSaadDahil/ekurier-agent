import os
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from google import genai

app = Flask(__name__)

# تهيئة عميل الذكاء الاصطناعي
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

@app.route('/webhook', methods=['POST'])
def webhook():
    # استقبال نص الرسالة الواردة من الواتساب
    incoming_msg = request.form.get('Body', '').strip()
    
    # إنشاء استجابة Twilio TwiML
    resp = MessagingResponse()
    msg = resp.message()
    
    try:
        # إرسال الرسالة إلى نموذج الذكاء الاصطناعي للحصول على الرد
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=incoming_msg,
        )
        ai_reply = response.text
        msg.body(ai_reply)
    except Exception as e:
        msg.body("عذراً يا أبو شهاب، حدث خطأ في معالجة طلبك حالياً.")
        
    return str(resp)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
