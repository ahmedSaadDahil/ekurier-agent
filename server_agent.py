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
        api_key = os.environ.get("GEMINI_API_KEY")
        client = genai.Client(api_key=api_key)
        
        # استخدام الموديل المستقر المعتمد على مفتاحك
        response = client.models.generate_content(
            model='gemini-3.7-flash',
            contents=incoming_msg
        )
        
        msg.body(response.text)
    except Exception as e:
        print("Error:", str(e))
        msg.body("عذراً يا أبو شهاب، حدث خطأ مؤقت في النظام.")
        
    return str(resp)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
