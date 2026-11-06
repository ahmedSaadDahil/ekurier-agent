import os
from playwright.sync_api import sync_playwright

BASE_URL = "https://www.e-kurier.net"
SESSION_FILE = os.path.join(os.path.dirname(__file__), "session.json")

def diagnostic_search():
    print("🔍 [تشخيص النظام]: بدء فحص صفحة الشحنات...")

    with sync_playwright() as p:
        # تشغيل المتصفح مع مهلة أمان واضحة
        browser = p.chromium.launch(headless=False, slow_mo=500)
        
        if not os.path.exists(SESSION_FILE):
            print("❌ ملف الجلسة غير موجود.")
            return

        context = browser.new_context(storage_state=SESSION_FILE)
        page = context.new_page()
        
        try:
            print(f"جاري الانتقال إلى الموقع: {BASE_URL}")
            page.goto(BASE_URL, timeout=30000)
            page.wait_for_timeout(2000)

            # الانتقال لتبويب الشحنات بأمان
            print("الانتقال لتبويب الشحنات (FRACHTEN)...")
            frachten_tab = page.locator("text=FRACHTEN").first
            if frachten_tab.is_visible():
                frachten_tab.click()
                page.wait_for_timeout(3000)
                print("✅ تم فتح تبويب الشحنات بنجاح.")
            else:
                print("⚠️ لم يتم العثور على تبويب FRACHTEN ظاهرياً، سنفحص الصفحة الحالية.")

            # طباعة كافة حقول النصوص المتاحة في الصفحة لنراها بوضوح في الـ Terminal
            inputs = page.locator("input")
            count = inputs.count()
            print(f"📊 إجمالي عناصر الحقول (inputs) المكتشفة في الصفحة: {count}")

            for i in range(count):
                el = inputs.nth(i)
                try:
                    if el.is_visible():
                        n = el.get_attribute("name") or "لا يوجد"
                        i_id = el.get_attribute("id") or "لا يوجد"
                        t = el.get_attribute("type") or "لا يوجد"
                        p_val = el.get_attribute("placeholder") or "لا يوجد"
                        print(f"   - حقل [{i}]: type={t}, name={n}, id={i_id}, placeholder={p_val}")
                except:
                    pass

            print("\n✨ انتهى التشخيص بنجاح دون تعليق. سيتم إغلاق المتصفح الآن.")
            page.wait_for_timeout(3000)

        except Exception as e:
            print(f"❌ حدث خطأ أثناء التشخيص: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    diagnostic_search()