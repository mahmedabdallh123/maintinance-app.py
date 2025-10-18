import streamlit as st
import pandas as pd
import re

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
# ⚙️ دالة مقارنة الصيانة
# ===============================
def check_machine_status(card_num, current_tons, all_sheets):
    # --- تحقق من وجود الشيتات الأساسية ---
    if "ServicePlan" not in all_sheets or "Machine" not in all_sheets:
        st.error("❌ الملف يجب أن يحتوي على شيتين باسم 'Machine' و 'ServicePlan'")
        return None

    service_plan_df = all_sheets["ServicePlan"]
    machine_df = all_sheets["Machine"]

    # --- تحديد شيت الماكينة ---
    card_sheet_name = f"Card{card_num}"
    if card_sheet_name not in all_sheets:
        st.warning(f"⚠️ لا يوجد شيت باسم {card_sheet_name}")
        return None

    card_df = all_sheets[card_sheet_name]

    # --- تحديد الخدمة المطلوبة من خطة الصيانة ---
    service_row = service_plan_df[
        (service_plan_df["Min_Tons"] <= current_tons) &
        (service_plan_df["Max_Tons"] >= current_tons)
    ]
    needed_service_raw = service_row["Service"].values[0] if not service_row.empty else ""
    needed_parts = split_needed_services(needed_service_raw)
    needed_norm = [normalize_name(p) for p in needed_parts]

    # --- التحقق من الخدمات المنفذة في كارد الماكينة ---
    service_done = card_df[
        (card_df["card"] == card_num) &
        (card_df["Tones"] <= current_tons)
    ]

    done_services, last_date, last_tons = [], "-", "-"
    status = "❌ لم يتم تنفيذ صيانة"

    if not service_done.empty:
        last_row = service_done.iloc[-1]
        last_date = last_row.get("Date", "-")
        last_tons = last_row.get("Tones", "-")

        # الأعمدة اللي فيها العلامات ✓ أو النصوص
        for col in card_df.columns:
            if col not in ["card", "Tones", "Date", "Current_Tons", "Service Needed"]:
                val = str(last_row.get(col, "")).strip().lower()
                if val and val not in ["nan", "none", ""]:
                    done_services.append(col)

        if done_services:
            status = "✅ تم تنفيذ صيانة"

    done_norm = [normalize_name(c) for c in done_services]
    not_done = [orig for orig, n in zip(needed_parts, needed_norm) if n not in done_norm]

    result = {
        "card": card_num,
        "Current_Tons": current_tons,
        "Service Needed": " + ".join(needed_parts) if needed_parts else "-",
        "Done Services": ", ".join(done_services) if done_services else "-",
        "Not Done Services": ", ".join(not_done) if not_done else "-",
        "Date": last_date,
        "Tones": last_tons,
        "Status": status
    }

    result_df = pd.DataFrame([result])
    st.dataframe(result_df, use_container_width=True)
    return result_df

# ===============================
# 🖥️ واجهة Streamlit
# ===============================
st.title("🔧 نظام متابعة الصيانة التنبؤية")
st.write("أدخل رقم الماكينة وعدد الأطنان الحالية لمعرفة حالة الصيانة")

all_sheets = load_all_sheets()
card_num = st.number_input("رقم الماكينة:", min_value=1, step=1)
current_tons = st.number_input("عدد الأطنان الحالية:", min_value=0, step=100)

if st.button("عرض الحالة"):
    check_machine_status(card_num, current_tons, all_sheets)
