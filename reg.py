import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, time, timedelta
from streamlit_geolocation import streamlit_geolocation
try:
    from streamlit_local_storage import LocalStorage
    localS = LocalStorage()
    LOCAL_STORAGE_OK = True
except Exception:
    localS = None
    LOCAL_STORAGE_OK = False
import math
import random
import string
import time as time_module

st.set_page_config(
    page_title="نظام الحضور والانصراف",
    page_icon="🕘",
    layout="centered"
)

# ─── إعدادات المدرسة ───────────────────────────────────────────
SCHOOL_LAT = 26.216371784473964
SCHOOL_LON = 50.54035843289093
ALLOWED_RADIUS = 150

# ─── Google Sheets ──────────────────────────────────────────────
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
    return client.open_by_key("1svkfgRq4-osKr86_2WJQFZShuoy8Ek5DOiUaaHKL-6Y")

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

sheet             = spreadsheet.worksheet("sheet1")
whitelist_sheet   = get_or_create_sheet("القائمة_البيضاء",         ["الرقم الشخصي","الاسم","المدرسة","المهمة","رقم التواصل","البريد الإلكتروني","المسمى الوظيفي","نشط"])
settings_sheet    = get_or_create_sheet("إعدادات_النظام",          ["المفتاح","القيمة","تاريخ_الانتهاء","ملاحظات"])
device_lock_sheet = get_or_create_sheet("device_lock",             ["التاريخ","بصمة الجهاز","الرقم الشخصي","الاسم","وقت_القفل"])
attempts_sheet    = get_or_create_sheet("محاولات_تسجيل_باسم_آخر", ["التاريخ","بصمة الجهاز","الرقم_المقفول_عليه","اسم_المقفول_عليه","الرقم_المحاول","اسم_المحاول","وقت_المحاولة","ملاحظات"])
audit_sheet       = get_or_create_sheet("سجل_التدقيق",             ["التاريخ","الوقت","المستخدم","الرقم الشخصي","نوع العملية","التفاصيل","بصمة الجهاز"])

# أعمدة sheet1 ── ══ محدّثة ══
COL_DATE       = 1
COL_DAY        = 2
COL_SCHOOL     = 3
COL_TASK       = 4
COL_SUPPORT    = 5   # ══ جديد: دعم ══
COL_NAME       = 6
COL_ID         = 7
COL_ATTEND     = 8
COL_LATE_RSN   = 9
COL_DEPART     = 10
COL_DEPART_RSN = 11
COL_EXIT       = 12
COL_RETURN     = 13
COL_ATTEMPT    = 14  # ══ جديد: محاولة تسجيل باسم آخر ══

# ─── بيانات ثابتة ───────────────────────────────────────────────
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
sections = TASKS_ALL

JOB_TITLES = [
    "منسقة","معلمة أولى","معلمة","معلم أول","معلم",
    "فني دعم تقنية المعلومات","مشرف تربوي","أخرى"
]
reasons = ["دوام مرن","موعد","مهمة رسمية","رعاية","أخرى"]

