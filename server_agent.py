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
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
    
    payload = {
        "contents": [{
            "parts": [{"text": incoming_msg}]
        }]
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        res_data = response.json()
        
        # طباعة الرد كاملاً في سجلات Render لنفحصه
        print("API Response:", res_data)
        
        ai_reply = res_data['candidates'][0]['content']['parts'][0]['text']
        msg.body(ai_reply)
    except Exception as e:
        # طباعة الخطأ بالتفصيل في السجلات
        print("ERROR OCCURRED:", str(e))
        print("FULL RESPONSE WAS:", res_data if 'res_data' in locals else 'No response')
        msg.body("عذراً، حدث خطأ داخلي. تم تسجيله في السجلات.")
        
    return str(resp)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
