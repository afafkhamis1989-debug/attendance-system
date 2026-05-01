import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, time
from streamlit_geolocation import streamlit_geolocation
from streamlit_local_storage import LocalStorage
import math

st.set_page_config(
    page_title="نظام الحضور والانصراف",
    page_icon="🕘",
    layout="centered"
)

localS = LocalStorage()

SCHOOL_LAT = 26.216371784473964
SCHOOL_LON = 50.54035843289093
ALLOWED_RADIUS = 150

scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

creds = ServiceAccountCredentials.from_json_keyfile_dict(
    st.secrets["gcp_service_account"],
    scope
)

client = gspread.authorize(creds)
sheet = client.open_by_key("1svkfgRq4-osKr86_2WJQFZShuoy8Ek5DOiUaaHKL-6Y").sheet1

def distance_m(lat1, lon1, lat2, lon2):
    R = 6371000
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))

schools = [
    "مدرسة النور الثانوية للبنات",
    "مدرسة المعرفة الثانوية للبنات",
    "مدرسة الرفاع الغربي الثانوية للبنات",
    "مدرسة جدحفص الثانوية للبنات"
]

sections = [
    "قسم اللغة العربية",
    "قسم اللغة الانجليزية",
    "قسم الرياضيات",
    "قسم العلوم",
    "قسم الحاسب الآلي",
    "قسم التربية الإسلامية",
    "قسم التربية الأسرية",
    "قسم التربية الفنية",
    "قسم التربية البدنية",
    "قسم المواد التجارية",
    "قسم المواد الإجتماعية والإنسانية",
    "الإداري",
    "الإشراف التربوي"
]

reasons = ["دوام مرن", "موعد", "مهمة رسمية", "رعاية", "أخرى"]

st.markdown("""
<style>
html, body, [class*="css"] {
    direction: rtl;
    text-align: right;
    font-family: Tahoma, sans-serif;
}

.block-container {
    max-width: 980px;
    padding-top: 20px;
}

.sub-title {
    text-align: center;
    font-size: 24px;
    font-weight: 700;
    color: #1f2937;
    margin-top: 10px;
}

.main-title {
    text-align: center;
    font-size: 46px;
    font-weight: 900;
    color: #173f6b;
    margin-top: 8px;
    margin-bottom: 25px;
}

.location-title {
    text-align: center;
    font-size: 30px;
    font-weight: 900;
    color: #1f2937;
    margin-bottom: 20px;
}

.operation-title {
    text-align: center;
    font-size: 40px;
    font-weight: 900;
    color: #0f2f55;
    margin: 30px 0 25px 0;
}

.reason-title {
    text-align: center;
    font-size: 32px;
    font-weight: 900;
    color: #1f2937;
    margin-bottom: 25px;
}

.locked-data {
    font-size: 23px;
    font-weight: 900;
    color: #0f172a;
    background-color: #f8fafc;
    border-radius: 16px;
    padding: 14px 18px;
    text-align: right;
    direction: rtl;
}

.locked-row {
    margin-bottom: 10px;
}

.locked-row:last-child {
    margin-bottom: 0;
}

.locked-label {
    margin-left: 8px;
    font-weight: 900;
}

label, .stSelectbox label, .stTextInput label {
    font-size: 23px !important;
    font-weight: 900 !important;
    color: #0f172a !important;
}

.stSelectbox div[data-baseweb="select"] > div,
.stTextInput input {
    min-height: 45px !important;
    border-radius: 16px !important;
    font-size: 20px !important;
    background-color: #f8fafc !important;
}

div[data-testid="stVerticalBlock"] > div {
    margin-bottom: 5px !important;
}

.stButton button {
    width: 100%;
    height: 76px;
    font-size: 22px;
    font-weight: 900;
    border-radius: 20px;
    border: 2px solid #d1d5db;
    background: #ffffff;
}

.footer {
    background: #f3f6fa;
    border-radius: 16px;
    font-size: 18px;
    font-weight: bold;
    margin-top: 28px;
    padding: 16px 22px;
    color: #333;
}
</style>
""", unsafe_allow_html=True)

if "pending_operation" not in st.session_state:
    st.session_state.pending_operation = None

today_for_storage = datetime.now().strftime("%Y-%m-%d")

stored_school = localS.getItem("saved_school")
stored_section = localS.getItem("saved_section")
stored_name = localS.getItem("saved_name")
stored_date = localS.getItem("saved_date")

if stored_date != today_for_storage:
    stored_school = None
    stored_section = None
    stored_name = None

data_locked = (
    stored_date == today_for_storage
    and stored_name is not None
    and str(stored_name).strip() != ""
)

if "school_input" not in st.session_state:
    st.session_state.school_input = stored_school if stored_school in schools else schools[0]

