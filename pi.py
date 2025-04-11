import os
import json
import time
import schedule
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# إعدادات المسار والتوقيع
LECTURES_DIR = os.path.join(os.path.dirname(__file__), "lectures")
METADATA_PATH = os.path.join(LECTURES_DIR, "metadata.json")
SIGNATURE = "\n\n👨‍💻 *dev by: IRIZI 😊*"
ALLOWED_USER = "212621957775"
GROUP_ID = None

if not os.path.exists(LECTURES_DIR):
    os.makedirs(LECTURES_DIR)

if not os.path.exists(METADATA_PATH):
    with open(METADATA_PATH, "w") as f:
        json.dump({}, f)

user_state = {}
request_count = 0

# إعداد Selenium
chrome_options = Options()
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--disable-gpu")
driver = webdriver.Chrome(service=Service(os.path.join(os.path.dirname(__file__), "chromedriver.exe")), options=chrome_options)
wait = WebDriverWait(driver, 120)

# تحميل البيانات الوصفية
def load_metadata():
    with open(METADATA_PATH, "r") as f:
        return json.load(f)

# حفظ البيانات الوصفية
def save_metadata(data):
    with open(METADATA_PATH, "w") as f:
        json.dump(data, f, indent=2)

# إرسال رسالة
def send_message(target_id, message):
    try:
        search_box = wait.until(EC.presence_of_element_located((By.XPATH, '//div[@data-testid="chat-list-search"]')))
        search_box.clear()
        search_box.send_keys(target_id)
        search_box.send_keys(Keys.ENTER)
        time.sleep(2)
        message_box = driver.find_element(By.XPATH, '//div[@title="Type a message"]')
        message_box.send_keys(message)
        message_box.send_keys(Keys.ENTER)
        print(f"[📩] تم إرسال رسالة إلى {target_id}: {message}")
    except Exception as e:
        print(f"[❌] خطأ أثناء إرسال الرسالة إلى {target_id}: {e}")

# قائمة المحاضرات
def get_lectures_list():
    return [f for f in os.listdir(LECTURES_DIR) if f.lower().endswith('.pdf')]

# تسجيل الدخول
def initialize():
    driver.get("https://web.whatsapp.com")
    print("📸 افتح WhatsApp على هاتفك وامسح رمز QR من المتصفح. خذ وقتك للمسح.")
    time.sleep(10)
    max_attempts = 3
    for attempt in range(max_attempts):
        try:
            wait.until_not(EC.presence_of_element_located((By.XPATH, '//canvas[@aria-label="Scan me!"]')))
            wait.until(EC.presence_of_element_located((By.XPATH, '//div[@data-testid="chat-list-search"]')))
            print("✅ تم تسجيل الدخول بنجاح!")
            global GROUP_ID
            GROUP_ID = "افتراضي@g.us"  # استبدل بمعرف المجموعة الحقيقي لاحقًا
            break
        except Exception as e:
            print(f"[⚠️] فشل المحاولة {attempt + 1}/{max_attempts}: {e}")
            if attempt < max_attempts - 1:
                time.sleep(5)
            else:
                raise Exception("فشل تسجيل الدخول بعد عدة محاولات")

# معالجة الرسائل
def process_messages():
    global request_count
    metadata = load_metadata()
    try:
        messages = driver.find_elements(By.XPATH, '//div[contains(@class, "message-in")]')
        for msg in messages[-5:]:  # آخر 5 رسائل
            try:
                sender = msg.find_element(By.XPATH, './/span[@dir="auto"]').get_attribute("title")
                content = msg.find_element(By.XPATH, './/span[@class="selectable-text"]').text.strip()
                user_id = sender.replace(" ", "").replace("+", "") + "@c.us"
                print(f"[📩] رسالة من {sender} ({user_id}): {content}")

                # التراجع
                if user_id in user_state and content.lower() == "تراجع":
                    send_message(user_id, f"✅ تم إلغاء العملية، يا {sender}! ابدأ من جديد." + SIGNATURE)
                    del user_state[user_id]
                    continue

                # إضافة محاضرة
                if user_id in user_state and user_state[user_id]["step"].startswith("add_lecture_"):
                    state = user_state[user_id]
                    if state["step"] == "add_lecture_subject":
                        state["subject"] = content
                        user_state[user_id]["step"] = "add_lecture_group"
                        send_message(user_id, f"✅ تم حفظ المادة!\n📌 أدخل رقم الفوج (مثال: 1)\n💡 اكتب 'تراجع' للإلغاء." + SIGNATURE)
                    elif state["step"] == "add_lecture_group":
                        state["group"] = content
                        user_state[user_id]["step"] = "add_lecture_number"
                        send_message(user_id, f"✅ تم حفظ الفوج!\n📌 أدخل رقم المحاضرة (مثال: 1)\n💡 اكتب 'تراجع' للإلغاء." + SIGNATURE)
                    elif state["step"] == "add_lecture_number":
                        state["number"] = content
                        user_state[user_id]["step"] = "add_lecture_professor"
                        send_message(user_id, f"✅ تم حفظ الرقم!\n📌 أدخل اسم الأستاذ\n💡 اكتب 'تراجع' للإلغاء." + SIGNATURE)
                    elif state["step"] == "add_lecture_professor":
                        state["professor"] = content
                        user_state[user_id]["step"] = "add_lecture_file"
                        send_message(user_id, f"✅ تم حفظ الأستاذ!\n📎 أرفق ملف PDF واكتب تعليقًا ينتهي بـ .pdf (مثال: 'book.pdf')\n💡 اكتب 'تراجع' للإلغاء." + SIGNATURE)
                    elif state["step"] == "add_lecture_file":
                        if not content.lower().endswith(".pdf"):
                            send_message(user_id, f"❌ التعليق يجب أن ينتهي بـ .pdf، يا {sender}!\n💡 اكتب 'تراجع' للإلغاء." + SIGNATURE)
                            continue
                        filename = content
                        file_path = os.path.join(LECTURES_DIR, filename)
                        # ملاحظة: لا يمكن تحميل الملف مباشرة مع Selenium، يدويًا للتجربة
                        with open(file_path, "w") as f:
                            f.write("ملف وهمي")
                        metadata[filename] = {
                            "name": filename,
                            "subject": state["subject"],
                            "group": state["group"],
                            "number": state["number"],
                            "professor": state["professor"]
                        }
                        save_metadata(metadata)
                        summary = (
                            f"✅ *تمت الإضافة!*\n"
                            f"📚 المادة: {state['subject']}\n"
                            f"👥 الفوج: {state['group']}\n"
                            f"🔢 الرقم: {state['number']}\n"
                            f"👨‍🏫 الأستاذ: {state['professor']}\n"
                            f"📎 الملف: {filename}\n{SIGNATURE}"
                        )
                        send_message(user_id, summary)
                        del user_state[user_id]
                    continue

                # الأوامر
                if content.lower() == "إضافة محاضرة":
                    user_state[user_id] = {"step": "add_lecture_subject"}
                    send_message(user_id, f"📌 أدخل اسم المادة (مثال: رياضيات)\n💡 اكتب 'تراجع' للإلغاء." + SIGNATURE)
                elif content.lower() in ["عرض المحاضرات", "pdf"]:
                    lectures = get_lectures_list()
                    if not lectures:
                        send_message(user_id, f"📂 لا توجد محاضرات، يا {sender}." + SIGNATURE)
                    else:
                        lecture_list = "📚 قائمة المحاضرات:\n"
                        for i, lecture in enumerate(lectures, 1):
                            lecture_list += f"{i}. {metadata.get(lecture, {}).get('name', lecture)}\n"
                        lecture_list += f"✉️ أرسل رقم المحاضرة (مثال: 1)"
                        send_message(user_id, lecture_list + SIGNATURE)
                        user_state[user_id] = {"step": "select_lecture", "lectures": lectures}
                elif content.lower() == "البحث عن محاضرة":
                    user_state[user_id] = {"step": "search_lecture"}
                    send_message(user_id, f"🔍 أرسل كلمة للبحث (مثال: رياضيات)" + SIGNATURE)
                elif content.lower() == "الإحصائيات":
                    lectures = get_lectures_list()
                    stats = (
                        f"📊 *إحصائيات البوت:*\n"
                        f"- عدد المحاضرات: {len(lectures)}\n"
                        f"- عدد الطلبات: {request_count}\n{SIGNATURE}"
                    )
                    send_message(user_id, stats)
                elif content.lower() == "إغلاق المجموعة" and user_id == ALLOWED_USER:
                    send_message(GROUP_ID, f"🚫 تم إغلاق المجموعة بواسطة {sender}!" + SIGNATURE)
                elif content.lower() == "فتح المجموعة" and user_id == ALLOWED_USER:
                    send_message(GROUP_ID, f"✅ تم فتح المجموعة بواسطة {sender}!" + SIGNATURE)

                # اختيار محاضرة
                if user_id in user_state and user_state[user_id]["step"] == "select_lecture":
                    try:
                        lecture_index = int(content) - 1
                        lectures = user_state[user_id]["lectures"]
                        if 0 <= lecture_index < len(lectures):
                            selected = lectures[lecture_index]
                            send_message(user_id, f"📎 المحاضرة: {selected} (الملف غير مرسل بعد)" + SIGNATURE)
                            request_count += 1
                            del user_state[user_id]
                        else:
                            send_message(user_id, f"⚠️ رقم غير صحيح، يا {sender}!" + SIGNATURE)
                    except ValueError:
                        send_message(user_id, f"⚠️ أرسل رقمًا، يا {sender}!" + SIGNATURE)

                # البحث
                if user_id in user_state and user_state[user_id]["step"] == "search_lecture":
                    query = content.lower()
                    lectures = get_lectures_list()
                    filtered = [l for l in lectures if query in l.lower() or query in metadata.get(l, {}).get("subject", "").lower()]
                    if not filtered:
                        send_message(user_id, f"📂 لا توجد نتائج لـ '{query}'، يا {sender}." + SIGNATURE)
                    else:
                        lecture_list = f"📚 نتائج البحث عن '{query}':\n"
                        for i, lecture in enumerate(filtered, 1):
                            lecture_list += f"{i}. {metadata.get(lecture, {}).get('name', lecture)}\n"
                        lecture_list += f"✉️ أرسل رقم المحاضرة"
                        send_message(user_id, lecture_list + SIGNATURE)
                        user_state[user_id] = {"step": "select_lecture", "lectures": filtered}

            except Exception as e:
                print(f"[❌] خطأ في معالجة رسالة: {e}")
    except Exception as e:
        print(f"[❌] خطأ عام في process_messages: {e}")

# جدولة إغلاق وفتح المجموعة
def close_group():
    if GROUP_ID:
        send_message(GROUP_ID, "🚫 تم إغلاق المجموعة الساعة 10:00 مساءً." + SIGNATURE)

def open_group():
    if GROUP_ID:
        send_message(GROUP_ID, "✅ تم فتح المجموعة الساعة 8:00 صباحًا." + SIGNATURE)

schedule.every().day.at("22:00").do(close_group)
schedule.every().day.at("08:00").do(open_group)

# التشغيل الرئيسي
def main():
    initialize()
    print("🚀 تم تشغيل البوت بنجاح!")
    while True:
        process_messages()
        schedule.run_pending()
        time.sleep(5)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"[❌] خطأ أثناء التشغيل: {e}")
        driver.quit()