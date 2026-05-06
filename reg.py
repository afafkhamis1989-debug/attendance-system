import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

BAHRAIN_TZ = ZoneInfo('Asia/Bahrain')
def now_bh(): return datetime.now(BAHRAIN_TZ)
from streamlit_geolocation import streamlit_geolocation
import math
import random
import string
import time as time_module
import urllib.parse

try:
    from streamlit_local_storage import LocalStorage
    localS = LocalStorage()
    LOCAL_STORAGE_OK = True
except Exception:
    localS = None
    LOCAL_STORAGE_OK = False

st.set_page_config(page_title="نظام الحضور والانصراف", page_icon="🕘", layout="centered")
st.markdown("""
<style>
.block-container {
    padding-top: 0.9rem !important;
}

section.main > div {
    padding-top: 0.6rem !important;
}

html, body {
    margin: 0 !important;
    padding: 0 !important;
}

[data-testid="stImage"] {
    margin-top: 12px !important;
}
</style>
""", unsafe_allow_html=True)
# ─── إعدادات ───────────────────────────────────────────────────
SHEET_ID       = "1svkfgRq4-osKr86_2WJQFZShuoy8Ek5DOiUaaHKL-6Y"
SCHOOL_LAT     = 26.216371784473964
SCHOOL_LON     = 50.54035843289093
ALLOWED_RADIUS = 1000
ADMIN_PASSWORD = "Afaf1234"
DEVICE_COOLDOWN_MINUTES = 10

# أعمدة sheet1
COL_DATE=1; COL_DAY=2; COL_SCHOOL=3; COL_TASK=4; COL_SUPPORT=5
COL_NAME=6; COL_ID=7; COL_ATTEND=8; COL_LATE_REASON=9
COL_DEPART=10; COL_DEPART_REASON=11; COL_EXIT=12; COL_RETURN=13; COL_ATTEMPT=14
COL_WORK_START=15; COL_EXPECTED_END=16; COL_WORK_HOURS=17; COL_EXTRA_HOURS=18
COL_WORK_STATUS=19; COL_DAILY_TYPE=20; COL_AUTO_CLOSE=21; COL_CARE_CONF=22

schools = [
    "مدرسة المنامة الثانوية للبنات",
    "مدرسة النور الثانوية للبنات",
    "مدرسة المعرفة الثانوية للبنات",
    "مدرسة الرفاع الغربي الثانوية للبنات",
    "مدرسة جدحفص الثانوية للبنات"
]

TASKS_MAIN = [
    "مصححة — اللغة العربية","مصححة — اللغة الإنجليزية","مصححة — الرياضيات",
    "مصححة — الفيزياء","مصححة — الكيمياء","مصححة — الأحياء",
    "مصححة — العلوم التجارية","مصححة — المواد الاجتماعية","مصححة — التربية الإسلامية",
    "مصححة — التربية الأسرية","مصححة — التربية الفنية","مصححة — الحاسب الآلي",
    "مصححة — التربية البدنية","كنترول خارجي — دعم فني",
    "كنترول خارجي — رصد الدرجات","كنترول خارجي — ضبط مركزي",
]
TASKS_SUPPORT = [
    "دعم — اللغة العربية","دعم — اللغة الإنجليزية","دعم — الرياضيات",
    "دعم — الفيزياء","دعم — الكيمياء","دعم — الأحياء",
    "دعم — العلوم التجارية","دعم — المواد الاجتماعية","دعم — التربية الإسلامية",
    "دعم — التربية الأسرية","دعم — التربية الفنية","دعم — الحاسب الآلي",
    "دعم — التربية البدنية","دعم — كنترول فني","دعم — رصد الدرجات","دعم — ضبط مركزي",
]
TASKS_ALL = TASKS_MAIN + TASKS_SUPPORT
JOB_TITLES    = ["منسقة","معلمة أولى","معلمة","الهيئة الإدارية","مشرف تربوي","مديرة مدرسة","المديرة المساعدة","أخرى"]
reasons       = ["دوام مرن","موعد","مهمة رسمية","رعاية","الانتهاء من التصحيح","أخرى"]
abs_reasons   = ["مرض","إجازة اعتيادية","إجازة طارئة","بدون عذر","مهمة رسمية","أخرى"]

