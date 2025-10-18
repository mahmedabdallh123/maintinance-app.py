import pandas as pd
import re
from IPython.display import display, HTML

# ===============================
# 🔹 مسار الملف
# ===============================
file_path = r"C:\Users\LAP ME\Desktop\داتا ساينس دبلومه\new projects\maintinance plan\Machine_Service_Lookup.xlsx"

# ===============================
# 🔹 دوال مساعدة
# ===============================
def load_all_sheets():
    return pd.read_excel(file_path, sheet_name=None)

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
# 🔹 دالة فحص الماكينة المحددة
# ===============================
def check_machine_status(card_num, current_tons, all_sheets):
    service_plan_df = all_sheets["ServicePlan"]
    machine_df = all_sheets["Machine"]

    # تحديد اسم الشيت الخاص بالماكينة
    card_sheet_name = f"Card{card_num}"
    if card_sheet_name not in all_sheets:
        print(f"❌ لا يوجد شيت باسم '{card_sheet_name}' في الملف.")
        return None

    card_df = all_sheets[card_sheet_name]

    # استخراج الخدمة المطلوبة من ServicePlan
    service_row = service_plan_df[
        (service_plan_df["Min_Tons"] <= current_tons) &
        (service_plan_df["Max_Tons"] >= current_tons)
    ]
    needed_service_raw = service_row["Service"].values[0] if not service_row.empty else ""
    needed_parts = split_needed_services(needed_service_raw)
    needed_norm = [normalize_name(p) for p in needed_parts]

    # البحث عن الصيانة المنفذة في شيت الكارد
    service_done = card_df[
        (card_df["card"] == card_num) &
        (card_df["Min_Tons"] <= current_tons) &
        (card_df["Max_Tons"] >= current_tons)
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
        "Service Needed": " + ".join(needed_parts) if needed_parts else "-",
        "last service": status,
        "Done Services": ", ".join(done_services_cols) if done_services_cols else "-",
        "Not Done Services": ", ".join(not_done) if not_done else "-",
        "Date": last_date,
        "Tones": last_tons
    }

    # تحديث الجدول Machine بنفس النتيجة
    idx = machine_df.index[machine_df["card"] == card_num]
    if not idx.empty:
        i = idx[0]
        for k, v in result.items():
            if k in machine_df.columns:
                machine_df.at[i, k] = v
            else:
                machine_df[k] = ""
                machine_df.at[i, k] = v

    # حفظ التحديث في نفس الملف
    with pd.ExcelWriter(file_path, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
        machine_df.to_excel(writer, sheet_name="Machine", index=False)
        service_plan_df.to_excel(writer, sheet_name="ServicePlan", index=False)
        for sheet_name, df in all_sheets.items():
            if sheet_name.startswith("Card"):
                df.to_excel(writer, sheet_name=sheet_name, index=False)

    # عرض النتيجة في جدول
    result_df = pd.DataFrame([result])
    styled = result_df.style.set_properties(**{'background-color': '#f9fcff', 'border': '1px solid #ccc'})
    display(HTML(f"<h3>🔧 نتيجة فحص الماكينة رقم {card_num}</h3>"))
    display(styled)
    return result_df


# ===============================
# 🔹 تشغيل تفاعلي
# ===============================
all_sheets = load_all_sheets()
print("✅ تم تحميل البيانات بنجاح.\n")

try:
    card_num = int(input("أدخل رقم الماكينة (مثل 1 أو 2 أو 3): "))
    current_tons = float(input("أدخل عدد الأطنان الحالية: "))
    check_machine_status(card_num, current_tons, all_sheets)
except Exception as e:
    print("⚠️ حدث خطأ:", e)


# 🖥 واجهة Streamlit
st.title("🧰 نظام متابعة الصيانة")
st.write("اختار رقم الماكينة وعدد الأطنان للتحقق من حالة الصيانة")

card_num = st.number_input("أدخل رقم الماكينة:", min_value=1, step=1)
current_tons = st.number_input("أدخل عدد الأطنان الحالية:", min_value=0.0, step=1.0)

if st.button("تحقق"):
    df = check_maintenance_status(card_num, current_tons)
    if not df.empty:
        st.dataframe(df.style.set_properties(**{'background-color': '#f0f9ff', 'border': '1px solid #ccc'}))

