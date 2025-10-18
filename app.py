# app.py
import streamlit as st
import pandas as pd
import re
import time
import json
import os
import uuid
import streamlit.components.v1 as components

# ===============================
# CONFIG
# ===============================
TOKENS_FILE = "tokens.json"
TRIAL_SECONDS = 60   # مدة التجربة المجانية بالثواني
ADMIN_PASSWORD = "admin123"   # عدّلها للباسورد اللي تحب لإدارة التوكنات
USER_PASSWORD = "1234"        # باسورد الوصول بعد انتهاء التجربة (حسب طلبك)

# ===============================
# Utilities: load/save tokens with robustness
# ===============================
def init_tokens_file():
    if not os.path.exists(TOKENS_FILE):
        with open(TOKENS_FILE, "w") as f:
            json.dump({}, f)

def load_tokens():
    init_tokens_file()
    try:
        with open(TOKENS_FILE, "r") as f:
            content = f.read().strip()
            if not content:
                return {}
            return json.loads(content)
    except (json.JSONDecodeError, ValueError):
        # إذا الملف تالف -> إصلاحه بملف فارغ
        with open(TOKENS_FILE, "w") as f:
            json.dump({}, f)
        return {}

def save_tokens(tokens):
    with open(TOKENS_FILE, "w") as f:
        json.dump(tokens, f, indent=4, ensure_ascii=False)

# ===============================
# Token model:
# tokens.json structure:
# {
#   "ABC123": {
#       "created_at": 1690000000,
#       "used": False,
#       "used_at": 0,
#       "owner": "",           # optional label (who you gave the link to)
#       "note": ""
#   }, ...
# }
# ===============================

def generate_token():
    # استخدم uuid4 واقتطع جزء ليكون قابل للنسخ
    return uuid.uuid4().hex[:12].upper()

# ===============================
# Frontend: copy button JS
# ===============================
COPY_JS = """
<script>
function copyToClipboard(text) {
  navigator.clipboard.writeText(text).then(function() {
    // success
  }, function(err) {
    console.error('Async: Could not copy text: ', err);
  });
}
</script>
"""

# ===============================
# Countdown renderer (client-side)
# ===============================
def render_countdown(start_ts, seconds=TRIAL_SECONDS):
    html = f"""
    <div id="countdown" style="font-family:Segoe UI, Tahoma, Geneva, Verdana, sans-serif; margin-top:10px;">
      <h4>⏳ التجربة المجانية متبقي: <span id='secs'>--</span> ثانية</h4>
      <div style="width:100%; background:#eee; border-radius:6px; height:12px; margin-top:6px;">
        <div id="bar" style="height:12px; width:100%; background:#4caf50; border-radius:6px; transition:width 1s linear;"></div>
      </div>
    </div>

    <script>
    const start_ts = {int(start_ts)} * 1000;
    const total = {int(seconds)};
    function update(){{
      const now = Date.now();
      let elapsed = Math.floor((now - start_ts)/1000);
      if(elapsed < 0) elapsed = 0;
      let remaining = total - elapsed;
      if(remaining < 0) remaining = 0;
      document.getElementById('secs').innerText = remaining;
      document.getElementById('bar').style.width = (remaining/total*100) + '%';
      setTimeout(update, 1000);
    }}
    update();
    </script>
    """
    components.html(html, height=120)

# ===============================
# Core logic when a visitor opens app with ?token=XYZ
# ===============================
def handle_incoming_token(token):
    tokens = load_tokens()
    now_ts = int(time.time())

    if token not in tokens:
        st.error("هذا الرابط غير صالح أو لم يتم إنشاؤه من قِبل المدير.")
        return False

    t = tokens[token]
    # إذا التوكن لم يستخدم => تفعيل التجربة ووسم التوكن كمستخدم
    if not t.get("used", False):
        # تفعيل تجربة مجانية للزائر الحالي (نخزن وقت البدء في session_state)
        # وليكن مفتاح session مرتبط بالتوكن لضمان كل توكن جلسة مستقلة
        key = f"trial_start_{token}"
        if key not in st.session_state:
            st.session_state[key] = int(time.time())
            # وعلشان نحفظ أن التوكن استُخدم (مرة واحدة فقط)
            t["used"] = True
            t["used_at"] = now_ts
            save_tokens(tokens)
            st.success("🎁 تم تفعيل التجربة المجانية لمدة {} ثانية ⏳".format(TRIAL_SECONDS))
        # عرض العداد
        elapsed = int(time.time()) - st.session_state.get(key, 0)
        if elapsed < TRIAL_SECONDS:
            render_countdown(st.session_state[key], TRIAL_SECONDS)
            st.info("✅ التجربة المجانية مفعلة — استخدم التطبيق الآن")
            return True
        else:
            st.warning("⏰ انتهت التجربة المجانية لهذا الرابط.")
            # بعد انتهاء التجربة نعرض باسورد
            return False
    else:
        # التوكن مُستخدم بالفعل مسبقًا
        st.warning("⚠ هذا الرابط استُخدم مسبقاً. للدخول أدخل كلمة المرور.")
        return False

