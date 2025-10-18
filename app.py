import streamlit as st
import pandas as pd
import re
import time
import json
import os
import streamlit.components.v1 as components

# ===============================
# 📂 تحميل البيانات من الإكسيل
# ===============================
@st.cache_data
def load_all_sheets():
    try:
        return pd.read_excel("Machine_Service_Lookup.xlsx", sheet_name=None)
    except FileNotFoundError:
        st.error("❌ لم يتم العثور على الملف Machine_Service_Lookup.xlsx في نفس المجلد.")
        st.stop()

# ===============================
# 🔠 دوال مساعدة
# ===============================
def normalize_name(s):
    if s is None:
        return ""
    s = str(s)
    s = s.replace("\n", "+")
    s = re.sub(r"👦.*?👦", "", s)
    s = re.sub(r"[^0-9a-zA-Z\u0600-\u06FF\+\s_/.-]", " ", s)
    s = re.sub(r"\s+", " ", s).strip().lower()
    return s

def split_needed_services(needed_service_str):
    if not isinstance(needed_service_str, str) or needed_service_str.strip() == "":
        return []
    parts = re.split(r"\+|,|\n|;", needed_service_str)
    return [p.strip() for p in parts if p.strip() != ""]

# ===============================
# 🔑 نظام الـ Tokens مع عداد التجربة
# ===============================
TOKENS_FILE = "tokens.json"

def load_tokens():
    if not os.path.exists(TOKENS_FILE):
        with open(TOKENS_FILE, "w") as f:
            json.dump({}, f)
    with open(TOKENS_FILE, "r") as f:
        return json.load(f)

def save_tokens(tokens):
    with open(TOKENS_FILE, "w") as f:
        json.dump(tokens, f, indent=4, ensure_ascii=False)

# ===============================
# 🧩 دالة عرض العداد (Client-side)
# ===============================
def render_countdown(trial_start_ts, seconds=60):
    """
    عداد تنازلي بالـ HTML/JS يشتغل فعليًا من لحظة البدء
    """
    html = f"""
    <div id="countdown" style="font-family:Segoe UI, Tahoma, Geneva, Verdana, sans-serif; margin-top:10px;">
      <h4>⏳ التجربة المجانية متبقي: <span id='secs'>--</span> ثانية</h4>
      <div style="width:100%; background:#eee; border-radius:6px; height:12px; margin-top:6px;">
        <div id="bar" style="height:12px; width:100%; background:#4caf50; border-radius:6px; transition:width 1s linear;"></div>
      </div>
    </div>

    <script>
    const start_ts = {int(trial_start_ts)} * 1000;
    const total = {int(seconds)};
    function update(){{
      const now = Date.now();
      let elapsed = Math.floor((now - start_ts)/1000);
      if(elapsed < 0) elapsed = 0;
      let remaining = total - elapsed;
      if(remaining < 0) remaining = 0;
      document.getElementById('secs').innerText = remaining;
      document.getElementById('bar').style.width = (remaining/total*100) + '%';
      if(remaining <= 0){{
        const url = new URL(window.location.href);
        url.searchParams.set('expired', '1');
        window.location.href = url.toString();
      }} else {{
        setTimeout(update, 1000);
      }}
    }}
    update();
    </script>
    """
    components.html(html, height=120)

# ===============================
# 🔑 نظام الـ Tokens (معدّل)
# ===============================
def check_token():
    st.subheader("🔐 الدخول / تفعيل رمز تجربة")

    tokens = load_tokens()
    available_tokens = [t for t, v in tokens.items() if not v.get("used", False)]

    # ⚙ التبديل إلى st.query_params بدلاً من experimental
    params = st.query_params
    expired = params.get("expired", ["0"])[0] if isinstance(params.get("expired"), list) else params.get("expired", "0")

    # إذا انتهت التجربة المجانية
    if expired == "1":
        st.error("⏰ انتهت التجربة المجانية. أدخل كلمة المرور للمتابعة.")
        password = st.text_input("كلمة المرور:", type="password")
        if password == "1234":
            st.success("✅ تم تسجيل الدخول بنجاح (بالباسورد).")
            st.session_state["access_granted"] = True
            return True
        else:
            st.stop()

    # لو عنده صلاحية دخول كاملة
    if st.session_state.get("access_granted", False):
        if "trial_start" in st.session_state:
            render_countdown(st.session_state["trial_start"], seconds=60)
        return True

    # لو التجربة المجانية شغالة
    if "trial_start" in st.session_state:
        elapsed = int(time.time() - st.session_state["trial_start"])
        if elapsed < 60:
            render_countdown(st.session_state["trial_start"], seconds=60)
            st.info("✅ التجربة المجانية مفعّلة — يمكنك استخدام التطبيق حتى انتهاء العداد.")
            return True
        else:
            st.error("⏰ انتهت التجربة المجانية. أدخل كلمة المرور للمتابعة.")
            password = st.text_input("كلمة المرور:", type="password")
            if password == "1234":
                st.success("✅ تم تسجيل الدخول بنجاح.")
                st.session_state["access_granted"] = True
                return True
            else:
                st.stop()

    # لو لسه مفيش جلسة نشطة — عرض التوكنات
    if available_tokens:
        token = st.selectbox("اختر رمز التجربة المجانية:", available_tokens)
        if st.button("تفعيل الرمز"):
            tokens[token]["used"] = True
            save_tokens(tokens)
            st.session_state["trial_start"] = time.time()
            st.success(f"🎁 تم تفعيل الرمز ({token}) — التجربة المجانية بدأت الآن لمدة 60 ثانية ⏳")
            st.rerun()
    else:
        st.warning("🔒 جميع الرموز استخدمت. أدخل كلمة المرور للوصول:")
        password = st.text_input("كلمة المرور:", type="password")
        if password == "1234":
            st.success("✅ تم تسجيل الدخول بنجاح.")
            st.session_state["access_granted"] = True
            return True
        else:
            st.stop()

    return False

