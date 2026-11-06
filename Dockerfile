# استخدام صورة مايكروسوفت الرسمية المجهزة خصيصاً لـ Playwright وبايثون
FROM mcr.microsoft.com/playwright/python:v1.42.0-jammy

WORKDIR /app

# نسخ ملف المتطلبات وتثبيتها
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# نسخ باقي ملفات المشروع إلى السيرفر
COPY . .

# منفذ التشغيل
EXPOSE 8080

# أمر تشغيل تطبيق FastAPI عبر uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]