import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, time, timedelta
from streamlit_geolocation import streamlit_geolocation
import math
import random
import string
import time as time_module

try:
    from streamlit_local_storage import LocalStorage
    localS = LocalStorage()
    LOCAL_STORAGE_OK = True
except Exception:
    localS = None
    LOCAL_STORAGE_OK = False

# =========================================================
# إعداد الصفحة
# =========================================================
st.set_page_config(
    page_title="نظام الحضور والانصراف",
    page_icon="🕘",
    layout="centered"
)

# =========================================================
# الإعدادات الأساسية
# =========================================================
SHEET_ID = "1svkfgRq4-osKr86_2WJQFZShuoy8Ek5DOiUaaHKL-6Y"
MAIN_SHEET_NAME = "sheet1"

SCHOOL_LAT = 26.216371784473964
SCHOOL_LON = 50.54035843289093
ALLOWED_RADIUS = 150

# أعمدة sheet1
COL_DATE = 1
COL_DAY = 2
COL_SCHOOL = 3
COL_TASK = 4
COL_SUPPORT = 5
COL_NAME = 6
COL_ID = 7
COL_ATTEND = 8
COL_LATE_REASON = 9
COL_DEPART = 10
COL_DEPART_REASON = 11
COL_EXIT = 12
COL_RETURN = 13
COL_ATTEMPT = 14

MAIN_HEADERS = [
    "التاريخ", "اليوم", "اسم المدرسة", "المهمة", "دعم",
    "الاسم الثلاثي", "الرقم الشخصي", "وقت الحضور", "سبب التأخير",
    "وقت الانصراف", "سبب الانصراف", "خروج استئذان", "عودة",
    "محاولة تسجيل باسم آخر"
]

WHITELIST_HEADERS = [
    "الرقم الشخصي", "الاسم", "المدرسة", "المهمة",
    "رقم التواصل", "البريد الإلكتروني", "المسمى الوظيفي", "نشط"
]

DEVICE_HEADERS = [
    "التاريخ", "بصمة الجهاز", "الرقم الشخصي", "الاسم", "وقت_القفل"
]

ATTEMPT_HEADERS = [
    "التاريخ", "بصمة الجهاز", "الرقم_المقفول_عليه", "اسم_المقفول_عليه",
    "الرقم_المحاول", "اسم_المحاول", "وقت_المحاولة", "ملاحظات"
]

SETTINGS_HEADERS = ["المفتاح", "القيمة", "تاريخ_الانتهاء", "ملاحظات"]

schools = [
    "مدرسة النور الثانوية للبنات",
    "مدرسة المعرفة الثانوية للبنات",
    "مدرسة الرفاع الغربي الثانوية للبنات",
    "مدرسة جدحفص الثانوية للبنات"
]

TASKS_MAIN = [
    "مصححة — اللغة العربية",
    "مصححة — اللغة الإنجليزية",
    "مصححة — الرياضيات",
    "مصححة — الفيزياء",
    "مصححة — الكيمياء",
    "مصححة — الأحياء",
    "مصححة — العلوم التجارية",
    "مصححة — المواد الاجتماعية",
    "مصححة — التربية الإسلامية",
    "مصححة — التربية الأسرية",
    "مصححة — التربية الفنية",
    "مصححة — الحاسب الآلي",
    "مصححة — التربية البدنية",
    "كنترول خارجي — دعم فني",
    "كنترول خارجي — رصد الدرجات",
    "كنترول خارجي — ضبط مركزي",
]
TASKS_SUPPORT = [t + " — دعم" for t in TASKS_MAIN]
TASKS_ALL = TASKS_MAIN + TASKS_SUPPORT

JOB_TITLES = [
    "منسقة",
    "معلمة أولى",
    "معلمة",
    "الهيئة الإدارية",
    "مشرف تربوي",
    "مديرة مدرسة",
    "المديرة المساعدة",
    "أخرى"
]

reasons = ["دوام مرن", "موعد", "مهمة رسمية", "رعاية", "أخرى"]

# =========================================================
# CSS - RTL كامل
# =========================================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;900&display=swap');

