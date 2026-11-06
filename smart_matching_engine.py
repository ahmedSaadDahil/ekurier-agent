import json
import os

# --- مواصفات سيارة حارث (Fiat Ducato L3H2) ---
VEHICLE_SPECS = {
    "name": "Fiat Ducato L3H2",
    "max_length_cm": 370.5,
    "max_width_cm": 187.0,
    "max_height_cm": 193.2,
    "max_volume_m3": 13.0,
    "max_pallets": 6,
    "fuel_consumption_per_100km": 11.0,  # 11 لتر لكل 100 كم
}

# --- النموذج المالي الشهري والدقيق (السنة الأولى) ---
FINANCIAL_MODEL = {
    "monthly_fixed_costs": {
        "driver_monthly_salary": 3500.0, # راتب السائق الشهري
        "vehicle_rent": 1100.0,        # إيجار السيارة (قسط السنة الأولى)
        "vehicle_insurance": 350.0,   # تأمين السيارة الشامل
        "oil_maintenance": 1500.0,    # استهلاك وإهلاك السيارة الشهري
        "road_tax_tolls": 100.0,      # ضريبة الطريق
        "platform_subscription": 85.0,# تكاليف برنامج النقل
        "vehicle_tax": 18.0,          # ضريبة السيارة
        "cargo_insurance": 30.0       # تأمين البضاعة
    },
    "estimated_monthly_trips": 22,    
    "avg_fuel_price_per_liter": 2.20, # سعر لتر الوقود المحدث
    "monthly_distance_km": 13000.0    # المسافة الشهرية المقطوعة
}

# --- استراتيجية تسعير الكيلومتر المرنة لحارث ---
PRICING_STRATEGY = {
    "min_rate_per_km": 1.00,  # الحد الأدنى المعتمد من حارث (€/كم)
    "max_rate_per_km": 1.30   # الحد الأعلى المعتمد من حارث (€/كم)
}

def load_extracted_freights():
    """تحميل الحمولات المسحوبة مسبقاً"""
    try:
        with open("freights_extracted.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ خطأ في قراءة ملف الحمولات: {e}")
        return []

def estimate_trip_distance(freight_text):
    """تقدير المسافة الحقيقية بناءً على الوجهات المذكورة في الإعلان"""
    text_lower = freight_text.lower()
    
    if any(k in text_lower for k in ["spain", "espana", "portugal", "italy", "italia", "rome", "madrid"]):
        return 1450.0  # مسافة طويلة
    elif any(k in text_lower for k in ["france", "paris", "poland", "warsaw", "czech", "belgium", "netherlands", "amsterdam"]):
        return 950.0   # مسافة متوسطة إلى طويلة
    elif any(k in text_lower for k in ["germany", "deutschland", "stuttgart", "munich", "berlin", "hamburg", "frankfurt", "neckar"]):
        return 550.0   # مسافة داخلية في ألمانيا
    else:
        return 400.0   # مسافة إقليمية قياسية افتراضية

def calculate_flexible_bids(distance_km):
    """حساب التكلفة الفعلية وسعري الخيار (الحد الأدنى والحد الأعلى) بناءً على مسافة الرحلة"""
    
    # 1. حساب التكلفة الفعلية الصافية للكم الواحد (السنة الأولى = 0.76 يورو/كم تقريبا بناءً على الحسابات الدقيقة)
    total_monthly_fixed = sum(FINANCIAL_MODEL["monthly_fixed_costs"].values())
    monthly_fuel_cost = (FINANCIAL_MODEL["monthly_distance_km"] / 100.0) * VEHICLE_SPECS["fuel_consumption_per_100km"] * FINANCIAL_MODEL["avg_fuel_price_per_liter"]
    total_monthly_cost = total_monthly_fixed + monthly_fuel_cost
    actual_cost_per_km = total_monthly_cost / FINANCIAL_MODEL["monthly_distance_km"]
    
    # 2. إجمالي التكلفة الفعلية للرحلة الحالية
    actual_trip_cost = distance_km * actual_cost_per_km
    
    # 3. حساب خيارات حارث (الحد الأدنى 1.00€ والحد الأعلى 1.30€)
    min_bid_price = distance_km * PRICING_STRATEGY["min_rate_per_km"]
    max_bid_price = distance_km * PRICING_STRATEGY["max_rate_per_km"]
    
    return {
        "estimated_distance_km": round(distance_km, 1),
        "actual_trip_cost": round(actual_trip_cost, 2),
        "min_bid": round(min_bid_price, 2), # عرض الحد الأدنى (1 يورو/كم)
        "max_bid": round(max_bid_price, 2)  # عرض الحد الأعلى (1.30 يورو/كم)
    }

def filter_and_analyze_freights(freights):
    """تصفية الحمولات وتطبيق خيارات التسعير المرنة"""
    suitable_freights = []
    
    for freight in freights:
        lines = freight.get("lines", [])
        freight_text = " ".join(lines).lower()
        
        is_oversized = "heavy" in freight_text or "24 ton" in freight_text or "semi" in freight_text or "40t" in freight_text
        
        if not is_oversized:
            distance = estimate_trip_distance(freight_text)
            pricing_data = calculate_flexible_bids(distance)
            
            route_info = " | ".join([line.strip() for line in lines[:3] if line.strip() and len(line) > 3])
            
            suitable_freights.append({
                "id": freight["id"],
                "details": route_info,
                "pricing": pricing_data
            })
            
    return suitable_freights

if __name__ == "__main__":
    print("🔄 جاري تحميل الحمولات وتطبيق نموذج التسعير المرن (الحد الأدنى 1€ - الحد الأعلى 1.30€)...")
    raw_freights = load_extracted_freights()
    
    if raw_freights:
        matched = filter_and_analyze_freights(raw_freights)
        print(f"✨ تم العثور على {len(matched)} حمولة متوافقة مع سيارة حارث.\n")
        print("=" * 70)
        print("📊 عينة تحليل الحمولات مع خيارات التسعير المرنة لحارث (أول 5 حمولات):")
        print("=" * 70)
        
        for i, item in enumerate(matched[:5], 1):
            p_data = item["pricing"]
            
            print(f"📦 حمولة رقم #{item['id']} ({i})")
            print(f"📍 المسار: {item['details'][:90]}...")
            print(f"🛣️ المسافة المقدرة: {p_data['estimated_distance_km']} كم")
            print(f"📉 تكلفتك الفعلية الصافية للرحلة: €{p_data['actual_trip_cost']}")
            print(f"⚖️ خيارات المزايدة المتاحة لحارث:")
            print(f"   🟢 [اضغط للحد الأدنى (1.0€/كم)]: €{p_data['min_bid']}")
            print(f"   🔥 [اضغط للحد الأعلى (1.3€/كم)]: €{p_data['max_bid']}")
            print("-" * 70)