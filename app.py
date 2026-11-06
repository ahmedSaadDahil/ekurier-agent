from flask import Flask, request, Response
from twilio.twiml.voice_response import VoiceResponse, Gather
import os

app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
def whatsapp_webhook():
    # كود الـ Webhook الخاص بالواتساب الموجود لديك مسبقاً
    data = request.json
    print("Received WhatsApp Webhook:", data)
    return "OK", 200

@app.route('/voice', methods=['POST'])
def voice_webhook():
    """
    مسار استقبال مكالمات Twilio الصوتية
    """
    response = VoiceResponse()
    
    # استقبال النص المحول من صوت المتصل (إذا وجد)
    user_speech = request.form.get('SpeechResult')
    
    if user_speech:
        print(f"صوت المتصل (تحويل إلى نص): {user_speech}")
        
        # هنا يتم التفاعل مع Gemini لتوليد الرد بناءً على كلام المتصل
        # كمثال مبسط للرد التفاعلي:
        ai_reply = f"أهلاً بك يا أبو شهاب، لقد سمعتك تقول: {user_speech}. جاري تنفيذ طلبك عبر نظام إيكوريير."
        
        # نطق الرد باللغة العربية
        response.say(ai_reply, language='ar-SA', voice='Polly.Zayd')
        
    else:
        # الترحيب المبدئي عند بدء المكالمة والاستماع لكلام المتصل
        gather = Gather(
            input='speech',
            action='/voice',
            method='POST',
            language='ar-SA',
            speech_timeout='auto'
        )
        gather.say("مرحباً بك في نظام إيكوريير الذكي. كيف يمكنني مساعدتك اليوم؟", language='ar-SA', voice='Polly.Zayd')
        response.append(gather)
        
        # في حال لم يتكلم المتصل
        response.say("لم أسمع أي طلب، شكراً لتواصلك معنا.", language='ar-SA')

    return Response(str(response), mimetype='text/xml')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)