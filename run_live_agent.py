import json
import os
import httpx
from bs4 import BeautifulSoup

# --- مواصفات سيارة حارث (Fiat Ducato L3H2) ---
VEHICLE_SPECS = {
    "name": "Fiat Ducato L3H2",
    "fuel_consumption_per_100km": 11.0,  # 11 لتر لكل 100 كم
}

# --- النموذج المالي الشهري الدقيق (السنة الأولى) ---
FINANCIAL_MODEL = {
    "monthly_fixed_costs": {
        "driver_monthly_salary": 3500.0,
        "vehicle_rent": 1100.0,
        "vehicle_insurance": 350.0,
        "oil_maintenance": 1500.0,
        "road_tax_tolls": 100.0,
        "platform_subscription": 85.0,
        "vehicle_tax": 18.0,
        "cargo_insurance": 30.0
    },
    "estimated_monthly_trips": 22,    
    "avg_fuel_price_per_liter": 2.20,
    "monthly_distance_km": 13000.0
}

# --- استراتيجية تسعير الكيلومتر المرنة لحارث ---
PRICING_STRATEGY = {
    "min_rate_per_km": 1.00,  # الحد الأدنى (€/كم)
    "max_rate_per_km": 1.30   # الحد الأعلى (€/كم)
}

def get_smart_gps_location():
    """
    تحديد الموقع الذكي:
    - أثناء التطوير والتجربة: يعتمد مؤقتاً على Thüringen بناءً على طلبك.
    - عند التشغيل الحقيقي على موبايل حارث: سيقرأ الإحداثيات الحية الفورية للهاتف صامتاً.
    """
    gps_file = "hareth_gps.json"
    
    # النقطة الافتراضية المؤقتة للاختبار التجريبي في Thüringen
    dev_simulation_location = {
        "city": "Thüringen",
        "country": "Germany",
        "latitude": 50.7766,
        "longitude": 11.0356,
        "status": "Dev Simulation Mode (Thüringen)"
    }
    
    # التحقق مما إذا كان هناك ملف GPS حي قادم من تطبيق الهاتف الحقيقي
    if os.path.exists(gps_file):
        try:
            with open(gps_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                # إذا وجدنا إحداثيات حقيقية مسجلة من الموبايل، نستخدمها
                if data.get("source") == "mobile_device_gps":
                    return data
        except Exception:
            pass
            
    # إذا لم يوجد تحديث حي من الهاتف، نعتمد نقطة Thüringen للاختبار التجريبي الحالي
    return dev_simulation_location

def fetch_all_freights():
    """سحب الحمولات الحية عبر الـ API السريع"""
    url = "https://e-kurier.net/portal/freights"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9,ar;q=0.8",
        "Referer": "https://e-kurier.net/portal/dashboard"
    }

    cookies = {}
    try:
        with open("session.json", "r", encoding="utf-8") as f:
            session_data = json.load(f)
            if "cookies" in session_data:
                for cookie in session_data["cookies"]:
                    cookies[cookie["name"]] = cookie["value"]
    except Exception as e:
        print(f"❌ خطأ في قراءة ملف الكوكيز: {e}")
        return False

    all_pages_freights = []
    max_pages = 7  # 7 صفحات لإجمالي الحمولات

    with httpx.Client(headers=headers, cookies=cookies, follow_redirects=True, timeout=30.0) as client:
        for page_num in range(1, max_pages + 1):
            target_url = f"{url}?page={page_num}"
            try:
                response = client.get(target_url)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    cards = soup.find_all('article')
                    if not cards:
                        cards = soup.select('div[class*="freight"], tr')

                    page_freights = []
                    for card in cards:
                        text = card.get_text(separator='\n', strip=True)
                        if len(text) > 40 and ('Loading:' in text or 'Distance' in text or 'Colli' in text):
                            lines = [line.strip() for line in text.split('\n') if line.strip()]
                            if lines not in page_freights:
                                page_freights.append(lines)

                    for f_lines in page_freights:
                        if f_lines not in all_pages_freights:
                            all_pages_freights.append(f_lines)
            except Exception as e:
                print(f"❌ خطأ في الصفحة {page_num}: {e}")

    structured_freights = []
    for idx, lines in enumerate(all_pages_freights, start=1):
        structured_freights.append({
            "id": idx,
            "lines": lines
        })

    with open("freights_extracted.json", "w", encoding="utf-8") as f_out:
        json.dump(structured_freights, f_out, ensure_ascii=False, indent=4)
    
    return True

def estimate_trip_distance(freight_text):
    """تقدير المسافة بناءً على تفاصيل الرحلة"""
    text_lower = freight_text.lower()
    if any(k in text_lower for k in ["spain", "espana", "portugal", "italy", "italia", "rome", "madrid"]):
        return 1450.0
    elif any(k in text_lower for k in ["france", "paris", "poland", "warsaw", "czech", "belgium", "netherlands", "amsterdam"]):
        return 950.0
    elif any(k in text_lower for k in ["germany", "deutschland", "stuttgart", "munich", "berlin", "hamburg", "frankfurt", "thüringen", "erfurt"]):
        return 350.0  # مسافة قريبة نسبياً داخل ألمانيا/ثورينغن
    else:
        return 400.0

