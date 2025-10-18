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
# 🔑 نظام الـ Tokens مع عداد التجربة
# ===============================
TOKENS_FILE = "tokens.json"
TRIAL_DURATION = 24 * 3600  # 24 ساعة بالثواني

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
# 🧩 دالة عرض العداد (HTML/JS)
# ===============================
def render_countdown(trial_start_ts, seconds=TRIAL_DURATION):
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
      setTimeout(update, 1000);
    }}
    update();
    </script>
    """
    components.html(html, height=120)

# ===============================
# 🔑 نظام الـ Tokens المحسّن
# ===============================
def check_token():
    st.subheader("🔐 الدخول / تفعيل رمز تجربة")

    tokens = load_tokens()
    available_tokens = []

    now_ts = int(time.time())

    # تحقق من صلاحية كل توكن
    for t, v in tokens.items():
        trial_start = v.get("trial_start", 0)
        if not v.get("used", False) or now_ts - trial_start >= TRIAL_DURATION:
            available_tokens.append(t)

    params = st.query_params
    expired = params.get("expired", ["0"])[0] if isinstance(params.get("expired"), list) else params.get("expired", "0")

    # كلمة مرور بديلة
    PASSWORD = "1234"

    # إذا انتهت التجربة المجانية
    if expired == "1":
        st.error("⏰ انتهت التجربة المجانية. أدخل كلمة المرور للمتابعة.")
        password = st.text_input("كلمة المرور:", type="password")
        if password == PASSWORD:
            st.success("✅ تم تسجيل الدخول بنجاح (بالباسورد).")
            st.session_state["access_granted"] = True
            return True
        else:
            st.stop()

    # لو عنده صلاحية دخول كاملة
    if st.session_state.get("access_granted", False):
        return True

    # اختيار توكن متاح
    if available_tokens:
        token = st.selectbox("اختر رمز التجربة المجانية:", available_tokens)
        if st.button("تفعيل الرمز"):
            tokens[token]["used"] = True
            tokens[token]["trial_start"] = now_ts
            save_tokens(tokens)
            st.session_state["trial_start"] = now_ts
            st.success(f"🎁 تم تفعيل الرمز ({token}) — التجربة المجانية بدأت الآن لمدة 24 ساعة ⏳")
            st.rerun()
    else:
        st.warning("🔒 جميع الرموز مستخدمة خلال الـ 24 ساعة الأخيرة. أدخل كلمة المرور للوصول:")
        password = st.text_input("كلمة المرور:", type="password")
        if password == PASSWORD:
            st.success("✅ تم تسجيل الدخول بنجاح.")
            st.session_state["access_granted"] = True
            return True
        else:
            st.stop()

    # إذا بدأ التجربة سابقًا
    if "trial_start" in st.session_state:
        elapsed = now_ts - st.session_state["trial_start"]
        if elapsed < TRIAL_DURATION:
            render_countdown(st.session_state["trial_start"], seconds=TRIAL_DURATION)
            st.info("✅ التجربة المجانية مفعّلة — يمكنك استخدام التطبيق حتى انتهاء العداد.")
            return True
        else:
            st.error("⏰ انتهت التجربة المجانية. أدخل كلمة المرور للمتابعة.")
            password = st.text_input("كلمة المرور:", type="password")
            if password == PASSWORD:
                st.success("✅ تم تسجيل الدخول بنجاح.")
                st.session_state["access_granted"] = True
                return True
            else:
                st.stop()

    return False

# ⚙ دالة مقارنة الصيانة
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

    result_df = pd.DataFrame([result])

    # 🎨 تلوين الأعمدة
    def highlight_cell(val, col_name):
        if col_name == "Service Needed":
            return "background-color: #fff3cd; color:#856404; font-weight:bold;"  # أصفر
        elif col_name == "Done Services":
            return "background-color: #d4edda; color:#155724; font-weight:bold;"  # أخضر
        elif col_name == "Not Done Services":
            return "background-color: #f8d7da; color:#721c24; font-weight:bold;"  # أحمر
        elif col_name in ["Date", "Tones"]:
            return "background-color: #e7f1ff; color:#004085;"  # أزرق فاتح
        elif col_name == "Status":
            if "✅" in val:
                return "background-color:#c3e6cb; color:#155724;"
            else:
                return "background-color:#f5c6cb; color:#721c24;"
        return ""

    def style_table(row):
        return [highlight_cell(row[col], col) for col in row.index]

    styled_df = result_df.style.apply(style_table, axis=1)
    st.dataframe(styled_df, use_container_width=True)

    save = st.button("💾 حفظ النتيجة في Excel")
    if save:
        result_df.to_excel("Machine_Result.xlsx", index=False)
        st.success("✅ تم حفظ النتيجة في ملف 'Machine_Result.xlsx' بنجاح.")

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