# ─── CSS ────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;900&display=swap');
html, body, [class*="css"] { direction: rtl; text-align: right; font-family: 'Cairo', Tahoma, sans-serif; }
.block-container { max-width: 620px; padding-top: 0px; padding-bottom: 40px; }
.stContainer > div, .element-container, .stMarkdown,
.stTextInput, .stSelectbox, .stRadio, .stButton { direction: rtl !important; text-align: right !important; }
.stAlert, .stSuccess, .stError, .stWarning, .stInfo { direction: rtl !important; text-align: right !important; }
.app-header {
    background: linear-gradient(135deg, #0c3460 0%, #1a5276 60%, #1f6fa3 100%);
    border-radius: 0 0 28px 28px; padding: 28px 24px 32px;
    text-align: center; margin: -1rem -1rem 20px -1rem;
}
.app-header .sub { color: rgba(255,255,255,0.78); font-size: 12px; font-weight: 600; margin-bottom: 6px; }
.app-header .title { color: #fff; font-size: 22px; font-weight: 900; }
.app-header .date-pill {
    display: inline-block; background: rgba(255,255,255,0.15);
    border: 1px solid rgba(255,255,255,0.2); border-radius: 20px;
    padding: 3px 14px; color: rgba(255,255,255,0.9);
    font-size: 12px; font-weight: 600; margin-top: 10px;
}
.pro-card { background: #fff; border-radius: 20px; padding: 18px 20px; box-shadow: 0 2px 14px rgba(12,52,96,0.07); margin-bottom: 14px; }
.card-head { display: flex; align-items: center; gap: 10px; margin-bottom: 14px; }
.card-ico { width: 36px; height: 36px; border-radius: 10px; display: flex; align-items: center; justify-content: center; font-size: 17px; flex-shrink: 0; }
.field-lbl { font-size: 11px; font-weight: 700; color: #888780; margin-bottom: 3px; }
.field-val { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 12px; padding: 10px 14px; font-size: 14px; font-weight: 700; color: #0c3460; margin-bottom: 10px; }
.field-val.locked { background: #eaf3de; border-color: #c0dd97; color: #27500A; }
.today-strip { display:flex; justify-content:space-around; background:#f0f4f8; border-radius:12px; padding:12px 8px; margin-bottom:14px; }
.stat-cell { text-align:center; }
.stat-val { font-size:17px; font-weight:900; color:#0c3460; display:block; }
.stat-lbl { font-size:10px; font-weight:600; color:#888780; }
.device-warn { background:#faeeda; border:1px solid #EF9F27; border-radius:12px; padding:11px 14px; font-size:12px; font-weight:700; color:#633806; margin-bottom:10px; }
.attempt-warn { background:#fcebeb; border:1px solid #f09595; border-radius:12px; padding:11px 14px; font-size:13px; font-weight:700; color:#791F1F; margin-bottom:10px; }
.admin-header { background: linear-gradient(135deg,#26215C,#3C3489); border-radius:16px; padding:16px 20px; margin-bottom:14px; text-align:center; }
.admin-header .t { color:#fff; font-size:18px; font-weight:900; }
.admin-header .s { color:rgba(255,255,255,.75); font-size:12px; }
.admin-section { font-size:11px;font-weight:700;color:#888780;letter-spacing:.5px;margin:16px 0 8px; }
.audit-row { background:#f8fafc; border-radius:10px; padding:10px 14px; border-right:3px solid #378ADD; margin-bottom:6px; font-size:12px; color:#0c3460; }
.audit-row .ar-op { font-weight:900; font-size:13px; }
.audit-row .ar-det { color:#5F5E5A; font-weight:600; margin-top:2px; }
.audit-row .ar-time { color:#888780; font-size:11px; float:left; }
.warn-row { background:#faeeda; border-radius:10px; padding:10px 14px; border-right:3px solid #BA7517; margin-bottom:6px; font-size:12px; color:#633806; font-weight:700; }
.footer-bar { background:#0c3460; border-radius:14px; padding:12px 18px; display:flex; justify-content:space-between; align-items:center; margin-top:6px; }
.footer-bar span { font-size:11px; font-weight:600; color:rgba(255,255,255,.7); }
.footer-bar .hl { color:#fff; }
label, .stSelectbox label, .stTextInput label { font-size:15px !important; font-weight:700 !important; color:#0c3460 !important; }
.stButton button { border-radius:14px !important; font-size:15px !important; font-weight:800 !important; font-family:'Cairo',sans-serif !important; }
</style>
""", unsafe_allow_html=True)

# ─── دوال مساعدة ────────────────────────────────────────────────
def distance_m(lat1, lon1, lat2, lon2):
    R = 6371000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))

def normalize_name(name):
    name = str(name).strip()
    for old, new in {"أ":"ا","إ":"ا","آ":"ا","ى":"ي","ة":"ه","ؤ":"و","ئ":"ي"}.items():
        name = name.replace(old, new)
    for ch in [".", "،", ",", "-", "_", "ـ", ":", ";"]:
        name = name.replace(ch, " ")
    return " ".join(name.split())

def ar_to_en_digits(text):
    ar = "٠١٢٣٤٥٦٧٨٩"
    en = "0123456789"
    result = str(text).strip()
    for a, e in zip(ar, en):
        result = result.replace(a, e)
    return result

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

@st.cache_data(ttl=60)
def get_whitelist():
    try:
        records = whitelist_sheet.get_all_records()
        result = {}
        for r in records:
            if str(r.get("نشط","")).strip() == "نعم":
                eid = str(r.get("الرقم الشخصي","")).strip()
                if eid:
                    result[eid] = r
        return result
    except Exception:
        return {}

def invalidate_whitelist():
    get_whitelist.clear()

def validate_employee(emp_id):
    return get_whitelist().get(str(emp_id).strip())

@st.cache_data(ttl=30)
def get_sheet_data():
    try:
        return sheet.get_all_records()
    except Exception:
        return []

def invalidate_sheet():
    get_sheet_data.clear()

@st.cache_data(ttl=120)
def get_device_locks():
    try:
        return device_lock_sheet.get_all_records()[-200:]
    except Exception:
        return []

def find_today_row(data, today, emp_id):
    for i, row in enumerate(data):
        if str(row.get("الرقم الشخصي","")).strip() == str(emp_id).strip() \
           and row.get("التاريخ") == today:
            return i + 2, row
    return None, None

def log_audit(emp_id, emp_name, operation, details):
    now = datetime.now()
    fp  = get_device_fingerprint()
    safe_append(audit_sheet, [
        now.strftime("%Y-%m-%d"),
        now.strftime("%H:%M:%S"),
        emp_name,
        str(emp_id),
        operation,
        details,
        fp
    ])

# ══════════════════════════════════════════════════════════════════
# ══ قفل الجهاز — جديد ══
# ══════════════════════════════════════════════════════════════════
def check_device_lock(today, emp_id, emp_name):
    """
    يتحقق إذا الجهاز مقفول على رقم شخصي مختلف اليوم.
    إذا مقفول → يسجّل المحاولة ويرفض.
    """
    fp    = get_device_fingerprint()
    locks = get_device_locks()

    for r in locks:
        if str(r.get("التاريخ","")).strip()      == today and \
           str(r.get("بصمة الجهاز","")).strip()  == fp:
            locked_id   = str(r.get("الرقم الشخصي","")).strip()
            locked_name = str(r.get("الاسم","")).strip()
            if locked_id and locked_id != str(emp_id).strip():
                # سجّل المحاولة
                _log_attempt(today, fp, locked_id, locked_name, emp_id, emp_name)
                st.markdown(f"""
<div class="attempt-warn">
🚫 هذا الجهاز مقفول اليوم على: <b>{locked_name}</b><br>
لا يمكن تسجيل رقم شخصي مختلف من نفس الجهاز.<br>
<span style="font-size:11px;">⚠️ تم توثيق هذه المحاولة في النظام.</span>
</div>""", unsafe_allow_html=True)
                return False
    return True

def lock_device_for_today(today, emp_id, emp_name):
    """يقفل الجهاز على الرقم الشخصي لهذا اليوم."""
    fp    = get_device_fingerprint()
    locks = get_device_locks()

    # تحقق إذا مقفول مسبقاً لنفس الرقم
    for r in locks:
        if str(r.get("التاريخ","")).strip()     == today and \
           str(r.get("بصمة الجهاز","")).strip() == fp    and \
           str(r.get("الرقم الشخصي","")).strip() == str(emp_id).strip():
            return True  # مقفول مسبقاً — لا حاجة لإعادة القفل

    ok = safe_append(device_lock_sheet, [
        today, fp, str(emp_id), emp_name,
        datetime.now().strftime("%H:%M:%S")
    ])
    get_device_locks.clear()
    return ok

def _log_attempt(today, fp, locked_id, locked_name, attempted_id, attempted_name):
    """يسجّل محاولة تسجيل برقم مختلف من نفس الجهاز."""
    now  = datetime.now().strftime("%H:%M:%S")
    note = "محاولة تسجيل رقم شخصي مختلف من نفس الجهاز"

    safe_append(attempts_sheet, [
        today, fp, locked_id, locked_name,
        attempted_id, attempted_name, now, note
    ])

    # علّم السجل في sheet1
    try:
        data = get_sheet_data()
        row_index, _ = find_today_row(data, today, locked_id)
        if row_index:
            safe_update_cell(sheet, row_index, COL_ATTEMPT, "⚠️ محاولة تسجيل باسم آخر")
    except Exception:
        pass

    log_audit(attempted_id, attempted_name, "محاولة تسجيل باسم آخر",
              f"الجهاز مقفول على: {locked_name} ({locked_id})")

# ══════════════════════════════════════════════════════════════════
# ══ تجاوز الموقع ══
# ══════════════════════════════════════════════════════════════════
def get_location_override():
    try:
        records = settings_sheet.get_all_records()
        for r in records:
            if str(r.get("المفتاح","")).strip() == "location_override":
                val      = str(r.get("القيمة","")).strip()
                end_time = str(r.get("تاريخ_الانتهاء","")).strip()
                if val == "true" and end_time:
                    try:
                        end_dt = datetime.strptime(end_time, "%Y-%m-%d %H:%M")
                        if datetime.now() < end_dt:
                            return True, end_dt
                        else:
                            _disable_location_override_silent()
                            return False, None
                    except Exception:
                        return False, None
    except Exception:
        pass
    return False, None

def _disable_location_override_silent():
    try:
        records = settings_sheet.get_all_records()
        for i, r in enumerate(records):
            if str(r.get("المفتاح","")).strip() == "location_override":
                settings_sheet.update_cell(i + 2, 2, "false")
                break
    except Exception:
        pass

def set_location_override(minutes, admin_note=""):
    end_dt  = datetime.now() + timedelta(minutes=minutes)
    end_str = end_dt.strftime("%Y-%m-%d %H:%M")
    try:
        records   = settings_sheet.get_all_records()
        row_found = None
        for i, r in enumerate(records):
            if str(r.get("المفتاح","")).strip() == "location_override":
                row_found = i + 2
                break
        if row_found:
            settings_sheet.update(f"A{row_found}:D{row_found}",
                                  [["location_override","true",end_str,admin_note]])
        else:
            safe_append(settings_sheet, ["location_override","true",end_str,admin_note])
        log_audit("أدمن","النظام","تفعيل تجاوز الموقع",
                  f"المدة: {minutes} دقيقة | ينتهي: {end_str} | {admin_note}")
        return True, end_dt
    except Exception:
        return False, None

def disable_location_override():
    _disable_location_override_silent()
    log_audit("أدمن","النظام","إيقاف تجاوز الموقع","أوقفه الأدمن يدوياً")

# ══════════════════════════════════════════════════════════════════
# ══ العملية الرئيسية للتسجيل ══
# ══════════════════════════════════════════════════════════════════
def register_operation(operation, emp_id, note=""):
    override_active, _ = get_location_override()
    if not st.session_state.get("location_allowed", False) and not override_active:
        st.error("❌ لا يمكن التسجيل خارج نطاق المدرسة")
        return False

    emp_id = ar_to_en_digits(str(emp_id)).strip()
    if not emp_id:
        st.error("❌ الرقم الشخصي مطلوب")
        return False

    emp = validate_employee(emp_id)
    if not emp:
        emp = st.session_state.get("emp_data")
        if not emp or str(emp.get("الرقم الشخصي","")).strip() != emp_id:
            st.error("❌ بيانات غير مكتملة")
            return False
        is_support = emp.get("دعم", False)
        if not is_support:
            try:
                whitelist_sheet.append_row([
                    emp_id, emp.get("الاسم",""), emp.get("المدرسة",""),
                    emp.get("المهمة",""), emp.get("رقم التواصل",""),
                    emp.get("البريد الإلكتروني",""), emp.get("المسمى الوظيفي",""), "نعم"
                ])
                log_audit(emp_id, emp.get("الاسم",""), "تسجيل موظفة جديدة",
                          f"مدرسة: {emp.get('المدرسة','')} | قسم: {emp.get('المهمة','')}")
            except Exception as e:
                st.warning(f"⚠️ تعذّر الحفظ في القائمة البيضاء: {e}")

    full_name  = normalize_name(emp.get("الاسم",""))
    school     = emp.get("المدرسة", schools[0])
    task       = emp.get("المهمة", TASKS_MAIN[0])
    is_support = emp.get("دعم", False) or "دعم" in str(task)
    support_val = "نعم" if is_support else "لا"   # ══ جديد ══

    now      = datetime.now()
    today    = now.strftime("%Y-%m-%d")
    day_name = now.strftime("%A")
    time_now = now.strftime("%H:%M:%S")

    # ══ فحص قفل الجهاز (حضور فقط) ══
    if operation == "تسجيل حضور":
        if not check_device_lock(today, emp_id, full_name):
            return False

    data = get_sheet_data()
    row_index, row = find_today_row(data, today, emp_id)

    if operation == "تسجيل حضور":
        if row_index and row.get("وقت الحضور"):
            st.error("❌ تم تسجيل الحضور مسبقاً لهذا الرقم الشخصي اليوم")
            return False

        if row_index:
            safe_update_cell(sheet, row_index, COL_ATTEND,   time_now)
            safe_update_cell(sheet, row_index, COL_LATE_RSN, note)
            safe_update_cell(sheet, row_index, COL_SUPPORT,  support_val)  # ══ جديد ══
        else:
            ok = safe_append(sheet, [
                today, day_name, school, task,
                support_val,           # ══ جديد: عمود دعم ══
                full_name, emp_id,
                time_now, note,
                "", "", "", "", ""     # انصراف، سبب، خروج، عودة، محاولة
            ])
            if not ok:
                st.error("❌ تعذر حفظ تسجيل الحضور، حاولي بعد قليل.")
                return False

        # ══ قفل الجهاز بعد الحضور ══
        lock_device_for_today(today, emp_id, full_name)

        log_audit(emp_id, full_name, "تسجيل حضور",
                  f"الوقت: {time_now} | السبب: {note or 'بدون'} | دعم: {support_val}")

        # حفظ في session + LocalStorage
        st.session_state.data_locked_today = True
        st.session_state.locked_emp = {
            "الرقم الشخصي": emp_id, "الاسم": full_name,
            "المدرسة": school, "المهمة": task,
            "دعم": is_support, "نشط": "نعم"
        }
        st.session_state.locked_date = today
        ls_set("saved_date",    today,        "sv_date")
        ls_set("saved_id",      emp_id,       "sv_id")
        ls_set("saved_name",    full_name,    "sv_name")
        ls_set("saved_school",  school,       "sv_school")
        ls_set("saved_section", task,         "sv_section")
        ls_set("saved_support", support_val,  "sv_support")

    elif operation == "تسجيل انصراف":
        if not row_index or not row.get("وقت الحضور"):
            st.error("❌ لا يوجد تسجيل حضور لهذا الرقم اليوم")
            return False
        if row.get("وقت الانصراف"):
            st.error("❌ تم تسجيل الانصراف مسبقاً")
            return False
        safe_update_cell(sheet, row_index, COL_DEPART,     time_now)
        safe_update_cell(sheet, row_index, COL_DEPART_RSN, note)
        log_audit(emp_id, full_name, "تسجيل انصراف",
                  f"الوقت: {time_now} | السبب: {note or 'بدون'}")

    elif operation == "خروج استئذان":
        if not row_index or not row.get("وقت الحضور"):
            st.error("❌ لا يوجد تسجيل حضور لهذا الرقم اليوم")
            return False
        if row.get("خروج استئذان") and not row.get("عودة"):
            st.error("❌ يوجد خروج استئذان مفتوح، سجّلي العودة أولاً")
            return False
        if row.get("خروج استئذان"):
            st.error("❌ تم تسجيل خروج الاستئذان مسبقاً")
            return False
        safe_update_cell(sheet, row_index, COL_EXIT,       time_now)
        safe_update_cell(sheet, row_index, COL_DEPART_RSN, note)
        log_audit(emp_id, full_name, "خروج استئذان",
                  f"الوقت: {time_now} | السبب: {note}")

    elif operation == "عودة من استئذان":
        if not row_index or not row.get("وقت الحضور"):
            st.error("❌ لا يوجد تسجيل حضور لهذا الرقم اليوم")
            return False
        if not row.get("خروج استئذان"):
            st.error("❌ لا يوجد خروج استئذان مفتوح")
            return False
        if row.get("عودة"):
            st.error("❌ تم تسجيل العودة مسبقاً")
            return False
        safe_update_cell(sheet, row_index, COL_RETURN, time_now)
        log_audit(emp_id, full_name, "عودة من استئذان", f"الوقت: {time_now}")

    invalidate_sheet()
    st.session_state.pending_operation = None
    st.success(f"✅ تم {operation} بنجاح")
    return True

# ══════════════════════════════════════════════════════════════════
# SESSION STATE
# ══════════════════════════════════════════════════════════════════
for k, v in {
    "pending_operation": None,
    "admin_logged_in": False,
    "admin_last_active": None,
    "location_allowed": False,
    "emp_verified": False,
    "emp_data": None,
    "data_unlocked": False,
    "data_locked_today": False,
    "locked_emp": None,
    "locked_date": None,
    "data_confirmed": False,
    "support_status": "",
}.items():
    if k not in st.session_state:
        st.session_state[k] = v

today_str = datetime.now().strftime("%Y-%m-%d")

_saved_date    = ls_get("saved_date")
_saved_id      = ls_get("saved_id")
_saved_name    = ls_get("saved_name")
_saved_school  = ls_get("saved_school")
_saved_section = ls_get("saved_section")
_saved_support = ls_get("saved_support")

_session_locked = (
    st.session_state.get("data_locked_today", False)
    and st.session_state.get("locked_date") == today_str
    and not st.session_state.get("data_unlocked", False)
)
_data_locked = _session_locked or (
    _saved_date == today_str and _saved_id
    and str(_saved_id).strip() != ""
    and not st.session_state.get("data_unlocked", False)
)

if _data_locked and not st.session_state.emp_verified:
    locked_emp = st.session_state.get("locked_emp") or {
        "الرقم الشخصي": _saved_id,
        "الاسم": _saved_name or "",
        "المدرسة": _saved_school or (schools[0] if schools else ""),
        "المهمة": _saved_section or (sections[0] if sections else ""),
        "نشط": "نعم",
        "دعم": _saved_support == "نعم"
    }
    st.session_state.emp_verified = True
    st.session_state.emp_data = locked_emp

if st.session_state.admin_logged_in and st.session_state.admin_last_active:
    idle = (datetime.now() - st.session_state.admin_last_active).seconds // 60
    if idle >= 30:
        st.session_state.admin_logged_in   = False
        st.session_state.admin_last_active = None
        st.warning("⏱️ انتهت جلسة الأدمن بسبب الخمول")

# ══════════════════════════════════════════════════════════════════
# HEADER
# ══════════════════════════════════════════════════════════════════
try:
    st.image("logo.png", use_container_width=True)
except Exception:
    pass

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

# ══════════════════════════════════════════════════════════════════
# واجهة الموظفة
# ══════════════════════════════════════════════════════════════════
if mode == "👤 موظفة":

    # ── كارد الموقع ──────────────────────────────────────────────
    with st.container(border=True):
        st.markdown('''<div style="display:flex;align-items:center;gap:10px;margin-bottom:10px;direction:rtl;">
<div style="width:36px;height:36px;border-radius:10px;background:#e6f1fb;display:flex;align-items:center;justify-content:center;font-size:17px;">📍</div>
<b style="color:#0c3460;font-size:15px;">التحقق من الموقع</b></div>''', unsafe_allow_html=True)

        location = streamlit_geolocation()

        if location:
            lat   = location.get("latitude")
            lon   = location.get("longitude")
            error = location.get("error", "")

            if error:
                st.session_state.location_allowed = False
                st.warning("⚠️ الموقع غير مفعّل — الرجاء تفعيله من إعدادات الهاتف")
            elif lat is not None and lon is not None:
                try:
                    dist_val = distance_m(float(lat), float(lon), SCHOOL_LAT, SCHOOL_LON)
                    if dist_val <= ALLOWED_RADIUS:
                        st.session_state.location_allowed = True
                        st.markdown(f'<div style="background:#eaf3de;border:1px solid #c0dd97;border-radius:12px;padding:11px 14px;font-size:13px;font-weight:700;color:#27500A;">✅ داخل نطاق المدرسة — المسافة: {int(dist_val)} م</div>', unsafe_allow_html=True)
                    else:
                        st.session_state.location_allowed = False
                        st.markdown(f'<div style="background:#fcebeb;border:1px solid #f09595;border-radius:12px;padding:11px 14px;font-size:13px;font-weight:700;color:#791F1F;">❌ خارج النطاق — المسافة: {int(dist_val)} م</div>', unsafe_allow_html=True)
                except Exception:
                    st.session_state.location_allowed = False
                    st.error("❌ خطأ في قراءة الموقع")
            else:
                st.session_state.location_allowed = False
                st.info("اضغطي زر تحديد الموقع أعلاه")
        else:
            st.session_state.location_allowed = False
            st.info("اضغطي زر تحديد الموقع أعلاه")

    _ov_active, _ov_end = get_location_override()
    if _ov_active and _ov_end:
        _ov_remaining = int((_ov_end - datetime.now()).seconds / 60)
        st.warning(f"⚠️ وضع تجاوز الموقع مفعّل — ينتهي بعد {_ov_remaining} دقيقة")
        st.session_state.location_allowed = True

    # ── كارد البيانات الشخصية ────────────────────────────────────
    with st.container(border=True):
        st.markdown('<div class="card-head"><div class="card-ico" style="background:#faeeda;">🪪</div><b style="color:#0c3460;font-size:15px;">البيانات الشخصية</b></div>', unsafe_allow_html=True)

        if _data_locked:
            emp         = st.session_state.emp_data
            locked_id   = emp.get("الرقم الشخصي","")
            locked_task = emp.get("المهمة","")
            task_ar     = locked_task.split("/")[0].strip() if "/" in locked_task else locked_task
            badge_color = "#185FA5" if "كنترول" in task_ar else "#3B6D11"
            badge_bg    = "#e6f1fb" if "كنترول" in task_ar else "#eaf3de"
            st.markdown(f"""
<div class="field-lbl">الرقم الشخصي</div>
<div class="field-val locked">{locked_id}</div>
<div class="field-lbl">الاسم</div>
<div class="field-val locked">{emp.get("الاسم","")}</div>
<div class="field-lbl">المدرسة</div>
<div class="field-val locked">{emp.get("المدرسة","")}</div>
<div class="field-lbl">المهمة في الكنترول</div>
<div class="field-val locked" style="background:{badge_bg};border-color:{badge_color};color:{badge_color};font-size:13px;">{task_ar}</div>
<div style="font-size:11px;color:#3B6D11;font-weight:700;margin-top:4px;">🔒 بياناتك محفوظة لهذا اليوم</div>
""", unsafe_allow_html=True)

        else:
            emp_id_raw   = st.text_input("الرقم الشخصي", placeholder="أدخلي رقمك الشخصي", max_chars=20, key="emp_id_field")
            emp_id_input = ar_to_en_digits(emp_id_raw).strip()

            if emp_id_input:
                wl_emp = validate_employee(emp_id_input)

                if wl_emp:
                    task_raw      = wl_emp.get("المهمة","")
                    task_ar       = task_raw.split("/")[0].strip() if "/" in task_raw else task_raw
                    is_support_wl = str(wl_emp.get("دعم","")).strip() == "نعم" or "دعم" in task_raw
                    badge_color   = "#185FA5" if "كنترول" in task_ar else "#3B6D11"
                    badge_bg      = "#e6f1fb" if "كنترول" in task_ar else "#eaf3de"

                    st.markdown(f"""
<div class="field-lbl">الاسم</div>
<div class="field-val locked">{wl_emp.get("الاسم","")}</div>
<div class="field-lbl">المدرسة</div>
<div class="field-val locked">{wl_emp.get("المدرسة","")}</div>
<div class="field-lbl">المهمة في الكنترول</div>
<div class="field-val locked" style="background:{badge_bg};border-color:{badge_color};color:{badge_color};font-size:13px;">{task_ar}</div>
""", unsafe_allow_html=True)

                    if is_support_wl:
                        st.warning("⚠️ سُجِّلت سابقاً كدعم — هل لا تزالين دعماً اليوم؟")
                        col_s, col_m = st.columns(2)
                        with col_s:
                            still_support = st.button("✅ نعم، لا تزال دعماً", use_container_width=True, key="btn_still_support")
                        with col_m:
                            now_member = st.button("👩‍🏫 لا، انضممت عضوة أصلية", use_container_width=True, key="btn_now_member")

                        if still_support:
                            st.session_state.support_status = "دعم"
                            st.rerun()
                        if now_member:
                            st.session_state.support_status = "عضوة"
                            st.rerun()

                        status = st.session_state.get("support_status","")
                        if status == "دعم":
                            st.success("✅ مسجّلة كدعم لهذا اليوم")
                            st.session_state.emp_verified = True
                            st.session_state.emp_data = {
                                "الرقم الشخصي": emp_id_input,
                                "الاسم":   wl_emp.get("الاسم",""),
                                "المدرسة": wl_emp.get("المدرسة",""),
                                "المهمة":  task_raw,
                                "نشط":     "نعم", "دعم": True,
                            }
                        elif status == "عضوة":
                            new_member_task = st.selectbox("المهمة الجديدة", TASKS_MAIN, key="new_member_task")
                            new_member_job  = st.selectbox("المسمى الوظيفي", JOB_TITLES, key="new_member_job")
                            if new_member_job == "أخرى":
                                new_member_job = st.text_input("اكتبي المسمى", key="new_member_job_other") or "أخرى"
                            if st.button("✅ تأكيد الانضمام كعضوة أصلية", use_container_width=True, key="btn_confirm_member", type="primary"):
                                try:
                                    wl_records = whitelist_sheet.get_all_records()
                                    for i, r in enumerate(wl_records):
                                        if str(r.get("الرقم الشخصي","")).strip() == emp_id_input:
                                            whitelist_sheet.update_cell(i+2, 4, new_member_task)
                                            whitelist_sheet.update_cell(i+2, 7, new_member_job)
                                            break
                                    log_audit(emp_id_input, wl_emp.get("الاسم",""),
                                              "تحويل من دعم لعضوة أصلية",
                                              f"المهمة الجديدة: {new_member_task}")
                                except Exception as ex:
                                    st.warning(f"⚠️ تعذّر التحديث: {ex}")
                                st.session_state.support_status = ""
                                st.session_state.emp_verified = True
                                st.session_state.emp_data = {
                                    "الرقم الشخصي": emp_id_input,
                                    "الاسم":   wl_emp.get("الاسم",""),
                                    "المدرسة": wl_emp.get("المدرسة",""),
                                    "المهمة":  new_member_task,
                                    "المسمى الوظيفي": new_member_job,
                                    "نشط": "نعم", "دعم": False,
                                }
                                st.rerun()
                    else:
                        st.markdown('<div style="font-size:11px;color:#3B6D11;font-weight:700;margin-top:4px;">✓ موظفة مسجّلة</div>', unsafe_allow_html=True)
                        st.session_state.emp_verified = True
                        st.session_state.emp_data = {
                            "الرقم الشخصي": emp_id_input,
                            "الاسم":   wl_emp.get("الاسم",""),
                            "المدرسة": wl_emp.get("المدرسة",""),
                            "المهمة":  task_raw,
                            "نشط": "نعم", "دعم": False,
                        }
                else:
                    # موظفة جديدة
                    st.markdown('<div style="font-size:12px;color:#185FA5;font-weight:700;margin-bottom:6px;">⚡ رقم جديد — أكملي بياناتك للتسجيل</div>', unsafe_allow_html=True)
                    new_name   = st.text_input("الاسم الرباعي", placeholder="اكتبي اسمك الرباعي كاملاً", key="new_name")
                    new_school = st.selectbox("المدرسة", schools, key="new_school")
                    emp_type   = st.radio("نوع التسجيل", ["👩‍🏫 عضوة في المركز", "🔄 دعم"], horizontal=True, key="emp_type_radio")
                    is_support = emp_type == "🔄 دعم"
                    new_task   = st.selectbox("المهمة", TASKS_SUPPORT if is_support else TASKS_MAIN, key="new_task")
                    new_job    = st.selectbox("المسمى الوظيفي", JOB_TITLES, key="new_job")
                    if new_job == "أخرى":
                        new_job = st.text_input("اكتبي المسمى الوظيفي", key="new_job_other") or "أخرى"
                    new_phone = st.text_input("رقم التواصل", placeholder="مثال: 33001122", key="new_phone")
                    new_email = st.text_input("البريد الإلكتروني الرسمي", key="new_email")

                    if is_support:
                        st.warning("🔄 دعم — سيُسجَّل حضورك لهذا اليوم فقط")
                    else:
                        st.info("💾 ستُحفظين في القائمة البيضاء عند أول تسجيل حضور")

                    if st.button("💾 حفظ البيانات والمتابعة", use_container_width=True, key="btn_confirm_data", type="primary"):
                        if not new_name.strip():
                            st.error("❌ الاسم الرباعي مطلوب")
                        else:
                            st.session_state.data_confirmed = True
                            st.session_state.emp_verified   = True
                            st.session_state.emp_data = {
                                "الرقم الشخصي":      emp_id_input,
                                "الاسم":             normalize_name(new_name.strip()),
                                "المدرسة":           new_school,
                                "المهمة":            new_task,
                                "المسمى الوظيفي":    new_job,
                                "رقم التواصل":       ar_to_en_digits(new_phone).strip(),
                                "البريد الإلكتروني": new_email.strip(),
                                "نشط": "نعم", "جديد": True, "دعم": is_support,
                            }
                            st.rerun()
            else:
                st.session_state.emp_verified = False
                st.session_state.emp_data     = None

    # ── كارد العمليات ────────────────────────────────────────────
    st.markdown('<div id="ops-anchor"></div>', unsafe_allow_html=True)
    if st.session_state.emp_verified and st.session_state.emp_data:
        emp    = st.session_state.emp_data
        emp_id = str(emp.get("الرقم الشخصي","")).strip()

        data = get_sheet_data()
        _, today_row = find_today_row(data, today_str, emp_id)

        att_time = today_row.get("وقت الحضور","—")  if today_row else "—"
        dep_time = today_row.get("وقت الانصراف","—") if today_row else "—"
        status   = "حاضر ✓" if today_row and today_row.get("وقت الحضور") else "لم يُسجَّل"
        stat_col = "#3B6D11" if today_row and today_row.get("وقت الحضور") else "#A32D2D"

        # ══ تحذير إذا محاولة توثيقها ══
        if today_row and today_row.get("محاولة تسجيل باسم آخر"):
            st.markdown('<div class="attempt-warn">⚠️ تم رصد محاولة تسجيل باسم آخر من جهازك — تم توثيقها في النظام</div>', unsafe_allow_html=True)

        with st.container(border=False):
            st.markdown(f"""
<div class="pro-card">
<div class="card-head"><div class="card-ico" style="background:#eaf3de;">⚡</div>
<b style="color:#0c3460;font-size:15px;">العمليات</b></div>
<div class="today-strip">
    <div class="stat-cell"><span class="stat-val">{att_time}</span><span class="stat-lbl">وقت الحضور</span></div>
    <div style="width:1px;background:#d3d1c7;margin:4px 0;"></div>
    <div class="stat-cell"><span class="stat-val">{dep_time}</span><span class="stat-lbl">وقت الانصراف</span></div>
    <div style="width:1px;background:#d3d1c7;margin:4px 0;"></div>
    <div class="stat-cell"><span class="stat-val" style="color:{stat_col};">{status}</span><span class="stat-lbl">الحالة</span></div>
</div>
""", unsafe_allow_html=True)

            col1, col2 = st.columns(2)
            with col1:
                if st.button("✅ تسجيل حضور", use_container_width=True, key="btn_att"):
                    st.session_state.pending_operation = None
                    if not st.session_state.location_allowed:
                        st.error("❌ يجب تحديد الموقع أولاً")
                    elif datetime.now().time() > time(7, 30):
                        st.session_state.pending_operation = "تسجيل حضور"
                    else:
                        register_operation("تسجيل حضور", emp_id)
                        st.rerun()
            with col2:
                if st.button("🔵 تسجيل انصراف", use_container_width=True, key="btn_dep"):
                    st.session_state.pending_operation = None
                    if not st.session_state.location_allowed:
                        st.error("❌ يجب تحديد الموقع أولاً")
                    elif datetime.now().time() < time(14, 0):
                        st.session_state.pending_operation = "تسجيل انصراف"
                    else:
                        register_operation("تسجيل انصراف", emp_id)
                        st.rerun()

            col3, col4 = st.columns(2)
            with col3:
                if st.button("📤 خروج استئذان", use_container_width=True, key="btn_exit"):
                    if not st.session_state.location_allowed:
                        st.error("❌ يجب تحديد الموقع أولاً")
                    else:
                        st.session_state.pending_operation = "خروج استئذان"
            with col4:
                if st.button("🔁 عودة من استئذان", use_container_width=True, key="btn_ret"):
                    st.session_state.pending_operation = None
                    register_operation("عودة من استئذان", emp_id)
                    st.rerun()

            st.markdown('</div>', unsafe_allow_html=True)

        # نوافذ السبب
        if st.session_state.pending_operation == "تسجيل حضور":
            with st.container(border=True):
                st.markdown("**سبب التأخير بعد الساعة 7:30 — اختياري**")
                late_reason = st.selectbox("السبب", ["اختاري السبب (اختياري)"] + reasons, key="late_reason")
                late_other  = ""
                if late_reason == "أخرى":
                    late_other = st.text_input("اكتبي السبب", key="late_other")
                final = "" if late_reason == "اختاري السبب (اختياري)" else (late_other.strip() if late_reason == "أخرى" else late_reason)
                if st.button("تأكيد تسجيل الحضور", use_container_width=True):
                    register_operation("تسجيل حضور", emp_id, final)
                    st.rerun()

        if st.session_state.pending_operation == "تسجيل انصراف":
            with st.container(border=True):
                st.markdown("**سبب الانصراف قبل الساعة 2:00**")
                reason = st.selectbox("السبب", reasons, key="early_leave_reason")
                other  = ""
                if reason == "أخرى":
                    other = st.text_input("اكتبي السبب", key="early_leave_other")
                final = other.strip() if reason == "أخرى" else reason
                if st.button("تأكيد تسجيل الانصراف", use_container_width=True):
                    if not final:
                        st.error("السبب مطلوب")
                    else:
                        register_operation("تسجيل انصراف", emp_id, final)
                        st.rerun()

        if st.session_state.pending_operation == "خروج استئذان":
            with st.container(border=True):
                st.markdown("**سبب خروج الاستئذان**")
                exit_reason = st.selectbox("السبب", reasons, key="exit_reason")
                exit_other  = ""
                if exit_reason == "أخرى":
                    exit_other = st.text_input("اكتبي السبب", key="exit_other")
                final = exit_other.strip() if exit_reason == "أخرى" else exit_reason
                if st.button("تأكيد خروج الاستئذان", use_container_width=True):
                    if not final:
                        st.error("السبب مطلوب")
                    else:
                        register_operation("خروج استئذان", emp_id, final)
                        st.rerun()

# ══════════════════════════════════════════════════════════════════
# واجهة الأدمن
# ══════════════════════════════════════════════════════════════════
else:
    if not st.session_state.admin_logged_in:
        with st.container(border=True):
            st.markdown('<div class="card-head"><div class="card-ico" style="background:#EEEDFE;">🛡️</div><b style="color:#26215C;font-size:15px;">دخول الأدمن</b></div>', unsafe_allow_html=True)
            pw = st.text_input("كلمة المرور", type="password", key="admin_pw")
            if st.button("دخول", use_container_width=True):
                ADMIN_PASSWORD = st.secrets.get("admin_password", "Afaf1234")
                if pw.strip() == ADMIN_PASSWORD:
                    st.session_state.admin_logged_in   = True
                    st.session_state.admin_last_active = datetime.now()
                    st.rerun()
                else:
                    st.error("❌ كلمة المرور غير صحيحة")
    else:
        st.session_state.admin_last_active = datetime.now()
        st.markdown("""
<div class="admin-header">
    <div class="t">🛡️ لوحة الأدمن</div>
    <div class="s">صلاحيات كاملة — جلسة تنتهي بعد 30 دقيقة خمول</div>
</div>""", unsafe_allow_html=True)

        admin_tab = st.selectbox("القسم", [
            "📊 إحصائيات اليوم",
            "🔴 تسجيل الغياب",
            "✏️ تعديل سجل",
            "➕ تسجيل يدوي",
            "📋 القائمة البيضاء",
            "🔄 إعادة تسجيل موظفة",
            "📡 تجاوز الموقع",
            "🚫 محاولات تسجيل باسم آخر",   # ══ جديد ══
            "🔓 فتح قفل جهاز",              # ══ جديد ══
            "🔍 سجل التدقيق",
            "⚠️ تقرير الأجهزة",
        ])

        # ── إحصائيات اليوم ──────────────────────────────────────
        if admin_tab == "📊 إحصائيات اليوم":
            data       = sheet.get_all_records()
            today_rows = [r for r in data if r.get("التاريخ") == today_str]

            try:
                abs_sheet_stats = get_or_create_sheet("سجل_الغياب", [
                    "التاريخ","اليوم","الرقم الشخصي","الاسم",
                    "المدرسة","المهمة","سبب الغياب","ملاحظات","سجّله"
                ])
                abs_today = [r for r in abs_sheet_stats.get_all_records() if r.get("التاريخ") == today_str]
            except Exception:
                abs_today = []

            total     = len(today_rows)
            attended  = sum(1 for r in today_rows if r.get("وقت الحضور"))
            departed  = sum(1 for r in today_rows if r.get("وقت الانصراف"))
            late_list = [r for r in today_rows if r.get("وقت الحضور","") > "07:30:00"]
            early_dep = [r for r in today_rows if r.get("وقت الانصراف","") and r.get("وقت الانصراف","") < "14:00:00"]
            on_leave  = [r for r in today_rows if r.get("خروج استئذان") and not r.get("عودة")]
            # ══ جديد: عدّ الدعم ══
            support_count = sum(1 for r in today_rows if str(r.get("دعم","")).strip() == "نعم")
            # ══ جديد: محاولات مشبوهة ══
            attempt_count = sum(1 for r in today_rows if r.get("محاولة تسجيل باسم آخر"))

            c1,c2,c3 = st.columns(3)
            c1.metric("إجمالي المسجّلين", total)
            c2.metric("حاضرون الآن", attended)
            c3.metric("منصرفون", departed)

            c4,c5,c6 = st.columns(3)
            c4.metric("متأخرون", len(late_list))
            c5.metric("دعم اليوم", support_count)      # ══ جديد ══
            c6.metric("محاولات مشبوهة", attempt_count) # ══ جديد ══

            if late_list:
                st.markdown('<div class="admin-section">المتأخرون اليوم</div>', unsafe_allow_html=True)
                for r in late_list:
                    st.markdown(f'<div class="warn-row">⏰ {r.get("الاسم الثلاثي","")} — وصل {r.get("وقت الحضور","")}</div>', unsafe_allow_html=True)

        # ── تسجيل الغياب ────────────────────────────────────────
        elif admin_tab == "🔴 تسجيل الغياب":
            absence_reasons = ["مرض","إجازة اعتيادية","إجازة طارئة","بدون عذر","مهمة رسمية","أخرى"]
            abs_date     = st.date_input("تاريخ الغياب", value=datetime.now().date(), key="abs_date")
            abs_date_str = str(abs_date)
            wl_all       = get_whitelist()

            if not wl_all:
                st.warning("⚠️ القائمة البيضاء فارغة")
            else:
                data         = sheet.get_all_records()
                attended_ids = set(str(r.get("الرقم الشخصي","")).strip() for r in data if r.get("التاريخ") == abs_date_str and r.get("وقت الحضور"))
                try:
                    abs_sheet    = get_or_create_sheet("سجل_الغياب", ["التاريخ","اليوم","الرقم الشخصي","الاسم","المدرسة","المهمة","سبب الغياب","ملاحظات","سجّله"])
                    abs_records  = abs_sheet.get_all_records()
                    absent_ids   = set(str(r.get("الرقم الشخصي","")).strip() for r in abs_records if r.get("التاريخ") == abs_date_str)
                except Exception:
                    abs_sheet = None; absent_ids = set()

                not_registered = {eid: emp for eid, emp in wl_all.items() if eid not in attended_ids and eid not in absent_ids}
                c1,c2,c3 = st.columns(3)
                c1.metric("إجمالي الموظفات", len(wl_all))
                c2.metric("حاضرات", len(attended_ids))
                c3.metric("لم يسجّلن بعد", len(not_registered))

                for eid, emp in not_registered.items():
                    with st.expander(f"🔴 {emp.get('الاسم','')} — {emp.get('المدرسة','')}"):
                        sel_reason = st.selectbox("سبب الغياب", absence_reasons, key=f"abs_{eid}")
                        other_txt  = st.text_input("اكتبي السبب", key=f"abs_o_{eid}") if sel_reason == "أخرى" else ""
                        note_txt   = st.text_input("ملاحظات", key=f"abs_n_{eid}")
                        final_r    = other_txt.strip() if sel_reason == "أخرى" else sel_reason
                        if st.button("تسجيل غياب", key=f"abs_b_{eid}", use_container_width=True):
                            if not final_r:
                                st.error("السبب مطلوب")
                            elif abs_sheet:
                                day_ar = {"Saturday":"السبت","Sunday":"الأحد","Monday":"الاثنين","Tuesday":"الثلاثاء","Wednesday":"الأربعاء","Thursday":"الخميس","Friday":"الجمعة"}.get(abs_date.strftime("%A"), "")
                                abs_sheet.append_row([abs_date_str, day_ar, eid, emp.get("الاسم",""), emp.get("المدرسة",""), emp.get("المهمة",""), final_r, note_txt, "أدمن"])
                                log_audit(eid, emp.get("الاسم",""), "تسجيل غياب", f"التاريخ: {abs_date_str} | السبب: {final_r}")
                                st.success(f"✅ تم تسجيل غياب {emp.get('الاسم','')}")
                                st.rerun()

        # ── تعديل سجل ────────────────────────────────────────────
        elif admin_tab == "✏️ تعديل سجل":
            search_id   = st.text_input("الرقم الشخصي", key="edit_id")
            search_date = st.date_input("التاريخ", value=datetime.now().date(), key="edit_date")
            if st.button("بحث", key="btn_search"):
                data = sheet.get_all_records()
                idx, row = find_today_row(data, str(search_date), search_id)
                if row:
                    st.session_state.edit_row_idx = idx
                    st.session_state.edit_row     = row
                else:
                    st.error("لا يوجد سجل بهذه البيانات")
                    st.session_state.edit_row_idx = None
                    st.session_state.edit_row     = None
            if st.session_state.get("edit_row"):
                row = st.session_state.edit_row
                idx = st.session_state.edit_row_idx
                st.info(f"السجل: {row.get('الاسم الثلاثي','')} — {row.get('التاريخ','')}")
                new_att     = st.text_input("وقت الحضور",   value=row.get("وقت الحضور",""),   key="new_att")
                new_dep     = st.text_input("وقت الانصراف", value=row.get("وقت الانصراف",""), key="new_dep")
                edit_reason = st.text_input("سبب التعديل (مطلوب)", key="edit_reason")
                if st.button("حفظ التعديل", use_container_width=True):
                    if not edit_reason.strip():
                        st.error("سبب التعديل مطلوب")
                    else:
                        safe_update_cell(sheet, idx, COL_ATTEND, new_att)
                        safe_update_cell(sheet, idx, COL_DEPART, new_dep)
                        log_audit(search_id, row.get("الاسم الثلاثي",""), "تعديل أدمن",
                                  f"حضور: {row.get('وقت الحضور','')} → {new_att} | انصراف: {row.get('وقت الانصراف','')} → {new_dep} | السبب: {edit_reason}")
                        st.success("✅ تم حفظ التعديل")
                        st.session_state.edit_row = None

        # ── تسجيل يدوي ──────────────────────────────────────────
        elif admin_tab == "➕ تسجيل يدوي":
            m_id   = st.text_input("الرقم الشخصي", key="manual_id")
            m_date = st.date_input("التاريخ", value=datetime.now().date(), key="manual_date")
            m_att  = st.text_input("وقت الحضور", value="07:00:00", key="manual_att")
            m_dep  = st.text_input("وقت الانصراف (اختياري)", key="manual_dep")
            m_note = st.text_input("سبب الإضافة اليدوية (مطلوب)", key="manual_note")
            if st.button("تسجيل يدوي", use_container_width=True):
                if not m_note.strip() or not m_id.strip():
                    st.error("الرقم الشخصي والسبب مطلوبان")
                else:
                    emp = validate_employee(m_id)
                    if not emp:
                        st.error("الرقم الشخصي غير موجود في القائمة البيضاء")
                    else:
                        date_str    = str(m_date)
                        day_name    = m_date.strftime("%A")
                        support_val = "نعم" if "دعم" in str(emp.get("المهمة","")) else "لا"
                        safe_append(sheet, [
                            date_str, day_name, emp.get("المدرسة",""), emp.get("المهمة",""),
                            support_val,
                            normalize_name(emp.get("الاسم","")), m_id,
                            m_att, f"[يدوي] {m_note}",
                            m_dep, "", "", "", ""
                        ])
                        log_audit(m_id, emp.get("الاسم",""), "تسجيل يدوي أدمن",
                                  f"التاريخ: {date_str} | حضور: {m_att} | انصراف: {m_dep} | السبب: {m_note}")
                        st.success("✅ تم التسجيل اليدوي بنجاح")

        # ── القائمة البيضاء ──────────────────────────────────────
        elif admin_tab == "📋 القائمة البيضاء":
            st.markdown('<div class="admin-section">إضافة موظفة جديدة</div>', unsafe_allow_html=True)
            wl_id      = st.text_input("الرقم الشخصي", key="wl_id")
            wl_name    = st.text_input("الاسم الثلاثي", key="wl_name")
            wl_school  = st.selectbox("المدرسة", schools, key="wl_school")
            wl_section = st.selectbox("المهمة", sections, key="wl_section")
            if st.button("إضافة للقائمة", use_container_width=True):
                if not wl_id.strip() or not wl_name.strip():
                    st.error("الرقم والاسم مطلوبان")
                else:
                    wl = get_whitelist()
                    if wl_id.strip() in wl:
                        st.error("الرقم الشخصي موجود مسبقاً")
                    else:
                        whitelist_sheet.append_row([wl_id.strip(), wl_name.strip(), wl_school, wl_section, "","","", "نعم"])
                        log_audit(wl_id, wl_name, "إضافة للقائمة البيضاء", f"مدرسة: {wl_school}")
                        invalidate_whitelist()
                        st.success(f"✅ تمت إضافة {wl_name}")
            st.markdown('<div class="admin-section">الموظفات المسجّلات</div>', unsafe_allow_html=True)
            for eid, emp in get_whitelist().items():
                st.markdown(f'<div class="audit-row"><span class="ar-op">{emp.get("الاسم","")}</span><div class="ar-det">#{eid} — {emp.get("المدرسة","")}</div></div>', unsafe_allow_html=True)

        # ── إعادة تسجيل موظفة ────────────────────────────────────
        elif admin_tab == "🔄 إعادة تسجيل موظفة":
            re_id = st.text_input("الرقم الشخصي", key="re_emp_id")
            if re_id.strip():
                re_id_clean = ar_to_en_digits(re_id).strip()
                emp_rec     = get_whitelist().get(re_id_clean)
                if emp_rec:
                    task_r  = emp_rec.get("المهمة","")
                    task_a  = task_r.split("/")[0].strip() if "/" in task_r else task_r
                    st.markdown(f'<div class="audit-row"><span class="ar-op">{emp_rec.get("الاسم","")}</span><div class="ar-det">#{re_id_clean} — {emp_rec.get("المدرسة","")} — {task_a}</div></div>', unsafe_allow_html=True)
                    re_action = st.radio("اختاري العملية", [
                        "✏️ تعديل جزئي","🔄 إعادة تسجيل كاملة",
                        "⛔ تعطيل الموظفة","🗑️ حذف نهائي"
                    ], key="re_action")
                    if re_action == "✏️ تعديل جزئي":
                        new_n  = st.text_input("الاسم الجديد", value=emp_rec.get("الاسم",""), key="re_new_name")
                        new_s  = st.selectbox("المدرسة", schools, index=schools.index(emp_rec.get("المدرسة",schools[0])) if emp_rec.get("المدرسة") in schools else 0, key="re_new_school")
                        task_options = TASKS_MAIN + TASKS_SUPPORT
                        cur_idx = task_options.index(task_r) if task_r in task_options else 0
                        new_t   = st.selectbox("المهمة", task_options, index=cur_idx, key="re_new_task")
                        re_rsn  = st.text_input("سبب التعديل (مطلوب)", key="re_reason")
                        if st.button("💾 حفظ التعديل", use_container_width=True, type="primary"):
                            if not re_rsn.strip():
                                st.error("❌ السبب مطلوب")
                            else:
                                wl_recs = whitelist_sheet.get_all_records()
                                for i, r in enumerate(wl_recs):
                                    if str(r.get("الرقم الشخصي","")).strip() == re_id_clean:
                                        whitelist_sheet.update_cell(i+2, 2, normalize_name(new_n))
                                        whitelist_sheet.update_cell(i+2, 3, new_s)
                                        whitelist_sheet.update_cell(i+2, 4, new_t)
                                        break
                                log_audit(re_id_clean, emp_rec.get("الاسم",""), "تعديل جزئي أدمن", f"السبب: {re_rsn}")
                                invalidate_whitelist()
                                st.success("✅ تم التعديل")
                                st.rerun()
                else:
                    st.warning(f"⚠️ الرقم {re_id_clean} غير موجود في القائمة البيضاء")

        # ── تجاوز الموقع ─────────────────────────────────────────
        elif admin_tab == "📡 تجاوز الموقع":
            ov_active, ov_end = get_location_override()
            if ov_active and ov_end:
                remaining_min = int((ov_end - datetime.now()).seconds / 60)
                st.warning(f"⚠️ التجاوز مفعّل — ينتهي الساعة {ov_end.strftime('%H:%M')} (بعد {remaining_min} دقيقة)")
                if st.button("🔴 إيقاف التجاوز الآن", use_container_width=True):
                    disable_location_override()
                    st.success("✅ تم إيقاف تجاوز الموقع")
                    st.rerun()
            else:
                st.success("✅ الفحص الطبيعي مفعّل")
                ov_duration = st.selectbox("مدة التجاوز", [30,60,90,120,180], format_func=lambda x: f"{x} دقيقة", key="ov_duration")
                ov_reason   = st.text_input("سبب التجاوز (مطلوب)", key="ov_reason")
                if st.button("✅ تفعيل تجاوز الموقع", use_container_width=True):
                    if not ov_reason.strip():
                        st.error("❌ السبب مطلوب")
                    else:
                        ok, end_dt = set_location_override(ov_duration, ov_reason.strip())
                        if ok:
                            st.success(f"✅ تم التفعيل حتى {end_dt.strftime('%H:%M')}")
                            st.rerun()

        # ══ جديد: محاولات تسجيل باسم آخر ══════════════════════════
        elif admin_tab == "🚫 محاولات تسجيل باسم آخر":
            st.markdown('<div class="admin-section">محاولات اليوم</div>', unsafe_allow_html=True)
            try:
                records      = attempts_sheet.get_all_records()
                today_attempts = [r for r in records if r.get("التاريخ") == today_str]
                st.metric("محاولات اليوم", len(today_attempts))
                if today_attempts:
                    for r in reversed(today_attempts[-50:]):
                        st.markdown(f"""
<div class="audit-row" style="border-right-color:#E24B4A;">
<span class="ar-op">🚫 {r.get("اسم_المحاول","")} ({r.get("الرقم_المحاول","")})</span>
<div class="ar-det">حاول من جهاز مقفول على: <b>{r.get("اسم_المقفول_عليه","")} ({r.get("الرقم_المقفول_عليه","")})</b></div>
<div class="ar-det">الوقت: {r.get("وقت_المحاولة","")}</div>
</div>""", unsafe_allow_html=True)
                else:
                    st.success("✅ لا يوجد محاولات مشبوهة اليوم")
            except Exception as e:
                st.error(f"خطأ: {e}")

        # ══ جديد: فتح قفل جهاز ══════════════════════════════════════
        elif admin_tab == "🔓 فتح قفل جهاز":
            st.info("استخدمي هذه الخاصية عند وجود سبب رسمي لاستخدام نفس الجهاز لموظفة أخرى.")
            unlock_id = st.text_input("الرقم الشخصي المقفول عليه", key="unlock_id")
            if st.button("حذف قفل اليوم لهذا الرقم", use_container_width=True):
                try:
                    records = device_lock_sheet.get_all_records()
                    deleted = False
                    for i, r in enumerate(records):
                        if str(r.get("التاريخ","")).strip() == today_str and \
                           str(r.get("الرقم الشخصي","")).strip() == unlock_id.strip():
                            device_lock_sheet.delete_rows(i + 2)
                            deleted = True
                            break
                    get_device_locks.clear()
                    if deleted:
                        log_audit(unlock_id, "—", "فتح قفل جهاز أدمن",
                                  f"الأدمن فتح قفل الجهاز للرقم {unlock_id} ليوم {today_str}")
                        st.success("✅ تم حذف القفل — يمكن الآن التسجيل برقم آخر من نفس الجهاز")
                    else:
                        st.warning("لم يتم العثور على قفل لهذا الرقم اليوم")
                except Exception as e:
                    st.error(f"تعذر حذف القفل: {e}")

        # ── سجل التدقيق ─────────────────────────────────────────
        elif admin_tab == "🔍 سجل التدقيق":
            st.markdown('<div class="admin-section">آخر 30 عملية</div>', unsafe_allow_html=True)
            try:
                audit_data = audit_sheet.get_all_records()
                for r in reversed(audit_data[-30:]):
                    st.markdown(f"""
<div class="audit-row">
<span class="ar-op">{r.get('نوع العملية','')}</span>
<span class="ar-time">{r.get('الوقت','')}</span>
<div class="ar-det">{r.get('المستخدم','')} (#{r.get('الرقم الشخصي','')}) — {r.get('التفاصيل','')}</div>
</div>""", unsafe_allow_html=True)
            except Exception as e:
                st.error(f"خطأ: {e}")

        # ── تقرير الأجهزة ────────────────────────────────────────
        elif admin_tab == "⚠️ تقرير الأجهزة":
            st.markdown('<div class="admin-section">أجهزة سجّلت أكثر من موظفة اليوم</div>', unsafe_allow_html=True)
            try:
                audit_data  = audit_sheet.get_all_records()
                device_map  = {}
                for r in audit_data:
                    if r.get("التاريخ") == today_str and r.get("نوع العملية") == "تسجيل حضور":
                        fp_key = str(r.get("بصمة الجهاز",""))
                        if fp_key not in device_map:
                            device_map[fp_key] = []
                        name = f"{r.get('المستخدم','')} (#{r.get('الرقم الشخصي','')})"
                        if name not in device_map[fp_key]:
                            device_map[fp_key].append(name)
                found = False
                for fp_key, names in device_map.items():
                    if len(names) > 1:
                        found = True
                        st.markdown(f'<div class="warn-row">⚠️ جهاز واحد سجّل لـ {len(names)} موظفات:<br>{"، ".join(names)}</div>', unsafe_allow_html=True)
                if not found:
                    st.success("✅ لا يوجد تسجيل مشبوه اليوم")
            except Exception as e:
                st.error(f"خطأ: {e}")

        st.markdown("---")
        if st.button("🚪 تسجيل خروج الأدمن", use_container_width=True):
            st.session_state.admin_logged_in   = False
            st.session_state.admin_last_active = None
            st.rerun()

# ── فوتر ─────────────────────────────────────────────────────────
st.markdown("""
<div class="footer-bar">
    <span>تصميم: <span class="hl">أ. عفاف حسين</span></span>
    <span>رئيسة المركز: <span class="hl">أ. خلود يعقوب بدو</span></span>
</div>
""", unsafe_allow_html=True)