def calculate_flexible_bids(distance_km):
    """حساب التكلفة الفعلية وخيارات المزايدة المرنة"""
    total_monthly_fixed = sum(FINANCIAL_MODEL["monthly_fixed_costs"].values())
    monthly_fuel_cost = (FINANCIAL_MODEL["monthly_distance_km"] / 100.0) * VEHICLE_SPECS["fuel_consumption_per_100km"] * FINANCIAL_MODEL["avg_fuel_price_per_liter"]
    total_monthly_cost = total_monthly_fixed + monthly_fuel_cost
    actual_cost_per_km = total_monthly_cost / FINANCIAL_MODEL["monthly_distance_km"]
    
    actual_trip_cost = distance_km * actual_cost_per_km
    min_bid_price = distance_km * PRICING_STRATEGY["min_rate_per_km"]
    max_bid_price = distance_km * PRICING_STRATEGY["max_rate_per_km"]
    
    return {
        "estimated_distance_km": round(distance_km, 1),
        "actual_trip_cost": round(actual_trip_cost, 2),
        "min_bid": round(min_bid_price, 2),
        "max_bid": round(max_bid_price, 2)
    }

def smart_thuringen_agent():
    """تشغيل المحرك الذكي مع اعتماد Thüringen مؤقتاً"""
    current_gps = get_smart_gps_location()
    current_city = current_gps.get("city", "").lower()

    print(f"\n🛰️ [GPS محاكاة التطوير]: تم ضبط الموقع الحالي مؤقتاً على ({current_gps.get('city')}, {current_gps.get('country')})")
    print("🔄 جاري سحب وتصفية الحمولات الحية بناءً على هذا الموقع...")

    if not fetch_all_freights():
        print("❌ فشل في جلب الحمولات.")
        return

    try:
        with open("freights_extracted.json", "r", encoding="utf-8") as f:
            freights = json.load(f)
    except Exception as e:
        print(f"❌ خطأ في قراءة الحمولات: {e}")
        return

    processed_freights = []
    for freight in freights:
        lines = freight.get("lines", [])
        freight_text = " ".join(lines).lower()
        
        is_oversized = "heavy" in freight_text or "24 ton" in freight_text or "semi" in freight_text or "40t" in freight_text
        if not is_oversized:
            distance = estimate_trip_distance(freight_text)
            pricing_data = calculate_flexible_bids(distance)
            route_info = " | ".join([line.strip() for line in lines[:3] if line.strip() and len(line) > 3])
            
            # مطابقة الموقع مع Thüringen أو المدن المجاورة
            is_near_gps = current_city in freight_text or "erfurt" in freight_text or "gera" in freight_text or "jena" in freight_text
            
            processed_freights.append({
                "id": freight["id"],
                "details": route_info,
                "pricing": pricing_data,
                "is_near_gps": is_near_gps
            })

    gps_matched = [f for f in processed_freights if f["is_near_gps"]]
    other_freights = [f for f in processed_freights if not f["is_near_gps"]]
    final_list = gps_matched + other_freights

    print(f"✨ [نتائج الفلترة الذكية]: تم مطابقة {len(gps_matched)} حمولة تنطلق من محيط Thüringen.")
    print("=" * 70)

    for i, item in enumerate(final_list[:10], 1):
        p_data = item["pricing"]
        badge = "📍 [مطابق لموقع Thüringen التجريبي]" if item["is_near_gps"] else "🌍 [رحلة عامة متاحة]"
        
        print(f"\n📦 [{badge}] فرصة رقم {i} - حمولة رقم #{item['id']}")
        print(f"📍 المسار: {item['details']}")
        print(f"🛣️ المسافة المقدرة: {p_data['estimated_distance_km']} كم")
        print(f"📉 تكلفتك الفعلية الصافية: €{p_data['actual_trip_cost']}")
        print(f"⚖️ خيارات المزايدة المرنة لحارث:")
        print(f"   🟢 [1] الحد الأدنى (1.0€/كم) --> €{p_data['min_bid']}")
        print(f"   🔥 [2] الحد الأعلى (1.3€/كم) --> €{p_data['max_bid']}")
        print(f"   ⏭️ [3] تخطي هذه الحمولة")
        print(f"   🚪 [Q] الخروج")
        
        choice = input("\n👉 اختر تفاعل حارث (1, 2, 3 أو Q): ").strip().lower()
        
        if choice == '1':
            print(f"\n🎯 [محاكاة آمنة]: اختار حارث **الحد الأدنى** بقيمة (€{p_data['min_bid']}).")
            print("🛡️ [وضع الأمان]: تم إيقاف الطلب النهائي هنا لحين التأكد التام.")
            print("=" * 70)
            cont = input("هل تريد الانتقال للحمولة التالية؟ (y/n): ").strip().lower()
            if cont != 'y':
                break
        elif choice == '2':
            print(f"\n🎯 [محاكاة آمنة]: اختار حارث **الحد الأعلى** بقيمة (€{p_data['max_bid']}).")
            print("🛡️ [وضع الأمان]: تم إيقاف الطلب النهائي هنا لحين التأكد التام.")
            print("=" * 70)
            cont = input("هل تريد الانتقال للحمولة التالية؟ (y/n): ").strip().lower()
            if cont != 'y':
                break
        elif choice == '3':
            print("⏩ تم تخطي الحمولة والذهاب للتالية...\n")
            continue
        elif choice == 'q':
            print("👋 إغلاق النظام. بالتوفيق يا أبو شهاب!")
            break
        else:
            print("⚠️ اختيار غير صحيح، تم تخطي الحمولة.\n")

if __name__ == "__main__":
    smart_thuringen_agent()