# ─── CSS ───────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;900&display=swap');
html,body,[class*="css"]{direction:rtl!important;text-align:right!important;font-family:'Cairo',Tahoma,sans-serif!important;}
.stApp{direction:rtl!important;}
.block-container{max-width:680px;padding-top:0px;padding-bottom:40px;}
[data-testid="stVerticalBlock"],[data-testid="stHorizontalBlock"],.element-container,.stMarkdown,.stTextInput,.stSelectbox,.stRadio,.stButton,.stAlert{direction:rtl!important;text-align:right!important;}
.stTextInput input,.stSelectbox div{direction:rtl!important;text-align:right!important;}
label{direction:rtl!important;text-align:right!important;display:block!important;font-size:15px!important;font-weight:700!important;color:#0c3460!important;}
.app-header{background:linear-gradient(135deg,#0c3460 0%,#1a5276 60%,#1f6fa3 100%);border-radius:0 0 28px 28px;padding:28px 24px 32px;text-align:center!important;margin:-1rem -1rem 20px -1rem;}
.app-header .sub{color:rgba(255,255,255,0.78);font-size:12px;font-weight:600;margin-bottom:6px;}
.app-header .title{color:#fff;font-size:22px;font-weight:900;}
.app-header .date-pill{display:inline-block;background:rgba(255,255,255,0.15);border:1px solid rgba(255,255,255,0.2);border-radius:20px;padding:3px 14px;color:rgba(255,255,255,0.9);font-size:12px;font-weight:600;margin-top:10px;}
.card-title{color:#0c3460;font-size:19px;font-weight:900;margin-bottom:14px;}
.field-lbl{font-size:12px;font-weight:700;color:#888780;margin-bottom:4px;}
.field-val{background:#eaf3de;border:1px solid #c0dd97;border-radius:14px;padding:12px 14px;font-size:15px;font-weight:800;color:#27500A;margin-bottom:12px;}
.field-val.blue{background:#e6f1fb;border-color:#185FA5;color:#185FA5;}
.pro-card{background:#fff;border-radius:22px;padding:18px 20px;box-shadow:0 2px 14px rgba(12,52,96,0.07);margin-bottom:14px;}
.today-strip{display:flex;justify-content:space-around;background:#f0f4f8;border-radius:14px;padding:12px 8px;margin-bottom:14px;}
.stat-cell{text-align:center!important;}
.stat-val{font-size:17px;font-weight:900;color:#0c3460;display:block;text-align:center!important;}
.stat-lbl{font-size:10px;font-weight:600;color:#888780;text-align:center!important;}
.footer-bar{background:#0c3460;border-radius:14px;padding:12px 18px;display:flex;justify-content:space-between;align-items:center;margin-top:12px;}
.footer-bar span{font-size:11px;font-weight:600;color:rgba(255,255,255,.7);}
.footer-bar .hl{color:#fff;}
.stButton button{border-radius:14px!important;font-size:15px!important;font-weight:800!important;font-family:'Cairo',sans-serif!important;}
.audit-row{background:#f8fafc;border-radius:10px;padding:10px 14px;border-right:3px solid #378ADD;margin-bottom:6px;font-size:12px;color:#0c3460;}
.warn-row{background:#faeeda;border-radius:10px;padding:10px 14px;border-right:3px solid #BA7517;margin-bottom:6px;font-size:12px;color:#633806;font-weight:700;}
.absent-row{background:#fcebeb;border-radius:10px;padding:10px 14px;border-right:3px solid #E24B4A;margin-bottom:6px;font-size:12px;color:#791F1F;font-weight:700;}
</style>
""", unsafe_allow_html=True)

# ─── Google Sheets ──────────────────────────────────────────────
scope = ["https://spreadsheets.google.com/feeds","https://www.googleapis.com/auth/drive"]

@st.cache_resource(show_spinner=False)
def get_all_sheets():
    creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
    client = gspread.authorize(creds)
    ss = client.open_by_key(SHEET_ID)

    def _get_or_create(name, headers):
        try:
            return ss.worksheet(name)
        except gspread.WorksheetNotFound:
            ws = ss.add_worksheet(title=name, rows=1000, cols=max(len(headers),10))
            ws.append_row(headers)
            return ws

    return {
        "spreadsheet": ss,
        "sheet":       ss.worksheet("sheet1"),
        "whitelist":   _get_or_create("القائمة_البيضاء",         ["الرقم الشخصي","الاسم","المدرسة","المهمة","دعم","رقم التواصل","البريد الإلكتروني","المسمى الوظيفي","نشط"]),
        "schedule":    _get_or_create("جدول_دوام_الأقسام",       ["المهمة","السبت","الأحد","الاثنين","الثلاثاء","الأربعاء","الخميس","الجمعة","نشط"]),
        "daily_schedule": _get_or_create("دوام_الأقسام_اليومي", ["التاريخ","المهمة","نشط","ملاحظات"]),
        "device":      _get_or_create("device_lock",              ["التاريخ","بصمة الجهاز","الرقم الشخصي","الاسم","وقت_القفل"]),
        "attempts":    _get_or_create("محاولات_تسجيل_باسم_آخر",  ["التاريخ","بصمة الجهاز","الرقم_المقفول_عليه","اسم_المقفول_عليه","الرقم_المحاول","اسم_المحاول","وقت_المحاولة","ملاحظات"]),
        "settings":    _get_or_create("إعدادات_النظام",           ["المفتاح","القيمة","تاريخ_الانتهاء","ملاحظات"]),
        "audit":       _get_or_create("سجل_التدقيق",              ["التاريخ","الوقت","المستخدم","الرقم الشخصي","نوع العملية","التفاصيل","بصمة الجهاز"]),
        "absence":     _get_or_create("سجل_الغياب",               ["التاريخ","اليوم","الرقم الشخصي","الاسم","المدرسة","المهمة","سبب الغياب","ملاحظات","سجّله"]),
    }

_sheets         = get_all_sheets()
spreadsheet     = _sheets["spreadsheet"]
sheet           = _sheets["sheet"]
whitelist_sheet = _sheets["whitelist"]
device_sheet    = _sheets["device"]
attempts_sheet  = _sheets["attempts"]
settings_sheet  = _sheets["settings"]
audit_sheet     = _sheets["audit"]
absence_sheet   = _sheets["absence"]
schedule_sheet  = _sheets["schedule"]
daily_schedule_sheet = _sheets["daily_schedule"]

# ─── ضمان الأعمدة الجديدة بدون الرجوع إلى Google Sheet ───────────────
def ensure_headers(ws, headers):
    try:
        current = ws.row_values(1)
        for i, h in enumerate(headers, start=1):
            if len(current) < i or not str(current[i-1]).strip():
                ws.update_cell(1, i, h)
    except Exception:
        pass

SHEET1_HEADERS = [
    "التاريخ","اليوم","اسم المدرسة","المهمة","دعم","الاسم الثلاثي","الرقم الشخصي",
    "وقت الحضور","سبب التأخير","وقت الانصراف","سبب الانصراف","خروج استئذان","عودة","محاولة",
    "وقت البداية المحسوب","وقت النهاية المتوقع","ساعات العمل","الساعات الإضافية",
    "حالة الدوام","نوع الدوام اليومي","إغلاق تلقائي","تأكيد الرعاية"
]
WHITELIST_HEADERS = [
    "الرقم الشخصي","الاسم","المدرسة","المهمة","دعم","رقم التواصل","البريد الإلكتروني",
    "المسمى الوظيفي","نشط","نوع الدوام الافتراضي","ملاحظات"
]
ensure_headers(sheet, SHEET1_HEADERS)
ensure_headers(whitelist_sheet, WHITELIST_HEADERS)

# ─── دوال مساعدة ───────────────────────────────────────────────
def ar_to_en_digits(text):
    ar="٠١٢٣٤٥٦٧٨٩"; en="0123456789"
    result=str(text).strip()
    for a,e in zip(ar,en): result=result.replace(a,e)
    return result

def normalize_name(name):
    name=str(name).strip()
    for old,new in {"أ":"ا","إ":"ا","آ":"ا","ى":"ي","ة":"ه","ؤ":"و","ئ":"ي"}.items():
        name=name.replace(old,new)
    for ch in [".",  "،",",","-","_","ـ",":",";"] : name=name.replace(ch," ")
    return " ".join(name.split())

def distance_m(lat1,lon1,lat2,lon2):
    R=6371000
    p1,p2=math.radians(lat1),math.radians(lat2)
    dp=math.radians(lat2-lat1); dl=math.radians(lon2-lon1)
    a=math.sin(dp/2)**2+math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2*R*math.atan2(math.sqrt(a),math.sqrt(1-a))

def ls_get(key):
    if LOCAL_STORAGE_OK:
        try: return localS.getItem(key)
        except: pass
    return st.session_state.get(f"ls_{key}")

def ls_set(key, value, ls_key=None):
    if LOCAL_STORAGE_OK:
        try: localS.setItem(key, value, key=ls_key or f"set_{key}"); return
        except: pass
    st.session_state[f"ls_{key}"] = value

def get_device_fingerprint():
    if LOCAL_STORAGE_OK:
        try:
            fp=localS.getItem("device_fp")
            if not fp:
                fp=''.join(random.choices(string.ascii_letters+string.digits,k=32))
                localS.setItem("device_fp",fp,key="set_device_fp")
            return fp or "unknown"
        except: pass
    if "device_fp" not in st.session_state:
        st.session_state.device_fp=''.join(random.choices(string.ascii_letters+string.digits,k=32))
    return st.session_state.device_fp

def safe_append(ws, row, retries=3):
    for _ in range(retries):
        try: ws.append_row(row,value_input_option="USER_ENTERED"); return True
        except: time_module.sleep(1.5)
    return False

def safe_update(ws, row, col, value, retries=3):
    for _ in range(retries):
        try: ws.update_cell(row,col,value); return True
        except: time_module.sleep(1.5)
    return False

@st.cache_data(ttl=120, show_spinner=False)
def get_sheet_data():
    try: return sheet.get_all_records()
    except: return []

@st.cache_data(ttl=300, show_spinner=False)
def get_whitelist():
    try:
        records=whitelist_sheet.get_all_records(); result={}
        for r in records:
            active=str(r.get("نشط","")).strip()
            if active in ["نعم","yes","Yes","TRUE","true","1"]:
                eid=str(r.get("الرقم الشخصي","")).strip()
                if eid: result[eid]=r
        return result
    except: return {}

@st.cache_data(ttl=120, show_spinner=False)
def get_device_locks():
    try: return device_sheet.get_all_records()[-200:]
    except: return []

@st.cache_data(ttl=60, show_spinner=False)
def get_settings_records():
    try: return settings_sheet.get_all_records()
    except: return []

@st.cache_data(ttl=120, show_spinner=False)
def get_schedule_records():
    try: return schedule_sheet.get_all_records()
    except: return []

@st.cache_data(ttl=60, show_spinner=False)
def get_daily_schedule_records():
    try: return daily_schedule_sheet.get_all_records()
    except: return []

def clear_caches():
    get_sheet_data.clear(); get_device_locks.clear(); get_settings_records.clear(); get_schedule_records.clear(); get_daily_schedule_records.clear()


# ─── دوال احتساب الدوام والساعات والإغلاق التلقائي ───────────────
def parse_time_value(t):
    t = str(t or "").strip()
    if not t:
        return None
    for fmt in ["%H:%M:%S", "%H:%M"]:
        try:
            return datetime.strptime(t, fmt).time()
        except Exception:
            pass
    return None

def combine_date_time(date_str, t):
    if not t:
        return None
    try:
        d = datetime.strptime(str(date_str), "%Y-%m-%d").date()
        return datetime.combine(d, t).replace(tzinfo=BAHRAIN_TZ)
    except Exception:
        return None

def fmt_time_dt(dt):
    return dt.strftime("%H:%M:%S") if dt else ""

def fmt_hours_from_seconds(seconds):
    seconds = max(0, int(seconds))
    h = seconds // 3600
    m = (seconds % 3600) // 60
    return f"{h}:{m:02d}"

def is_care_day(row):
    txt = " ".join([str(row.get("سبب التأخير", "")), str(row.get("سبب الانصراف", "")), str(row.get("تأكيد الرعاية", "")), str(row.get("نوع الدوام اليومي", ""))])
    return "رعاية" in txt

def is_flexible_day(row):
    txt = " ".join([str(row.get("سبب التأخير", "")), str(row.get("سبب الانصراف", "")), str(row.get("نوع الدوام اليومي", ""))])
    return "دوام مرن" in txt

def is_official_mission_day(row):
    txt = " ".join([str(row.get("سبب التأخير", "")), str(row.get("سبب الانصراف", "")), str(row.get("نوع الدوام اليومي", ""))])
    return "مهمة رسمية" in txt

def is_correction_done_day(row):
    """حالة الانتهاء من التصحيح: لا تُحسب كتأخير ولا كساعات إضافية، وتظهر كحالة معفاة."""
    txt = " ".join([str(row.get("سبب التأخير", "")), str(row.get("سبب الانصراف", "")), str(row.get("حالة الدوام", "")), str(row.get("نوع الدوام اليومي", ""))])
    return "الانتهاء من التصحيح" in txt

def is_implicit_leave_late(row):
    """
    إذا كان الدوام عادي والموظفة حضرت بعد السماح وكتبت سببًا مثل موعد أو سبب آخر،
    فهذا يعتبر تأخيرًا موثقًا كاستئذان ضمني من بداية الدوام،
    ووقت الحضور يعتبر عودة من الاستئذان.
    لا ينطبق على الرعاية أو الدوام المرن أو المهمة الرسمية.
    """
    att = parse_time_value(row.get("وقت الحضور", ""))
    if not att or att <= time(7, 5, 0):
        return False
    reason = str(row.get("سبب التأخير", "")).strip()
    if not reason:
        return False
    if any(x in reason for x in ["رعاية", "دوام مرن", "مهمة رسمية", "الانتهاء من التصحيح"]):
        return False
    return True

def is_late_for_statistics(row):
    """التأخير الإحصائي: يحسب للدوام العادي فقط، ويستثني الرعاية/المرن/المهمة الرسمية."""
    att = parse_time_value(row.get("وقت الحضور", ""))
    if not att or att <= time(7, 5, 0):
        return False
    if is_care_day(row) or is_flexible_day(row) or is_official_mission_day(row) or is_correction_done_day(row):
        return False
    return True

def calculate_work_values(row):
    date_str = str(row.get("التاريخ", "")).strip()
    att = parse_time_value(row.get("وقت الحضور", ""))
    dep = parse_time_value(row.get("وقت الانصراف", ""))
    if not date_str or not att:
        return None
    care = is_care_day(row)
    flexible = is_flexible_day(row)
    att_dt = combine_date_time(date_str, att)
    dep_dt = combine_date_time(date_str, dep) if dep else None
    official_start = combine_date_time(date_str, time(7, 0, 0))
    grace_end = combine_date_time(date_str, time(7, 5, 0))
    official_mission = is_official_mission_day(row)
    correction_done = is_correction_done_day(row)
    implicit_leave = is_implicit_leave_late(row)
    if correction_done:
        daily_type = "انتهاء التصحيح"
        required_hours = 0
        calc_start = official_start if att_dt <= grace_end else att_dt
    elif care:
        daily_type = "رعاية"
        required_hours = 5
        calc_start = max(att_dt, official_start)
    elif flexible:
        daily_type = "دوام مرن"
        required_hours = 7
        calc_start = att_dt
    elif official_mission:
        daily_type = "مهمة رسمية"
        required_hours = 7
        calc_start = official_start
    elif implicit_leave:
        daily_type = "استئذان تأخير"
        required_hours = 7
        calc_start = official_start
    else:
        daily_type = "دوام عادي"
        required_hours = 7
        calc_start = official_start if att_dt <= grace_end else att_dt
    expected_end = calc_start + timedelta(hours=required_hours)
    work_seconds = 0
    extra_seconds = 0
    status = "لم يكتمل"
    if dep_dt:
        if dep_dt < att_dt:
            dep_dt += timedelta(days=1)
        work_seconds = max(0, int((dep_dt - calc_start).total_seconds()))
        if correction_done:
            # الانتهاء من التصحيح حالة معفاة: نحتفظ بالوقت الفعلي للعرض فقط، ولا نحسب نقصًا أو إضافيًا.
            expected_end = dep_dt
            extra_seconds = 0
            status = "معفى - انتهاء التصحيح"
        else:
            extra_seconds = max(0, int((dep_dt - expected_end).total_seconds()))
            if work_seconds < required_hours * 3600:
                status = "ناقص"
            elif extra_seconds > 0:
                status = "رعاية + إضافي" if care else "مكتمل + إضافي"
            else:
                status = "مكتمل رعاية" if care else "مكتمل"
    return {"calc_start": fmt_time_dt(calc_start), "expected_end": fmt_time_dt(expected_end), "work_hours": fmt_hours_from_seconds(work_seconds), "extra_hours": fmt_hours_from_seconds(extra_seconds), "status": status, "daily_type": daily_type}

def update_work_calculation(row_index, row_data=None):
    try:
        if row_data is None:
            records = get_sheet_data()
            row_data = records[row_index - 2]
        vals = calculate_work_values(row_data)
        if not vals:
            return False
        sheet.update(f"O{row_index}:T{row_index}", [[vals["calc_start"], vals["expected_end"], vals["work_hours"], vals["extra_hours"], vals["status"], vals["daily_type"]]], value_input_option="USER_ENTERED")
        return True
    except Exception:
        return False

def auto_close_previous_open_records():
    try:
        today = now_bh().strftime("%Y-%m-%d")
        records = get_sheet_data()
        changed = 0
        for i, row in enumerate(records):
            row_num = i + 2
            date_str = str(row.get("التاريخ", "")).strip()
            if not date_str or date_str >= today:
                continue
            if not row.get("وقت الحضور") or row.get("وقت الانصراف"):
                continue
            if row.get("خروج استئذان") and not row.get("عودة"):
                dep_time = str(row.get("خروج استئذان", "")).strip()
                dep_reason = "إغلاق تلقائي — استئذان مفتوح احتُسب انصرافًا"
                auto_note = "نعم — استئذان مفتوح"
            else:
                vals = calculate_work_values(row)
                dep_time = vals["expected_end"] if vals else ""
                dep_reason = "إغلاق تلقائي — نسيان تسجيل الانصراف"
                auto_note = "نعم — نسيان انصراف"
            if dep_time:
                safe_update(sheet, row_num, COL_DEPART, dep_time)
                safe_update(sheet, row_num, COL_DEPART_REASON, dep_reason)
                safe_update(sheet, row_num, COL_AUTO_CLOSE, auto_note)
                new_row = dict(row)
                new_row["وقت الانصراف"] = dep_time
                new_row["سبب الانصراف"] = dep_reason
                update_work_calculation(row_num, new_row)
                changed += 1
        if changed:
            get_sheet_data.clear()
    except Exception:
        pass


def show_previous_auto_close_notice(emp_id):
    """تنبيه الموظفة في اليوم الجديد إذا تم إغلاق يوم سابق تلقائياً بسبب نسيان الانصراف أو استئذان مفتوح."""
    try:
        emp_id = str(emp_id or "").strip()
        if not emp_id:
            return

        today = now_bh().date()
        yesterday = (today - timedelta(days=1)).strftime("%Y-%m-%d")
        today_key = today.strftime("%Y-%m-%d")
        dismissed_key = f"auto_close_notice_{emp_id}_{today_key}"

        if str(ls_get(dismissed_key) or "").strip() == "done":
            return

        data = get_sheet_data()
        matches = []
        for r in data:
            if str(r.get("الرقم الشخصي", "")).strip() != emp_id:
                continue
            if str(r.get("التاريخ", "")).strip() != yesterday:
                continue
            if str(r.get("إغلاق تلقائي", "")).strip():
                matches.append(r)

        if not matches:
            return

        r = matches[-1]
        st.warning(
            "⚠️ تنبيه: تم إغلاق سجل يوم أمس تلقائيًا لأن الانصراف لم يُسجَّل قبل نهاية اليوم. "
            "يرجى التأكد من تسجيل الانصراف يوميًا قبل مغادرة المركز."
        )
        st.markdown(f"""
        <div class="warn-row">
            <b>تفاصيل الإغلاق التلقائي:</b><br>
            التاريخ: {r.get('التاريخ','')}<br>
            وقت الحضور: {r.get('وقت الحضور','—') or '—'}<br>
            وقت الانصراف المسجّل تلقائيًا: {r.get('وقت الانصراف','—') or '—'}<br>
            السبب: {r.get('سبب الانصراف','—') or '—'}<br>
            الحالة: {r.get('إغلاق تلقائي','—') or '—'}
        </div>
        """, unsafe_allow_html=True)

        if st.button("✅ تم الاطلاع على التنبيه", use_container_width=True, key=f"dismiss_auto_close_{emp_id}_{today_key}"):
            ls_set(dismissed_key, "done", f"set_{dismissed_key}")
            st.success("✅ تم إخفاء التنبيه لهذا اليوم.")
            st.rerun()
    except Exception:
        pass

def mark_care_for_today(emp_id):
    data = get_sheet_data()
    idx, row = find_today_row(data, today_str, str(emp_id).strip())
    if not idx or not row:
        st.error("❌ لا يوجد سجل لهذا اليوم.")
        return False
    if not row.get("وقت الانصراف"):
        st.error("❌ يجب تسجيل الانصراف أولاً.")
        return False
    old_reason = str(row.get("سبب الانصراف", "")).strip()
    new_reason = old_reason if "رعاية" in old_reason else (old_reason + " | رعاية" if old_reason else "رعاية")
    safe_update(sheet, idx, COL_DEPART_REASON, new_reason)
    safe_update(sheet, idx, COL_CARE_CONF, "نعم")
    row["سبب الانصراف"] = new_reason
    row["تأكيد الرعاية"] = "نعم"
    update_work_calculation(idx, row)
    log_audit(emp_id, row.get("الاسم الثلاثي", ""), "تأكيد رعاية", "تأكيد الموظفة أن دوام اليوم رعاية بعد تسجيل الانصراف")
    clear_caches()
    st.success("✅ تم اعتماد الرعاية لهذا اليوم وإعادة احتساب الساعات على أساس 5 ساعات.")
    return True

def validate_employee(emp_id):
    return get_whitelist().get(str(emp_id).strip())

def day_ar_from_date(date_obj):
    return {"Saturday":"السبت","Sunday":"الأحد","Monday":"الاثنين","Tuesday":"الثلاثاء","Wednesday":"الأربعاء","Thursday":"الخميس","Friday":"الجمعة"}.get(date_obj.strftime("%A"), date_obj.strftime("%A"))

def is_yes(value):
    return str(value).strip() in ["نعم","yes","Yes","TRUE","true","1","✅","صح"]

def normalize_task_for_schedule(task):
    task=str(task or "").strip()
    # إذا كانت المهمة دعم — نفس القسم، نطابقها على اسم الدعم أو اسم المصححة عند الحاجة
    return task

def scheduled_tasks_for_day(day_ar):
    """الجدول الأسبوعي القديم حسب اليوم."""
    records=get_schedule_records()
    tasks=[]
    for r in records:
        task=str(r.get("المهمة","")).strip()
        active_raw=str(r.get("نشط","")).strip()
        active = active_raw=="" or is_yes(active_raw)
        if task and active and is_yes(r.get(day_ar,"")):
            tasks.append(task)
    # إزالة التكرار مع الحفاظ على الترتيب
    return list(dict.fromkeys(tasks)) if tasks else None

def scheduled_tasks_for_date(date_str):
    """يرجع مهام الدوام لتاريخ محدد.
    الأولوية لجدول دوام_الأقسام_اليومي إذا وُجدت مهام نشطة لذلك التاريخ.
    إذا لا يوجد جدول يومي، يرجع للجدول الأسبوعي حسب اليوم.
    """
    date_str = str(date_str).strip()
    daily_tasks=[]
    try:
        for r in get_daily_schedule_records():
            if str(r.get("التاريخ","")).strip()==date_str:
                task=str(r.get("المهمة","")).strip()
                active_raw=str(r.get("نشط","")).strip()
                active = active_raw=="" or is_yes(active_raw)
                if task and active:
                    daily_tasks.append(task)
    except Exception:
        pass
    if daily_tasks:
        return list(dict.fromkeys(daily_tasks)), "يومي"
    try:
        d=datetime.strptime(date_str,"%Y-%m-%d").date()
        day_ar=day_ar_from_date(d)
    except Exception:
        day_ar=day_arabic
    return scheduled_tasks_for_day(day_ar), "أسبوعي"

def emp_required_on_day(emp, scheduled_tasks):
    """يتحقق هل الموظفة ضمن أقسام/مهام الدوام المختارة لهذا اليوم."""
    if scheduled_tasks is None:
        return True
    task=str(emp.get("المهمة","")).strip()
    if task in scheduled_tasks:
        return True
    # دعم — الرياضيات يعتبر ضمن الرياضيات إذا تم اختيار مصححة — الرياضيات والعكس
    task_clean=task.replace("دعم —","").replace("مصححة —","").strip()
    for t in scheduled_tasks:
        t_clean=str(t).replace("دعم —","").replace("مصححة —","").strip()
        if task_clean and task_clean==t_clean:
            return True
    return False

def find_today_row(data, today, emp_id):
    for i,row in enumerate(data):
        if str(row.get("التاريخ","")).strip()==str(today).strip() and \
           str(row.get("الرقم الشخصي","")).strip()==str(emp_id).strip():
            return i+2, row
    return None, None


def get_sheet_data_fresh():
    """قراءة مباشرة من sheet1 بدون كاش لاستخدامها في منع التكرار والتنظيف."""
    try:
        return sheet.get_all_records()
    except Exception:
        return []

def find_today_row_fresh(today, emp_id):
    data = get_sheet_data_fresh()
    return find_today_row(data, today, emp_id)

def find_duplicate_attendance_groups():
    """يرجع المجموعات المكررة حسب التاريخ + الرقم الشخصي في sheet1."""
    records = get_sheet_data_fresh()
    groups = {}
    for i, r in enumerate(records, start=2):
        date_val = str(r.get("التاريخ", "")).strip()
        emp_id_val = str(r.get("الرقم الشخصي", "")).strip()
        if not date_val or not emp_id_val:
            continue
        key = (date_val, emp_id_val)
        groups.setdefault(key, []).append((i, r))
    return {k: v for k, v in groups.items() if len(v) > 1}



def find_daily_rows_fresh(today, emp_id):
    """يرجع كل صفوف نفس الرقم الشخصي في نفس التاريخ من sheet1 مباشرة بدون كاش."""
    records = get_sheet_data_fresh()
    matches = []
    for i, r in enumerate(records, start=2):
        if str(r.get("التاريخ", "")).strip() == str(today).strip() and str(r.get("الرقم الشخصي", "")).strip() == str(emp_id).strip():
            matches.append((i, r))
    return matches

def pick_main_daily_row(matches):
    """اختيار السجل الأساسي عند وجود أكثر من صف: نفضّل أول صف فيه حضور، وإلا أول صف."""
    if not matches:
        return None, None
    with_attendance = [(i, r) for i, r in matches if str(r.get("وقت الحضور", "")).strip()]
    return (with_attendance[0] if with_attendance else matches[0])

def has_duplicate_daily_record(today, emp_id):
    return len(find_daily_rows_fresh(today, emp_id)) > 1

def parse_bahrain_datetime(dt_text):
    """تحويل التاريخ المحفوظ في الشيت إلى وقت البحرين حتى لا يفشل تجاوز الموقع."""
    dt_text = str(dt_text or "").strip()
    if not dt_text:
        return None
    for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"]:
        try:
            return datetime.strptime(dt_text, fmt).replace(tzinfo=BAHRAIN_TZ)
        except Exception:
            pass
    return None

def get_location_override():
    """يرجع True إذا كان الأدمن فعّل تجاوز الموقع وما زال الوقت ساريًا."""
    try:
        records = get_settings_records()
        for r in records:
            key = str(r.get("المفتاح", "")).strip()
            if key == "location_override":
                val = str(r.get("القيمة", "")).strip().lower()
                end_dt = parse_bahrain_datetime(r.get("تاريخ_الانتهاء", ""))

                if val in ["true", "1", "yes", "نعم"] and end_dt:
                    if now_bh() < end_dt:
                        return True, end_dt
                    else:
                        # انتهى الوقت، نطفئه تلقائياً حتى يظهر للأدمن أنه غير مفعّل
                        try:
                            disable_location_override()
                        except Exception:
                            pass
                        return False, None
    except Exception:
        pass
    return False, None

def set_location_override(minutes, note=""):
    """تفعيل تجاوز الموقع لمدة محددة وحفظه في شيت إعدادات_النظام."""
    end_dt = now_bh() + timedelta(minutes=int(minutes))
    end_str = end_dt.strftime("%Y-%m-%d %H:%M:%S")
    try:
        records = settings_sheet.get_all_records()
        row_found = None
        for i, r in enumerate(records):
            if str(r.get("المفتاح", "")).strip() == "location_override":
                row_found = i + 2
                break

        if row_found:
            settings_sheet.update(f"A{row_found}:D{row_found}", [["location_override", "true", end_str, note]])
        else:
            safe_append(settings_sheet, ["location_override", "true", end_str, note])

        get_settings_records.clear()
        return True, end_dt
    except Exception as e:
        st.error(f"❌ خطأ أثناء تفعيل تجاوز الموقع: {e}")
        return False, None

def disable_location_override():
    """إيقاف تجاوز الموقع من شيت إعدادات_النظام."""
    try:
        records = settings_sheet.get_all_records()
        found = False
        for i, r in enumerate(records):
            if str(r.get("المفتاح", "")).strip() == "location_override":
                row_num = i + 2
                settings_sheet.update(f"A{row_num}:D{row_num}", [["location_override", "false", "", "تم الإيقاف"]])
                found = True
                break

        if not found:
            safe_append(settings_sheet, ["location_override", "false", "", "تم الإيقاف"] )

        get_settings_records.clear()
        return True
    except Exception as e:
        st.error(f"❌ خطأ أثناء تعطيل تجاوز الموقع: {e}")
        return False

def log_audit(emp_id, emp_name, operation, details):
    now=now_bh(); fp=get_device_fingerprint()
    safe_append(audit_sheet,[now.strftime("%Y-%m-%d"),now.strftime("%H:%M:%S"),emp_name,str(emp_id),operation,details,fp])

def check_device_lock(today, emp_id, emp_name):
    fp=get_device_fingerprint(); locks=get_device_locks()
    for r in locks:
        if str(r.get("التاريخ","")).strip()==today and str(r.get("بصمة الجهاز","")).strip()==fp:
            locked_id=str(r.get("الرقم الشخصي","")).strip()
            locked_name=str(r.get("الاسم","")).strip()
            if locked_id and locked_id!=str(emp_id).strip():
                # تحقق من الـ cooldown
                last_time=str(r.get("وقت_القفل","")).strip()
                if last_time:
                    try:
                        last_dt=datetime.strptime(f"{today} {last_time}","%Y-%m-%d %H:%M:%S")
                        diff_min=(now_bh()-last_dt).seconds//60
                        if diff_min<DEVICE_COOLDOWN_MINUTES:
                            safe_append(attempts_sheet,[today,fp,locked_id,locked_name,emp_id,emp_name,now_bh().strftime("%H:%M:%S"),"محاولة تسجيل من نفس الجهاز"])
                            try:
                                data=get_sheet_data(); row_index,_=find_today_row(data,today,locked_id)
                                if row_index: safe_update(sheet,row_index,COL_ATTEMPT,"⚠️ محاولة تسجيل باسم آخر")
                            except: pass
                            st.error("🚫 هذا الجهاز سجّل موظفة أخرى منذ أقل من 10 دقائق.")
                            st.warning(f"⚠️ يجب الانتظار {DEVICE_COOLDOWN_MINUTES-diff_min} دقيقة أخرى.")
                            return False
                    except: pass
    return True

def lock_device(today, emp_id, emp_name):
    fp=get_device_fingerprint(); locks=get_device_locks()
    for r in locks:
        if str(r.get("التاريخ","")).strip()==today and \
           str(r.get("بصمة الجهاز","")).strip()==fp and \
           str(r.get("الرقم الشخصي","")).strip()==str(emp_id).strip(): return True
    ok=safe_append(device_sheet,[today,fp,str(emp_id),emp_name,now_bh().strftime("%H:%M:%S")])
    get_device_locks.clear(); return ok

def register_operation(operation, emp_id, note=""):
    override_active,_=get_location_override()
    if not st.session_state.get("location_allowed",False) and not override_active:
        st.error("❌ يجب تحديد الموقع أولاً أو تفعيل تجاوز الموقع من الأدمن."); return False

    emp_id=ar_to_en_digits(emp_id).strip()
    emp=validate_employee(emp_id) or st.session_state.get("emp_data")
    if not emp or str(emp.get("الرقم الشخصي",emp_id)).strip()!=emp_id:
        st.error("❌ بيانات الموظفة غير مكتملة."); return False

    # حفظ موظفة جديدة في القائمة البيضاء
    if not validate_employee(emp_id) and operation=="تسجيل حضور":
        is_support_new="دعم" in str(emp.get("المهمة",""))
        if not is_support_new and not emp.get("دعم"):
            try:
                whitelist_sheet.append_row([
                    emp_id,
                    emp.get("الاسم",""),
                    emp.get("المدرسة",""),
                    emp.get("المهمة",""),
                    "لا",
                    emp.get("رقم التواصل",""),
                    emp.get("البريد الإلكتروني",""),
                    emp.get("المسمى الوظيفي","موظفة"),
                    "نعم"
                ])
                get_whitelist.clear()
            except: pass

    full_name=normalize_name(emp.get("الاسم",""))
    school=emp.get("المدرسة",schools[0])
    task=emp.get("المهمة",TASKS_MAIN[0])
    is_support="نعم" if ("دعم" in str(task) or emp.get("دعم")) else "لا"

    now=now_bh(); today=now.strftime("%Y-%m-%d")
    day_name=now.strftime("%A"); time_now=now.strftime("%H:%M:%S")

    if not check_device_lock(today,emp_id,full_name): return False

    # قراءة مباشرة بدون كاش حتى لا تتكرر العمليات بسبب تأخر تحديث Google Sheet
    daily_matches = find_daily_rows_fresh(today, emp_id)
    row_index, row = pick_main_daily_row(daily_matches)

    if len(daily_matches) > 1:
        st.warning("⚠️ يوجد أكثر من سجل لنفس الموظفة في نفس التاريخ. يرجى تنظيف التكرارات من لوحة الأدمن. لن يتم إنشاء سجل جديد.")

    if operation=="تسجيل حضور":
        # حماية مباشرة من التكرار: أي سجل لنفس الرقم في نفس التاريخ يمنع إنشاء سجل حضور جديد
        daily_matches = find_daily_rows_fresh(today, emp_id)
        row_index, row = pick_main_daily_row(daily_matches)
        if row and str(row.get("وقت الحضور", "")).strip():
            st.error(f"❌ تم تسجيل حضورك مسبقاً لهذا اليوم الساعة {row.get('وقت الحضور','')}. لا يمكن تسجيل حضور مكرر.")
            return False
        if len(daily_matches) > 1:
            st.error("❌ يوجد تكرار سابق لهذا الرقم في نفس التاريخ. افتحي لوحة الأدمن > تنظيف التكرارات، ثم حاولي مرة أخرى.")
            return False

        # إذا حضرت متأخرة بسبب موعد/سبب آخر، يوثق النظام ذلك كاستئذان ضمني:
        # خروج الاستئذان من 7:00، ووقت الحضور هو العودة.
        att_is_late = now.time() > time(7, 5, 0)
        note_txt = str(note or "").strip()
        implicit_leave = att_is_late and note_txt and not any(x in note_txt for x in ["رعاية", "دوام مرن", "مهمة رسمية"])
        implicit_exit_time = "07:00:00" if implicit_leave else ""
        implicit_return_time = time_now if implicit_leave else ""

        if row_index:
            safe_update(sheet,row_index,COL_ATTEND,time_now)
            safe_update(sheet,row_index,COL_LATE_REASON,note)
            if implicit_leave:
                safe_update(sheet,row_index,COL_EXIT,implicit_exit_time)
                safe_update(sheet,row_index,COL_RETURN,implicit_return_time)
        else:
            # فحص أخير مباشرة قبل الإضافة لمنع التكرار عند الضغط السريع أو فتح أكثر من نافذة
            final_matches = find_daily_rows_fresh(today, emp_id)
            final_row_index, final_row = pick_main_daily_row(final_matches)
            if final_row and str(final_row.get("وقت الحضور", "")).strip():
                st.error(f"❌ تم تسجيل حضورك مسبقاً لهذا اليوم الساعة {final_row.get('وقت الحضور','')}. لا يمكن تسجيل حضور مكرر.")
                return False
            if final_row_index:
                safe_update(sheet,final_row_index,COL_ATTEND,time_now)
                safe_update(sheet,final_row_index,COL_LATE_REASON,note)
                if implicit_leave:
                    safe_update(sheet,final_row_index,COL_EXIT,implicit_exit_time)
                    safe_update(sheet,final_row_index,COL_RETURN,implicit_return_time)
                row_index = final_row_index
            else:
                ok=safe_append(sheet,[today,day_name,school,task,is_support,full_name,emp_id,time_now,note,"","",implicit_exit_time,implicit_return_time,""])
                if not ok: st.error("❌ تعذر الحفظ، حاولي بعد قليل."); return False
        lock_device(today,emp_id,full_name)
        log_audit(emp_id,full_name,"تسجيل حضور",f"الوقت:{time_now}|السبب:{note or 'بدون'}")
        # ثبّت البيانات
        st.session_state.data_locked_today=True
        st.session_state.locked_emp={"الرقم الشخصي":emp_id,"الاسم":full_name,"المدرسة":school,"المهمة":task,"دعم":is_support=="نعم","نشط":"نعم"}
        st.session_state.locked_date=today
        ls_set("saved_date",today,"sv_date"); ls_set("saved_id",emp_id,"sv_id")
        ls_set("saved_name",full_name,"sv_name"); ls_set("saved_school",school,"sv_school")
        ls_set("saved_section",task,"sv_section"); ls_set("saved_support",is_support,"sv_support")
        clear_caches(); st.success("✅ تم تسجيل الحضور بنجاح."); return True

    if operation=="تسجيل انصراف":
        if not row_index or not row or not row.get("وقت الحضور"): st.error("❌ يجب تسجيل الحضور أولاً."); return False
        if row.get("وقت الانصراف"): st.error("❌ تم تسجيل الانصراف مسبقاً."); return False
        safe_update(sheet,row_index,COL_DEPART,time_now); safe_update(sheet,row_index,COL_DEPART_REASON,note)
        row["وقت الانصراف"] = time_now
        row["سبب الانصراف"] = note
        update_work_calculation(row_index, row)
        log_audit(emp_id,full_name,"تسجيل انصراف",f"الوقت:{time_now}|السبب:{note or 'بدون'}")
        clear_caches(); st.success("✅ تم تسجيل الانصراف بنجاح."); return True

    if operation=="خروج استئذان":
        if not row_index or not row or not row.get("وقت الحضور"): st.error("❌ يجب تسجيل الحضور أولاً."); return False
        if row.get("خروج استئذان") and not row.get("عودة"): st.error("❌ يوجد خروج استئذان مفتوح."); return False
        if row.get("خروج استئذان"): st.error("❌ تم تسجيل خروج الاستئذان مسبقاً."); return False
        safe_update(sheet,row_index,COL_EXIT,time_now); safe_update(sheet,row_index,COL_DEPART_REASON,note)
        if "استئذان انصراف" in str(note):
            safe_update(sheet,row_index,COL_DEPART,time_now)
            row["خروج استئذان"] = time_now
            row["وقت الانصراف"] = time_now
            row["سبب الانصراف"] = note
            update_work_calculation(row_index, row)
            log_audit(emp_id,full_name,"استئذان انصراف",f"الوقت:{time_now}|السبب:{note}")
            clear_caches(); st.success("✅ تم تسجيل استئذان انصراف بنجاح. تم احتساب وقت الاستئذان كوقت انصراف."); return True
        log_audit(emp_id,full_name,"خروج استئذان",f"الوقت:{time_now}|السبب:{note}")
        clear_caches(); st.success("✅ تم تسجيل خروج الاستئذان بنجاح. عند الرجوع اضغطي زر عودة من استئذان."); return True

    if operation=="عودة من استئذان":
        if not row_index or not row or not row.get("وقت الحضور"): st.error("❌ يجب تسجيل الحضور أولاً."); return False
        if not row.get("خروج استئذان"): st.error("❌ لا يوجد خروج استئذان مفتوح."); return False
        if row.get("عودة"): st.error("❌ تم تسجيل العودة مسبقاً."); return False
        safe_update(sheet,row_index,COL_RETURN,time_now)
        log_audit(emp_id,full_name,"عودة من استئذان",f"الوقت:{time_now}")
        clear_caches(); st.success("✅ تم تسجيل العودة من الاستئذان بنجاح."); return True

    st.error("❌ عملية غير معروفة."); return False

# ─── Session State ──────────────────────────────────────────────
default_state={
    "pending_operation":None,"admin_logged_in":False,"admin_last_active":None,
    "location_allowed":False,"emp_verified":False,"emp_data":None,
    "data_locked_today":False,"locked_emp":None,"locked_date":None,
}
for k,v in default_state.items():
    if k not in st.session_state: st.session_state[k]=v

today_str=now_bh().strftime("%Y-%m-%d")
auto_close_previous_open_records()

_saved_date=ls_get("saved_date"); _saved_id=ls_get("saved_id")
_saved_name=ls_get("saved_name"); _saved_school=ls_get("saved_school")
_saved_section=ls_get("saved_section"); _saved_support=ls_get("saved_support")

_data_locked=(
    (st.session_state.get("data_locked_today",False) and st.session_state.get("locked_date")==today_str)
    or (_saved_date==today_str and _saved_id and str(_saved_id).strip()!="")
)

if _data_locked and not st.session_state.emp_verified:
    st.session_state.emp_verified=True
    st.session_state.emp_data=st.session_state.get("locked_emp") or {
        "الرقم الشخصي":_saved_id,"الاسم":_saved_name or "","المدرسة":_saved_school or "",
        "المهمة":_saved_section or "","دعم":_saved_support=="نعم","نشط":"نعم"
    }

if st.session_state.admin_logged_in and st.session_state.admin_last_active:
    idle=(now_bh()-st.session_state.admin_last_active).seconds//60
    if idle>=30:
        st.session_state.admin_logged_in=False; st.session_state.admin_last_active=None
        st.warning("⏱️ انتهت جلسة الأدمن بسبب الخمول.")

# ─── Header ────────────────────────────────────────────────────
day_arabic={"Saturday":"السبت","Sunday":"الأحد","Monday":"الاثنين","Tuesday":"الثلاثاء","Wednesday":"الأربعاء","Thursday":"الخميس","Friday":"الجمعة"}.get(now_bh().strftime("%A"),now_bh().strftime("%A"))

st.image("logo.png", use_container_width=True)

st.markdown(f"""
<div class="app-header">
    <div class="sub">مركز مدرسة جدحفص للتصحيح المركزي — المنطقة التعليمية (2)</div>
    <div class="title">نظام الحضور والانصراف</div>
    <div class="date-pill">{day_arabic} — {today_str}</div>
</div>
""", unsafe_allow_html=True)

mode=st.radio("",["👤 موظفة","🛡️ أدمن"],horizontal=True,label_visibility="collapsed")

# ══════════════════════════════════════════════════════════════════
# ══ واجهة الموظفة ══
# ══════════════════════════════════════════════════════════════════
if mode=="👤 موظفة":

    # ── الموقع ──────────────────────────────────────────────────
    with st.container(border=True):
        st.markdown('<div class="card-title">📍 التحقق من الموقع</div>', unsafe_allow_html=True)

        with st.expander("📋 كيف أفعّل الموقع؟ اضغطي هنا"):
            st.markdown("""
**📱 على الجوال (iOS/Safari):**
1. اضغطي على **⚙️ الإعدادات**
2. اختاري **الخصوصية والأمان** ← **خدمات الموقع**
3. فعّلي خدمات الموقع
4. ابحثي عن **Safari** وغيّري إلى **أثناء الاستخدام**
5. ارجعي للتطبيق وحدّثي الصفحة

**📱 على الجوال (Android/Chrome):**
1. اضغطي على **⚙️ الإعدادات**
2. اختاري **التطبيقات** ← **Chrome**
3. اضغطي **الأذونات** ← **الموقع** ← **السماح**
4. ارجعي للتطبيق وحدّثي الصفحة

**💻 على الكمبيوتر (Chrome):**
1. اضغطي على أيقونة 🔒 يسار رابط الموقع
2. اختاري **إعدادات الموقع**
3. غيّري **الموقع** إلى **سماح**
4. حدّثي الصفحة
            """)

        location=streamlit_geolocation()
        if location:
            lat=location.get("latitude"); lon=location.get("longitude"); error=location.get("error","")
            if error:
                st.session_state.location_allowed=False
                st.warning("⚠️ الموقع غير مفعّل، الرجاء تفعيله من إعدادات المتصفح.")
            elif lat is not None and lon is not None:
                try:
                    dist_val=distance_m(float(lat),float(lon),SCHOOL_LAT,SCHOOL_LON)
                    if dist_val<=ALLOWED_RADIUS:
                        st.session_state.location_allowed=True
                        st.success(f"✅ داخل نطاق المدرسة — المسافة: {int(dist_val)} م")
                    else:
                        st.session_state.location_allowed=False
                        st.error(f"❌ خارج النطاق — المسافة: {int(dist_val)} م")
                except:
                    st.session_state.location_allowed=False; st.error("❌ خطأ في قراءة الموقع.")
            else:
                st.session_state.location_allowed=False; st.info("اضغطي زر تحديد الموقع أعلاه.")
        else:
            st.session_state.location_allowed=False; st.info("اضغطي زر تحديد الموقع أعلاه.")

    ov_active,ov_end=get_location_override()
    if ov_active and ov_end:
        remaining=max(0, int((ov_end-now_bh()).total_seconds()//60))
        st.warning(f"⚠️ وضع تجاوز الموقع مفعّل — ينتهي بعد {remaining} دقيقة.")
        st.session_state.location_allowed=True

    # ── البيانات الشخصية ─────────────────────────────────────────
    with st.container(border=True):
        st.markdown('<div class="card-title">🪪 البيانات الشخصية</div>', unsafe_allow_html=True)

        if _data_locked:
            emp=st.session_state.emp_data
            st.markdown(f"""
            <div class="field-lbl">الرقم الشخصي</div><div class="field-val">{emp.get("الرقم الشخصي","")}</div>
            <div class="field-lbl">الاسم</div><div class="field-val">{emp.get("الاسم","")}</div>
            <div class="field-lbl">المدرسة</div><div class="field-val">{emp.get("المدرسة","")}</div>
            <div class="field-lbl">المهمة في الكنترول</div><div class="field-val blue">{emp.get("المهمة","")}</div>
            <div style="font-size:12px;color:#3B6D11;font-weight:700;">🔒 بياناتك محفوظة لهذا اليوم</div>
            """, unsafe_allow_html=True)
            show_previous_auto_close_notice(emp.get("الرقم الشخصي", ""))
        else:
            emp_id_raw=st.text_input("الرقم الشخصي", placeholder="أدخلي رقمك الشخصي", max_chars=20)
            emp_id=ar_to_en_digits(emp_id_raw).strip()

            if emp_id:
                show_previous_auto_close_notice(emp_id)
                existing=validate_employee(emp_id)
                if existing:
                    is_prev_support = str(existing.get("دعم","")).strip() in ["نعم","yes","Yes","TRUE","true","1"]

                    if is_prev_support:
                        # موظفة كانت دعم — نسألها هل لا زالت دعم
                        st.markdown(f"""
                        <div class="field-lbl">الاسم</div><div class="field-val">{existing.get("الاسم","")}</div>
                        <div style="background:#faeeda;border-radius:12px;padding:10px 14px;font-size:13px;font-weight:700;color:#633806;margin-bottom:10px;">
                        🔄 أنتِ مسجّلة كدعم مؤقت
                        </div>
                        """, unsafe_allow_html=True)

                        still_support = st.radio(
                            "ما زلتِ دعم أم صرتِ عضوة في المركز؟",
                            ["🔄 لا زلت دعم", "🏫 صرت عضوة في المركز"],
                            horizontal=True, key="support_upgrade"
                        )

                        if still_support == "🔄 لا زلت دعم":
                            st.session_state.emp_verified=True
                            st.session_state.emp_data={"الرقم الشخصي":emp_id,"الاسم":existing.get("الاسم",""),"المدرسة":existing.get("المدرسة",""),"المهمة":existing.get("المهمة",""),"نشط":"نعم","دعم":True}
                            st.warning("🔄سيتم تسجيل حضوركِ لهذا اليوم فقط كدعم")

                        else:
                            # تريد تنتقل لعضوة — تكمّل بياناتها
                            st.info("🏫 ممتاز! أكملي بياناتك لتُضافي كعضوة دائمة")
                            emp_task_new=st.selectbox("المهمة الجديدة", TASKS_MAIN, key="upgrade_task")
                            emp_job_new=st.selectbox("المسمى الوظيفي", JOB_TITLES, key="upgrade_job")
                            emp_phone_new=st.text_input("رقم التواصل", value=existing.get("رقم التواصل",""), key="upgrade_phone")
                            emp_email_new=st.text_input("البريد الإلكتروني", value=existing.get("البريد الإلكتروني",""), key="upgrade_email")

                            if st.button("💾 حفظ كعضوة دائمة", use_container_width=True, type="primary", key="btn_upgrade"):
                                try:
                                    # ابحث عن صف الموظفة في القائمة البيضاء وحدّثه
                                    wl_records = whitelist_sheet.get_all_records()
                                    for i, r in enumerate(wl_records):
                                        if str(r.get("الرقم الشخصي","")).strip() == emp_id:
                                            row_num = i + 2
                                            whitelist_sheet.update_cell(row_num, 4, emp_task_new)   # D - المهمة
                                            whitelist_sheet.update_cell(row_num, 5, "لا")           # E - دعم
                                            whitelist_sheet.update_cell(row_num, 6, emp_phone_new)  # F - رقم التواصل
                                            whitelist_sheet.update_cell(row_num, 7, emp_email_new)  # G - البريد
                                            whitelist_sheet.update_cell(row_num, 8, emp_job_new)    # H - المسمى
                                            break
                                    get_whitelist.clear()
                                    st.session_state.emp_verified=True
                                    st.session_state.emp_data={"الرقم الشخصي":emp_id,"الاسم":existing.get("الاسم",""),"المدرسة":existing.get("المدرسة",""),"المهمة":emp_task_new,"نشط":"نعم","دعم":False}
                                    st.success("✅ تم تحديث بياناتك كعضوة دائمة!")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"خطأ: {e}")
                    else:
                        # موظفة دائمة عادية
                        st.session_state.emp_verified=True
                        st.session_state.emp_data={"الرقم الشخصي":emp_id,"الاسم":existing.get("الاسم",""),"المدرسة":existing.get("المدرسة",""),"المهمة":existing.get("المهمة",""),"نشط":"نعم","دعم":False}
                        st.markdown(f"""
                        <div class="field-lbl">الاسم</div><div class="field-val">{existing.get("الاسم","")}</div>
                        <div class="field-lbl">المدرسة</div><div class="field-val">{existing.get("المدرسة","")}</div>
                        <div class="field-lbl">المهمة في الكنترول</div><div class="field-val blue">{existing.get("المهمة","")}</div>
                        """, unsafe_allow_html=True)
                        st.success("✅ تم التحقق من بياناتك.")
                else:
                    # موظفة جديدة — تدخل بياناتها
                    # ── نوع التسجيل أولاً ──
                    emp_type=st.radio("نوع التسجيل",["🏫 عضوة في المركز","🔄 دعم"],horizontal=True,key="emp_type")
                    is_sup=emp_type=="🔄 دعم"

                    # ── البيانات حسب النوع ──
                    emp_name=st.text_input("الاسم الثلاثي", placeholder="اكتبي اسمك الثلاثي", key="new_name")
                    emp_school=st.selectbox("المدرسة", schools, key="new_school")
                    emp_task=st.selectbox("المهمة", TASKS_SUPPORT if is_sup else TASKS_MAIN, key="new_task")

                    if not is_sup:
                        emp_job=st.selectbox("المسمى الوظيفي", JOB_TITLES, key="new_job")
                        emp_phone=st.text_input("رقم التواصل", placeholder="مثال: 39XXXXXX", key="new_phone")
                        emp_email=st.text_input("البريد الإلكتروني", placeholder="مثال: name@moe.bh", key="new_email")
                    else:
                        emp_job="دعم"; emp_phone=""; emp_email=""
                        st.warning("🔄 سيتم تسجيل حضورك اليوم فقط كدعم")

                    # ── زر الحفظ ──
                    if emp_name.strip():
                        if st.button("💾 حفظ البيانات والمتابعة", use_container_width=True, type="primary", key="confirm_new"):
                            new_emp_data={
                                "الرقم الشخصي":emp_id,
                                "الاسم":normalize_name(emp_name),
                                "المدرسة":emp_school,
                                "المهمة":emp_task,
                                "المسمى الوظيفي":emp_job,
                                "رقم التواصل":emp_phone,
                                "البريد الإلكتروني":emp_email,
                                "نشط":"نعم",
                                "دعم":is_sup
                            }
                            st.session_state.emp_verified=True
                            st.session_state.emp_data=new_emp_data
                            # حفظ في القائمة البيضاء فوراً (إلا دعم)
                            if not is_sup:
                                try:
                                    whitelist_sheet.append_row([
                                        emp_id,           # A - الرقم الشخصي
                                        normalize_name(emp_name),  # B - الاسم
                                        emp_school,       # C - المدرسة
                                        emp_task,         # D - المهمة
                                        "لا",             # E - دعم
                                        emp_phone,        # F - رقم التواصل
                                        emp_email,        # G - البريد الإلكتروني
                                        emp_job,          # H - المسمى الوظيفي
                                        "نعم"             # I - نشط
                                    ])
                                    get_whitelist.clear()
                                    st.success("✅ تم حفظ بياناتك في القائمة البيضاء، يمكنك الآن تسجيل الحضور")
                                except Exception as e:
                                    st.warning(f"⚠️ تعذّر الحفظ في القائمة: {e}")
                            else:
                                st.success("✅ تم تسجيل بياناتك، يمكنك الآن تسجيل الحضور")
                            st.rerun()
            else:
                st.session_state.emp_verified=False; st.session_state.emp_data=None

    # ── العمليات ─────────────────────────────────────────────────
    if st.session_state.emp_verified and st.session_state.emp_data:
        emp=st.session_state.emp_data
        emp_id=str(emp.get("الرقم الشخصي","")).strip()
        data=get_sheet_data(); _,today_row=find_today_row(data,today_str,emp_id)
        att_time=today_row.get("وقت الحضور","—") if today_row else "—"
        dep_time=today_row.get("وقت الانصراف","—") if today_row else "—"
        exit_time=today_row.get("خروج استئذان","—") if today_row else "—"
        return_time=today_row.get("عودة","—") if today_row else "—"
        has_exit = bool(today_row and today_row.get("خروج استئذان"))
        has_return = bool(today_row and today_row.get("عودة"))
        has_depart = bool(today_row and today_row.get("وقت الانصراف"))
        if has_exit and not has_return and not has_depart:
            status="استئذان مفتوح"
            stat_col="#BA7517"
        elif has_exit and has_depart and "استئذان انصراف" in str(today_row.get("سبب الانصراف", "")):
            status="انصراف باستئذان"
            stat_col="#185FA5"
        elif today_row and today_row.get("وقت الحضور"):
            status="حاضر ✓"
            stat_col="#3B6D11"
        else:
            status="لم يُسجَّل"
            stat_col="#A32D2D"

        if today_row and today_row.get("وقت الحضور") and not today_row.get("وقت الانصراف") and now_bh().time() >= time(13,30):
            st.warning("⚠️ لم يتم تسجيل الانصراف حتى الآن. يرجى تسجيل الانصراف قبل مغادرة المركز.")

        if has_exit:
            st.markdown(f"""
            <div class="pro-card"><h3 style="color:#0c3460;text-align:right;">⚡ العمليات</h3>
            <div class="today-strip">
                <div class="stat-cell"><span class="stat-val">{att_time}</span><span class="stat-lbl">وقت الحضور</span></div>
                <div style="width:1px;background:#d3d1c7;margin:4px 0;"></div>
                <div class="stat-cell"><span class="stat-val">{exit_time}</span><span class="stat-lbl">خروج استئذان</span></div>
                <div style="width:1px;background:#d3d1c7;margin:4px 0;"></div>
                <div class="stat-cell"><span class="stat-val">{return_time if has_return else 'لم تُسجل'}</span><span class="stat-lbl">العودة</span></div>
                <div style="width:1px;background:#d3d1c7;margin:4px 0;"></div>
                <div class="stat-cell"><span class="stat-val" style="color:{stat_col};">{status}</span><span class="stat-lbl">الحالة</span></div>
            </div></div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="pro-card"><h3 style="color:#0c3460;text-align:right;">⚡ العمليات</h3>
            <div class="today-strip">
                <div class="stat-cell"><span class="stat-val">{att_time}</span><span class="stat-lbl">وقت الحضور</span></div>
                <div style="width:1px;background:#d3d1c7;margin:4px 0;"></div>
                <div class="stat-cell"><span class="stat-val">{dep_time}</span><span class="stat-lbl">وقت الانصراف</span></div>
                <div style="width:1px;background:#d3d1c7;margin:4px 0;"></div>
                <div class="stat-cell"><span class="stat-val" style="color:{stat_col};">{status}</span><span class="stat-lbl">الحالة</span></div>
            </div></div>
            """, unsafe_allow_html=True)

        if today_row and today_row.get("وقت الانصراف") and "رعاية" not in str(today_row.get("سبب الانصراف", "")) and "رعاية" not in str(today_row.get("سبب التأخير", "")):
            with st.expander("هل لديكِ رعاية لهذا اليوم؟", expanded=False):
                st.info("إذا كان دوامك اليوم رعاية، اضغطي نعم ليتم احتساب المطلوب 5 ساعات. إذا لم تختاري رعاية سيبقى الحساب دوام عادي/مرن حسب البيانات.")
                if st.button("نعم، لدي رعاية", use_container_width=True, key="confirm_care_today"):
                    if mark_care_for_today(emp_id):
                        st.rerun()

        col1,col2=st.columns(2)
        with col1:
            if st.button("✅ تسجيل حضور",use_container_width=True):
                st.session_state.pending_operation=None
                if now_bh().time()>time(7,30): st.session_state.pending_operation="تسجيل حضور"
                else: register_operation("تسجيل حضور",emp_id); st.rerun()
        with col2:
            if st.button("🔵 تسجيل انصراف",use_container_width=True):
                st.session_state.pending_operation=None
                if now_bh().time()<time(14,0): st.session_state.pending_operation="تسجيل انصراف"
                else: register_operation("تسجيل انصراف",emp_id); st.rerun()
        col3,col4=st.columns(2)
        with col3:
            if st.button("📤 خروج استئذان",use_container_width=True):
                st.session_state.pending_operation="خروج استئذان"
        with col4:
            if st.button("🔁 عودة من استئذان",use_container_width=True):
                st.session_state.pending_operation=None
                register_operation("عودة من استئذان",emp_id); st.rerun()

        if st.session_state.pending_operation=="تسجيل حضور":
            with st.container(border=True):
                st.markdown('<div class="card-title">سبب التأخير بعد 7:05:30 — اختياري</div>',unsafe_allow_html=True)
                late_reason=st.selectbox("السبب",["اختاري السبب (اختياري)"]+reasons,key="late_reason")
                late_other="" 
                if late_reason=="أخرى": late_other=st.text_input("اكتبي السبب",key="late_other")
                final="" if late_reason=="اختاري السبب (اختياري)" else (late_other.strip() if late_reason=="أخرى" else late_reason)
                if st.button("تأكيد تسجيل الحضور",use_container_width=True,type="primary"):
                    st.session_state.pending_operation=None
                    register_operation("تسجيل حضور",emp_id,final); st.rerun()

        if st.session_state.pending_operation=="تسجيل انصراف":
            with st.container(border=True):
                st.markdown('<div class="card-title">سبب الانصراف قبل 2:00</div>',unsafe_allow_html=True)
                reason=st.selectbox("السبب",reasons,key="early_reason")
                other="" 
                if reason=="أخرى": other=st.text_input("اكتبي السبب",key="early_other")
                final=other.strip() if reason=="أخرى" else reason
                if st.button("تأكيد تسجيل الانصراف",use_container_width=True,type="primary"):
                    if not final: st.error("السبب مطلوب")
                    else: st.session_state.pending_operation=None; register_operation("تسجيل انصراف",emp_id,final); st.rerun()

        if st.session_state.pending_operation=="خروج استئذان":
            with st.container(border=True):
                st.markdown('<div class="card-title">نوع وسبب خروج الاستئذان</div>',unsafe_allow_html=True)
                leave_kind=st.radio("نوع الاستئذان",["استئذان مع عودة","استئذان انصراف"],horizontal=True,key="leave_kind")
                if leave_kind=="استئذان مع عودة":
                    st.info("سيتم تسجيل خروج الاستئذان فقط. عند الرجوع يجب الضغط على زر عودة من استئذان، ثم تسجيل الانصراف لاحقًا.")
                else:
                    st.warning("سيتم احتساب وقت خروج الاستئذان كوقت انصراف، ولا تحتاجين لتسجيل عودة.")
                reason=st.selectbox("السبب",reasons,key="exit_reason")
                other=""
                if reason=="أخرى": other=st.text_input("اكتبي السبب",key="exit_other")
                reason_final=other.strip() if reason=="أخرى" else reason
                final=f"{leave_kind} — {reason_final}" if reason_final else leave_kind
                if st.button("تأكيد خروج الاستئذان",use_container_width=True,type="primary"):
                    if not reason_final: st.error("السبب مطلوب")
                    else: st.session_state.pending_operation=None; register_operation("خروج استئذان",emp_id,final); st.rerun()

# ══════════════════════════════════════════════════════════════════
# ══ واجهة الأدمن ══
# ══════════════════════════════════════════════════════════════════
else:
    if not st.session_state.admin_logged_in:
        with st.container(border=True):
            st.markdown('<div class="card-title">🛡️ دخول الأدمن</div>',unsafe_allow_html=True)
            pw=st.text_input("كلمة المرور",type="password")
            if st.button("دخول",use_container_width=True):
                if pw.strip()==ADMIN_PASSWORD:
                    st.session_state.admin_logged_in=True; st.session_state.admin_last_active=now_bh(); st.rerun()
                else: st.error("❌ كلمة المرور غير صحيحة.")
    else:
        st.session_state.admin_last_active=now_bh()
        st.markdown("## 🛡️ لوحة الأدمن")

        admin_tab=st.selectbox("القسم",[
            "📊 إحصائيات اليوم",
            "🔴 تسجيل الغياب",
            "📅 دوام الأقسام",
            "🧹 تنظيف التكرارات",
            "✏️ تعديل سجل",
            "➕ تسجيل يدوي",
            "📋 القائمة البيضاء",
            "🚫 محاولات التسجيل",
            "📡 تجاوز الموقع",
            "🔓 فتح قفل جهاز",
            "🔍 سجل التدقيق",
            "⚠️ تقرير الأجهزة",
        ])

        # ── إحصائيات اليوم ──────────────────────────────────────
        if admin_tab=="📊 إحصائيات اليوم":
            data=get_sheet_data()
            today_rows=[r for r in data if r.get("التاريخ")==today_str]

            # ربط إحصائيات اليوم بجدول دوام الأقسام الأسبوعي أو اليومي
            today_day_ar = day_arabic
            scheduled_tasks, schedule_source = scheduled_tasks_for_date(today_str)
            wl_all = get_whitelist()
            if scheduled_tasks is None:
                required_wl = wl_all
                st.warning("⚠️ لم يتم تحديد دوام أقسام لهذا اليوم، لذلك ستعرض الإحصائيات على جميع القائمة البيضاء.")
            else:
                required_wl = {eid: emp for eid, emp in wl_all.items() if emp_required_on_day(emp, scheduled_tasks)}
                with st.expander(f"📅 الأقسام المعتمدة في إحصائيات اليوم ({today_day_ar}) — مصدر الجدول: {schedule_source}", expanded=False):
                    for t in scheduled_tasks:
                        st.markdown(f"- {t}")

            required_ids = set(str(eid).strip() for eid in required_wl.keys())

            # سجلات اليوم للأقسام المطلوبة فقط
            today_required_rows = [r for r in today_rows if str(r.get("الرقم الشخصي","")).strip() in required_ids]

            # دعم خارجي: حضر اليوم لكنه غير موجود في القائمة البيضاء
            external_support_rows = []
            for r in today_rows:
                eid = str(r.get("الرقم الشخصي","")).strip()
                support_raw = str(r.get("دعم","")).strip()
                task_txt = str(r.get("المهمة","")).strip()
                is_external_support = eid and eid not in wl_all and (is_yes(support_raw) or "دعم" in task_txt)
                if is_external_support:
                    external_support_rows.append(r)

            try:
                abs_records_all = absence_sheet.get_all_records()
                abs_today=[r for r in abs_records_all if r.get("التاريخ")==today_str and str(r.get("الرقم الشخصي","")).strip() in required_ids]
            except:
                abs_today=[]

            attended=[r for r in today_required_rows if r.get("وقت الحضور")]
            late_list=[r for r in today_required_rows if is_late_for_statistics(r)]
            early_dep=[r for r in today_required_rows if r.get("وقت الانصراف","") and r.get("وقت الانصراف","")< "14:00:00"]
            on_leave=[r for r in today_required_rows if r.get("خروج استئذان") and not r.get("عودة") and not r.get("وقت الانصراف")]
            missing_depart=[r for r in today_required_rows if r.get("وقت الحضور") and not r.get("وقت الانصراف")]
            auto_closed=[r for r in data if str(r.get("إغلاق تلقائي","")).strip()]
            correction_done_rows=[r for r in today_required_rows if is_correction_done_day(r)]

            c1,c2,c3=st.columns(3)
            c1.metric("المتوقع حضورهم اليوم",len(required_wl))
            c2.metric("حاضرون من الأقسام",len(attended))
            c3.metric("غائبات",len(abs_today))
            c4,c5,c6=st.columns(3)
            c4.metric("متأخرون",len(late_list))
            c5.metric("لم يسجلن انصراف",len(missing_depart))
            c6.metric("استئذان مفتوح",len(on_leave))
            c7,c8,c9=st.columns(3)
            c7.metric("الدعم الخارجي",len(external_support_rows))
            c8.metric("إجمالي حضور اليوم",len([r for r in today_rows if r.get("وقت الحضور")]))
            c9.metric("خارج الأقسام المحددة",max(0, len([r for r in today_rows if r.get("وقت الحضور")])-len(attended)-len(external_support_rows)))
            c10,c11,c12=st.columns(3)
            c10.metric("معفى - انتهاء التصحيح",len(correction_done_rows))
            c11.metric("إغلاق تلقائي",len(auto_closed))
            c12.metric("", "")

            st.info("✅ الإحصائيات الأساسية أعلاه تعتمد على دوام الأقسام المحدد لهذا اليوم، مع فصل الدعم الخارجي غير الموجود في القائمة البيضاء.")

            if correction_done_rows:
                st.markdown("#### ✅ معفى - الانتهاء من التصحيح")
                for r in correction_done_rows:
                    st.markdown(f'<div class="audit-row">✅ {r.get("الاسم الثلاثي","")} — {r.get("المهمة","")} — حضور: {r.get("وقت الحضور","")} — انصراف: {r.get("وقت الانصراف","") or "لم يسجل"}</div>',unsafe_allow_html=True)

            if external_support_rows:
                st.markdown("#### 🟣 الدعم الخارجي غير الموجود في القائمة البيضاء")
                for r in external_support_rows:
                    st.markdown(f'<div class="audit-row">🟣 {r.get("الاسم الثلاثي","")} — #{r.get("الرقم الشخصي","")} — {r.get("اسم المدرسة",r.get("المدرسة",""))} — {r.get("المهمة","")} — حضور: {r.get("وقت الحضور","")} — انصراف: {r.get("وقت الانصراف","") or "لم يسجل"}</div>',unsafe_allow_html=True)

            if missing_depart:
                st.markdown("#### 🚨 لم يسجلن الانصراف حتى الآن — من الأقسام المطلوبة")
                for r in missing_depart:
                    st.markdown(f'<div class="warn-row">🚨 {r.get("الاسم الثلاثي","")} — {r.get("اسم المدرسة",r.get("المدرسة",""))} — {r.get("المهمة","")} — حضور: {r.get("وقت الحضور","")}</div>',unsafe_allow_html=True)
            if on_leave:
                st.markdown("#### 📤 استئذان مفتوح — من الأقسام المطلوبة")
                for r in on_leave:
                    st.markdown(f'<div class="warn-row">📤 {r.get("الاسم الثلاثي","")} — خروج: {r.get("خروج استئذان","")} — لم تسجل عودة أو انصراف</div>',unsafe_allow_html=True)
            if abs_today:
                st.markdown("#### الغائبات — حسب دوام الأقسام")
                for r in abs_today:
                    st.markdown(f'<div class="absent-row">🔴 {r.get("الاسم","")} — {r.get("المدرسة","")} — {r.get("المهمة","")} — سبب: {r.get("سبب الغياب","")}</div>',unsafe_allow_html=True)
            if late_list:
                st.markdown("#### المتأخرون — حسب القواعد المعتمدة")
                for r in late_list:
                    st.markdown(f'<div class="warn-row">⏰ {r.get("الاسم الثلاثي","")} — وصل {r.get("وقت الحضور","")} — السبب: {r.get("سبب التأخير","") or "بدون"}</div>',unsafe_allow_html=True)
            if auto_closed:
                with st.expander("🔄 سجلات أُغلقت تلقائيًا", expanded=False):
                    for r in reversed(auto_closed[-50:]):
                        st.markdown(f'<div class="audit-row">{r.get("التاريخ","")} — {r.get("الاسم الثلاثي","")} — انصراف: {r.get("وقت الانصراف","")} — {r.get("إغلاق تلقائي","")}</div>',unsafe_allow_html=True)

        # ── تسجيل الغياب ────────────────────────────────────────
        elif admin_tab=="🔴 تسجيل الغياب":
            abs_date=st.date_input("تاريخ الغياب",value=now_bh().date(),key="abs_date")
            abs_date_str=str(abs_date)
            abs_day_ar=day_ar_from_date(abs_date)

            scheduled_tasks, schedule_source = scheduled_tasks_for_date(abs_date_str)
            if scheduled_tasks is None:
                st.warning("⚠️ لم يتم تحديد دوام أقسام لهذا اليوم في ورقة جدول_دوام_الأقسام، لذلك سيتم حصر الغياب على جميع القائمة البيضاء.")
            else:
                with st.expander(f"📅 الأقسام المطلوب دوامها يوم {abs_day_ar} — مصدر الجدول: {schedule_source}", expanded=False):
                    for t in scheduled_tasks:
                        st.markdown(f"- {t}")

            wl_all=get_whitelist()
            if not wl_all:
                st.warning("⚠️ القائمة البيضاء فارغة")
            else:
                # فلترة القائمة البيضاء حسب جدول الدوام
                required_wl={eid:emp for eid,emp in wl_all.items() if emp_required_on_day(emp, scheduled_tasks)}

                data=get_sheet_data()
                attended_ids=set(str(r.get("الرقم الشخصي","")).strip() for r in data if r.get("التاريخ")==abs_date_str and r.get("وقت الحضور"))
                try:
                    abs_records=absence_sheet.get_all_records()
                    absent_ids=set(str(r.get("الرقم الشخصي","")).strip() for r in abs_records if r.get("التاريخ")==abs_date_str)
                except:
                    abs_records=[]; absent_ids=set()

                not_registered={eid:emp for eid,emp in required_wl.items() if eid not in attended_ids and eid not in absent_ids}
                already_absent={eid:emp for eid,emp in required_wl.items() if eid in absent_ids}

                c1,c2,c3=st.columns(3)
                c1.metric("المطلوب دوامهم",len(required_wl))
                c2.metric("حاضرات",len(attended_ids.intersection(set(required_wl.keys()))))
                c3.metric("لم يسجّلن",len(not_registered))

                if scheduled_tasks is not None:
                    st.info("✅ الحصر الحالي يعتمد فقط على الأقسام/المهام المحددة في جدول دوام الأقسام لهذا اليوم.")

                if already_absent:
                    st.markdown("#### تم تسجيل غيابهن")
                    for eid,emp in already_absent.items():
                        rec=next((r for r in abs_records if str(r.get("الرقم الشخصي",""))==eid and r.get("التاريخ")==abs_date_str),{})
                        st.markdown(f'<div class="absent-row">🔴 {emp.get("الاسم","")} — {emp.get("المهمة","")} — سبب: {rec.get("سبب الغياب","")}</div>',unsafe_allow_html=True)

                if not_registered:
                    st.markdown("#### لم يسجّلن بعد")
                    for eid,emp in not_registered.items():
                        with st.expander(f"🔴 {emp.get('الاسم','')} — {emp.get('المدرسة','')} — {emp.get('المهمة','')}"):
                            sel=st.selectbox("سبب الغياب",abs_reasons,key=f"ar_{eid}")
                            other_txt=""
                            if sel=="أخرى": other_txt=st.text_input("اكتبي السبب",key=f"ao_{eid}")
                            note_txt=st.text_input("ملاحظات (اختياري)",key=f"an_{eid}")
                            final_r=other_txt.strip() if sel=="أخرى" else sel
                            if st.button("تسجيل غياب",key=f"ab_{eid}",use_container_width=True):
                                absence_sheet.append_row([abs_date_str,abs_day_ar,eid,emp.get("الاسم",""),emp.get("المدرسة",""),emp.get("المهمة",""),final_r,note_txt,"أدمن"])
                                log_audit(eid,emp.get("الاسم",""),"تسجيل غياب",f"التاريخ:{abs_date_str}|السبب:{final_r}")
                                st.success(f"✅ تم تسجيل غياب {emp.get('الاسم','')}"); st.rerun()
                else:
                    st.success("✅ تم تسجيل وضع جميع الموظفات المطلوب دوامهن لهذا اليوم")

        # ── دوام الأقسام ────────────────────────────────────────
        elif admin_tab=="📅 دوام الأقسام":
            st.markdown("#### 📅 تحديد الأقسام/المهام التي تداوم في كل يوم")
            st.info("حددي الأيام المطلوبة لكل مهمة. عند حصر الغياب سيحسب البرنامج فقط الموظفات التابعات للمهام المفعّلة في يوم الغياب.")

            st.markdown("### 🗓️ دوام يوم محدد — مرن")
            st.caption("استخدمي هذا إذا تغير الجدول في يوم معيّن. هذا الجدول له أولوية على الجدول الأسبوعي لذلك التاريخ.")
            daily_date = st.date_input("تاريخ الدوام الخاص", value=now_bh().date(), key="daily_sch_date")
            daily_date_str = str(daily_date)
            daily_tasks_selected = st.multiselect("اختاري الأقسام/المهام التي ستداوم في هذا التاريخ", TASKS_ALL, key="daily_sch_tasks")
            daily_note = st.text_input("ملاحظات اختيارية", key="daily_sch_note")
            if st.button("💾 حفظ دوام هذا التاريخ", use_container_width=True, type="primary", key="save_daily_schedule"):
                if not daily_tasks_selected:
                    st.error("❌ اختاري مهمة واحدة على الأقل.")
                else:
                    try:
                        # تعطيل السجلات القديمة لنفس التاريخ، ثم إضافة الاختيارات الجديدة
                        records = daily_schedule_sheet.get_all_records()
                        for i, r in enumerate(records):
                            if str(r.get("التاريخ","")).strip() == daily_date_str:
                                daily_schedule_sheet.update_cell(i+2, 3, "لا")
                        for t in daily_tasks_selected:
                            daily_schedule_sheet.append_row([daily_date_str, t, "نعم", daily_note], value_input_option="USER_ENTERED")
                        get_daily_schedule_records.clear()
                        st.success("✅ تم حفظ دوام التاريخ المحدد. سيعتمد عليه حصر الغياب والإحصائيات لهذا اليوم.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ خطأ أثناء حفظ دوام اليوم: {e}")

            current_daily = [r for r in get_daily_schedule_records() if str(r.get("التاريخ","")).strip()==daily_date_str and (str(r.get("نشط","")).strip()=="" or is_yes(r.get("نشط","")))]
            if current_daily:
                with st.expander(f"📌 دوام محفوظ لتاريخ {daily_date_str}", expanded=True):
                    for i, r in enumerate(current_daily, start=1):
                        st.markdown(f'<div class="audit-row"><b>{r.get("المهمة","")}</b><br><small>{r.get("ملاحظات","")}</small></div>', unsafe_allow_html=True)
                    if st.button("🗑️ تعطيل دوام هذا التاريخ", use_container_width=True, key="disable_daily_schedule"):
                        try:
                            records = daily_schedule_sheet.get_all_records()
                            for i, r in enumerate(records):
                                if str(r.get("التاريخ","")).strip() == daily_date_str:
                                    daily_schedule_sheet.update_cell(i+2, 3, "لا")
                            get_daily_schedule_records.clear()
                            st.success("✅ تم تعطيل دوام هذا التاريخ، وسيعود النظام للجدول الأسبوعي.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ تعذر التعطيل: {e}")

            st.markdown("---")
            st.markdown("### 📅 الجدول الأسبوعي الثابت")

            with st.expander("➕ إضافة / تحديث مهمة", expanded=True):
                sch_task=st.selectbox("المهمة", TASKS_ALL, key="sch_task")
                days_cols=st.columns(4)
                with days_cols[0]: d_sat=st.checkbox("السبت", key="d_sat")
                with days_cols[1]: d_sun=st.checkbox("الأحد", key="d_sun")
                with days_cols[2]: d_mon=st.checkbox("الاثنين", key="d_mon")
                with days_cols[3]: d_tue=st.checkbox("الثلاثاء", key="d_tue")
                days_cols2=st.columns(3)
                with days_cols2[0]: d_wed=st.checkbox("الأربعاء", key="d_wed")
                with days_cols2[1]: d_thu=st.checkbox("الخميس", key="d_thu")
                with days_cols2[2]: d_fri=st.checkbox("الجمعة", key="d_fri")

                active_task=st.checkbox("نشط", value=True, key="sch_active")
                if st.button("💾 حفظ دوام المهمة", use_container_width=True, type="primary"):
                    row_values=[
                        sch_task,
                        "نعم" if d_sat else "لا",
                        "نعم" if d_sun else "لا",
                        "نعم" if d_mon else "لا",
                        "نعم" if d_tue else "لا",
                        "نعم" if d_wed else "لا",
                        "نعم" if d_thu else "لا",
                        "نعم" if d_fri else "لا",
                        "نعم" if active_task else "لا",
                    ]
                    try:
                        records=schedule_sheet.get_all_records()
                        found_row=None
                        for i,r in enumerate(records):
                            if str(r.get("المهمة","")).strip()==sch_task:
                                found_row=i+2; break
                        if found_row:
                            schedule_sheet.update(f"A{found_row}:I{found_row}",[row_values])
                        else:
                            schedule_sheet.append_row(row_values, value_input_option="USER_ENTERED")
                        get_schedule_records.clear()
                        st.success("✅ تم حفظ جدول دوام المهمة")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ خطأ أثناء حفظ جدول الدوام: {e}")

            st.markdown("#### الجدول الحالي")
            try:
                records=get_schedule_records()
                if not records:
                    st.warning("لم يتم إدخال أي دوام أقسام حتى الآن.")
                else:
                    for r in records:
                        task=str(r.get("المهمة","")).strip()
                        active="نشط" if is_yes(r.get("نشط","")) or str(r.get("نشط","")).strip()=="" else "غير نشط"
                        days=[d for d in ["السبت","الأحد","الاثنين","الثلاثاء","الأربعاء","الخميس","الجمعة"] if is_yes(r.get(d,""))]
                        days_txt="، ".join(days) if days else "لا توجد أيام محددة"
                        st.markdown(f'<div class="audit-row"><b>{task}</b><br><small>{days_txt} — {active}</small></div>',unsafe_allow_html=True)
            except Exception as e:
                st.error(f"خطأ: {e}")

        # ── تنظيف التكرارات ───────────────────────────────────────
        elif admin_tab=="🧹 تنظيف التكرارات":
            st.markdown("#### 🧹 تنظيف تكرار سجلات sheet1")
            st.info("يفحص النظام التكرار في نفس اليوم فقط حسب: التاريخ + الرقم الشخصي. اختاري التاريخ أولاً، ثم افتحي السهم للمعلمة واحذفي الصفوف الزائدة.")

            if st.button("🔍 فحص التكرارات الآن", use_container_width=True, type="primary"):
                st.session_state.duplicate_groups = find_duplicate_attendance_groups()

            duplicate_groups = st.session_state.get("duplicate_groups", None)
            if duplicate_groups is None:
                duplicate_groups = find_duplicate_attendance_groups()
                st.session_state.duplicate_groups = duplicate_groups

            if not duplicate_groups:
                st.success("✅ لا توجد سجلات مكررة حالياً في sheet1.")
            else:
                # ترتيب التكرارات حسب التاريخ حتى يكون واضح أن التكرار داخل نفس اليوم
                dates_available = sorted(set(k[0] for k in duplicate_groups.keys()), reverse=True)
                selected_date_filter = st.selectbox(
                    "اختاري التاريخ لعرض تكرارات نفس اليوم",
                    ["كل التواريخ"] + dates_available,
                    key="dup_date_filter"
                )

                filtered_groups = {
                    k: v for k, v in duplicate_groups.items()
                    if selected_date_filter == "كل التواريخ" or k[0] == selected_date_filter
                }

                st.warning(f"⚠️ تم العثور على {len(filtered_groups)} حالة تكرار حسب التاريخ + الرقم الشخصي.")

                # نجمع العرض تحت كل تاريخ
                groups_by_date = {}
                for (dup_date, dup_id), rows_list in filtered_groups.items():
                    groups_by_date.setdefault(dup_date, []).append((dup_id, rows_list))

                for dup_date in sorted(groups_by_date.keys(), reverse=True):
                    with st.expander(f"📅 تاريخ {dup_date} — عدد حالات التكرار: {len(groups_by_date[dup_date])}", expanded=(selected_date_filter != "كل التواريخ")):
                        for group_no, (dup_id, rows_list) in enumerate(groups_by_date[dup_date], start=1):
                            first_row = rows_list[0][1]
                            emp_name = first_row.get("الاسم الثلاثي", "") or first_row.get("الاسم", "")
                            task_name = first_row.get("المهمة", "")

                            with st.expander(f"🔁 {emp_name} — #{dup_id} — عدد السجلات في نفس اليوم: {len(rows_list)}", expanded=False):
                                options = []
                                option_map = {}
                                st.caption("اختاري فقط الصفوف الزائدة للحذف. انتبهي: الحذف من Google Sheet نهائي.")

                                for row_num, r in rows_list:
                                    label = f"صف {row_num} | التاريخ: {dup_date} | حضور: {r.get('وقت الحضور','—') or '—'} | انصراف: {r.get('وقت الانصراف','—') or '—'} | مهمة: {r.get('المهمة','—')}"
                                    options.append(label)
                                    option_map[label] = row_num
                                    st.markdown(f"""
                                    <div class="audit-row">
                                        <b>صف {row_num}</b><br>
                                        التاريخ: {dup_date}<br>
                                        الاسم: {r.get('الاسم الثلاثي','')}<br>
                                        الرقم الشخصي: {r.get('الرقم الشخصي','')}<br>
                                        المدرسة: {r.get('اسم المدرسة', r.get('المدرسة',''))}<br>
                                        المهمة: {r.get('المهمة','')}<br>
                                        وقت الحضور: {r.get('وقت الحضور','') or '—'}<br>
                                        وقت الانصراف: {r.get('وقت الانصراف','') or '—'}<br>
                                        سبب التأخير: {r.get('سبب التأخير','') or '—'}<br>
                                        سبب الانصراف: {r.get('سبب الانصراف','') or '—'}
                                    </div>
                                    """, unsafe_allow_html=True)

                                selected = st.multiselect(
                                    "حددي الصفوف التي تريدين حذفها",
                                    options,
                                    key=f"dup_select_{dup_date}_{dup_id}_{group_no}"
                                )
                                confirm_delete = st.checkbox(
                                    "أؤكد حذف الصفوف المحددة من sheet1",
                                    key=f"dup_confirm_{dup_date}_{dup_id}_{group_no}"
                                )
                                if st.button("🗑️ حذف الصفوف المحددة", key=f"dup_delete_{dup_date}_{dup_id}_{group_no}", use_container_width=True):
                                    if not selected:
                                        st.error("❌ لم تختاري أي صف للحذف.")
                                    elif not confirm_delete:
                                        st.error("❌ يجب تفعيل خانة التأكيد قبل الحذف.")
                                    elif len(selected) >= len(rows_list):
                                        st.error("❌ لا يمكن حذف كل سجلات المعلمة لهذا اليوم. اتركي سجل واحد صحيح على الأقل.")
                                    else:
                                        row_numbers = sorted([option_map[x] for x in selected], reverse=True)
                                        try:
                                            for rn in row_numbers:
                                                sheet.delete_rows(rn)
                                            log_audit(dup_id, emp_name, "حذف تكرار", f"التاريخ:{dup_date}|الصفوف المحذوفة:{row_numbers}|المهمة:{task_name}")
                                            clear_caches()
                                            st.session_state.duplicate_groups = find_duplicate_attendance_groups()
                                            st.success(f"✅ تم حذف {len(row_numbers)} صف/صفوف بنجاح من تكرارات تاريخ {dup_date}.")
                                            st.rerun()
                                        except Exception as e:
                                            st.error(f"❌ تعذر حذف الصفوف: {e}")

        # ── تعديل سجل ────────────────────────────────────────────
        elif admin_tab=="✏️ تعديل سجل":
            search_id=st.text_input("الرقم الشخصي",key="edit_id")
            search_date=st.date_input("التاريخ",value=now_bh().date(),key="edit_date")
            if st.button("بحث",key="btn_search"):
                data=get_sheet_data(); idx,row=find_today_row(data,str(search_date),search_id)
                if row: st.session_state.edit_row_idx=idx; st.session_state.edit_row=row
                else: st.error("لا يوجد سجل"); st.session_state.edit_row=None
            if st.session_state.get("edit_row"):
                row=st.session_state.edit_row; idx=st.session_state.edit_row_idx
                st.info(f"السجل: {row.get('الاسم الثلاثي','')} — {row.get('التاريخ','')}")
                new_att=st.text_input("وقت الحضور",value=row.get("وقت الحضور",""),key="new_att")
                new_dep=st.text_input("وقت الانصراف",value=row.get("وقت الانصراف",""),key="new_dep")
                edit_reason=st.text_input("سبب التعديل (مطلوب)",key="edit_reason")
                if st.button("حفظ التعديل",use_container_width=True):
                    if not edit_reason.strip(): st.error("سبب التعديل مطلوب")
                    else:
                        safe_update(sheet,idx,COL_ATTEND,new_att); safe_update(sheet,idx,COL_DEPART,new_dep)
                        row["وقت الحضور"] = new_att
                        row["وقت الانصراف"] = new_dep
                        update_work_calculation(idx, row)
                        log_audit(search_id,row.get("الاسم الثلاثي",""),"تعديل أدمن",f"حضور:{row.get('وقت الحضور','')}→{new_att}|انصراف:{row.get('وقت الانصراف','')}→{new_dep}|السبب:{edit_reason}")
                        clear_caches(); st.success("✅ تم الحفظ"); st.session_state.edit_row=None

        # ── تسجيل يدوي ──────────────────────────────────────────
        elif admin_tab=="➕ تسجيل يدوي":
            st.markdown("#### ➕ تسجيل حضور/انصراف يدوي")
            st.info("يتم التسجيل اليدوي بنفس ترتيب أعمدة sheet1 بدون لخبطة: التاريخ، اليوم، المدرسة، المهمة، دعم، الاسم، الرقم، وقت الحضور...")

            m_id=ar_to_en_digits(st.text_input("الرقم الشخصي",key="mid")).strip()
            m_date=st.date_input("التاريخ",value=now_bh().date(),key="mdate")
            m_att=st.text_input("وقت الحضور",value="07:00:00",key="matt")
            m_dep=st.text_input("وقت الانصراف (اختياري)",key="mdep")
            m_note=st.text_input("سبب الإضافة اليدوية (مطلوب)",key="mnote")

            if st.button("تسجيل يدوي",use_container_width=True,type="primary"):
                if not m_id:
                    st.error("❌ الرقم الشخصي مطلوب")
                elif not m_note.strip():
                    st.error("❌ سبب الإضافة اليدوية مطلوب")
                else:
                    emp=validate_employee(m_id)
                    if not emp:
                        st.error("❌ الرقم غير موجود في القائمة البيضاء")
                    else:
                        date_str=str(m_date)
                        day_name=m_date.strftime("%A")
                        task=str(emp.get("المهمة","")).strip()

                        # تحديد قيمة عمود دعم من القائمة البيضاء أو من اسم المهمة
                        support_raw=str(emp.get("دعم","")).strip()
                        support_value="نعم" if support_raw in ["نعم","yes","Yes","TRUE","true","1"] or "دعم" in task else "لا"
                        full_name=normalize_name(emp.get("الاسم",""))

                        row_data=[
                            date_str,                       # A التاريخ
                            day_name,                       # B اليوم
                            emp.get("المدرسة",""),          # C اسم المدرسة
                            task,                           # D المهمة
                            support_value,                  # E دعم
                            full_name,                      # F الاسم الثلاثي
                            m_id,                           # G الرقم الشخصي
                            m_att,                          # H وقت الحضور
                            f"[يدوي] {m_note.strip()}",     # I سبب التأخير
                            m_dep,                          # J وقت الانصراف
                            "",                             # K سبب الانصراف
                            "",                             # L خروج استئذان
                            "",                             # M عودة
                            ""                              # N محاولة
                        ]

                        existing_matches = find_daily_rows_fresh(date_str, m_id)
                        existing_idx, existing_row = pick_main_daily_row(existing_matches)
                        if existing_idx and existing_row and str(existing_row.get("وقت الحضور", "")).strip():
                            st.error(f"❌ يوجد سجل حضور مسبق لهذا الرقم في تاريخ {date_str} الساعة {existing_row.get('وقت الحضور','')}. لا يمكن إضافة سجل يدوي مكرر.")
                        elif len(existing_matches) > 1:
                            st.error("❌ يوجد تكرار سابق لهذا الرقم في نفس التاريخ. نظّفي التكرارات أولاً من قسم تنظيف التكرارات.")
                        elif existing_idx:
                            safe_update(sheet,existing_idx,COL_ATTEND,m_att)
                            safe_update(sheet,existing_idx,COL_LATE_REASON,f"[يدوي] {m_note.strip()}")
                            safe_update(sheet,existing_idx,COL_DEPART,m_dep)
                            existing_row["وقت الحضور"] = m_att
                            existing_row["وقت الانصراف"] = m_dep
                            update_work_calculation(existing_idx,existing_row)
                            log_audit(m_id,full_name,"تسجيل يدوي",f"تحديث سجل موجود|التاريخ:{date_str}|حضور:{m_att}|انصراف:{m_dep}|السبب:{m_note.strip()}")
                            clear_caches()
                            st.success("✅ تم تحديث السجل الموجود بدون إنشاء تكرار")
                        else:
                            ok=safe_append(sheet,row_data)
                            if ok:
                                try:
                                    data_after=get_sheet_data_fresh()
                                    idx_after,row_after=find_today_row(data_after,date_str,m_id)
                                    if idx_after:
                                        update_work_calculation(idx_after,row_after)
                                except Exception:
                                    pass
                                log_audit(
                                    m_id,
                                    full_name,
                                    "تسجيل يدوي",
                                    f"التاريخ:{date_str}|حضور:{m_att}|انصراف:{m_dep}|السبب:{m_note.strip()}"
                                )
                                clear_caches()
                                st.success("✅ تم التسجيل اليدوي بنجاح وبالأعمدة الصحيحة")
                            else:
                                st.error("❌ تعذر حفظ التسجيل اليدوي، حاولي مرة أخرى")

        # ── القائمة البيضاء ──────────────────────────────────────
        elif admin_tab=="📋 القائمة البيضاء":
            st.markdown("#### إضافة موظفة")
            wl_id=st.text_input("الرقم الشخصي",key="wlid")
            wl_name=st.text_input("الاسم",key="wlname")
            wl_school=st.selectbox("المدرسة",schools,key="wlschool")
            wl_task=st.selectbox("المهمة",TASKS_ALL,key="wltask")
            wl_job=st.selectbox("المسمى الوظيفي",JOB_TITLES,key="wljob")
            if st.button("إضافة",use_container_width=True):
                if not wl_id.strip() or not wl_name.strip(): st.error("الرقم والاسم مطلوبان")
                else:
                    ok=safe_append(whitelist_sheet,[ar_to_en_digits(wl_id).strip(),normalize_name(wl_name),wl_school,wl_task,"نعم" if "دعم" in wl_task else "لا","","",wl_job,"نعم"])
                    get_whitelist.clear()
                    if ok: st.success("✅ تمت الإضافة")
                    else: st.error("❌ تعذرت الإضافة")
            st.markdown("#### الموظفات المسجّلات")
            wl_all=get_whitelist()
            for eid,emp in wl_all.items():
                st.markdown(f'<div class="audit-row"><b>{emp.get("الاسم","")}</b> — #{eid} — {emp.get("المدرسة","")}</div>',unsafe_allow_html=True)

        # ── محاولات التسجيل ─────────────────────────────────────
        elif admin_tab=="🚫 محاولات التسجيل":
            try:
                records=attempts_sheet.get_all_records()
                today_att=[r for r in records if r.get("التاريخ")==today_str]
                st.metric("محاولات اليوم",len(today_att))
                for r in reversed(today_att[-50:]):
                    st.markdown(f'<div class="warn-row">⚠️ {r.get("اسم_المقفول_عليه","")} ({r.get("الرقم_المقفول_عليه","")}) ← حاول: {r.get("اسم_المحاول","")} — {r.get("وقت_المحاولة","")}</div>',unsafe_allow_html=True)
            except Exception as e: st.error(f"خطأ: {e}")

        # ── تجاوز الموقع ────────────────────────────────────────
        elif admin_tab=="📡 تجاوز الموقع":
            st.markdown("#### 📡 إدارة تجاوز الموقع")
            active,end_dt=get_location_override()

            if active and end_dt:
                remaining_seconds = max(0, int((end_dt - now_bh()).total_seconds()))
                remaining_minutes = remaining_seconds // 60
                st.success(f"✅ تجاوز الموقع مفعّل حالياً حتى الساعة {end_dt.strftime('%H:%M')}")
                st.info(f"المتبقي تقريباً: {remaining_minutes} دقيقة. الموظفات يمكنهن التسجيل بدون تحديد الموقع خلال هذه المدة.")

                if st.button("🔴 تعطيل تجاوز الموقع الآن", use_container_width=True, type="primary"):
                    ok = disable_location_override()
                    if ok:
                        st.success("✅ تم تعطيل تجاوز الموقع.")
                    st.rerun()

            else:
                st.warning("⚠️ تجاوز الموقع غير مفعّل حالياً.")
                duration=st.selectbox("مدة تفعيل تجاوز الموقع بالدقائق",[30,60,90,120,180], key="override_duration")
                reason=st.text_input("سبب تفعيل تجاوز الموقع", key="override_reason")

                if st.button("🟢 تفعيل تجاوز الموقع", use_container_width=True, type="primary"):
                    if not reason.strip():
                        st.error("❌ السبب مطلوب.")
                    else:
                        ok,end_dt=set_location_override(duration,reason.strip())
                        if ok and end_dt:
                            # نتحقق مباشرة من الشيت بعد الحفظ حتى نضمن أن الزر سيتغير للتعطيل
                            get_settings_records.clear()
                            active_check,end_check=get_location_override()
                            if active_check:
                                st.success(f"✅ تم تفعيل تجاوز الموقع حتى الساعة {end_check.strftime('%H:%M')}")
                                st.rerun()
                            else:
                                st.error("❌ تم الحفظ لكن لم يظهر التفعيل. تأكدي من شيت إعدادات_النظام أن الأعمدة هي: المفتاح، القيمة، تاريخ_الانتهاء، ملاحظات.")
                        else:
                            st.error("❌ تعذر تفعيل تجاوز الموقع.")

        # ── فتح قفل جهاز ────────────────────────────────────────
        elif admin_tab=="🔓 فتح قفل جهاز":
            st.info("استخدمي هذه الخاصية عند وجود سبب رسمي.")
            unlock_id=st.text_input("الرقم الشخصي المقفول عليه")
            if st.button("حذف قفل اليوم لهذا الرقم",use_container_width=True):
                try:
                    records=device_sheet.get_all_records(); deleted=False
                    for i,r in enumerate(records):
                        if str(r.get("التاريخ","")).strip()==today_str and str(r.get("الرقم الشخصي","")).strip()==unlock_id.strip():
                            device_sheet.delete_rows(i+2); deleted=True; break
                    get_device_locks.clear()
                    if deleted: log_audit(unlock_id,"—","فتح قفل أدمن",f"فتح قفل الرقم {unlock_id} ليوم {today_str}"); st.success("✅ تم حذف القفل.")
                    else: st.warning("لم يتم العثور على قفل لهذا الرقم اليوم.")
                except Exception as e: st.error(f"خطأ: {e}")

        # ── سجل التدقيق ─────────────────────────────────────────
        elif admin_tab=="🔍 سجل التدقيق":
            try:
                audit_data=audit_sheet.get_all_records()
                for r in reversed(audit_data[-30:]):
                    st.markdown(f'<div class="audit-row"><b>{r.get("نوع العملية","")}</b> — {r.get("الوقت","")}<br><small>{r.get("المستخدم","")} (#{r.get("الرقم الشخصي","")}) — {r.get("التفاصيل","")}</small></div>',unsafe_allow_html=True)
            except Exception as e: st.error(f"خطأ: {e}")

        # ── تقرير الأجهزة ────────────────────────────────────────
        elif admin_tab=="⚠️ تقرير الأجهزة":
            try:
                audit_data=audit_sheet.get_all_records(); device_map={}
                for r in audit_data:
                    if r.get("التاريخ")==today_str and r.get("نوع العملية")=="تسجيل حضور":
                        fp_key=str(r.get("بصمة الجهاز",""))
                        if fp_key not in device_map: device_map[fp_key]=[]
                        name=f"{r.get('المستخدم','')} (#{r.get('الرقم الشخصي','')})"
                        if name not in device_map[fp_key]: device_map[fp_key].append(name)
                found=False
                for fp_key,names in device_map.items():
                    if len(names)>1:
                        found=True
                        st.markdown(f'<div class="warn-row">⚠️ جهاز واحد سجّل لـ {len(names)} موظفات: {"، ".join(names)}</div>',unsafe_allow_html=True)
                if not found: st.success("✅ لا يوجد تسجيل مشبوه اليوم")
            except Exception as e: st.error(f"خطأ: {e}")

        if st.button("🚪 تسجيل خروج الأدمن",use_container_width=True):
            st.session_state.admin_logged_in=False; st.session_state.admin_last_active=None; st.rerun()


# ─── دعم واتساب للموظفة ───────────────────────────────────────
if mode == "👤 موظفة" and st.session_state.get("emp_data"):
    try:
        emp = st.session_state.get("emp_data") or {}
        emp_id_support = str(emp.get("الرقم الشخصي", "") or "").strip()
        data_support = get_sheet_data()
        _, support_row = find_today_row(data_support, today_str, emp_id_support) if emp_id_support else (None, None)

        name_support = emp.get("الاسم", "") or (support_row.get("الاسم الثلاثي", "") if support_row else "")
        school_support = emp.get("المدرسة", "") or (support_row.get("اسم المدرسة", "") if support_row else "")
        task_support = emp.get("المهمة", "") or (support_row.get("المهمة", "") if support_row else "")
        attend_support = support_row.get("وقت الحضور", "—") if support_row else "—"
        depart_support = support_row.get("وقت الانصراف", "—") if support_row else "—"
        exit_support = support_row.get("خروج استئذان", "—") if support_row else "—"
        return_support = support_row.get("عودة", "—") if support_row else "—"

        support_msg = f"""مرحباً 👋

لدي مشكلة في نظام الحضور والانصراف:

الاسم: {name_support}
الرقم الشخصي: {emp_id_support}
المدرسة: {school_support}
المهمة: {task_support}
التاريخ: {today_str}
الوقت الحالي: {now_bh().strftime('%H:%M:%S')}

بيانات اليوم:
وقت الحضور: {attend_support or '—'}
وقت الانصراف: {depart_support or '—'}
خروج استئذان: {exit_support or '—'}
عودة من استئذان: {return_support or '—'}

تفاصيل المشكلة:
"""
        wa_link = "https://wa.me/97333738668?text=" + urllib.parse.quote(support_msg)

        st.markdown("---")
        with st.container(border=True):
            st.markdown('<div class="card-title">🆘 الدعم الفني</div>', unsafe_allow_html=True)
            st.caption("إذا واجهتك مشكلة، اضغطي الزر وسيُفتح واتساب برسالة جاهزة تحتوي بياناتك. اكتبي تفاصيل المشكلة فقط ثم أرسليها.")
            st.link_button("📞 تواصل مع الأدمن عبر واتساب", wa_link, use_container_width=True)
    except Exception:
        pass

# ─── Footer ─────────────────────────────────────────────────────
st.markdown("""
<div class="footer-bar">
    <span>تصميم وبرمجة: <span class="hl">أ. عفاف حسين</span></span>
    <span>رئيسة المركز: <span class="hl">أ. خلود يعقوب بدو</span></span>
</div>
""", unsafe_allow_html=True)





