import streamlit as st
import pandas as pd
import re

file_path = r"C:\Users\LAP ME\Desktop\داتا ساينس دبلومه\new projects\maintinance plan\maintinance-app.py\Machine_Service_Lookup"

# =====================================
# 🔹 دوال مساعدة
# =====================================
def load_data():
    sheets = pd.read_excel(file_path, sheet_name=None)
    return sheets["Machine"].copy(), sheets["ServicePlan"].copy(), sheets

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

# =====================================
# 🔹 منطق التطبيق
# =====================================
def check_maintenance_status(card_num, current_tons):
    card_df, service_plan_df, sheets = load_data()
    sheet_name = f"Card{card_num}"
    if sheet_name not in sheets:
        st.error(f"❌ لا يوجد شيت باسم {sheet_name}")
        return pd.DataFrame()

    card1_df = sheets[sheet_name].copy()

    service_row = service_plan_df[
        (service_plan_df["Min_Tons"] <= current_tons) &
        (service_plan_df["Max_Tons"] >= current_tons)
    ]
    needed_service_raw = service_row["Service"].values[0] if not service_row.empty else ""
    needed_parts = split_needed_services(needed_service_raw)
    needed_norm = [normalize_name(p) for p in needed_parts]

    service_done = card1_df[
        (card1_df["card"] == card_num) &
        (card1_df["Min_Tons"] <= current_tons) &
        (card1_df["Max_Tons"] >= current_tons)
    ]

    done_services_cols, last_date, last_tons = [], "-", "-"
    status = "لم يتم تنفيذ صيانة"

    if not service_done.empty:
        last_row = service_done.iloc[-1]
        last_date = last_row.get("Date", "-")
        last_tons = last_row.get("Tones", "-")
        service_columns = list(service_done.columns[4:-1])
        for col in service_columns:
            val = str(last_row.get(col, "")).strip().lower()
            if val and val not in ["nan", "none"]:
                done_services_cols.append(col)
        if done_services_cols:
            status = "تم تنفيذ الصيانة"

    done_norm = [normalize_name(c) for c in done_services_cols]
    not_done = [orig for orig, n in zip(needed_parts, needed_norm) if n not in done_norm]

    result = {
        "card": card_num,
        "Current_Tons": current_tons,
        "Service Needed": " + ".join(needed_parts),
        "last service": status,
        "Done Services": ", ".join(done_services_cols) if done_services_cols else "-",
        "Not Done Services": ", ".join(not_done) if not_done else "-",
        "Date": last_date,
        "Tones": last_tons
    }

    return pd.DataFrame([result])

# 🖥 واجهة Streamlit
st.title("🧰 نظام متابعة الصيانة")
st.write("اختار رقم الماكينة وعدد الأطنان للتحقق من حالة الصيانة")

card_num = st.number_input("أدخل رقم الماكينة:", min_value=1, step=1)
current_tons = st.number_input("أدخل عدد الأطنان الحالية:", min_value=0.0, step=1.0)

if st.button("تحقق"):
    df = check_maintenance_status(card_num, current_tons)
    if not df.empty:
        st.dataframe(df.style.set_properties(**{'background-color': '#f0f9ff', 'border': '1px solid #ccc'}))

