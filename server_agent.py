import os
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import google.generativeai as genai

app = Flask(__name__)

# تهيئة مفتاح جيميناي بالطريقة المباشرة
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-1.5-flash')

@app.route('/webhook', methods=['POST'])
def webhook():
    incoming_msg = request.form.get('Body', '').strip()
    resp = MessagingResponse()
    msg = resp.message()

    try:
        # إرسال الرسالة والحصول على الرد
        response = model.generate_content(incoming_msg)
        msg.body(response.text)
    except Exception as e:
        msg.body(f"خطأ تقني: {str(e)[:50]}")

    return str(resp)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
