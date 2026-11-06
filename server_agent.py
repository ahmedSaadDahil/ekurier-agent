import os
import requests
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse

app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
def webhook():
    incoming_msg = request.form.get('Body', '').strip()
    resp = MessagingResponse()
    msg = resp.message()

    api_key = os.environ.get("GEMINI_API_KEY")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"

    payload = {
        "contents": [{
            "parts": [{"text": incoming_msg}]
        }]
    }

    try:
        response = requests.post(url, json=payload, timeout=10)
        res_data = response.json()

        # استخراج الرد من هيكل بيانات جوجل المباشر
        ai_reply = res_data['candidates'][0]['content']['parts'][0]['text']
        msg.body(ai_reply)
    except Exception as e:
        msg.body(f"عذراً يا أبو شهاب، حدث خطأ: {str(e)[:50]}")

    return str(resp)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
