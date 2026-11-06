import sqlite3

def init_db():
    conn = sqlite3.connect("ekurier.db")
    cursor = conn.cursor()
    
    # جدول الحمولات والرحلات المحسوبة
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS loads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            origin TEXT,
            destination TEXT,
            distance_km REAL,
            diesel_price REAL,
            fuel_cost REAL,
            maintenance_cost REAL,
            driver_wage REAL,
            total_trip_cost REAL,
            floor_price REAL,
            recommended_bid REAL,
            vehicle_match TEXT,
            status TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # جدول المصاريف الثابتة الشهرية (لغرض حساب التكلفة الشهرية والاحتياطي الضريبي)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS monthly_expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            allianz_insurance REAL DEFAULT 30.0,
            road_tax REAL DEFAULT 100.0,
            car_insurance REAL DEFAULT 350.0,
            car_installment REAL DEFAULT 1100.0, -- سيصبح 333 بعد سنة
            software_fee REAL DEFAULT 85.0,
            annual_car_tax_monthly REAL DEFAULT 17.5, -- (210 / 12)
            tax_reserve REAL DEFAULT 200.0, -- احتياطي الضريبة المبدئي
            month_year TEXT
        )
    """)
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("Database schema updated with financial and cost parameters successfully.")