import os
import time
import requests
from playwright.sync_api import sync_playwright

USERNAME = "asmaa10.logistik@gmail.com"
PASSWORD = "kP4100UY"
BASE_URL = "https://www.e-kurier.net"
SESSION_FILE = os.path.join(os.path.dirname(__file__), "session.json")
SCREENSHOT_PATH = os.path.join(os.path.dirname(__file__), "bidding_preview.png")

DRY_RUN = True  # وضع التجربة الآمنة
CHECK_INTERVAL_SECONDS = 180  # فحص كل 3 دقائق

def send_whatsapp_alert(message):
    """
    دالة إرسال التنبيهات إلى الواتساب (يمكن ربطها بمنصة مثل CallMeBot أو Twilio أو API جاهز)
    """
    try:
        print(f"📲 [إشعار واتساب]: {message}")
        # هنا يتم وضع رابط الـ API الخاص بإرسال الرسائل (مثل CallMeBot المجاني أو Twilio)
        # مثال تجريبي للربط السريع:
        # phone = "+964XXXXXXXXX" # رقمك في العراق
        # requests.get(f"https://api.callmebot.com/whatsapp.php?phone={phone}&text={message}&apikey=YOUR_KEY")
    except Exception as e:
        print(f"⚠️ تعذر إرسال إشعار الواتساب: {e}")

def run_continuous_monitor():
    print("🤖 [مشغل الوكيل الذكي]: بدء نظام المراقبة المستمرة مع تنبيهات الواتساب...")
    
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
            print(f"Opening website: {BASE_URL}")
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
                print("Logging in...")
                user_field.click()
                user_field.fill(USERNAME)
                pass_field.click()
                pass_field.fill(PASSWORD)
                page.locator("input[value='Anmelden'], button:has-text('Anmelden')").first.click()
                page.wait_for_timeout(4000)
            
            context.storage_state(path=SESSION_FILE)

            cycle_count = 1
            while True:
                print(f"\n==========================================")
                print(f"🔄 [دورة الفحص رقم {cycle_count}] - {time.strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"==========================================")

                frachten_tab = page.locator("text=FRACHTEN").first
                if frachten_tab.is_visible():
                    frachten_tab.click()
                    page.wait_for_timeout(2000)

                target_plz_list = ["60311", "60313", "60329", "60549", "60327"]
                bidding_found = False

                for plz in target_plz_list:
                    print(f"🔍 فحص الرمز البريدي [{plz}]...")
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
                        print(f"ملاحظة أثناء إدخال PLZ {plz}: {e}")

                    bid_buttons = page.locator("input[value*='Mail'], button:has-text('Mail'), a:has-text('Mail'), :text('Mail a. Anbiet.')")
                    
                    if bid_buttons.count() > 0:
                        success_msg = f"🎉 تم العثور على شحنة نشطة في الرمز البريدي ({plz}) لحارث! وتم تعبئة السعر (380€)."
                        print(success_msg)
                        
                        # إرسال إشعار فوري للواتساب
                        send_whatsapp_alert(success_msg)

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
                    else:
                        print(f"   - لا توجد شحنات في ({plz}).")

                if bidding_found:
                    print("🎯 تمت العملية بنجاح في هذه الدورة.")
                else:
                    print(f"💤 لا توجد شحنات حالياً. انتظار 3 دقائق للدورة القادمة...")

                time.sleep(CHECK_INTERVAL_SECONDS)
                cycle_count += 1

        except KeyboardInterrupt:
            print("\n🛑 تم إيقاف الوكيل يدويًا.")
        except Exception as e:
            print(f"❌ حدث خطأ: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    run_continuous_monitor()