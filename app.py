import streamlit as st
import pandas as pd
import re
import time
import json
import os

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
# 🔑 نظام الـ Tokens لتجربة مجانية
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
        json.dump(tokens, f, indent=4)

def check_token():
    query_params = st.query_params
    token = query_params.get("token", [None])[0]

    if not token:
        st.error("🚫 لم يتم تمرير رمز (token) في الرابط.")
        st.stop()

    tokens = load_tokens()

    if token not in tokens:
        st.error("❌ هذا الرمز غير صالح أو غير مسموح به.")
        st.stop()

    if tokens[token]["used"]:
        st.error("🔒 تم استخدام هذا الرابط مسبقًا. يرجى إدخال كلمة المرور للمتابعة.")
        password = st.text_input("كلمة المرور:", type="password")
        if password == "1234":
            st.success("✅ تم تسجيل الدخول بنجاح.")
            return True
        else:
            st.stop()
    else:
        st.info("🎁 تجربة مجانية متاحة لهذا الرابط. سيتم تسجيلها الآن.")
        tokens[token]["used"] = True
        save_tokens(tokens)
        return True


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

    # 🎨 تلوين الجدول
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
    st.write("أدخل رقم الماكينة وعدد الأطنان الحالية لمعرفة حالة الصيانة")
    all_sheets = load_all_sheets()
    card_num = st.number_input("رقم الماكينة:", min_value=1, step=1)
    current_tons = st.number_input("عدد الأطنان الحالية:", min_value=0, step=100)

    if st.button("عرض الحالة"):
        check_machine_status(card_num, current_tons, all_sheets)
