import os
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from google import genai

app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
def webhook():
    incoming_msg = request.form.get('Body', '').strip()
    resp = MessagingResponse()
    msg = resp.message()
    
    try:
        client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
        # استخدام الموديل القياسي الموثوق
        response = client.models.generate_content(
            model='gemini-1.5-flash',
            contents=incoming_msg
        )
        ai_reply = response.text
        msg.body(ai_reply)
    except Exception as e:
        msg.body(f"خطأ: {str(e)[:60]}")
        
    return str(resp)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
