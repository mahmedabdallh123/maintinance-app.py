import streamlit as st
import pandas as pd
import re

# 📂 تحميل البيانات من ملف الإكسيل
@st.cache_data
def load_data():
    sheets = pd.read_excel("Machine_Service_Lookup.xlsx", sheet_name=None)
    return sheets["Machine"].copy(), sheets["ServicePlan"].copy(), sheets

# 🔠 توحيد شكل الأسماء
def normalize_name(s):
    if isinstance(s, str):
        return re.sub(r'\s+', '', s.strip().lower())
    return s

# ⚙ دالة لإيجاد خطة الصيانة
def find_service_plan(machine_df, plan_df, machine_id, tons):
    machine_id = normalize_name(machine_id)
    df_machine = machine_df.copy()
    df_machine["Normalized"] = df_machine["MachineID"].apply(normalize_name)

    row = df_machine[df_machine["Normalized"] == machine_id]
    if row.empty:
        return "❌ الماكينة غير موجودة في البيانات."

    model = normalize_name(row["Model"].iloc[0])
    df_plan = plan_df.copy()
    df_plan["NormalizedModel"] = df_plan["Model"].apply(normalize_name)

    related_plan = df_plan[df_plan["NormalizedModel"] == model]
    if related_plan.empty:
        return "⚠ لا توجد خطة صيانة لهذا الموديل."

    related_plan = related_plan.sort_values(by="Tons")
    next_service = related_plan[related_plan["Tons"] >= tons].head(1)
    if next_service.empty:
        return "✅ الماكينة تجاوزت كل الحدود المتاحة في الخطة."

    service_task = next_service["ServiceTask"].iloc[0]
    due_at = next_service["Tons"].iloc[0]
    return f"🔧 الخدمة القادمة: *{service_task}* عند {due_at} طن."

# 🖥 واجهة Streamlit
st.title("📊 نظام متابعة الصيانة التنبؤية")
st.write("أدخل رقم الماكينة وعدد الأطنان الحالية لمعرفة الصيانة القادمة")

machine_df, plan_df, _ = load_data()

machine_id = st.text_input("رقم الماكينة:")
tons = st.number_input("عدد الأطنان الحالية:", min_value=0, step=100)

if st.button("عرض خطة الصيانة"):
    if machine_id:
        result = find_service_plan(machine_df, plan_df, machine_id, tons)
        st.success(result)
    else:
        st.warning("من فضلك أدخل رقم الماكينة أولًا.")
