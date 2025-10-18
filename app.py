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
    params = st.query_params
    token = params.get("token", [None])[0] if isinstance(params.get("token"), list) else params.get("token")

    if not token:
        st.warning("🚫 لم يتم تمرير رمز (token) في الرابط.")
        return False

    with open("tokens.json", "r", encoding="utf-8") as f:
        tokens = json.load(f)

    # لو الرمز مش موجود
    if token not in tokens:
        st.error("❌ هذا الرمز غير صالح أو غير مسموح به.")
        return False

    token_data = tokens[token]
    now = datetime.datetime.now()

    # لو تم استخدامه سابقًا
    if token_data.get("used", False):
        last_used_str = token_data.get("last_used")
        if last_used_str:
            last_used = datetime.datetime.fromisoformat(last_used_str)
            elapsed = (now - last_used).total_seconds() / 3600  # بالساعات

            if elapsed < 24:
                remaining = 24 - elapsed
                st.error(f"⏳ لقد استخدمت التجربة المجانية مؤخرًا. حاول بعد {remaining:.1f} ساعة.")
                return False
            else:
                # إعادة التفعيل بعد 24 ساعة
                token_data["used"] = False

    # تفعيل التجربة
    st.success(f"🎁 تم تفعيل الرمز ({token}) — التجربة المجانية بدأت الآن لمدة 60 ثانية ⏳")

    # تحديث حالة التوكين
    token_data["used"] = True
    token_data["last_used"] = now.isoformat()
    tokens[token] = token_data

    with open("tokens.json", "w", encoding="utf-8") as f:
        json.dump(tokens, f, indent=2, ensure_ascii=False)

    st.session_state["free_trial_active"] = True
    st.session_state["trial_start_time"] = now.timestamp()
    st.session_state["trial_duration"] = 60

    return True

# ===============================
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
