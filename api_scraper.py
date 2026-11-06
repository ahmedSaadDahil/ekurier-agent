import json
import httpx
from bs4 import BeautifulSoup

def fetch_all_freights():
    url = "https://e-kurier.net/portal/freights"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9,ar;q=0.8",
        "Referer": "https://e-kurier.net/portal/dashboard"
    }

    # تحميل الكوكيز من ملف session.json
    cookies = {}
    try:
        with open("session.json", "r", encoding="utf-8") as f:
            session_data = json.load(f)
            if "cookies" in session_data:
                for cookie in session_data["cookies"]:
                    cookies[cookie["name"]] = cookie["value"]
                print("✅ تم تحميل ملف الكوكيز بنجاح.")
    except Exception as e:
        print(f"❌ خطأ في قراءة ملف الكوكيز: {e}")
        return

    all_pages_freights = []
    max_pages = 7  # 7 صفحات لإجمالي 130 حمولة

    with httpx.Client(headers=headers, cookies=cookies, follow_redirects=True, timeout=30.0) as client:
        for page_num in range(1, max_pages + 1):
            target_url = f"{url}?page={page_num}"
            print(f"🚀 جاري سحب الصفحة {page_num} عبر الـ API: {target_url}")
            
            try:
                response = client.get(target_url)
                if response.status_code == 200:
                    # تحليل كود الـ HTML المسترجع
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # البحث عن عناصر الحمولات (غالباً تبدأ بـ article أو عناصر تحوي بيانات الشحن)
                    cards = soup.find_all('article')
                    if not cards:
                        # بديل لو كانت الحمولات داخل عناصر div مخصصة
                        cards = soup.select('div[class*="freight"], tr')

                    page_freights = []
                    for card in cards:
                        text = card.get_text(separator='\n', strip=True)
                        if len(text) > 40 and ('Loading:' in text or 'Distance' in text or 'Colli' in text):
                            lines = [line.strip() for line in text.split('\n') if line.strip()]
                            if lines not in page_freights:
                                page_freights.append(lines)

                    print(f"📦 تم سحب {len(page_freights)} حمولة من الصفحة {page_num}.")
                    
                    for f_lines in page_freights:
                        if f_lines not in all_pages_freights:
                            all_pages_freights.append(f_lines)
                else:
                    print(f"⚠️ فشل سحب الصفحة {page_num} برمز استجابة: {response.status_code}")
            except Exception as e:
                print(f"❌ حدث خطأ في الصفحة {page_num}: {e}")

    # ترقيم نهائي وحفظ البيانات في ملف JSON
    structured_freights = []
    for idx, lines in enumerate(all_pages_freights, start=1):
        structured_freights.append({
            "id": idx,
            "lines": lines
        })

    print(f"\n🎉 [الإجمالي الكلي: تم سحب {len(structured_freights)} حمولة بنجاح وخاصة بـ Render!]\n")

    with open("freights_extracted.json", "w", encoding="utf-8") as f_out:
        json.dump(structured_freights, f_out, ensure_ascii=False, indent=4)
    
    print("💾 تم حفظ جميع الحمولات بنجاح في ملف `freights_extracted.json`.")

if __name__ == "__main__":
    fetch_all_freights()