import os
import time
from playwright.sync_api import sync_playwright

USERNAME = "asmaa10.logistik@gmail.com"
PASSWORD = "kP4100UY"
BASE_URL = "https://www.e-kurier.net"
SESSION_FILE = os.path.join(os.path.dirname(__file__), "session.json")
SCREENSHOT_PATH = os.path.join(os.path.dirname(__file__), "bidding_preview.png")

DRY_RUN = True  # اجعلها False عندما ترغب بالبدء الفعلي في الميدان
CHECK_INTERVAL_SECONDS = 180  # فحص كل 3 دقائق

def run_harith_agent():
    print("🚛 [وكيل حارث اللوجستي]: بدء تشغيل نظام مراقبة شحنات ألمانيا...")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=400)
        
        if os.path.exists(SESSION_FILE):
            context = browser.new_context(storage_state=SESSION_FILE)
            print("✅ تم تحميل جلسة العمل بنجاح.")
        else:
            context = browser.new_context()
            print("⚠️ ملف الجلسة غير موجود.")
            
        page = context.new_page()
        
        try:
            page.goto(BASE_URL, timeout=60000, wait_until="domcontentloaded")
            page.wait_for_timeout(3000)

            # تخطي الكوكيز
            try:
                cookie_btn = page.locator("text=Alle akzeptieren")
                if cookie_btn.is_visible():
                    cookie_btn.click()
                    page.wait_for_timeout(1000)
            except:
                pass

            # تسجيل الدخول
            user_field = page.locator("input[name='user'], input[type='text'], input#user").first
            pass_field = page.locator("input[name='pass'], input[type='password'], input#pass").first

            if user_field.is_visible() and pass_field.is_visible():
                user_field.fill(USERNAME)
                pass_field.fill(PASSWORD)
                page.locator("input[value='Anmelden'], button:has-text('Anmelden')").first.click()
                page.wait_for_timeout(4000)
            
            context.storage_state(path=SESSION_FILE)

            cycle_count = 1
            while True:
                print(f"\n🔄 [فحص حارث رقم {cycle_count}] - {time.strftime('%Y-%m-%d %H:%M:%S')}")

                frachten_tab = page.locator("text=FRACHTEN").first
                if frachten_tab.is_visible():
                    frachten_tab.click()
                    page.wait_for_timeout(2000)

                target_plz_list = ["60311", "60313", "60329", "60549", "60327"]
                bidding_found = False

                for plz in target_plz_list:
                    try:
                        inputs = page.locator("input[type='text']")
                        for i in range(inputs.count()):
                            box = inputs.nth(i)
                            if box.is_visible():
                                name_attr = box.get_attribute("name") or ""
                                if any(k in name_attr.lower() for k in ['plz', 'ort', 'such', 'abf']):
                                    box.click()
                                    box.fill("")
                                    box.fill(plz)
                                    break
                        
                        search_btn = page.locator("input[type='submit'][value*='Suchen'], button:has-text('Suchen')")
                        if search_btn.count() > 0:
                            search_btn.first.click()
                            page.wait_for_timeout(2500)
                    except Exception as e:
                        pass

                    bid_buttons = page.locator("input[value*='Mail'], button:has-text('Mail'), a:has-text('Mail'), :text('Mail a. Anbiet.')")
                    
                    if bid_buttons.count() > 0:
                        print(f"🎉 تم العثور على شحنة في الرمز البريدي ({plz}) لحارث!")
                        bid_buttons.first.click()
                        page.wait_for_timeout(3000)

                        form_inputs = page.locator("input[type='text'], textarea")
                        if form_inputs.count() > 0:
                            form_inputs.first.fill("380")

                        page.screenshot(path=SCREENSHOT_PATH)
                        print(f"📸 تم حفظ صورة المعاينة في: {SCREENSHOT_PATH}")

                        if DRY_RUN:
                            print("🛑 [DRY_RUN]: متوقف بأمان قبل التأكيد النهائي.")
                        
                        bidding_found = True
                        break

                if not bidding_found:
                    print(f"💤 لا توجد شحنات حالياً. انتظار 3 دقائق...")

                time.sleep(CHECK_INTERVAL_SECONDS)
                cycle_count += 1

        except KeyboardInterrupt:
            print("\n🛑 تم إيقاف وكيل حارث.")
        finally:
            browser.close()

if __name__ == "__main__":
    run_harith_agent()