if "section_input" not in st.session_state:
    st.session_state.section_input = stored_section if stored_section in sections else sections[0]

if "name_input" not in st.session_state:
    st.session_state.name_input = stored_name if stored_name else ""

st.image("logo.png", use_container_width=True)

st.markdown("""
<div class="sub-title">مركز مدرسة جدحفص للتصحيح المركزي - المنطقة التعليمية (2)</div>
<div class="main-title">نظام الحضور والانصراف</div>
""", unsafe_allow_html=True)

with st.container(border=True):
    st.markdown('<div class="location-title">📍 التحقق من الموقع</div>', unsafe_allow_html=True)

    location = streamlit_geolocation()

    allowed = False

    if location:
        lat = location.get("latitude")
        lon = location.get("longitude")

        if lat is not None and lon is not None:
            try:
                user_lat = float(lat)
                user_lon = float(lon)

                dist = distance_m(user_lat, user_lon, SCHOOL_LAT, SCHOOL_LON)

                if dist <= ALLOWED_RADIUS:
                    allowed = True
                    st.success("أنتِ داخل نطاق المدرسة، يمكنك التسجيل ✅")
                else:
                    st.error("❌ لا يمكن التسجيل خارج نطاق المدرسة")

            except Exception:
                st.warning("حدث خطأ في قراءة الموقع، حاول مرة أخرى")
        else:
            st.warning("اضغطي زر تحديد الموقع 📍")
    else:
        st.warning("اضغطي زر تحديد الموقع 📍")

with st.container(border=True):
    if data_locked:
        st.markdown(
            f"""
            <div class="locked-data">
                <div class="locked-row"><span class="locked-label">اسم المدرسة:</span> {st.session_state.school_input}</div>
                <div class="locked-row"><span class="locked-label">القسم:</span> {st.session_state.section_input}</div>
                <div class="locked-row"><span class="locked-label">الاسم الثلاثي:</span> {st.session_state.name_input}</div>
            </div>
            """,
            unsafe_allow_html=True
        )

        school = st.session_state.school_input
        section = st.session_state.section_input
        name = st.session_state.name_input

    else:
        school = st.selectbox("اسم المدرسة", schools, key="school_input")
        section = st.selectbox("القسم", sections, key="section_input")
        name = st.text_input("الاسم الثلاثي", placeholder="اكتبي الاسم الثلاثي", key="name_input")

def find_today_row(data, today, full_name):
    for i, row in enumerate(data):
        if row.get("التاريخ") == today and row.get("الاسم الثلاثي") == full_name:
            return i + 2, row
    return None, None

def register_operation(operation, note=""):
    if not allowed:
        st.error("لا يمكن التسجيل خارج نطاق المدرسة")
        return

    full_name = st.session_state.name_input.strip()

    if full_name == "":
        st.error("الرجاء كتابة الاسم الثلاثي")
        return

    now = datetime.now()
    today = now.strftime("%Y-%m-%d")
    day_name = now.strftime("%A")
    time_now = now.strftime("%H:%M:%S")

    data = sheet.get_all_records()
    row_index, row = find_today_row(data, today, full_name)

    if operation == "تسجيل حضور":
        if row_index and row.get("وقت الحضور"):
            st.error("تم تسجيل الحضور مسبقًا لهذا اليوم")
            return

        if row_index:
            sheet.update_cell(row_index, 6, time_now)
            sheet.update_cell(row_index, 7, note)
        else:
            sheet.append_row([
                today, day_name,
                st.session_state.school_input,
                st.session_state.section_input,
                full_name,
                time_now,
                note,
                "",
                "",
                "",
                "",
                ""
            ])

    elif operation == "تسجيل انصراف":
        if not row_index or not row.get("وقت الحضور"):
            st.error("لا يوجد تسجيل حضور لهذا الاسم اليوم")
            return

        if row.get("وقت الانصراف"):
            st.error("تم تسجيل الانصراف مسبقًا لهذا اليوم")
            return

        sheet.update_cell(row_index, 8, time_now)
        sheet.update_cell(row_index, 9, note)

    elif operation == "خروج استئذان":
        if not row_index or not row.get("وقت الحضور"):
            st.error("لا يوجد تسجيل حضور لهذا الاسم اليوم")
            return

        if row.get("خروج استئذان") and not row.get("عودة"):
            st.error("يوجد خروج استئذان مفتوح، الرجاء تسجيل العودة أولًا")
            return

        if row.get("خروج استئذان"):
            st.error("تم تسجيل خروج الاستئذان مسبقًا لهذا اليوم")
            return

        sheet.update_cell(row_index, 10, time_now)
        sheet.update_cell(row_index, 12, note)

    elif operation == "عودة من استئذان":
        if not row_index or not row.get("وقت الحضور"):
            st.error("لا يوجد تسجيل حضور لهذا الاسم اليوم")
            return

        if not row.get("خروج استئذان"):
            st.error("لا يوجد خروج استئذان مفتوح لهذا الاسم")
            return

        if row.get("عودة"):
            st.error("تم تسجيل العودة من الاستئذان مسبقًا لهذا اليوم")
            return

        sheet.update_cell(row_index, 11, time_now)

    st.session_state.pending_operation = None
    st.success(f"تم {operation} بنجاح ✅")

