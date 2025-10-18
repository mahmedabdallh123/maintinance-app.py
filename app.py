import streamlit as st
import pandas as pd
import re
from io import BytesIO
import time

# ===============================
# 🔒 إعداد الأمان (Security)
# ===============================
PASSWORD = "1234"  # 🔑 غيّر الباسورد هنا
FREE_ACCESS_TIME = 60        # ثانية
LOGIN_ACCESS_TIME = 600      # ثانية

if "session_start" not in st.session_state:
    st.session_state.session_start = time.time()
if "is_authenticated" not in st.session_state:
    st.session_state.is_authenticated = False
if "auth_start_time" not in st.session_state:
    st.session_state.auth_start_time = None

def check_security():
    current_time = time.time()

    # 1️⃣ السماح الحر لمدة 60 ثانية
    if not st.session_state.is_authenticated:
        if current_time - st.session_state.session_start < FREE_ACCESS_TIME:
            return True
        else:
            st.warning("🔒 انتهت المهلة المجانية. أدخل كلمة المرور للمتابعة.")
            password_input = st.text_input("كلمة المرور:", type="password")
            if st.button("تسجيل الدخول"):
                if password_input == PASSWORD:
                    st.session_state.is_authenticated = True
                    st.session_state.auth_start_time = time.time()
                    st.success("✅ تم تسجيل الدخول بنجاح.")
                    st.experimental_rerun()
                else:
                    st.error("❌ كلمة المرور غير صحيحة.")
            st.stop()

    # 2️⃣ السماح بعد تسجيل الدخول لمدة 600 ثانية
    elif st.session_state.is_authenticated:
        if current_time - st.session_state.auth_start_time > LOGIN_ACCESS_TIME:
            st.session_state.is_authenticated = False
            st.session_state.session_start = time.time()
            st.warning("⏰ انتهت صلاحية الجلسة. يرجى تسجيل الدخول مجددًا.")
            st.stop()
        else:
            return True

# ===============================
# ✅ تنفيذ فحص الأمان أولاً
# ===============================
check_security()

# ===============================
# 📂 تحميل البيانات
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
    s = re.sub(r"\(.*?\)", "", s)
    s = re.sub(r"[^0-9a-zA-Z\u0600-\u06FF\+\s_/.-]", " ", s)
    s = re.sub(r"\s+", " ", s).strip().lower()
    return s

def split_needed_services(needed_service_str):
    if not isinstance(needed_service_str, str) or needed_service_str.strip() == "":
        return []
    parts = re.split(r"\+|,|\n|;", needed_service_str)
    return [p.strip() for p in parts if p.strip() != ""]

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

    def highlight_columns(val, col_name, status):
        if col_name == "Service Needed":
            return "background-color: #fff3cd; color: #856404; font-weight: bold;"  # أصفر
        elif col_name == "Done Services" or ("تم تنفيذ" in status and col_name == "Status"):
            return "background-color: #d4edda; color: #155724; font-weight: bold;"  # أخضر
        elif col_name == "Not Done Services" or ("لم يتم" in status and col_name == "Status"):
            return "background-color: #f8d7da; color: #721c24; font-weight: bold;"  # أحمر
        else:
            return ""

    def style_table(row):
        return [highlight_columns(row[col], col, row["Status"]) for col in row.index]

    styled_df = result_df.style.apply(style_table, axis=1)
    st.dataframe(styled_df, use_container_width=True)

    # 💾 زر التحميل
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        result_df.to_excel(writer, index=False, sheet_name="Result")
    excel_data = output.getvalue()

    st.download_button(
        label="💾 تحميل النتيجة كملف Excel",
        data=excel_data,
        file_name=f"Service_Result_Card{card_num}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    return result_df

# ===============================
# 🖥 واجهة Streamlit
# ===============================
st.title("🔧 نظام متابعة الصيانة التنبؤية")
st.write("أدخل رقم الماكينة وعدد الأطنان الحالية لمعرفة حالة الصيانة")

all_sheets = load_all_sheets()
card_num = st.number_input("رقم الماكينة:", min_value=1, step=1)
current_tons = st.number_input("عدد الأطنان الحالية:", min_value=0, step=100)

if st.button("عرض الحالة"):
    check_machine_status(card_num, current_tons, all_sheets)
