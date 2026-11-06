import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_order_confirmation(order_id, delivery_address, recipient_email):
    # معلومات بريدك الإلكتروني الذي سيرسل التأكيد
    sender_email = "YOUR_EMAIL@gmail.com"
    sender_password = "YOUR_APP_PASSWORD" # كلمة المرور الخاصة بالتطبيقات من إعدادات جوجل
    
    # تفاصيل الرسالة
    subject = f"تأكيد الطلب رقم: {order_id}"
    body = f"""
    مرحباً،
    
    نود إعلامكم بتأكيد الطلب رقم: {order_id}
    عنوان التوصيل الحالي (موقع حارث عبر GPS): {delivery_address}
    
    يرجى المتابعة وتأكيد الشحنة.
    
    تحياتنا،
    نظام الإدارة الآلي
    """
    
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = recipient_email
    msg['Subject'] = subject
    
    msg.attach(MIMEText(body, 'plain'))
    
    try:
        # الاتصال بسيرفر جوجل لإرسال الإيميل بشكل آمن
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, sender_password)
        text = msg.as_string()
        server.sendmail(sender_email, recipient_email, text)
        server.quit()
        print("تم إرسال تأكيد الطلب عبر البريد الإلكتروني بنجاح!")
        return True
    except Exception as e:
        print(f"حدث خطأ أثناء إرسال البريد: {e}")
        return False

# تجربة دالة الإرسال (يمكنك تفعيلها لاحقاً عند ربطها بتطبيق Flutter)
if __name__ == "__main__":
    # مثال تجريبي
    # send_order_confirmation("12345", "Mosul - Al-Safa Street", "company@e-kurier.net")
    pass