with st.container(border=True):
    st.markdown('<div class="operation-title">نوع العملية</div>', unsafe_allow_html=True)

    col_right1, col_left1 = st.columns(2)

    with col_right1:
        if st.button("🟢 تسجيل حضور", use_container_width=True):
            st.session_state.pending_operation = None

            if not allowed:
                st.error("لا يمكن التسجيل خارج نطاق المدرسة")
            elif datetime.now().time() > time(7, 30):
                st.session_state.pending_operation = "تسجيل حضور"
            else:
                register_operation("تسجيل حضور")

    with col_left1:
        if st.button("🔵 تسجيل انصراف", use_container_width=True):
            st.session_state.pending_operation = None

            if not allowed:
                st.error("لا يمكن التسجيل خارج نطاق المدرسة")
            elif datetime.now().time() < time(14, 0):
                st.session_state.pending_operation = "تسجيل انصراف"
            else:
                register_operation("تسجيل انصراف")

    col_right2, col_left2 = st.columns(2)

    with col_right2:
        if st.button("📤 خروج استئذان", use_container_width=True):
            st.session_state.pending_operation = None

            if not allowed:
                st.error("لا يمكن التسجيل خارج نطاق المدرسة")
            else:
                st.session_state.pending_operation = "خروج استئذان"

    with col_left2:
        if st.button("🔁 عودة من استئذان", use_container_width=True):
            st.session_state.pending_operation = None
            register_operation("عودة من استئذان")

if st.session_state.pending_operation == "تسجيل انصراف":
    with st.container(border=True):
        st.markdown('<div class="reason-title">سبب الانصراف قبل الساعة 2:00</div>', unsafe_allow_html=True)

        reason = st.selectbox("اختاري السبب", reasons, key="early_leave_reason")
        other_reason = ""

        if reason == "أخرى":
            other_reason = st.text_input("اكتب السبب الآخر", key="early_leave_other")

        final_reason = other_reason.strip() if reason == "أخرى" else reason

        if st.button("تأكيد تسجيل الانصراف", use_container_width=True):
            if final_reason == "":
                st.error("سبب الانصراف قبل الساعة 2:00 مطلوب")
            else:
                register_operation("تسجيل انصراف", final_reason)

if st.session_state.pending_operation == "خروج استئذان":
    with st.container(border=True):
        st.markdown('<div class="reason-title">سبب خروج الاستئذان</div>', unsafe_allow_html=True)

        exit_reason = st.selectbox("اختار السبب", reasons, key="exit_reason")
        exit_other = ""

        if exit_reason == "أخرى":
            exit_other = st.text_input("اكتب السبب الآخر", key="exit_other")

        final_exit_reason = exit_other.strip() if exit_reason == "أخرى" else exit_reason

        if st.button("تأكيد تسجيل خروج الاستئذان", use_container_width=True):
            if final_exit_reason == "":
                st.error("سبب خروج الاستئذان مطلوب")
            else:
                register_operation("خروج استئذان", final_exit_reason)

if st.session_state.pending_operation == "تسجيل حضور":
    with st.container(border=True):
        st.markdown('<div class="reason-title">سبب التأخير بعد الساعة 7:30 - اختياري</div>', unsafe_allow_html=True)

        late_reason = st.selectbox(
            "اختار السبب أو اترك بدون اختيار",
            ["بدون سبب"] + reasons,
            key="late_reason"
        )

        late_other = ""
        if late_reason == "أخرى":
            late_other = st.text_input("اكتب السبب الآخر", key="late_other")

        final_late_reason = ""
        if late_reason == "أخرى":
            final_late_reason = late_other.strip()
        elif late_reason != "بدون سبب":
            final_late_reason = late_reason

        if st.button("تأكيد تسجيل الحضور", use_container_width=True):
            register_operation("تسجيل حضور", final_late_reason)

st.markdown("""
<div class="footer" style="display:flex; justify-content:space-between; direction:rtl;">
    <div>تصميم وبرمجة: عفاف حسين</div>
    <div>رئيسة المركز: أ. خلود يعقوب بدو</div>
</div>
""", unsafe_allow_html=True)

localS.setItem("saved_school", school, key="set_saved_school")
localS.setItem("saved_section", section, key="set_saved_section")
localS.setItem("saved_name", name, key="set_saved_name")
localS.setItem("saved_date", today_for_storage, key="set_saved_date")
