import streamlit as st
import pandas as pd
import re

# 📂 تحميل البيانات من الإكسيل
@st.cache_data
def load_data():
    sheets = pd.read_excel("Machine_Service_Lookup.xlsx", sheet_name=None)
    return sheets["Machine"].copy(), sheets["ServicePlan"].copy(), sheets

# 🔠 لتوحيد النصوص
def normalize_name(s):
    if isinstance(s, str):
        return re.sub(r'\s+', '', s.strip().lower())
    return s

# ⚙ دالة استخراج خطة الصيانة ومقارنتها
def get_service_status(machine_df, plan_df, machine_id, current_tons):
    machine_id = normalize_name(machine_id)
    df_machine = machine_df.copy()
    df_machine["Normalized"] = df_machine["card"].apply(normalize_name)

    row = df_machine[df_machine["Normalized"] == machine_id]
    if row.empty:
        return None, "❌ رقم الماكينة غير موجود."

    # استخراج الخدمات المنفذة والمتبقية من جدول الماكينة
    done_services = str(row["Done Services"].iloc[0]).split(",")
    not_done_services = str(row["Not Done Services"].iloc[0]).split(",")
    done_tons = row.get("Current_Tons", pd.Series([None])).iloc[0]
    last_date = row.get("Date", pd.Series([None])).iloc[0]

    # خطة الصيانة العامة
    df_plan = plan_df.copy()
    df_plan = df_plan.sort_values(by=["Min_Tons"])

    # اختيار الخدمات اللي المفروض تتعمل عند عدد الأطنان الحالي
    needed = df_plan[(df_plan["Min_Tons"] <= current_tons) & (df_plan["Max_Tons"] >= current_tons)]

    if needed.empty:
        return None, "✅ لا توجد صيانة مطلوبة عند هذا العدد من الأطنان."

    # تجهيز جدول النتيجة
    results = []
    for _, row_plan in needed.iterrows():
        service = row_plan["Service"]
        results.append({
            "Service Needed": service,
            "Done Services": "✅" if service in done_services else "",
            "Not Done Services": "❌" if service in not_done_services or service not in done_services else "",
            "Done at Tons": done_tons,
            "Date": last_date
        })

    result_df = pd.DataFrame(results)
    return result_df, None

# 🖥 واجهة Streamlit
st.title("📊 نظام متابعة الصيانة التنبؤية")
st.write("أدخل رقم الماكينة وعدد الأطنان الحالية لمعرفة حالة الصيانة")

machine_df, plan_df, _ = load_data()

machine_id = st.text_input("رقم الماكينة:")
tons = st.number_input("عدد الأطنان الحالية:", min_value=0, step=100)

if st.button("عرض النتيجة"):
    if machine_id:
        df, msg = get_service_status(machine_df, plan_df, machine_id, tons)
        if msg:
            st.warning(msg)
        else:
            st.dataframe(df, use_container_width=True)
    else:
        st.warning("⚠ من فضلك أدخل رقم الماكينة أولاً.")
