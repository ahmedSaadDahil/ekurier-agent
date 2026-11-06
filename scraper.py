import json
import asyncio
from playwright.async_api import async_playwright

async def parse_ekurier_freights():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=[
                "--start-maximized",
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage"
            ]
        )
        
        context = await browser.new_context(
            no_viewport=True,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )

        # تحميل الكوكيز المحفوظة مسبقاً
        try:
            with open("session.json", "r", encoding="utf-8") as f:
                session_data = json.load(f)
                if "cookies" in session_data:
                    await context.add_cookies(session_data["cookies"])
                    print("✅ تم تحميل ملف الكوكيز ودخول النظام تلقائياً.")
        except Exception as e:
            print(f"⚠️ تنبيه الكوكيز: {e}")

        page = await context.new_page()
        
        all_pages_freights = []
        max_pages = 7  # 7 صفحات لإجمالي 130 حمولة

        for page_num in range(1, max_pages + 1):
            target_url = f"https://e-kurier.net/portal/freights?page={page_num}"
            print(f"\n🚀 الانتقال المباشر إلى الصفحة {page_num}: {target_url}")
            
            try:
                await page.goto(target_url, wait_until="load", timeout=120000)
            except:
                pass

            # إغلاق نافذة الكوكيز إن وجدت في الصفحة الأولى
            if page_num == 1:
                try:
                    await page.evaluate("""() => {
                        const buttons = Array.from(document.querySelectorAll('button, div, span'));
                        const acceptBtn = buttons.find(el => el.textContent.trim() === 'Accept all');
                        if (acceptBtn) acceptBtn.click();
                    }""")
                except:
                    pass

            # رفع وقت الانتظار الإلزامي إلى 4 دقائق (240 ثانية) نظراً للبطء الشديد للسيرفر
            print(f"⏳ انتظار إلزامي لمدة 4 دقائق (240 ثانية) لاكتمال ضخ جميع كروت الصفحة {page_num} من السيرفر...")
            for remaining in range(240, 0, -30):
                print(f"   - متبقي {remaining} ثانية...")
                await page.wait_for_timeout(30000)

            # استخراج الكروت وسحبها دفعة واحدة بعد انتهاء الانتظار الكامل
            js_code = """() => {
                const allElements = Array.from(document.querySelectorAll('div, tr, li'));
                const cards = allElements.filter(el => {
                    const text = el.innerText ? el.innerText : '';
                    return (text.includes('Loading:') && text.includes('Unloading:')) || 
                           (text.includes('Distance:') && text.includes('Goods:')) ||
                           (text.includes('Colli') && text.includes('km'));
                });

                const uniqueCards = [];
                cards.forEach(card => {
                    if (card.innerText.length > 40 && card.innerText.length < 2500) {
                        if (!uniqueCards.some(c => c.contains(card))) {
                            uniqueCards.push(card);
                        }
                    }
                });

                return uniqueCards.map((card) => {
                    return card.innerText.split('\\n').map(l => l.trim()).filter(l => l.length > 0);
                });
            }"""

            page_freights = await page.evaluate(js_code)
            print(f"📦 تم بنجاح سحب {len(page_freights)} حمولة من الصفحة {page_num}.")
            
            # إضافة الحمولات للقائمة الكلية بدون تكرار
            for f_lines in page_freights:
                if f_lines not in all_pages_freights:
                    all_pages_freights.append(f_lines)

        # ترقيم نهائي لجميع الحمولات المجمعة
        structured_freights = []
        for idx, lines in enumerate(all_pages_freights, start=1):
            structured_freights.append({
                "id": idx,
                "lines": lines
            })

        print(f"\n🎉 [الإجمالي الكلي: تم سحب {len(structured_freights)} حمولة بنجاح من كافة الصفحات السبع!]\n")

        # حفظ البيانات المستخرجة في ملف JSON
        with open("freights_extracted.json", "w", encoding="utf-8") as f_out:
            json.dump(structured_freights, f_out, ensure_ascii=False, indent=4)
        
        print("\n💾 تم حفظ جميع الحمولات بنجاح في ملف `freights_extracted.json`.")

        print("\n⏳ المتصفح سيبقى مفتوحاً. قم بإغلاقه يدوياً متى شئت...")
        while not page.is_closed():
            await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(parse_ekurier_freights())