html, body, [class*="css"] {
    direction: rtl !important;
    text-align: right !important;
    font-family: 'Cairo', Tahoma, sans-serif !important;
}
.stApp {
    direction: rtl !important;
    text-align: right !important;
}
.block-container {
    max-width: 680px;
    padding-top: 0px;
    padding-bottom: 40px;
    direction: rtl !important;
    text-align: right !important;
}
[data-testid="stVerticalBlock"],
[data-testid="stHorizontalBlock"],
.element-container,
.stMarkdown,
.stTextInput,
.stSelectbox,
.stRadio,
.stButton,
.stAlert {
    direction: rtl !important;
    text-align: right !important;
}
.stTextInput input {
    direction: rtl !important;
    text-align: right !important;
}
.stSelectbox div {
    direction: rtl !important;
    text-align: right !important;
}
label {
    direction: rtl !important;
    text-align: right !important;
    display: block !important;
    font-size: 15px !important;
    font-weight: 700 !important;
    color: #0c3460 !important;
}
.app-header {
    background: linear-gradient(135deg, #0c3460 0%, #1a5276 60%, #1f6fa3 100%);
    border-radius: 0 0 28px 28px;
    padding: 28px 24px 32px;
    text-align: center !important;
    margin: -1rem -1rem 20px -1rem;
}
.app-header .sub {
    color: rgba(255,255,255,0.78);
    font-size: 12px;
    font-weight: 600;
    margin-bottom: 6px;
    text-align: center !important;
}
.app-header .title {
    color: #fff;
    font-size: 22px;
    font-weight: 900;
    text-align: center !important;
}
.app-header .date-pill {
    display: inline-block;
    background: rgba(255,255,255,0.15);
    border: 1px solid rgba(255,255,255,0.2);
    border-radius: 20px;
    padding: 3px 14px;
    color: rgba(255,255,255,0.9);
    font-size: 12px;
    font-weight: 600;
    margin-top: 10px;
}
.card-title {
    color: #0c3460;
    font-size: 19px;
    font-weight: 900;
    margin-bottom: 14px;
    text-align: right !important;
}
.field-lbl {
    font-size: 12px;
    font-weight: 700;
    color: #888780;
    margin-bottom: 4px;
    text-align: right !important;
}
.field-val {
    background: #eaf3de;
    border: 1px solid #c0dd97;
    border-radius: 14px;
    padding: 12px 14px;
    font-size: 15px;
    font-weight: 800;
    color: #27500A;
    margin-bottom: 12px;
    text-align: right !important;
    direction: rtl !important;
}
.field-val.blue {
    background: #e6f1fb;
    border-color: #185FA5;
    color: #185FA5;
}
.pro-card {
    background: #fff;
    border-radius: 22px;
    padding: 18px 20px;
    box-shadow: 0 2px 14px rgba(12,52,96,0.07);
    margin-bottom: 14px;
    text-align: right !important;
}
.today-strip {
    display:flex;
    justify-content:space-around;
    background:#f0f4f8;
    border-radius:14px;
    padding:12px 8px;
    margin-bottom:14px;
}
.stat-cell { text-align:center !important; }
.stat-val  { font-size:17px; font-weight:900; color:#0c3460; display:block; text-align:center !important; }
.stat-lbl  { font-size:10px; font-weight:600; color:#888780; text-align:center !important; }
.footer-bar {
    background:#0c3460;
    border-radius:14px;
    padding:12px 18px;
    display:flex;
    justify-content:space-between;
    align-items:center;
    margin-top:12px;
}
.footer-bar span { font-size:11px; font-weight:600; color:rgba(255,255,255,.7); }
.footer-bar .hl  { color:#fff; }
.stButton button {
    border-radius:14px !important;
    font-size:15px !important;
    font-weight:800 !important;
    font-family:'Cairo',sans-serif !important;
}
</style>
""", unsafe_allow_html=True)

# =========================================================
# الاتصال بـ Google Sheets
# =========================================================
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

@st.cache_resource
def connect_google_sheets():
    creds = ServiceAccountCredentials.from_json_keyfile_dict(
        st.secrets["gcp_service_account"], scope
    )
    client = gspread.authorize(creds)
    return client.open_by_key(SHEET_ID)

spreadsheet = connect_google_sheets()

def get_or_create_sheet(name, headers, rows=1000):
    try:
        ws = spreadsheet.worksheet(name)
    except gspread.WorksheetNotFound:
        ws = spreadsheet.add_worksheet(title=name, rows=rows, cols=max(len(headers), 10))
        ws.append_row(headers)
        return ws

    try:
        existing = ws.row_values(1)
        if not existing:
            ws.append_row(headers)
        elif len(existing) < len(headers):
            for i, h in enumerate(headers, start=1):
                if i > len(existing) or not existing[i - 1]:
                    ws.update_cell(1, i, h)
    except Exception:
        pass
    return ws

sheet = spreadsheet.worksheet("sheet1")
whitelist_sheet = spreadsheet.worksheet("القائمة_البيضاء")
device_lock_sheet = spreadsheet.worksheet("device_lock")
attempts_sheet = spreadsheet.worksheet("محاولات_تسجيل_باسم_آخر")
settings_sheet = spreadsheet.worksheet("إعدادات_النظام")

# =========================================================
# دوال مساعدة
# =========================================================
def ar_to_en_digits(text):
    ar = "٠١٢٣٤٥٦٧٨٩"
    en = "0123456789"
    result = str(text).strip()
    for a, e in zip(ar, en):
        result = result.replace(a, e)
    return result

def normalize_name(name):
    name = str(name).strip()
    for old, new in {"أ":"ا","إ":"ا","آ":"ا","ى":"ي","ة":"ه","ؤ":"و","ئ":"ي"}.items():
        name = name.replace(old, new)
    for ch in [".", "،", ",", "-", "_", "ـ", ":", ";"]:
        name = name.replace(ch, " ")
    return " ".join(name.split())

def distance_m(lat1, lon1, lat2, lon2):
    R = 6371000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))

def ls_get(key):
    if LOCAL_STORAGE_OK:
        try:
            return localS.getItem(key)
        except Exception:
            pass
    return st.session_state.get(f"ls_{key}")

def ls_set(key, value, ls_key=None):
    if LOCAL_STORAGE_OK:
        try:
            localS.setItem(key, value, key=ls_key or f"set_{key}")
            return
        except Exception:
            pass
    st.session_state[f"ls_{key}"] = value

def get_device_fingerprint():
    if LOCAL_STORAGE_OK:
        try:
            fp = localS.getItem("device_fp")
            if not fp:
                fp = ''.join(random.choices(string.ascii_letters + string.digits, k=32))
                localS.setItem("device_fp", fp, key="set_device_fp")
            return fp or "unknown"
        except Exception:
            pass

    if "device_fp" not in st.session_state:
        st.session_state.device_fp = ''.join(random.choices(string.ascii_letters + string.digits, k=32))
    return st.session_state.device_fp

def safe_append(ws, row, retries=3):
    for _ in range(retries):
        try:
            ws.append_row(row, value_input_option="USER_ENTERED")
            return True
        except Exception:
            time_module.sleep(1.5)
    return False

def safe_update_cell(ws, row, col, value, retries=3):
    for _ in range(retries):
        try:
            ws.update_cell(row, col, value)
            return True
        except Exception:
            time_module.sleep(1.5)
    return False

@st.cache_data(ttl=120)
def get_sheet_data():
    try:
        return sheet.get_all_records()
    except Exception:
        return []

@st.cache_data(ttl=300)
def get_whitelist():
    try:
        records = whitelist_sheet.get_all_records()
        result = {}
        for r in records:
            active = str(r.get("نشط", "")).strip()
            if active in ["نعم", "yes", "Yes", "TRUE", "true", "1"]:
                eid = str(r.get("الرقم الشخصي", "")).strip()
                if eid:
                    result[eid] = r
        return result
    except Exception:
        return {}

@st.cache_data(ttl=120)
def get_device_locks():
    try:
        return device_lock_sheet.get_all_records()[-200:]
    except Exception:
        return []

@st.cache_data(ttl=120)
def get_settings_records():
    try:
        return settings_sheet.get_all_records()
    except Exception:
        return []

def clear_caches():
    get_sheet_data.clear()
    get_device_locks.clear()
    get_settings_records.clear()

def validate_employee(emp_id):
    return get_whitelist().get(str(emp_id).strip())

def find_today_row(data, today, emp_id):
    for i, row in enumerate(data):
        if str(row.get("التاريخ", "")).strip() == str(today).strip() and \
           str(row.get("الرقم الشخصي", "")).strip() == str(emp_id).strip():
            return i + 2, row
    return None, None

def get_location_override():
    try:
        records = get_settings_records()
        for r in records:
            if str(r.get("المفتاح","")).strip() == "location_override":
                val = str(r.get("القيمة","")).strip()
                end_time = str(r.get("تاريخ_الانتهاء","")).strip()
                if val == "true" and end_time:
                    try:
                        end_dt = datetime.strptime(end_time, "%Y-%m-%d %H:%M")
                        if datetime.now() < end_dt:
                            return True, end_dt
                    except Exception:
                        pass
    except Exception:
        pass
    return False, None

def set_location_override(minutes, note=""):
    end_dt = datetime.now() + timedelta(minutes=minutes)
    end_str = end_dt.strftime("%Y-%m-%d %H:%M")
    try:
        records = settings_sheet.get_all_records()
        row_found = None
        for i, r in enumerate(records):
            if str(r.get("المفتاح","")).strip() == "location_override":
                row_found = i + 2
                break
        if row_found:
            settings_sheet.update(f"A{row_found}:D{row_found}", [["location_override", "true", end_str, note]])
        else:
            safe_append(settings_sheet, ["location_override", "true", end_str, note])
        get_settings_records.clear()
        return True, end_dt
    except Exception:
        return False, None

def disable_location_override():
    try:
        records = settings_sheet.get_all_records()
        for i, r in enumerate(records):
            if str(r.get("المفتاح","")).strip() == "location_override":
                settings_sheet.update_cell(i + 2, 2, "false")
                break
        get_settings_records.clear()
    except Exception:
        pass

def log_attempt(today, fp, locked_id, locked_name, attempted_id, attempted_name):
    now = datetime.now().strftime("%H:%M:%S")
    note = "محاولة تسجيل رقم شخصي مختلف من نفس الجهاز"

    safe_append(attempts_sheet, [
        today, fp, locked_id, locked_name,
        attempted_id, attempted_name, now, note
    ])

    try:
        data = get_sheet_data()
        row_index, _ = find_today_row(data, today, locked_id)
        if row_index:
            safe_update_cell(sheet, row_index, COL_ATTEMPT, "⚠️ محاولة تسجيل باسم آخر")
    except Exception:
        pass

def check_device_lock(today, emp_id, emp_name):
    fp = get_device_fingerprint()
    locks = get_device_locks()

    for r in locks:
        if str(r.get("التاريخ","")).strip() == today and str(r.get("بصمة الجهاز","")).strip() == fp:
            locked_id = str(r.get("الرقم الشخصي","")).strip()
            locked_name = str(r.get("الاسم","")).strip()
            if locked_id and locked_id != str(emp_id).strip():
                log_attempt(today, fp, locked_id, locked_name, emp_id, emp_name)
                st.error("🚫 لا يمكن استخدام هذا الجهاز لتسجيل رقم شخصي آخر اليوم.")
                st.warning("⚠️ تم رصد محاولة تسجيل باسم مختلف، وتم توثيقها في النظام.")
                return False
    return True

def lock_device_for_today(today, emp_id, emp_name):
    fp = get_device_fingerprint()
    locks = get_device_locks()
    for r in locks:
        if str(r.get("التاريخ","")).strip() == today and \
           str(r.get("بصمة الجهاز","")).strip() == fp and \
           str(r.get("الرقم الشخصي","")).strip() == str(emp_id).strip():
            return True

    ok = safe_append(device_lock_sheet, [
        today, fp, str(emp_id), emp_name, datetime.now().strftime("%H:%M:%S")
    ])
    get_device_locks.clear()
    return ok

def register_operation(operation, emp_id, note=""):
    override_active, _ = get_location_override()
    if not st.session_state.get("location_allowed", False) and not override_active:
        st.error("❌ يجب تحديد الموقع أولاً أو تفعيل تجاوز الموقع من الأدمن.")
        return False

    emp_id = ar_to_en_digits(emp_id).strip()
    emp = validate_employee(emp_id) or st.session_state.get("emp_data")

    if not emp or str(emp.get("الرقم الشخصي", emp_id)).strip() != emp_id:
        st.error("❌ بيانات الموظفة غير مكتملة أو غير موجودة في القائمة البيضاء.")
        return False

    full_name = normalize_name(emp.get("الاسم", ""))
    school = emp.get("المدرسة", schools[0])
    task = emp.get("المهمة", TASKS_MAIN[0])
    is_support = "نعم" if ("دعم" in str(task) or emp.get("دعم")) else "لا"

    now = datetime.now()
    today = now.strftime("%Y-%m-%d")
    day_name = now.strftime("%A")
    time_now = now.strftime("%H:%M:%S")

    if not check_device_lock(today, emp_id, full_name):
        return False

    data = get_sheet_data()
    row_index, row = find_today_row(data, today, emp_id)

    if operation == "تسجيل حضور":
        if row and row.get("وقت الحضور"):
            st.error("❌ تم تسجيل الحضور مسبقاً لهذا اليوم.")
            return False

        if row_index:
            safe_update_cell(sheet, row_index, COL_ATTEND, time_now)
            safe_update_cell(sheet, row_index, COL_LATE_REASON, note)
        else:
            ok = safe_append(sheet, [
                today, day_name, school, task, is_support,
                full_name, emp_id, time_now, note,
                "", "", "", "", ""
            ])
            if not ok:
                st.error("❌ تعذر حفظ تسجيل الحضور، حاولي بعد قليل.")
                return False

        lock_device_for_today(today, emp_id, full_name)

        st.session_state.data_locked_today = True
        st.session_state.locked_emp = {
            "الرقم الشخصي": emp_id,
            "الاسم": full_name,
            "المدرسة": school,
            "المهمة": task,
            "دعم": is_support == "نعم",
            "نشط": "نعم"
        }
        st.session_state.locked_date = today
        ls_set("saved_date", today, "sv_date")
        ls_set("saved_id", emp_id, "sv_id")
        ls_set("saved_name", full_name, "sv_name")
        ls_set("saved_school", school, "sv_school")
        ls_set("saved_section", task, "sv_section")
        ls_set("saved_support", is_support, "sv_support")

        clear_caches()
        st.success("✅ تم تسجيل الحضور بنجاح.")
        return True

    if operation == "تسجيل انصراف":
        if not row_index or not row or not row.get("وقت الحضور"):
            st.error("❌ يجب تسجيل الحضور أولاً.")
            return False
        if row.get("وقت الانصراف"):
            st.error("❌ تم تسجيل الانصراف مسبقاً.")
            return False

        safe_update_cell(sheet, row_index, COL_DEPART, time_now)
        safe_update_cell(sheet, row_index, COL_DEPART_REASON, note)
        clear_caches()
        st.success("✅ تم تسجيل الانصراف بنجاح.")
        return True

    if operation == "خروج استئذان":
        if not row_index or not row or not row.get("وقت الحضور"):
            st.error("❌ يجب تسجيل الحضور أولاً.")
            return False
        if row.get("خروج استئذان") and not row.get("عودة"):
            st.error("❌ يوجد خروج استئذان مفتوح، سجّلي العودة أولاً.")
            return False
        if row.get("خروج استئذان"):
            st.error("❌ تم تسجيل خروج الاستئذان مسبقاً.")
            return False

        safe_update_cell(sheet, row_index, COL_EXIT, time_now)
        safe_update_cell(sheet, row_index, COL_DEPART_REASON, note)
        clear_caches()
        st.success("✅ تم تسجيل خروج الاستئذان بنجاح.")
        return True

    if operation == "عودة من استئذان":
        if not row_index or not row or not row.get("وقت الحضور"):
            st.error("❌ يجب تسجيل الحضور أولاً.")
            return False
        if not row.get("خروج استئذان"):
            st.error("❌ لا يوجد خروج استئذان مفتوح.")
            return False
        if row.get("عودة"):
            st.error("❌ تم تسجيل العودة مسبقاً.")
            return False

        safe_update_cell(sheet, row_index, COL_RETURN, time_now)
        clear_caches()
        st.success("✅ تم تسجيل العودة من الاستئذان بنجاح.")
        return True

    st.error("❌ عملية غير معروفة.")
    return False

# =========================================================
# Session State
# =========================================================
default_state = {
    "pending_operation": None,
    "admin_logged_in": False,
    "admin_last_active": None,
    "location_allowed": False,
    "emp_verified": False,
    "emp_data": None,
    "data_locked_today": False,
    "locked_emp": None,
    "locked_date": None,
}
for k, v in default_state.items():
    if k not in st.session_state:
        st.session_state[k] = v

today_str = datetime.now().strftime("%Y-%m-%d")

_saved_date = ls_get("saved_date")
_saved_id = ls_get("saved_id")
_saved_name = ls_get("saved_name")
_saved_school = ls_get("saved_school")
_saved_section = ls_get("saved_section")
_saved_support = ls_get("saved_support")

_data_locked = (
    st.session_state.get("data_locked_today", False)
    and st.session_state.get("locked_date") == today_str
) or (
    _saved_date == today_str and _saved_id and str(_saved_id).strip() != ""
)

if _data_locked and not st.session_state.emp_verified:
    st.session_state.emp_verified = True
    st.session_state.emp_data = st.session_state.get("locked_emp") or {
        "الرقم الشخصي": _saved_id,
        "الاسم": _saved_name or "",
        "المدرسة": _saved_school or "",
        "المهمة": _saved_section or "",
        "دعم": _saved_support == "نعم",
        "نشط": "نعم"
    }

if st.session_state.admin_logged_in and st.session_state.admin_last_active:
    idle = (datetime.now() - st.session_state.admin_last_active).seconds // 60
    if idle >= 30:
        st.session_state.admin_logged_in = False
        st.session_state.admin_last_active = None
        st.warning("⏱️ انتهت جلسة الأدمن بسبب الخمول.")

# =========================================================
# HEADER
# =========================================================
day_arabic = {
    "Saturday":"السبت","Sunday":"الأحد","Monday":"الاثنين",
    "Tuesday":"الثلاثاء","Wednesday":"الأربعاء",
    "Thursday":"الخميس","Friday":"الجمعة"
}.get(datetime.now().strftime("%A"), datetime.now().strftime("%A"))

st.markdown(f"""
<div class="app-header">
    <div class="sub">مركز مدرسة جدحفص للتصحيح المركزي — المنطقة التعليمية (2)</div>
    <div class="title">نظام الحضور والانصراف</div>
    <div class="date-pill">{day_arabic} — {today_str}</div>
</div>
""", unsafe_allow_html=True)

mode = st.radio("", ["👤 موظفة", "🛡️ أدمن"], horizontal=True, label_visibility="collapsed")

# =========================================================
# واجهة الموظفة
# =========================================================
if mode == "👤 موظفة":

    with st.container(border=True):
        st.markdown('<div class="card-title">📍 التحقق من الموقع</div>', unsafe_allow_html=True)
        location = streamlit_geolocation()

        if location:
            lat = location.get("latitude")
            lon = location.get("longitude")
            error = location.get("error", "")

            if error:
                st.session_state.location_allowed = False
                st.warning("⚠️ الموقع غير مفعّل، الرجاء تفعيل الموقع من إعدادات المتصفح أو الهاتف.")
            elif lat is not None and lon is not None:
                try:
                    dist_val = distance_m(float(lat), float(lon), SCHOOL_LAT, SCHOOL_LON)
                    if dist_val <= ALLOWED_RADIUS:
                        st.session_state.location_allowed = True
                        st.success(f"✅ داخل نطاق المدرسة — المسافة: {int(dist_val)} م")
                    else:
                        st.session_state.location_allowed = False
                        st.error(f"❌ خارج النطاق — المسافة: {int(dist_val)} م")
                except Exception:
                    st.session_state.location_allowed = False
                    st.error("❌ خطأ في قراءة الموقع.")
            else:
                st.session_state.location_allowed = False
                st.info("اضغطي زر تحديد الموقع أعلاه.")
        else:
            st.session_state.location_allowed = False
            st.info("اضغطي زر تحديد الموقع أعلاه.")

    ov_active, ov_end = get_location_override()
    if ov_active and ov_end:
        remaining = int((ov_end - datetime.now()).seconds / 60)
        st.warning(f"⚠️ وضع تجاوز الموقع مفعّل — ينتهي بعد {remaining} دقيقة.")
        st.session_state.location_allowed = True

    with st.container(border=True):
        st.markdown('<div class="card-title">🪪 البيانات الشخصية</div>', unsafe_allow_html=True)

        if _data_locked:
            emp = st.session_state.emp_data
            st.markdown(f"""
            <div class="field-lbl">الرقم الشخصي</div>
            <div class="field-val">{emp.get("الرقم الشخصي","")}</div>
            <div class="field-lbl">الاسم</div>
            <div class="field-val">{emp.get("الاسم","")}</div>
            <div class="field-lbl">المدرسة</div>
            <div class="field-val">{emp.get("المدرسة","")}</div>
            <div class="field-lbl">المهمة في الكنترول</div>
            <div class="field-val blue">{emp.get("المهمة","")}</div>
            <div style="font-size:12px;color:#3B6D11;font-weight:700;text-align:right;">🔒 بياناتك محفوظة لهذا اليوم</div>
            """, unsafe_allow_html=True)

        else:
            emp_id_raw = st.text_input("الرقم الشخصي", placeholder="أدخلي رقمك الشخصي", max_chars=20)
            emp_id = ar_to_en_digits(emp_id_raw).strip()

            if emp_id:
                emp = validate_employee(emp_id)
                if emp:
                    st.session_state.emp_verified = True
                    st.session_state.emp_data = {
                        "الرقم الشخصي": emp_id,
                        "الاسم": emp.get("الاسم",""),
                        "المدرسة": emp.get("المدرسة",""),
                        "المهمة": emp.get("المهمة",""),
                        "نشط": "نعم",
                        "دعم": "دعم" in str(emp.get("المهمة",""))
                    }
                    st.markdown(f"""
                    <div class="field-lbl">الاسم</div>
                    <div class="field-val">{emp.get("الاسم","")}</div>
                    <div class="field-lbl">المدرسة</div>
                    <div class="field-val">{emp.get("المدرسة","")}</div>
                    <div class="field-lbl">المهمة في الكنترول</div>
                    <div class="field-val blue">{emp.get("المهمة","")}</div>
                    """, unsafe_allow_html=True)
                    st.success("✅ تم التحقق من بياناتك.")
                else:
                    st.error("❌ الرقم الشخصي غير موجود أو غير نشط في القائمة البيضاء.")
                    st.session_state.emp_verified = False
                    st.session_state.emp_data = None

    if st.session_state.emp_verified and st.session_state.emp_data:
        emp = st.session_state.emp_data
        emp_id = str(emp.get("الرقم الشخصي","")).strip()

        data = get_sheet_data()
        _, today_row = find_today_row(data, today_str, emp_id)

        att_time = today_row.get("وقت الحضور","—") if today_row else "—"
        dep_time = today_row.get("وقت الانصراف","—") if today_row else "—"
        status = "حاضر ✓" if today_row and today_row.get("وقت الحضور") else "لم يُسجَّل"
        stat_col = "#3B6D11" if today_row and today_row.get("وقت الحضور") else "#A32D2D"

        st.markdown(f"""
        <div class="pro-card">
        <h3 style="color:#0c3460;text-align:right;">⚡ العمليات</h3>
        <div class="today-strip">
            <div class="stat-cell"><span class="stat-val">{att_time}</span><span class="stat-lbl">وقت الحضور</span></div>
            <div style="width:1px;background:#d3d1c7;margin:4px 0;"></div>
            <div class="stat-cell"><span class="stat-val">{dep_time}</span><span class="stat-lbl">وقت الانصراف</span></div>
            <div style="width:1px;background:#d3d1c7;margin:4px 0;"></div>
            <div class="stat-cell"><span class="stat-val" style="color:{stat_col};">{status}</span><span class="stat-lbl">الحالة</span></div>
        </div>
        </div>
        """, unsafe_allow_html=True)

        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ تسجيل حضور", use_container_width=True):
                st.session_state.pending_operation = None
                if datetime.now().time() > time(7, 30):
                    st.session_state.pending_operation = "تسجيل حضور"
                else:
                    register_operation("تسجيل حضور", emp_id)
        with col2:
            if st.button("🔵 تسجيل انصراف", use_container_width=True):
                st.session_state.pending_operation = None
                if datetime.now().time() < time(14, 0):
                    st.session_state.pending_operation = "تسجيل انصراف"
                else:
                    register_operation("تسجيل انصراف", emp_id)

        col3, col4 = st.columns(2)
        with col3:
            if st.button("📤 خروج استئذان", use_container_width=True):
                st.session_state.pending_operation = "خروج استئذان"
        with col4:
            if st.button("🔁 عودة من استئذان", use_container_width=True):
                st.session_state.pending_operation = None
                register_operation("عودة من استئذان", emp_id)

        if st.session_state.pending_operation == "تسجيل حضور":
            with st.container(border=True):
                st.markdown('<div class="card-title">سبب التأخير بعد الساعة 7:30 — اختياري</div>', unsafe_allow_html=True)
                late_reason = st.selectbox("السبب", ["اختاري السبب (اختياري)"] + reasons, key="late_reason")
                late_other = ""
                if late_reason == "أخرى":
                    late_other = st.text_input("اكتبي السبب", key="late_other")
                final = "" if late_reason == "اختاري السبب (اختياري)" else (late_other.strip() if late_reason == "أخرى" else late_reason)
                if st.button("تأكيد تسجيل الحضور", use_container_width=True, type="primary"):
                    st.session_state.pending_operation = None
                    register_operation("تسجيل حضور", emp_id, final)

        if st.session_state.pending_operation == "تسجيل انصراف":
            with st.container(border=True):
                st.markdown('<div class="card-title">سبب الانصراف قبل الساعة 2:00</div>', unsafe_allow_html=True)
                reason = st.selectbox("السبب", reasons, key="early_reason")
                other = ""
                if reason == "أخرى":
                    other = st.text_input("اكتبي السبب", key="early_other")
                final = other.strip() if reason == "أخرى" else reason
                if st.button("تأكيد تسجيل الانصراف", use_container_width=True, type="primary"):
                    st.session_state.pending_operation = None
                    register_operation("تسجيل انصراف", emp_id, final)

        if st.session_state.pending_operation == "خروج استئذان":
            with st.container(border=True):
                st.markdown('<div class="card-title">سبب خروج الاستئذان</div>', unsafe_allow_html=True)
                reason = st.selectbox("السبب", reasons, key="exit_reason")
                other = ""
                if reason == "أخرى":
                    other = st.text_input("اكتبي السبب", key="exit_other")
                final = other.strip() if reason == "أخرى" else reason
                if st.button("تأكيد خروج الاستئذان", use_container_width=True, type="primary"):
                    st.session_state.pending_operation = None
                    register_operation("خروج استئذان", emp_id, final)

# =========================================================
# واجهة الأدمن
# =========================================================
else:
    if not st.session_state.admin_logged_in:
        with st.container(border=True):
            st.markdown('<div class="card-title">🛡️ دخول الأدمن</div>', unsafe_allow_html=True)
            pw = st.text_input("كلمة المرور", type="password")
            if st.button("دخول", use_container_width=True):
                ADMIN_PASSWORD = st.secrets.get("admin_password", "Afaf1234")
                if pw.strip() == ADMIN_PASSWORD:
                    st.session_state.admin_logged_in = True
                    st.session_state.admin_last_active = datetime.now()
                    st.rerun()
                else:
                    st.error("❌ كلمة المرور غير صحيحة.")
    else:
        st.session_state.admin_last_active = datetime.now()
        st.markdown("## 🛡️ لوحة الأدمن")

        admin_tab = st.selectbox("القسم", [
            "📊 إحصائيات اليوم",
            "📋 القائمة البيضاء",
            "🚫 محاولات تسجيل باسم آخر",
            "📡 تجاوز الموقع",
            "🔓 فتح قفل جهاز",
        ])

        if admin_tab == "📊 إحصائيات اليوم":
            data = get_sheet_data()
            today_rows = [r for r in data if r.get("التاريخ") == today_str]
            c1, c2, c3 = st.columns(3)
            c1.metric("إجمالي المسجّلين", len(today_rows))
            c2.metric("حضور", sum(1 for r in today_rows if r.get("وقت الحضور")))
            c3.metric("انصراف", sum(1 for r in today_rows if r.get("وقت الانصراف")))

            st.markdown("### سجلات اليوم")
            for r in today_rows[-30:]:
                st.write(f"{r.get('الاسم الثلاثي','')} — حضور: {r.get('وقت الحضور','—')} — انصراف: {r.get('وقت الانصراف','—')}")

        elif admin_tab == "📋 القائمة البيضاء":
            st.markdown("### إضافة موظفة للقائمة البيضاء")
            wl_id = st.text_input("الرقم الشخصي")
            wl_name = st.text_input("الاسم")
            wl_school = st.selectbox("المدرسة", schools)
            wl_task = st.selectbox("المهمة", TASKS_ALL)
            wl_job = st.selectbox("المسمى الوظيفي", JOB_TITLES)

            if st.button("إضافة", use_container_width=True):
                if not wl_id.strip() or not wl_name.strip():
                    st.error("الرقم والاسم مطلوبان.")
                else:
                    ok = safe_append(whitelist_sheet, [
                        ar_to_en_digits(wl_id).strip(),
                        normalize_name(wl_name),
                        wl_school,
                        wl_task,
                        "",
                        "",
                        wl_job,
                        "نعم"
                    ])
                    get_whitelist.clear()
                    if ok:
                        st.success("✅ تمت الإضافة.")
                    else:
                        st.error("❌ تعذرت الإضافة.")

        elif admin_tab == "🚫 محاولات تسجيل باسم آخر":
            try:
                records = attempts_sheet.get_all_records()
                today_attempts = [r for r in records if r.get("التاريخ") == today_str]
                st.metric("محاولات اليوم", len(today_attempts))
                for r in reversed(today_attempts[-50:]):
                    st.warning(
                        f"الجهاز المقفول على: {r.get('اسم_المقفول_عليه','')} ({r.get('الرقم_المقفول_عليه','')}) "
                        f"— حاول: {r.get('اسم_المحاول','')} ({r.get('الرقم_المحاول','')}) "
                        f"— الوقت: {r.get('وقت_المحاولة','')}"
                    )
            except Exception as e:
                st.error(f"تعذر تحميل المحاولات: {e}")

        elif admin_tab == "📡 تجاوز الموقع":
            active, end_dt = get_location_override()
            if active and end_dt:
                st.warning(f"تجاوز الموقع مفعّل حتى {end_dt.strftime('%H:%M')}")
                if st.button("إيقاف تجاوز الموقع", use_container_width=True):
                    disable_location_override()
                    st.success("تم الإيقاف.")
                    st.rerun()
            else:
                duration = st.selectbox("مدة التجاوز", [30, 60, 90, 120, 180])
                reason = st.text_input("سبب التجاوز")
                if st.button("تفعيل تجاوز الموقع", use_container_width=True):
                    if not reason.strip():
                        st.error("السبب مطلوب.")
                    else:
                        ok, end_dt = set_location_override(duration, reason)
                        if ok:
                            st.success(f"تم التفعيل حتى {end_dt.strftime('%H:%M')}")
                            st.rerun()
                        else:
                            st.error("تعذر التفعيل.")

        elif admin_tab == "🔓 فتح قفل جهاز":
            st.info("استخدمي هذه الخاصية عند وجود سبب رسمي لاستخدام نفس الجهاز لموظفة أخرى.")
            unlock_id = st.text_input("الرقم الشخصي المقفول عليه")
            if st.button("حذف قفل اليوم لهذا الرقم", use_container_width=True):
                try:
                    records = device_lock_sheet.get_all_records()
                    deleted = False
                    for i, r in enumerate(records):
                        if str(r.get("التاريخ","")).strip() == today_str and str(r.get("الرقم الشخصي","")).strip() == unlock_id.strip():
                            device_lock_sheet.delete_rows(i + 2)
                            deleted = True
                            break
                    get_device_locks.clear()
                    if deleted:
                        st.success("✅ تم حذف القفل.")
                    else:
                        st.warning("لم يتم العثور على قفل لهذا الرقم اليوم.")
                except Exception as e:
                    st.error(f"تعذر حذف القفل: {e}")

        if st.button("🚪 تسجيل خروج الأدمن", use_container_width=True):
            st.session_state.admin_logged_in = False
            st.session_state.admin_last_active = None
            st.rerun()

# =========================================================
# Footer
# =========================================================
st.markdown("""
<div class="footer-bar">
    <span>تصميم: <span class="hl">أ. عفاف حسين</span></span>
    <span>رئيسة المركز: <span class="hl">أ. خلود يعقوب بدو</span></span>
</div>
""", unsafe_allow_html=True)

