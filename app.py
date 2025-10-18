import streamlit as st
import pandas as pd
import re
import time

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
# 🔒 نظام الأمان بالباسورد + عداد
# ===============================
def security_timer():
    if "auth" not in st.session_state:
        st.session_state.auth = False
        st.session_state.start_time = time.time()
        st.session_state.timer_mode = "trial"  # trial -> 60s, full -> 600s

    elapsed = time.time() - st.session_state.start_time

    if not st.session_state.auth:
        remaining = 60 - int(elapsed)
        if remaining > 0:
            st.warning(f"⏳ مهلة التجربة المجانية تنتهي خلال {remaining} ثانية...")
        else:
            st.error("🔒 انتهت المهلة التجريبية. يرجى إدخال كلمة المرور للمتابعة.")
            password = st.text_input("أدخل كلمة المرور:", type="password")
            if password == "1234":
                st.success("✅ تم تسجيل الدخول بنجاح.")
                st.session_state.auth = True
                st.session_state.start_time = time.time()
                st.session_state.timer_mode = "full"
                st.rerun()
            else:
                st.stop()

    elif st.session_state.auth:
        limit = 600 if st.session_state.timer_mode == "full" else 60
        remaining = limit - int(elapsed)
        if remaining <= 0:
            st.session_state.auth = False
            st.error("🔐 انتهت الجلسة، سيتم القفل.")
            st.rerun()
        else:
            st.info(f"⏰ الجلسة ستنتهي بعد {remaining} ثانية.")


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

    # --- 🟢 تحديد الشريحة الحالية ---
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

    # --- 🟡 فلترة البيانات المنفذة داخل نفس الشريحة فقط ---
    slice_df = card_df[
        (card_df["card"] == card_num) &
        (card_df["Tones"] >= min_tons) &
        (card_df["Tones"] <= max_tons)
    ]

    done_services, last_date, last_tons = [], "-", "-"
    status = "❌ لم يتم تنفيذ صيانة في هذه الشريحة"

    if not slice_df.empty:
