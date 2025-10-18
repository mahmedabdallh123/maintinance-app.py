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
# 🧩 دالة عرض العداد (Client-side) بالـ HTML/JS
# ===============================
def render_countdown(trial_start_ts, seconds=60):
    """
    يعرض عدادًا تنازليًا في المتصفح يبدأ من (seconds) اعتمادًا على trial_start_ts (unix seconds).
    عند انتهاء العدّ يعيد توجيه الصفحة مع expired=1
    """
    html = f"""
    <div id="countdown" style="font-family:Segoe UI, Tahoma, Geneva, Verdana, sans-serif;">
      <h4>⏳ التجربة المجانية متبقي: <span id='secs'>--</span> ثانية</h4>
      <div style="width:100%; background:#eee; border-radius:6px; height:12px; margin-top:6px;">
        <div id="bar" style="height:12px; width:0%; background:#4caf50; border-radius:6px;"></div>
      </div>
    </div>

    <script>
    const start_ts = {int(trial_start_ts)} * 1000; // ms
    const total = {int(seconds)}; // seconds
    function update(){{
      const now = Date.now();
      let elapsed = Math.floor((now - start_ts)/1000);
      if(elapsed < 0) elapsed = 0;
      let remaining = total - elapsed;
      if(remaining < 0) remaining = 0;
      document.getElementById('secs').innerText = remaining;
      const pct = Math.max(0, Math.min(100, ((total - remaining) / total) * 100));
      document.getElementById('bar').style.width = pct + '%';
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
    components.html(html, height=100)

# ===============================
# 🔑 نظام الـ Tokens (معدّل ليعرض العداد ويترك التفاعل شغّال)
# ===============================
def check_token():
    st.subheader("🔐 الدخول / تفعيل رمز تجربة")

    tokens = load_tokens()
    available_tokens = [t for t, v in tokens.items() if not v.get("used", False)]

    # لو باراميتر expired موجود في الرابط → انتهت التجربة، اطلب باسورد
    params = st.experimental_get_query_params()
    if params.get("expired", ["0"])[0] == "1":
        st.error("⏰ انتهت التجربة المجانية. أدخل كلمة المرور للمتابعة.")
        password = st.text_input("كلمة المرور:", type="password")
        if password == "1234":
            st.success("✅ تم تسجيل الدخول بنجاح (بالباسورد).")
            st.session_state["access_granted"] = True
            return True
        else:
            st.stop()

    # لو المستخدم مفعل دخول كامل سابقًا
    if st.session_state.get("access_granted", False):
        # لو في trial_start نعرض العداد كإشارة لكن السماح بالاستخدام حتى الانتهاء
        if "trial_start" in st.session_state:
            render_countdown(st.session_state["trial_start"], seconds=60)
        return True

    # لو الجلسة التجريبية بدأت بالفعل (server-side) — نتحقق زمنياً ونسمح بالاستخدام
    if "trial_start" in st.session_state:
        elapsed = int(time.time() - st.session_state["trial_start"])
        if elapsed < 60:
            # عرض العداد client-side
            render_countdown(st.session_state["trial_start"], seconds=60)
            st.info("✅ التجربة المجانية مفعّلة — يمكنك استخدام التطبيق حتى انتهاء العداد.")
            return True
        else:
            # انتهت التجربة (لم يتم إدخال باسورد بعد)
            st.error("⏰ انتهت التجربة المجانية. يرجى إدخال كلمة المرور للمتابعة.")
            password = st.text_input("كلمة المرور:", type="password")
            if password == "1234":
                st.success("✅ تم تسجيل الدخول بنجاح (بالباسورد).")
                st.session_state["access_granted"] = True
                return True
            else:
                st.stop()

    # لو لسه في توكنات متاحة، اعرضها للاختيار
    if available_tokens:
        token = st.selectbox("اختر رمز التجربة المجانية:", available_tokens)
        if st.button("تفعيل الرمز"):
            tokens[token]["used"] = True
            save_tokens(tokens)
            st.session_state["trial_start"] = time.time()
            st.success(f"🎁 تم تفعيل الرمز ({token}) — التجربة المجانية بدأت الآن لمدة 60 ثانية ⏳")
            # بعد التفعيل نعيد تحميل الصفحة عشان الـ JS يقرأ القيمة الجديدة
            st.experimental_rerun()
    else:
        # لو مفيش توكنات متاحة — اطلب باسورد
        st.warning("🔒 جميع الرموز استخدمت. أدخل كلمة المرور للوصول:")
        password = st.text_input("كلمة المرور:", type="password")
        if password == "1234":
            st.success("✅ تم تسجيل الدخول بنجاح (بالباسورد).")
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

        ignore_cols = ["card", "Tones", "Date", "Current_Tons",
                       "Service Needed", "Min_Tons", "Max_Tons"]

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

    def highlight(val, col_name):
        if col_name == "Service Needed":
            return "background-color: #fff3cd; color: #856404; font-weight: bold;"
        elif col_name == "Done Services":
            return "background-color: #d4edda; color: #155724; font-weight: bold;"
        elif col_name == "Not Done Services":
            return "background-color: #f8d7da; color: #721c24; font-weight: bold;"
        elif col_name == "Status":
            if "✅" in val:
                return "background-color: #c3e6cb; color: #155724;"
            else:
                return "background-color: #f5c6cb; color: #721c24;"
        return ""

    def style_table(row):
        return [highlight(row[col], col) for col in row.index]

    styled_df = result_df.style.apply(style_table, axis=1)
    st.dataframe(styled_df, use_container_width=True)

    save = st.button("💾 حفظ النتيجة في Excel")
    if save:
        result_df.to_excel("Machine_Result.xlsx", index=False)
        st.success("✅ تم حفظ النتيجة في ملف 'Machine_Result.xlsx' بنجاح.")

    return result_df

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
