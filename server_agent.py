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
    # استخدام الموديل الأحدث المخصص للطلبات السريعة والمستقرة
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-2.5-flash-lite:generateContent?key={api_key}"
    
    payload = {
        "contents": [{
            "parts": [{"text": incoming_msg}]
        }]
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        res_data = response.json()
        
        if "candidates" in res_data and len(res_data["candidates"]) > 0:
            ai_reply = res_data['candidates'][0]['content']['parts'][0]['text']
            msg.body(ai_reply)
        elif "error" in res_data:
            err_msg = res_data["error"].get("message", "خطأ من جوجل")
            msg.body(f"خطأ: {err_msg[:100]}")
        else:
            msg.body("عذراً، استجابة غير متوقعة.")
            
    except Exception as e:
        msg.body("عذراً يا أبو شهاب، حدث خطأ في النظام.")
        
    return str(resp)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
