import streamlit as st
import pandas as pd

# 📂 تحميل البيانات من الإكسيل
@st.cache_data
def load_data():
    sheets = pd.read_excel("Machine_Service_Lookup.xlsx", sheet_name=None)
    return sheets["Machine"].copy(), sheets["ServicePlan"].copy()

# ⚙ دالة لتحديد الصيانة المنفذة وغير المنفذة
def check_services(machine_df, plan_df, card, current_tons):
    # نتاكد أن الماكينة موجودة
    machine_data = machine_df[machine_df["card"].astype(str).str.lower() == str(card).lower()]
    if machine_data.empty:
        return f"❌ الماكينة {card} غير موجودة في البيانات.", None, None

    # نجيب الخدمات المطلوبة عند عدد الأطنان دي من جدول ServicePlan
    plan_match = plan_df[
        (plan_df["Min_Tons"] <= current_tons) & (plan_df["Max_Tons"] >= current_tons)
    ]

    if plan_match.empty:
        return "✅ لا توجد خطة صيانة مطلوبة عند هذا العدد من الأطنان.", None, None

    required_services = plan_match["Service"].tolist()

    # الخدمات المنفذة فعلاً في Machine
    done_services = machine_data["Done Services"].dropna().tolist()
    not_done_services = []

    # نتحقق من كل خدمة مطلوبة
    for service in required_services:
        if not any(service.lower() in str(s).lower() for s in done_services):
            not_done_services.append(service)

    # نجمع التاريخ والأطنان لو فيه صيانة منفذة
    last_service = machine_data["last service"].iloc[-1] if not machine_data["last service"].isna().all() else "—"
    last_tons = machine_data["Tones"].iloc[-1] if not machine_data["Tones"].isna().all() else "—"

    return "✅ تم الفحص بنجاح", done_services, not_done_services, last_service, last_tons

# 🖥 واجهة Streamlit
st.title("📊 نظام متابعة الصيانة")
st.write("أدخل رقم الماكينة وعدد الأطنان الحالية لمعرفة الخدمات المنفذة والمتبقية")

machine_df, plan_df = load_data()

card = st.text_input("رقم الماكينة:")
current_tons = st.number_input("عدد الأطنان الحالية:", min_value=0, step=100)

if st.button("تحليل حالة الصيانة"):
    if card:
        status, done_services, not_done_services, last_service, last_tons = check_services(machine_df, plan_df, card, current_tons)
        st.info(status)
        if done_services:
            st.success(f"🔧 الخدمات المنفذة: {', '.join(done_services)}")
            st.write(f"📅 آخر صيانة عند {last_tons} طن بتاريخ {last_service}")
        if not_done_services:
            st.warning(f"⚠ الخدمات التي لم تُنفذ بعد: {', '.join(not_done_services)}")
    else:
        st.warning("من فضلك أدخل رقم الماكينة أولاً.")