# ===============================
# Admin tools: توليد روابط وادارتها
# ===============================
def admin_panel(base_url):
    st.header("🔐 لوحة إدارة التوكنات (Admin)")
    pwd = st.text_input("أدخل باسورد الأدمن:", type="password")
    if pwd != ADMIN_PASSWORD:
        st.info("أدخل كلمة المرور لعرض أدوات الإدارة.")
        return

    st.success("مرحباً أدمين — يمكنك توليد روابط وإدارتها.")

    tokens = load_tokens()

    col1, col2 = st.columns([2,1])
    with col1:
        n = st.number_input("كم رابط تولد الآن؟", min_value=1, max_value=100, value=1)
        owner = st.text_input("وضع وسم/اسم مُستلم (اختياري):", value="")
        note = st.text_input("ملاحظة (اختياري):", value="")
        if st.button("توليد الرابط/الروابط"):
            new = {}
            for _ in range(int(n)):
                tk = generate_token()
                tokens[tk] = {
                    "created_at": int(time.time()),
                    "used": False,
                    "used_at": 0,
                    "owner": owner or "",
                    "note": note or ""
                }
                new[tk] = tokens[tk]
            save_tokens(tokens)
            st.success(f"✅ تم توليد {n} رابط/روابط.")
            # عرض الروابط كاملة
            st.write("الروابط الناتجة (انسخها وابعثها):")
            for tk in new:
                link = f"{base_url.rstrip('/')}/?token={tk}"
                st.code(link)
                st.markdown(f"<button onclick=\"navigator.clipboard.writeText('{link}')\">نسخ الرابط</button>", unsafe_allow_html=True)

    with col2:
        if st.button("تحديث قائمة التوكنات"):
            tokens = load_tokens()
        st.markdown("### قائمة التوكنات")
        if tokens:
            df = []
            for k, v in tokens.items():
                created = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(v.get("created_at",0))) if v.get("created_at") else "-"
                used = v.get("used", False)
                used_at = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(v.get("used_at",0))) if v.get("used_at") else "-"
                owner = v.get("owner","")
                note = v.get("note","")
                df.append({"token":k, "owner":owner, "used":used, "used_at":used_at, "created":created, "note":note})
            st.dataframe(pd.DataFrame(df))
        else:
            st.write("لا توجد توكنات حتى الآن.")

    st.markdown("---")
    if st.button("حذف كل التوكنات (احذر)"):
        save_tokens({})
        st.warning("✅ تم حذف كل التوكنات.")

# ===============================
# Main app
# ===============================
def main():
    st.set_page_config(page_title="نظام روابط تجريبية مرّة واحدة", layout="wide")
    st.title("🔧 نظام روابط تجريبية لمرة واحدة + حماية بكلمة مرور بعد الاستخدام")

    # Sidebar: base URL and admin quick access
    st.sidebar.header("إعدادات")
    base_url = st.sidebar.text_input("Base app URL (ضع رابط التطبيق هنا لاستخراج روابط كاملة)", value="https://your-app-url")
    mode = st.sidebar.selectbox("أعرض:", ["زائر (افتراضي)", "لوحة الإدارة (admin)"])
    st.sidebar.markdown("---")
    st.sidebar.markdown("ملاحظة: الرابط الكامل يجب أن يكون على شكل: `https://your-app-url/?token=ABC...`")

    # إذا اختار admin -> اعرض لوحة الادارة
    if mode == "لوحة الإدارة (admin)":
        admin_panel(base_url)
        return

    # زائر: نتحقق إن فيه ?token= في العنوان عبر st.experimental_get_query_params
    params = st.experimental_get_query_params()
    token = None
    if "token" in params:
        token = params.get("token")[0]

    st.markdown("### كيف يعمل:")
    st.markdown("- قم بتوليد رابط فريد من لوحة الإدارة ثم أرسله لأي شخص.")
    st.markdown("- الرابط يعطي تجربة مجانية لمرة واحدة فقط (60 ثانية).")
    st.markdown("- بعد انتهاء التجربة أو لو استخدم الرابط سابقًا، سيُطلب إدخال كلمة المرور للوصول.")

    st.markdown("---")

    # إذا وصل الزائر عبر رابط مع توكن
    if token:
        st.info(f"رابط التوكن: `{token}`")
        allowed = handle_incoming_token(token)
        if allowed:
            # هنا اجعل التطبيق العادي / صفحة النتيجة تظهر للزائر
            st.success("يمكنك الآن استخدام التطبيق أثناء فترة التجربة.")
            # يمكنك وضع هنا الواجهة الخاصة بك (مثلاً الفورم لحالة الماكينات)
            st.write("**هنا تحط محتوى التطبيق الذي تريد إتاحته أثناء التجربة.**")
            # مثال: إدخالات بسيطة
            who = st.text_input("اكتب اسمك (اختياري):")
            st.write("تجربة فقط — افعل ما تريد هنا.")
        else:
            # توكن مستخدم أو انتهت التجربة -> نعرض حقل باسورد للولوج
            password = st.text_input("أدخل كلمة المرور للوصول:", type="password")
            if password == USER_PASSWORD:
                st.success("✅ تم قبول كلمة المرور — لديك وصول كامل الآن.")
                st.write("**هنا محتوى التطبيق بعد إدخال الباسورد.**")
            else:
                st.info("أدخل الباسورد للوصول أو استخدم رابط آخر غير مستخدم.")
    else:
        # لم تأتِ بتوكن في الرابط: عرض تعليمات أو واجهة لإدخال توكن يدوياً
        st.warning("لم يتم تزويد توكن في الرابط. إذا لديك توكن، يمكنك إدخاله هنا أو اطلب من المدير رابط تجريبي.")
        manual = st.text_input("أدخل التوكن يدوياً (مثلاً ABC123):")
        if manual:
            allowed = handle_incoming_token(manual.strip())
            if allowed:
                st.success("يمكنك الآن استخدام التطبيق خلال فترة التجربة.")
                st.write("**محتوى التطبيق هنا**")
            else:
                pwd = st.text_input("أدخل كلمة المرور للوصول:", type="password", key="manual_pwd")
                if pwd == USER_PASSWORD:
                    st.success("✅ تم قبول كلمة المرور — لديك وصول كامل الآن.")
                    st.write("**محتوى التطبيق بعد إدخال الباسورد.**")

if __name__ == "__main__":
    main()
