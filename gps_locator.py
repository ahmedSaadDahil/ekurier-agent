import requests

def get_location_from_gps(lat: float, lon: float):
    """
    تحويل إحداثيات الـ GPS الحقيقية أينما كان حارث في أوروبا 
    إلى الرمز البريدي والمدينة لتطبيقها في موقع الشحن تلقائياً.
    استخدام خدمة Geocoding مجانية وموثوقة.
    """
    try:
        # استخدام خدمة خرائط مفتوحة لتحويل الإحداثيات إلى تفاصيل عنوان
        url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}&zoom=18&addressdetails=1"
        headers = {'User-Agent': 'KurierAgent/1.0'}
        
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            address = data.get("address", {})
            
            postal_code = address.get("postcode", "")
            city = address.get("city", address.get("town", address.get("village", "")))
            country = address.get("country", "")
            
            print(f"📍 تم تحديد موقع حارث بنجاح عبر GPS:")
            print(f"   - الدولة: {country}")
            print(f"   - المدينة: {city}")
            print(f"   - الرمز البريدي: {postal_code}")
            
            return postal_code, city
        else:
            print("⚠️ تعذر جلب تفاصيل الموقع من الإحداثيات.")
            return None, None
    except Exception as e:
        print(f"خطأ في الاتصال بخدمة تحديد الموقع: {e}")
        return None, None

if __name__ == "__main__":
    # تجربة وهمية لإحداثيات في ألمانيا (مثلاً في مدينة فرانكفورت أو إرفورت)
    # سيقوم التطبيق لاحقاً بجلب هذه الإحداثيات من هاتف حارث تلقائياً بضغطة زر
    sample_lat, sample_lon = 50.1109, 8.6821 # إحداثيات فرانكفورت كمثال أوروبي
    get_location_from_gps(sample_lat, sample_lon)