# ===============================
# ⚙ دالة مقارنة الصيانة
# ===============================
def check_machine_status(card_num, current_tons, all_sheets):
    if "ServicePlan" not in all_sheets or "Machine" not in all_sheets:
        st.error("❌ الملف لازم يحتوي على شيتين: 'Machine' و 'ServicePlan'")
        return None

    service_plan_df = all_sheets["ServicePlan"]
    card_sheet_name = f"Card{card_num}"
    if card_sheet_name not in all_sheets:
        st.warning(f"⚠ لا يوجد شيت باسم {card_sheet_name}")
        return None

    card_df = all_sheets[card_sheet_name]
    current_slice = service_plan_df[
        (service_plan_df["Min_Tons"] <= current_tons) &
        (service_plan_df["Max_Tons"] >= current_tons)
    ]

    if current_slice.empty:
        st.warning("⚠ لم يتم العثور على شريحة تناسب عدد الأطنان الحالي.")
        return None

    min_tons = current_slice["Min_Tons"].values[0]
    max_tons = current_slice["Max_Tons"].values[0]
    needed_service_raw = current_slice["Service"].values[0]
    needed_parts = split_needed_services(needed_service_raw)
    needed_norm = [normalize_name(p) for p in needed_parts]

    slice_df = card_df[
        (card_df["card"] == card_num) &
        (card_df["Tones"] >= min_tons) &
        (card_df["Tones"] <= max_tons)
    ]

    done_services, last_date, last_tons = [], "-", "-"
    status = "❌ لم يتم تنفيذ صيانة في هذه الشريحة"

    if not slice_df.empty:
        last_row = slice_df.iloc[-1]
        last_date = last_row.get("Date", "-")
        last_tons = last_row.get("Tones", "-")

        ignore_cols = ["card", "Tones", "Date", "Current_Tons", "Service Needed", "Min_Tons", "Max_Tons"]
        for col in card_df.columns:
            if col not in ignore_cols:
                val = str(last_row.get(col, "")).strip().lower()
                if val and val not in ["nan", "none", ""]:
                    done_services.append(col)
        if done_services:
            status = "✅ تم تنفيذ صيانة في هذه الشريحة"

    done_norm = [normalize_name(c) for c in done_services]
    not_done = [orig for orig, n in zip(needed_parts, needed_norm) if n not in done_norm]

    result = {
        "Card": card_num,
        "Current_Tons": current_tons,
        "Service Needed": " + ".join(needed_parts) if needed_parts else "-",
        "Done Services": ", ".join(done_services) if done_services else "-",
        "Not Done Services": ", ".join(not_done) if not_done else "-",
        "Date": last_date,
        "Tones": last_tons,
        "Status": status,
    }

    st.dataframe(pd.DataFrame([result]), use_container_width=True)

# ===============================
# 🖥 واجهة Streamlit
# ===============================
st.title("🔧 نظام متابعة الصيانة التنبؤية")

if check_token():
    all_sheets = load_all_sheets()
    st.write("أدخل رقم الماكينة وعدد الأطنان الحالية لمعرفة حالة الصيانة")
    card_num = st.number_input("رقم الماكينة:", min_value=1, step=1)
    current_tons = st.number_input("عدد الأطنان الحالية:", min_value=0, step=100)
    if st.button("عرض الحالة"):
        check_machine_status(card_num, current_tons, all_sheets)
