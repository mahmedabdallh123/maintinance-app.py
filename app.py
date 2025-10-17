import streamlit as st
import pandas as pd
import re

def check_maintenance_status(card_num, current_tons):
    # استخراج الخدمة المطلوبة
    service_row = service_plan_df[
        (service_plan_df["Min_Tons"] <= current_tons) &
        (service_plan_df["Max_Tons"] >= current_tons)
    ]
def split_service_type(name):
    """
    ترجع tuple فيها (الاسم الأساسي, نوع الصيانة)
    o = استبدال، X = صيانة
    """
    name = str(name).strip()
    match = re.match(r"([a-zA-Z\s_]+)\(([oOxX])\)", name)
    if match:
        return match.group(1).strip().lower(), match.group(2).lower()
    return name.lower(), ""
    needed_service_raw = service_row["Service"].values[0] if not service_row.empty else ""
    needed_parts = re.split(r"\+|,|\n|;", needed_service_raw)
    needed_parts = [p.strip() for p in needed_parts if p.strip() != ""]

    # استخراج قائمة الخدمات المطلوبة (الاسم + النوع)
    needed_info = [split_service_type(p) for p in needed_parts]

    # البحث في جدول التنفيذ
    service_done = card1_df[
        (card1_df["card"] == card_num) &
        (card1_df["Min_Tons"] <= current_tons) &
        (card1_df["Max_Tons"] >= current_tons)
    ]

    done_list, not_done_list = [], []

    if not service_done.empty:
        last_row = service_done.iloc[-1]
        done_services_cols = list(service_done.columns[4:-1])  # الأعمدة اللي فيها الخدمات

        for base_name, s_type in needed_info:
            # نبني شكل العمود اللي المفروض نبحث عنه
            search_pattern = f"{base_name}({s_type})" if s_type else base_name
            found = False

            for col in done_services_cols:
                if col.replace(" ", "").lower() == search_pattern.replace(" ", "").lower():
                    val = str(last_row.get(col, "")).strip()
                    if val != "" and val.lower() != "nan":
                        done_list.append(col)
                        found = True
                        break

            if not found:
                not_done_list.append(search_pattern)

        last_service = "تم تنفيذ الصيانة" if done_list else "لم يتم التنفيذ"
        last_date = last_row["Date"]
        last_tons = last_row["Tones"]
    else:
        last_service = "لم يتم التنفيذ"
        done_list = []
        not_done_list = [f"{n[0]}({n[1]})" if n[1] else n[0] for n in needed_info]
        last_date = ""
        last_tons = ""

    result = pd.DataFrame([{
        "card": card_num,
        "Current_Tones": current_tons,
        "Service Needed": " + ".join(needed_parts),
        "last service": last_service,
        "Done Services": ", ".join(done_list),
        "Not Done Services": ", ".join(not_done_list),
        "Date": last_date,
        "Tones": last_tons
    }])

    display(result)


# 🖥 واجهة Streamlit
st.title("📊 نظام متابعة الصيانة التنبؤية")
st.write("أدخل رقم الماكينة وعدد الأطنان الحالية لمعرفة حالة الصيانة")

machine_df, plan_df, _ = load_data()

card = st.text_input("رقم الماكينة:")
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
