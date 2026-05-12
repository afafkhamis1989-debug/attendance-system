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
from io import BytesIO
import pandas as pd

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
ADMIN_PASSWORD = st.secrets.get("ADMIN_PASSWORD", "Afaf1234")
DEVICE_COOLDOWN_MINUTES = 10  # لم يعد مستخدماً كمهلة أساسية؛ القفل الآن طوال اليوم إلا إذا عطله الأدمن
DEVICE_LOCK_STRICT_FULL_DAY = True
APP_URL = "ضعوا رابط النظام هنا"

# أعمدة sheet1
COL_DATE=1; COL_DAY=2; COL_SCHOOL=3; COL_TASK=4; COL_SUPPORT=5
COL_NAME=6; COL_ID=7; COL_ATTEND=8; COL_LATE_REASON=9
COL_DEPART=10; COL_DEPART_REASON=11; COL_EXIT=12; COL_RETURN=13; COL_ATTEMPT=14
COL_WORK_START=15; COL_EXPECTED_END=16; COL_WORK_HOURS=17; COL_EXTRA_HOURS=18
COL_WORK_STATUS=19; COL_DAILY_TYPE=20; COL_AUTO_CLOSE=21; COL_CARE_CONF=22; COL_REG_TYPE=23

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
/* كرت إرشادات الموقع */
.gps-steps-box{background:#fff8e8;border:1px solid #f0c36d;border-radius:18px;padding:16px 18px;margin:12px 0;color:#5b3a05;text-align:right!important;}
.gps-steps-title{font-size:19px;font-weight:900;color:#6b4300;margin-bottom:10px;text-align:center!important;}
.gps-step{display:flex;gap:10px;align-items:flex-start;margin:8px 0;font-size:15px;font-weight:800;color:#173763;}
.gps-step-num{background:#185FA5;color:white;border-radius:50%;min-width:26px;height:26px;display:inline-flex;align-items:center;justify-content:center;font-weight:900;}
.gps-click-hint{background:#edf8ef;border:1px solid #9bd0a8;border-radius:16px;padding:14px 16px;margin:10px 0 10px 0;color:#1f6b2a;font-weight:900;text-align:center!important;font-size:17px;}
.no-gps-approved{background:#fff6e7;border:1px solid #eba83a;border-radius:14px;padding:12px 14px;color:#7a4700;font-weight:800;margin-top:10px;}
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
        "device_exceptions": _get_or_create("استثناءات_قفل_الجهاز", ["الرقم الشخصي","الاسم","تاريخ_الانتهاء","نشط","ملاحظات","تاريخ_الإضافة"]),
        "trusted_devices": _get_or_create("الأجهزة_الموثوقة", ["بصمة الجهاز","اسم الجهاز","نشط","ملاحظات","تاريخ الاعتماد","آخر استخدام"]),
        "attempts":    _get_or_create("محاولات_تسجيل_باسم_آخر",  ["التاريخ","بصمة الجهاز","الرقم_المقفول_عليه","اسم_المقفول_عليه","الرقم_المحاول","اسم_المحاول","وقت_المحاولة","ملاحظات"]),
        "settings":    _get_or_create("إعدادات_النظام",           ["المفتاح","القيمة","تاريخ_الانتهاء","ملاحظات"]),
        "audit":       _get_or_create("سجل_التدقيق",              ["التاريخ","الوقت","المستخدم","الرقم الشخصي","نوع العملية","التفاصيل","بصمة الجهاز"]),
        "absence":     _get_or_create("سجل_الغياب",               ["التاريخ","اليوم","الرقم الشخصي","الاسم","المدرسة","المهمة","سبب الغياب","ملاحظات","سجّله"]),
        "manual_requests": _get_or_create("طلبات_التسجيل_اليدوي", ["تاريخ الطلب","وقت الطلب","الرقم الشخصي","الاسم","المدرسة","المهمة","نوع الطلب","وقت الحضور الفعلي","وقت الانصراف الفعلي","نوع المشكلة","ملاحظات","الحالة","بصمة الجهاز","وقت الاعتماد","اعتمده"]),
        "time_permits":    _get_or_create("تصاريح_الوقت_اليدوي",   ["تاريخ الإضافة","الرقم الشخصي","نوع التصريح","تاريخ البداية","تاريخ النهاية","وقت الفتح","وقت الإغلاق","نشط","ملاحظات","أضافه"]),
    }

_sheets         = get_all_sheets()
spreadsheet     = _sheets["spreadsheet"]
sheet           = _sheets["sheet"]
whitelist_sheet = _sheets["whitelist"]
device_sheet    = _sheets["device"]
device_exceptions_sheet = _sheets["device_exceptions"]
trusted_devices_sheet = _sheets["trusted_devices"]
attempts_sheet  = _sheets["attempts"]
settings_sheet  = _sheets["settings"]
audit_sheet     = _sheets["audit"]
absence_sheet   = _sheets["absence"]
manual_requests_sheet = _sheets["manual_requests"]
time_permits_sheet    = _sheets["time_permits"]

@st.cache_data(ttl=60)
def get_time_permits():
    try: return time_permits_sheet.get_all_records()
    except: return []

def get_active_permit(emp_id):
    """يرجع التصريح النشط للموظفة إذا وجد، مع مراعاة نطاق التاريخ ونافذة الوقت."""
    now     = now_bh()
    today   = now.strftime("%Y-%m-%d")
    now_t   = now.strftime("%H:%M")
    permits = get_time_permits()
    for p in permits:
        if str(p.get("نشط","")).strip() not in ["نعم","yes","1","TRUE","true"]:
            continue
        p_id    = str(p.get("الرقم الشخصي","")).strip()
        # يطابق الموظفة أو كل الموظفات
        if p_id not in ["","الكل","*"] and p_id != str(emp_id).strip():
            continue
        # نطاق التاريخ
        d_from  = str(p.get("تاريخ البداية","")).strip()
        d_to    = str(p.get("تاريخ النهاية","")).strip()
        if d_from and today < d_from: continue
        if d_to   and today > d_to:   continue
        # نافذة الوقت (اختيارية)
        t_open  = str(p.get("وقت الفتح","")).strip()
        t_close = str(p.get("وقت الإغلاق","")).strip()
        if t_open  and now_t < t_open:  continue
        if t_close and now_t > t_close: continue
        return p
    return None

def has_time_permit(emp_id, permit_type="كليهما"):
    p = get_active_permit(emp_id)
    if not p: return False
    p_type = str(p.get("نوع التصريح","")).strip()
    return p_type in ["كليهما", permit_type] or permit_type == "كليهما"

def get_permit_dates(emp_id):
    """يرجع (تاريخ البداية, تاريخ النهاية) للتصريح النشط."""
    p = get_active_permit(emp_id)
    if not p: return None, None
    return str(p.get("تاريخ البداية","")).strip(), str(p.get("تاريخ النهاية","")).strip()

def add_time_permit(emp_id, permit_type, date_from, date_to, time_open="", time_close="", note=""):
    today = now_bh().strftime("%Y-%m-%d")
    time_permits_sheet.append_row([today, emp_id, permit_type, date_from, date_to, time_open, time_close, "نعم", note, "أدمن"])
    get_time_permits.clear()

def revoke_time_permit_row(row_num):
    time_permits_sheet.update_cell(row_num, 8, "لا")
    get_time_permits.clear()
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
    "حالة الدوام","نوع الدوام اليومي","إغلاق تلقائي","تأكيد الرعاية","نوع التسجيل"
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

def ls_clear_emp_data():
    """يمسح بيانات الموظفة المحفوظة في LocalStorage."""
    for key in ["saved_id","saved_name","saved_school","saved_section","saved_support","saved_date"]:
        ls_set(key, "", f"clear_{key}")

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
    try: return device_sheet.get_all_records()[-500:]
    except: return []

@st.cache_data(ttl=60, show_spinner=False)
def get_device_exceptions():
    try: return device_exceptions_sheet.get_all_records()
    except: return []

@st.cache_data(ttl=60, show_spinner=False)
def get_trusted_devices():
    try: return trusted_devices_sheet.get_all_records()
    except: return []

@st.cache_data(ttl=60, show_spinner=False)
def get_settings_records():
    try: return settings_sheet.get_all_records()
    except: return []

def get_system_setting(key, default=""):
    """قراءة قيمة من ورقة إعدادات_النظام."""
    try:
        for r in get_settings_records():
            if str(r.get("المفتاح", "")).strip() == str(key).strip():
                return str(r.get("القيمة", default)).strip()
    except Exception:
        pass
    return default


def set_system_setting(key, value, note=""):
    """حفظ/تحديث قيمة في ورقة إعدادات_النظام."""
    try:
        records = settings_sheet.get_all_records()
        row_found = None
        for i, r in enumerate(records):
            if str(r.get("المفتاح", "")).strip() == str(key).strip():
                row_found = i + 2
                break
        row_values = [str(key), str(value), "", note]
        if row_found:
            settings_sheet.update(f"A{row_found}:D{row_found}", [row_values], value_input_option="USER_ENTERED")
        else:
            safe_append(settings_sheet, row_values)
        get_settings_records.clear()
        return True
    except Exception as e:
        st.error(f"❌ تعذر حفظ الإعداد: {e}")
        return False


def manual_requests_enabled():
    """طلبات التسجيل اليدوي من واجهة الموظفة مفعلة افتراضيًا، ويمكن تعطيلها من الأدمن."""
    val = get_system_setting("manual_requests_enabled", "true").lower()
    return val in ["true", "1", "yes", "نعم", "مفعل", "on", ""]

@st.cache_data(ttl=60, show_spinner=False)
def get_manual_requests():
    try: return manual_requests_sheet.get_all_records()
    except: return []

def manual_request_exists_today(emp_id, req_type):
    """يمنع تكرار نفس نوع الطلب لنفس الرقم في نفس التاريخ فقط.
    يسمح بحضور ثم انصراف، لكنه يمنع حضورين أو انصرافين في نفس اليوم.
    """
    emp_id = ar_to_en_digits(emp_id).strip()
    req_type = str(req_type or "").strip()
    today = now_bh().strftime("%Y-%m-%d")
    try:
        for r in get_manual_requests():
            status = str(r.get("الحالة", "")).strip()
            if status == "مرفوض":
                continue
            if str(r.get("تاريخ الطلب", "")).strip() == today and \
               str(r.get("الرقم الشخصي", "")).strip() == emp_id and \
               str(r.get("نوع الطلب", "")).strip() == req_type:
                return True, r
    except Exception:
        pass
    return False, None

@st.cache_data(ttl=120, show_spinner=False)
def get_schedule_records():
    try: return schedule_sheet.get_all_records()
    except: return []

@st.cache_data(ttl=60, show_spinner=False)
def get_daily_schedule_records():
    try: return daily_schedule_sheet.get_all_records()
    except: return []

def clear_caches():
    get_sheet_data.clear(); get_device_locks.clear(); get_device_exceptions.clear(); get_trusted_devices.clear(); get_settings_records.clear(); get_schedule_records.clear(); get_daily_schedule_records.clear(); get_manual_requests.clear(); get_time_permits.clear()


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
    if not att or att <= time(7, 5, 30):
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
    if not att or att <= time(7, 5, 30):
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
    grace_end = combine_date_time(date_str, time(7, 5, 30))
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


def get_device_lock_global_override():
    """تعطيل قفل الجهاز للجميع لمدة محددة من إعدادات_النظام."""
    try:
        for r in get_settings_records():
            key = str(r.get("المفتاح", "")).strip()
            if key == "device_lock_override":
                val = str(r.get("القيمة", "")).strip().lower()
                end_dt = parse_bahrain_datetime(r.get("تاريخ_الانتهاء", ""))
                if val in ["true", "1", "yes", "نعم"] and end_dt and now_bh() < end_dt:
                    return True, end_dt
                if val in ["true", "1", "yes", "نعم"] and end_dt and now_bh() >= end_dt:
                    disable_device_lock_global_override()
                    return False, None
    except Exception:
        pass
    return False, None

def set_device_lock_global_override(minutes, note=""):
    end_dt = now_bh() + timedelta(minutes=int(minutes))
    end_str = end_dt.strftime("%Y-%m-%d %H:%M:%S")
    try:
        records = settings_sheet.get_all_records()
        row_found = None
        for i, r in enumerate(records):
            if str(r.get("المفتاح", "")).strip() == "device_lock_override":
                row_found = i + 2
                break
        if row_found:
            settings_sheet.update(f"A{row_found}:D{row_found}", [["device_lock_override", "true", end_str, note]])
        else:
            safe_append(settings_sheet, ["device_lock_override", "true", end_str, note])
        get_settings_records.clear()
        return True, end_dt
    except Exception as e:
        st.error(f"❌ خطأ أثناء تعطيل قفل الجهاز للجميع: {e}")
        return False, None

def disable_device_lock_global_override():
    try:
        records = settings_sheet.get_all_records()
        found = False
        for i, r in enumerate(records):
            if str(r.get("المفتاح", "")).strip() == "device_lock_override":
                settings_sheet.update(f"A{i+2}:D{i+2}", [["device_lock_override", "false", "", "تم الإيقاف"]])
                found = True
                break
        if not found:
            safe_append(settings_sheet, ["device_lock_override", "false", "", "تم الإيقاف"])
        get_settings_records.clear()
        return True
    except Exception as e:
        st.error(f"❌ خطأ أثناء تفعيل قفل الجهاز: {e}")
        return False

def employee_has_device_exception(emp_id):
    emp_id = str(emp_id or "").strip()
    if not emp_id:
        return False, None
    try:
        for r in get_device_exceptions():
            if str(r.get("الرقم الشخصي", "")).strip() != emp_id:
                continue
            if not is_yes(r.get("نشط", "")):
                continue
            end_dt = parse_bahrain_datetime(r.get("تاريخ_الانتهاء", ""))
            if end_dt and now_bh() < end_dt:
                return True, end_dt
            if end_dt and now_bh() >= end_dt:
                # الاستثناء منتهي، لا نعتمده
                continue
    except Exception:
        pass
    return False, None

def add_device_exception_for_employee(emp_id, emp_name, minutes, note=""):
    end_dt = now_bh() + timedelta(minutes=int(minutes))
    try:
        safe_append(device_exceptions_sheet, [
            str(emp_id).strip(),
            str(emp_name or "").strip(),
            end_dt.strftime("%Y-%m-%d %H:%M:%S"),
            "نعم",
            note,
            now_bh().strftime("%Y-%m-%d %H:%M:%S")
        ])
        get_device_exceptions.clear()
        return True, end_dt
    except Exception as e:
        st.error(f"❌ خطأ أثناء إضافة الاستثناء: {e}")
        return False, None

def disable_device_exception_for_employee(emp_id):
    emp_id = str(emp_id or "").strip()
    try:
        records = device_exceptions_sheet.get_all_records()
        changed = 0
        for i, r in enumerate(records):
            if str(r.get("الرقم الشخصي", "")).strip() == emp_id and is_yes(r.get("نشط", "")):
                device_exceptions_sheet.update_cell(i+2, 4, "لا")
                changed += 1
        get_device_exceptions.clear()
        return changed
    except Exception as e:
        st.error(f"❌ تعذر تعطيل الاستثناء: {e}")
        return 0

def auto_cleanup_duplicate_attendance_for_emp(today, emp_id, reason="تنظيف تلقائي"):
    """تنظيف ذكي لتكرار نفس الموظفة في نفس التاريخ.
    يحتفظ بالأكمل، ثم الأقدم حضوراً، ويحذف الباقي. يرجع عدد الصفوف المحذوفة.
    """
    matches = find_daily_rows_fresh(today, emp_id)
    if len(matches) <= 1:
        return 0

    def score(item):
        row_num, r = item
        has_att = 1 if str(r.get("وقت الحضور", "")).strip() else 0
        has_dep = 1 if str(r.get("وقت الانصراف", "")).strip() else 0
        has_exit = 1 if str(r.get("خروج استئذان", "")).strip() else 0
        has_return = 1 if str(r.get("عودة", "")).strip() else 0
        att_time = str(r.get("وقت الحضور", "") or "99:99:99")
        # نفضل السجل الأكمل، ثم أقدم حضور، ثم أقل رقم صف
        return (has_att + has_dep + has_exit + has_return, has_dep, has_att, -row_num, att_time)

    # اختيار السجل الذي نبقيه: الأكمل، وإذا تساووا نحتفظ بالأقدم في الشيت
    keep_item = sorted(matches, key=lambda x: (- (1 if str(x[1].get("وقت الحضور", "")).strip() else 0)
                                               - (1 if str(x[1].get("وقت الانصراف", "")).strip() else 0)
                                               - (1 if str(x[1].get("خروج استئذان", "")).strip() else 0)
                                               - (1 if str(x[1].get("عودة", "")).strip() else 0), x[0]))[0]
    keep_row_num = keep_item[0]
    delete_rows = sorted([rn for rn, _ in matches if rn != keep_row_num], reverse=True)
    emp_name = keep_item[1].get("الاسم الثلاثي", "") or keep_item[1].get("الاسم", "")
    for rn in delete_rows:
        try:
            sheet.delete_rows(rn)
        except Exception:
            pass
    if delete_rows:
        log_audit(emp_id, emp_name, reason, f"التاريخ:{today}|تم الاحتفاظ بالصف:{keep_row_num}|حذف الصفوف:{delete_rows}")
        clear_caches()
    return len(delete_rows)

def is_current_device_trusted():
    """يتحقق هل بصمة المتصفح الحالية معتمدة كجهاز موثوق في المركز."""
    fp = get_device_fingerprint()
    try:
        for r in get_trusted_devices():
            if str(r.get("بصمة الجهاز", "")).strip() == fp and is_yes(r.get("نشط", "")):
                return True, r
    except Exception:
        pass
    return False, None

def approve_current_device_as_trusted(device_name, note=""):
    """اعتماد الجهاز الحالي كجهاز موثوق يسمح بتسجيل أكثر من موظفة."""
    fp = get_device_fingerprint()
    now_txt = now_bh().strftime("%Y-%m-%d %H:%M:%S")
    try:
        records = trusted_devices_sheet.get_all_records()
        found = None
        for i, r in enumerate(records, start=2):
            if str(r.get("بصمة الجهاز", "")).strip() == fp:
                found = i
                break
        row = [fp, device_name or "جهاز موثوق", "نعم", note, now_txt, now_txt]
        if found:
            trusted_devices_sheet.update(f"A{found}:F{found}", [row], value_input_option="USER_ENTERED")
        else:
            trusted_devices_sheet.append_row(row, value_input_option="USER_ENTERED")
        get_trusted_devices.clear()
        return True
    except Exception as e:
        st.error(f"❌ تعذر اعتماد الجهاز: {e}")
        return False

def disable_trusted_device(fp):
    try:
        records = trusted_devices_sheet.get_all_records()
        for i, r in enumerate(records, start=2):
            if str(r.get("بصمة الجهاز", "")).strip() == str(fp).strip():
                trusted_devices_sheet.update_cell(i, 3, "لا")
                get_trusted_devices.clear()
                return True
    except Exception as e:
        st.error(f"❌ تعذر تعطيل الجهاز: {e}")
    return False

def touch_trusted_device_usage():
    fp = get_device_fingerprint()
    try:
        records = trusted_devices_sheet.get_all_records()
        for i, r in enumerate(records, start=2):
            if str(r.get("بصمة الجهاز", "")).strip() == fp and is_yes(r.get("نشط", "")):
                trusted_devices_sheet.update_cell(i, 6, now_bh().strftime("%Y-%m-%d %H:%M:%S"))
                get_trusted_devices.clear()
                return
    except Exception:
        pass

def check_device_lock(today, emp_id, emp_name):
    """قفل الجهاز طوال اليوم: نفس بصمة المتصفح لا تسجل لأكثر من رقم في نفس التاريخ.
    يمكن للأدمن تعطيله للجميع أو استثناء رقم شخصي محدد.
    """
    # تعطيل عام مؤقت من الأدمن
    global_off, _ = get_device_lock_global_override()
    if global_off:
        return True

    # استثناء شخصي مؤقت من الأدمن
    emp_off, _ = employee_has_device_exception(emp_id)
    if emp_off:
        return True

    # الجهاز الموثوق يسمح بتسجيل أكثر من موظفة من نفس الجهاز الاحتياطي داخل المركز
    trusted, _trusted_row = is_current_device_trusted()
    if trusted:
        touch_trusted_device_usage()
        return True

    fp = get_device_fingerprint()
    locks = get_device_locks()
    for r in locks:
        if str(r.get("التاريخ", "")).strip() == today and str(r.get("بصمة الجهاز", "")).strip() == fp:
            locked_id = str(r.get("الرقم الشخصي", "")).strip()
            locked_name = str(r.get("الاسم", "")).strip()
            if locked_id and locked_id != str(emp_id).strip():
                safe_append(attempts_sheet, [
                    today, fp, locked_id, locked_name, emp_id, emp_name,
                    now_bh().strftime("%H:%M:%S"),
                    "محاولة تسجيل رقم آخر من نفس الجهاز — قفل اليوم الكامل"
                ])
                try:
                    data = get_sheet_data_fresh()
                    row_index, _ = find_today_row(data, today, locked_id)
                    if row_index:
                        safe_update(sheet, row_index, COL_ATTEMPT, "⚠️ محاولة تسجيل باسم آخر من نفس الجهاز")
                except Exception:
                    pass
                st.error("🚫 هذا الجهاز مسجّل اليوم باسم موظفة أخرى، ولا يمكن التسجيل برقم مختلف من نفس الجهاز.")
                st.warning("يمكن للأدمن فتح قفل الجهاز، أو تعطيل قفل الجهاز مؤقتًا للجميع، أو إضافة استثناء لهذا الرقم عند وجود سبب رسمي.")
                return False
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
    no_gps_allowed = bool(st.session_state.get("allow_no_gps_today", False))
    gps_status_note = ""
    if not st.session_state.get("location_allowed",False) and not override_active:
        if no_gps_allowed:
            gps_status_note = " | ⚠️ بدون تحقق GPS"
        else:
            st.error("❌ يجب تحديد الموقع أولاً، أو اختيار تعذر التحقق من الموقع، أو تفعيل تجاوز الموقع من الأدمن."); return False

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
    if gps_status_note and gps_status_note not in str(note or ""):
        note = (str(note or "").strip() + gps_status_note).strip()

    # تنظيف أي تكرار سابق لنفس الموظفة قبل العملية حتى لا يعتمد النظام آخر ضغطة بالخطأ
    try:
        auto_cleanup_duplicate_attendance_for_emp(today, emp_id, "تنظيف تلقائي قبل التسجيل")
    except Exception:
        pass

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
        att_is_late = now.time() > time(7, 5, 30)
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
                ok=safe_append(sheet,[today,day_name,school,task,is_support,full_name,emp_id,time_now,note,"","",implicit_exit_time,implicit_return_time,"","","","","","","","","","دعم مباشر" if is_support == "نعم" else "تسجيل ذاتي"])
                if not ok: st.error("❌ تعذر الحفظ، حاولي بعد قليل."); return False
        lock_device(today,emp_id,full_name)
        log_audit(emp_id,full_name,"تسجيل حضور",f"الوقت:{time_now}|السبب:{note or 'بدون'}" + ("|جهاز موثوق" if is_current_device_trusted()[0] else ""))
        # ثبّت البيانات
        st.session_state.data_locked_today=True
        st.session_state.locked_emp={"الرقم الشخصي":emp_id,"الاسم":full_name,"المدرسة":school,"المهمة":task,"دعم":is_support=="نعم","نشط":"نعم"}
        st.session_state.locked_date=today
        ls_set("saved_date",today,"sv_date"); ls_set("saved_id",emp_id,"sv_id")
        ls_set("saved_name",full_name,"sv_name"); ls_set("saved_school",school,"sv_school")
        ls_set("saved_section",task,"sv_section"); ls_set("saved_support",is_support,"sv_support")
        try:
            deleted_count = auto_cleanup_duplicate_attendance_for_emp(today, emp_id, "تنظيف تلقائي بعد تسجيل الحضور")
            if deleted_count:
                st.info(f"🧹 تم تنظيف {deleted_count} سجل مكرر تلقائيًا لهذا اليوم.")
        except Exception:
            pass
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


# ─── طلبات التسجيل اليدوي / مشاكل المتصفح والموقع ─────────────────────
def submit_manual_request(emp_id, emp_name, school, task, req_type, actual_att="", actual_dep="", problem_type="", notes=""):
    """إرسال طلب تسجيل يدوي للأدمن.
    الوقت يعتمد تلقائيًا على وقت إرسال الطلب، ولا يُطلب من الموظفة إدخال وقت يدوي.
    يمنع تكرار نفس نوع الطلب لنفس الرقم في نفس اليوم.
    """
    try:
        emp_id = ar_to_en_digits(emp_id).strip()
        req_type = str(req_type or "").strip()
        exists, old_req = manual_request_exists_today(emp_id, req_type)
        if exists:
            old_time = str(old_req.get("وقت الطلب", "") or "")
            st.warning(f"⚠️ تم إرسال طلب {req_type} سابق لهذا اليوم{(' الساعة ' + old_time) if old_time else ''}. لا يمكن تكرار نفس الطلب.")
            return "duplicate"

        now = now_bh()
        request_time = now.strftime("%H:%M:%S")
        fp = get_device_fingerprint()

        # نحفظ وقت الإرسال في خانة الحضور أو الانصراف حسب نوع الطلب، للتوثيق فقط.
        request_att = request_time if req_type == "حضور" else ""
        request_dep = request_time if req_type == "انصراف" else ""

        row = [
            now.strftime("%Y-%m-%d"),
            request_time,
            emp_id,
            normalize_name(emp_name),
            str(school or "").strip(),
            str(task or "").strip(),
            req_type,
            request_att,
            request_dep,
            str(problem_type or "").strip(),
            str(notes or "").strip(),
            "بانتظار الاعتماد",
            fp,
            "",
            ""
        ]
        ok = safe_append(manual_requests_sheet, row)
        get_manual_requests.clear()
        return True if ok else False
    except Exception:
        return False

def approve_manual_request(req_row_num, req, approve_type="حضور", use_actual_time=True):
    eid = str(req.get("الرقم الشخصي", "")).strip()
    if not eid:
        st.error("❌ لا يوجد رقم شخصي في الطلب.")
        return False
    emp = validate_employee(eid) or {}
    full_name = normalize_name(req.get("الاسم", "") or emp.get("الاسم", ""))
    school = req.get("المدرسة", "") or emp.get("المدرسة", "")
    task = req.get("المهمة", "") or emp.get("المهمة", "")
    support_value = "نعم" if ("دعم" in str(task) or is_yes(emp.get("دعم", ""))) else "لا"
    date_str = str(req.get("تاريخ الطلب", "") or now_bh().strftime("%Y-%m-%d"))
    try:
        d_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
        day_name = d_obj.strftime("%A")
    except Exception:
        day_name = day_arabic
    request_time = str(req.get("وقت الطلب", "") or now_bh().strftime("%H:%M:%S"))
    # الاعتماد يكون دائمًا حسب وقت إرسال الطلب، وليس وقتًا تكتبه الموظفة يدويًا.
    att_time = request_time
    dep_time = request_time
    problem = str(req.get("نوع المشكلة", "") or "مشكلة تقنية").strip()
    notes = str(req.get("ملاحظات", "") or "").strip()
    reason_note = f"[طلب يدوي] {problem} | وقت إرسال الطلب: {request_time} | {notes}".strip()
    existing_matches = find_daily_rows_fresh(date_str, eid)
    existing_idx, existing_row = pick_main_daily_row(existing_matches)
    if approve_type == "حضور":
        if existing_idx:
            safe_update(sheet, existing_idx, COL_ATTEND, att_time)
            safe_update(sheet, existing_idx, COL_LATE_REASON, reason_note)
            existing_row["وقت الحضور"] = att_time
            existing_row["سبب التأخير"] = reason_note
            update_work_calculation(existing_idx, existing_row)
        else:
            safe_append(sheet, [date_str, day_name, school, task, support_value, full_name, eid, att_time, reason_note, "", "", "", "", "⚠️ طلب يدوي بدون تحقق GPS", "", "", "", "", "", "", "", "", "طلب يدوي معتمد" if support_value != "نعم" else "طلب دعم معتمد"])
            idx_after, row_after = find_today_row_fresh(date_str, eid)
            if idx_after:
                update_work_calculation(idx_after, row_after)
        log_audit(eid, full_name, "اعتماد طلب حضور يدوي", f"التاريخ:{date_str}|حضور:{att_time}|السبب:{reason_note}")
    elif approve_type == "انصراف":
        if not existing_idx:
            st.error("❌ لا يوجد سجل حضور لاعتماد الانصراف.")
            return False
        dep_to_use = dep_time or request_time
        safe_update(sheet, existing_idx, COL_DEPART, dep_to_use)
        safe_update(sheet, existing_idx, COL_DEPART_REASON, reason_note)
        existing_row["وقت الانصراف"] = dep_to_use
        existing_row["سبب الانصراف"] = reason_note
        update_work_calculation(existing_idx, existing_row)
        log_audit(eid, full_name, "اعتماد طلب انصراف يدوي", f"التاريخ:{date_str}|انصراف:{dep_to_use}|السبب:{reason_note}")
    else:
        return False
    try:
        manual_requests_sheet.update_cell(req_row_num, 12, "تم الاعتماد")
        manual_requests_sheet.update_cell(req_row_num, 14, now_bh().strftime("%Y-%m-%d %H:%M:%S"))
        manual_requests_sheet.update_cell(req_row_num, 15, "أدمن")
    except Exception:
        pass
    clear_caches()
    # ── إعادة حساب الساعات بعد الاعتماد بقراءة مباشرة من الشيت ──
    try:
        fresh_matches = find_daily_rows_fresh(date_str, eid)
        fresh_idx, fresh_row = pick_main_daily_row(fresh_matches)
        if fresh_idx and fresh_row:
            update_work_calculation(fresh_idx, fresh_row)
    except Exception:
        pass
    return True


# ─── وضع الطوارئ الخفيف لنفس الرابط ─────────────────────────────
def _get_query_param_value(name, default=""):
    try:
        val = st.query_params.get(name, default)
        if isinstance(val, list):
            return val[0] if val else default
        return val
    except Exception:
        try:
            val = st.experimental_get_query_params().get(name, [default])
            return val[0] if isinstance(val, list) and val else val
        except Exception:
            return default


def is_lite_emergency_mode():
    mode_val = str(_get_query_param_value("lite", "")).strip().lower()
    emergency_val = str(_get_query_param_value("emergency", "")).strip().lower()
    return mode_val in ["1", "true", "yes", "نعم"] or emergency_val in ["1", "true", "yes", "نعم"]


def render_lite_emergency_mode():
    """واجهة خفيفة جدًا للأجهزة القديمة: بدون GPS وبدون LocalStorage وبدون عناصر ثقيلة."""
    st.markdown("""
    <style>
    html,body,[class*="css"]{direction:rtl!important;text-align:right!important;font-family:Tahoma,Arial,sans-serif!important;}
    .block-container{max-width:560px;padding-top:1rem;padding-bottom:2rem;}
    .lite-title{background:#0c3460;color:white;border-radius:18px;padding:18px;text-align:center!important;font-size:22px;font-weight:800;margin-bottom:14px;}
    .lite-card{border:1px solid #ddd;border-radius:16px;padding:14px;background:#fff;margin-bottom:12px;}
    .lite-note{background:#fff7e6;border-right:4px solid #BA7517;border-radius:12px;padding:10px;color:#5f3908;font-weight:700;margin-bottom:12px;}
    label{font-weight:700!important;color:#0c3460!important;}
    .stButton button{border-radius:14px!important;font-weight:800!important;}
    </style>
    """, unsafe_allow_html=True)
    st.markdown('<div class="lite-title">🆘 طلب تسجيل يدوي — وضع الطوارئ الخفيف</div>', unsafe_allow_html=True)
    st.markdown('<div class="lite-note">هذه الصفحة مخصصة للأجهزة القديمة أو عند ظهور صفحة بيضاء في النظام الكامل. الطلب لا يُسجل مباشرة إلا بعد اعتماد الأدمن.</div>', unsafe_allow_html=True)

    with st.container(border=True):
        emp_id = ar_to_en_digits(st.text_input("الرقم الشخصي", max_chars=20, key="lite_emp_id")).strip()
        emp = validate_employee(emp_id) if emp_id else None

        if emp:
            # لا نعرض الاسم تلقائيًا للموظفة في وضع الطوارئ؛ نستخدمه داخليًا للأدمن فقط.
            emp_name = str(emp.get("الاسم", "")).strip()
            emp_school = str(emp.get("المدرسة", "")).strip()
            emp_task = str(emp.get("المهمة", "")).strip()
            st.success("✅ تم التعرف على الرقم من القائمة البيضاء. أكملي نوع الطلب والوقت فقط.")
        else:
            if emp_id:
                st.warning("⚠️ الرقم غير موجود في القائمة البيضاء، اكتبي البيانات ليتمكن الأدمن من مراجعة الطلب.")
            emp_name = st.text_input("الاسم الثلاثي", key="lite_emp_name")
            school_choice = st.selectbox("المدرسة", schools + ["أخرى"], key="lite_school_choice")
            if school_choice == "أخرى":
                emp_school = st.text_input("اكتبي اسم المدرسة", key="lite_school_other").strip()
            else:
                emp_school = school_choice
            emp_task = st.selectbox("المهمة", TASKS_ALL, key="lite_task")

        req_type = st.selectbox("نوع الطلب", ["حضور", "انصراف"], key="lite_req_type")
        actual_att = st.text_input("وقت الحضور الفعلي", value="07:00:00", key="lite_actual_att")
        actual_dep = st.text_input("وقت الانصراف الفعلي (اختياري)", key="lite_actual_dep")
        problem_type = st.selectbox("نوع المشكلة", ["صفحة بيضاء", "تعذر تحديد الموقع", "الموقع لا يعمل", "زر لا يستجيب", "مشكلة في المتصفح", "أخرى"], key="lite_problem_type")
        notes = st.text_area("ملاحظات اختيارية", key="lite_notes")

        if st.button("📨 إرسال الطلب للأدمن", use_container_width=True, type="primary", key="lite_submit_request"):
            if not emp_id:
                st.error("❌ الرقم الشخصي مطلوب.")
            elif not str(emp_name).strip() or not str(emp_school).strip() or not str(emp_task).strip():
                st.error("❌ الاسم والمدرسة والمهمة مطلوبة إذا لم يكن الرقم موجودًا في القائمة البيضاء.")
            elif not actual_att.strip() and req_type == "حضور":
                st.error("❌ وقت الحضور الفعلي مطلوب.")
            else:
                ok = submit_manual_request(emp_id, emp_name, emp_school, emp_task, req_type, actual_att, actual_dep, problem_type + " — وضع الطوارئ الخفيف", notes)
                if ok:
                    st.success("✅ تم إرسال الطلب للأدمن. لا تضغطي مرة ثانية.")
                    st.info("سيظهر طلبك في لوحة الأدمن ليتم اعتماده يدويًا.")
                else:
                    st.error("❌ تعذر إرسال الطلب. تواصلي مع الأدمن عبر واتساب.")

    st.markdown("---")
    st.markdown('[الرجوع للنظام الكامل](?lite=0)')


if is_lite_emergency_mode():
    render_lite_emergency_mode()
    st.stop()

# ─── Session State ──────────────────────────────────────────────
default_state={
    "pending_operation":None,"admin_logged_in":False,"admin_last_active":None,
    "location_allowed":False,"emp_verified":False,"emp_data":None,
    "data_locked_today":False,"locked_emp":None,"locked_date":None,"operation_saving":False,
    "location_check_requested":False,
    "allow_no_gps_today":False,
    "no_gps_option_available":False,
    "emp_step":"login",
    "nogps_saving":False,
    "_queued_op":"",
    "_queued_note":"",
    "_loc_step_initialized": False,
    "_emp_session_active": False,
    "_trusted_cleared": False,
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

if _data_locked and not st.session_state.emp_verified and not st.session_state.get("_trusted_cleared"):
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
# ══════════════════════════════════════════════════════════════════
# ══ واجهة الموظفة ══
# ══════════════════════════════════════════════════════════════════
if mode=="👤 موظفة":

    # ── شاشة تحميل تمنع الضغط المزدوج ──
    st.markdown("""
    <style>
    .loading-overlay {
        display: none;
        position: fixed;
        top: 0; left: 0;
        width: 100%; height: 100%;
        background: rgba(255,255,255,0.88);
        z-index: 9999;
        justify-content: center;
        align-items: center;
        flex-direction: column;
        font-size: 18px;
        font-weight: 700;
        color: #0c3460;
        direction: rtl;
        cursor: not-allowed;
        pointer-events: all;
    }
    .loading-overlay.show { display: flex; }
    </style>
    <div class="loading-overlay" id="loadingOverlay">
        <div>⏳ جارٍ التحميل… يرجى الانتظار</div>
        <div style="font-size:13px;font-weight:400;margin-top:8px;color:#666;">لا تضغطي مرة أخرى</div>
    </div>
    <script>
    document.addEventListener('click', function(e) {
        var btn = e.target.tagName === 'BUTTON' || e.target.closest('button');
        if (btn) {
            var overlay = document.getElementById('loadingOverlay');
            overlay.classList.add('show');
            // يختفي تلقائياً بعد 5 ثواني كحماية
            setTimeout(function() {
                overlay.classList.remove('show');
            }, 5000);
        }
    }, true);
    </script>
    """, unsafe_allow_html=True)

    # ── تهيئة الـ session state ──
    if "emp_verified" not in st.session_state:
        st.session_state.emp_verified = False
    if "emp_data" not in st.session_state:
        st.session_state.emp_data = None

    # ── مسح البيانات القديمة إذا ما في رقم مدخل في هذه الجلسة ──
    if not st.session_state.get("_emp_session_active"):
        st.session_state.emp_verified        = False
        st.session_state.emp_data            = None
        st.session_state.pending_operation   = None
        st.session_state._queued_op          = ""
        st.session_state._queued_note        = ""
        st.session_state._emp_session_active = True

    trusted, _trusted_rec = is_current_device_trusted()

    # ══════════════════════════════════
    # كرت 1: البيانات الشخصية
    # ══════════════════════════════════
    with st.container(border=True):
        st.markdown('<div class="card-title">🪪 البيانات الشخصية</div>', unsafe_allow_html=True)

        if _data_locked and st.session_state.emp_data:
            emp = st.session_state.emp_data
            st.markdown(f"""
            <div class="field-lbl">الاسم</div><div class="field-val">{emp.get("الاسم","")}</div>
            <div class="field-lbl">المدرسة</div><div class="field-val">{emp.get("المدرسة","")}</div>
            <div class="field-lbl">المهمة</div><div class="field-val blue">{emp.get("المهمة","")}</div>
            <div style="font-size:12px;color:#3B6D11;font-weight:700;">🔒 بياناتك محفوظة</div>
            """, unsafe_allow_html=True)
            show_previous_auto_close_notice(emp.get("الرقم الشخصي",""))
        else:
            emp_id_raw = st.text_input("الرقم الشخصي", placeholder="أدخلي رقمك الشخصي", max_chars=20, key="main_emp_id")
            emp_id_input = ar_to_en_digits(emp_id_raw).strip()

            if emp_id_input:
                existing = validate_employee(emp_id_input)
                if existing:
                    is_sup = str(existing.get("دعم","")).strip() in ["نعم","yes","Yes","TRUE","true","1"]
                    is_sup_pending = is_sup

                    if is_sup_pending:
                        st.markdown(f"""
                        <div class="field-lbl">الاسم</div><div class="field-val">{existing.get("الاسم","")}</div>
                        <div style="background:#faeeda;border-radius:12px;padding:10px 14px;font-size:13px;font-weight:700;color:#633806;">
                        🔄 أنتِ مسجّلة كدعم مؤقت
                        </div>
                        """, unsafe_allow_html=True)
                        still_sup = st.radio("ما زلتِ دعم أم صرتِ عضوة؟",
                                             ["🔄 لا زلت دعم","🏫 صرت عضوة في المركز"],
                                             horizontal=True, key="sup_upgrade")
                        if still_sup == "🔄 لا زلت دعم":
                            st.session_state.emp_data = {"الرقم الشخصي":emp_id_input,"الاسم":existing.get("الاسم",""),"المدرسة":existing.get("المدرسة",""),"المهمة":existing.get("المهمة",""),"نشط":"نعم","دعم":True,"_existing":True}
                            st.session_state.emp_verified = True
                            st.warning("🔄 سيتم تسجيل حضورك لهذا اليوم فقط كدعم")
                        else:
                            emp_task_new = st.selectbox("المهمة الجديدة", TASKS_MAIN, key="upgrade_task")
                            emp_job_new  = st.selectbox("المسمى الوظيفي", JOB_TITLES, key="upgrade_job")
                            emp_phone_new= st.text_input("رقم التواصل", value=existing.get("رقم التواصل",""), key="upgrade_phone")
                            emp_email_new= st.text_input("البريد الإلكتروني", value=existing.get("البريد الإلكتروني",""), key="upgrade_email")
                            if st.button("💾 حفظ كعضوة", use_container_width=True, type="primary", key="btn_upgrade"):
                                try:
                                    wl_records = whitelist_sheet.get_all_records()
                                    for i, r in enumerate(wl_records):
                                        if str(r.get("الرقم الشخصي","")).strip() == emp_id_input:
                                            rn = i+2
                                            whitelist_sheet.update_cell(rn,4,emp_task_new)
                                            whitelist_sheet.update_cell(rn,5,"لا")
                                            whitelist_sheet.update_cell(rn,6,emp_phone_new)
                                            whitelist_sheet.update_cell(rn,7,emp_email_new)
                                            whitelist_sheet.update_cell(rn,8,emp_job_new)
                                            break
                                    get_whitelist.clear()
                                    st.session_state.emp_data = {"الرقم الشخصي":emp_id_input,"الاسم":existing.get("الاسم",""),"المدرسة":existing.get("المدرسة",""),"المهمة":emp_task_new,"نشط":"نعم","دعم":False,"_existing":True}
                                    st.session_state.emp_verified = True
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"خطأ: {e}")
                    else:
                        st.session_state.emp_data = {"الرقم الشخصي":emp_id_input,"الاسم":existing.get("الاسم",""),"المدرسة":existing.get("المدرسة",""),"المهمة":existing.get("المهمة",""),"نشط":"نعم","دعم":False,"_existing":True}
                        st.session_state.emp_verified = True
                        st.markdown(f"""
                        <div class="field-lbl">الاسم</div><div class="field-val">{existing.get("الاسم","")}</div>
                        <div class="field-lbl">المدرسة</div><div class="field-val">{existing.get("المدرسة","")}</div>
                        <div class="field-lbl">المهمة</div><div class="field-val blue">{existing.get("المهمة","")}</div>
                        """, unsafe_allow_html=True)
                        show_previous_auto_close_notice(emp_id_input)
                else:
                    # موظفة جديدة
                    emp_type = st.radio("نوع التسجيل",["🏫 عضوة في المركز","🔄 دعم"],horizontal=True,key="emp_type")
                    is_sup = emp_type == "🔄 دعم"
                    emp_name = st.text_input("الاسم الثلاثي", placeholder="اكتبي اسمك الثلاثي", key="new_name")
                    if is_sup:
                        sch_choice = st.selectbox("المدرسة", schools+["أخرى"], key="new_school_sup")
                        emp_school = st.text_input("اكتبي اسم المدرسة", key="new_school_other").strip() if sch_choice=="أخرى" else sch_choice
                    else:
                        emp_school = st.selectbox("المدرسة", schools, key="new_school")
                    emp_task = st.selectbox("المهمة", TASKS_SUPPORT if is_sup else TASKS_MAIN, key="new_task")
                    if not is_sup:
                        emp_job   = st.selectbox("المسمى الوظيفي", JOB_TITLES, key="new_job")
                        emp_phone = st.text_input("رقم التواصل", key="new_phone")
                        emp_email = st.text_input("البريد الإلكتروني", key="new_email")
                    else:
                        emp_job="دعم"; emp_phone=""; emp_email=""
                        st.warning("🔄 سيتم تسجيل حضورك اليوم فقط كدعم")

                    if emp_name.strip() and st.button("💾 حفظ البيانات", use_container_width=True, type="primary", key="btn_save_new"):
                        if not str(emp_school).strip():
                            st.error("❌ اسم المدرسة مطلوب.")
                        else:
                            new_data = {"الرقم الشخصي":emp_id_input,"الاسم":normalize_name(emp_name),"المدرسة":emp_school,"المهمة":emp_task,"المسمى الوظيفي":emp_job,"رقم التواصل":emp_phone,"البريد الإلكتروني":emp_email,"نشط":"نعم","دعم":is_sup,"_existing":False}
                            if not is_sup:
                                try:
                                    whitelist_sheet.append_row([emp_id_input,normalize_name(emp_name),emp_school,emp_task,"لا",emp_phone,emp_email,emp_job,"نعم"])
                                    get_whitelist.clear()
                                except Exception as e:
                                    st.warning(f"⚠️ تعذّر الحفظ: {e}")
                            st.session_state.emp_data = new_data
                            st.session_state.emp_verified = True
                            st.rerun()

    # ══════════════════════════════════
    # كرت 2: التحقق من الموقع
    # ══════════════════════════════════
    if trusted:
        st.session_state.location_allowed = True
        st.success("✅ جهاز موثوق — تم تجاوز التحقق من الموقع.")

    elif st.session_state.get("location_allowed"):
        st.success("✅ تم التحقق من الموقع بنجاح.")

    else:
        with st.expander("📍 التحقق من الموقع — اضغطي للفتح", expanded=False):
            st.markdown('''
            <div style="font-size:13px;color:#444;margin-bottom:12px;direction:rtl;">
            اضغطي الزر ثم اضغطي أيقونة الموقع الصغيرة التي تظهر بالأسفل واختاري <b>سماح / Allow</b>
            </div>
            ''', unsafe_allow_html=True)

            if st.button("📍 ابدئي التحقق من موقعي", use_container_width=True, type="primary", key="btn_gps"):
                st.session_state.location_check_requested = True
                st.session_state.no_gps_option_available  = False
                st.session_state.location_allowed          = False
                st.rerun()

            if st.session_state.get("location_check_requested") and not st.session_state.get("location_allowed"):
                st.info("⏳ جارٍ محاولة التحقق… اضغطي أيقونة الموقع بالأسفل")
                try:
                    location = streamlit_geolocation()
                except Exception:
                    location = None
                    st.session_state.no_gps_option_available = True

                if location:
                    lat   = location.get("latitude")
                    lon   = location.get("longitude")
                    error = location.get("error","")
                    if error:
                        st.session_state.no_gps_option_available = True
                        st.warning("⚠️ الموقع غير مفعّل أو تم رفض السماح.")
                    elif lat is not None and lon is not None:
                        try:
                            dist_val = distance_m(float(lat),float(lon),SCHOOL_LAT,SCHOOL_LON)
                            if dist_val <= ALLOWED_RADIUS:
                                st.session_state.location_allowed = True
                                st.session_state.no_gps_option_available = False
                                st.success(f"✅ داخل نطاق المدرسة — {int(dist_val)} م")
                                st.info("⏳ تم التحقق من الموقع، جارٍ تحميل بياناتك… يرجى الانتظار")
                                import time as _time; _time.sleep(1.5)
                                st.rerun()
                            else:
                                st.session_state.no_gps_option_available = True
                                st.error(f"❌ خارج النطاق — {int(dist_val)} م")
                        except Exception:
                            st.session_state.no_gps_option_available = True
                            st.error("❌ خطأ في قراءة الموقع.")
                    else:
                        st.session_state.no_gps_option_available = True
                        st.warning("⚠️ لم يتم استلام إحداثيات.")
                else:
                    st.session_state.no_gps_option_available = True

    # ══════════════════════════════════
    # كرت 3: تصريح الوقت اليدوي
    # ══════════════════════════════════
    if st.session_state.emp_verified and st.session_state.emp_data:
        _emp_permit = st.session_state.emp_data
        _permit_id  = str(_emp_permit.get("الرقم الشخصي","")).strip()
        _active_p   = get_active_permit(_permit_id) if _permit_id else None

        if _active_p:
            p_type  = str(_active_p.get("نوع التصريح","")).strip()
            d_from  = str(_active_p.get("تاريخ البداية","")).strip()
            d_to    = str(_active_p.get("تاريخ النهاية","")).strip()
            t_open  = str(_active_p.get("وقت الفتح","")).strip()
            t_close = str(_active_p.get("وقت الإغلاق","")).strip()
            time_w  = f"من {t_open} إلى {t_close}" if t_open else "يوم كامل"

            with st.container(border=True):
                st.markdown('<div class="card-title">⏰ تعديل وقت يدوي — مصرّح من الأدمن</div>', unsafe_allow_html=True)
                st.markdown(f"""
                <div style="font-size:12px;color:#3B6D11;margin-bottom:10px;">
                صالح من {d_from} إلى {d_to} — {time_w}
                </div>
                """, unsafe_allow_html=True)

                # اختيار التاريخ ضمن نطاق التصريح
                try:
                    min_d = datetime.strptime(d_from, "%Y-%m-%d").date() if d_from else now_bh().date()
                    max_d = datetime.strptime(d_to,   "%Y-%m-%d").date() if d_to   else now_bh().date()
                except:
                    min_d = max_d = now_bh().date()

                sel_date = st.date_input("اختاري التاريخ", value=max_d,
                                          min_value=min_d, max_value=max_d, key="permit_sel_date")
                sel_date_str = sel_date.strftime("%Y-%m-%d")

                # جلب السجل الموجود لهذا التاريخ — قراءة مباشرة بدون كاش
                _idx_p, _row_p = find_today_row_fresh(sel_date_str, _permit_id)

                if _row_p:
                    st.markdown(f"""
                    <div style="background:#f0f4f8;border-radius:10px;padding:8px 12px;font-size:13px;margin-bottom:10px;">
                    السجل الحالي — حضور: <b>{_row_p.get("وقت الحضور","—")}</b> |
                    انصراف: <b>{_row_p.get("وقت الانصراف","—")}</b>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.info("لا يوجد سجل لهذا التاريخ — سيتم إنشاء سجل جديد.")

                col_p1, col_p2 = st.columns(2)

                with col_p1:
                    if p_type in ["حضور","كليهما"]:
                        st.markdown("**وقت الحضور الجديد**")
                        try:
                            curr_att = datetime.strptime(_row_p.get("وقت الحضور","07:00:00"),"%H:%M:%S").time() if _row_p and _row_p.get("وقت الحضور") else time(7,0)
                        except: curr_att = time(7,0)
                        p_att = st.time_input("الوقت", value=curr_att, key="permit_att_time")
                        p_att_str = p_att.strftime("%H:%M:%S")
                        if st.button("✅ حفظ الحضور", use_container_width=True, type="primary", key="btn_permit_att"):
                            try:
                                emp_d = validate_employee(_permit_id) or _emp_permit
                                if _idx_p:
                                    safe_update(sheet, _idx_p, COL_ATTEND, p_att_str)
                                    safe_update(sheet, _idx_p, COL_LATE_REASON, "تعديل يدوي بتصريح الأدمن")
                                    update_work_calculation(_idx_p, {**_row_p, "وقت الحضور": p_att_str})
                                else:
                                    day_n = datetime.strptime(sel_date_str,"%Y-%m-%d").strftime("%A")
                                    safe_append(sheet,[sel_date_str,day_n,
                                        emp_d.get("المدرسة",""),emp_d.get("المهمة",""),
                                        "نعم" if is_yes(emp_d.get("دعم","")) else "لا",
                                        emp_d.get("الاسم",""),_permit_id,
                                        p_att_str,"تعديل يدوي بتصريح الأدمن",
                                        "","","","","","","","","","","","","",""])
                                    _idx2,_row2 = find_today_row_fresh(sel_date_str,_permit_id)
                                    if _idx2: update_work_calculation(_idx2,_row2)
                                log_audit(_permit_id,_emp_permit.get("الاسم",""),"تعديل وقت يدوي بتصريح",f"تاريخ:{sel_date_str}|حضور:{p_att_str}")
                                clear_caches()
                                st.success(f"✅ تم حفظ الحضور: {p_att_str}")
                                st.rerun()
                            except Exception as e:
                                st.error(f"❌ خطأ: {e}")

                with col_p2:
                    if p_type in ["انصراف","كليهما"]:
                        st.markdown("**وقت الانصراف الجديد**")
                        try:
                            curr_dep = datetime.strptime(_row_p.get("وقت الانصراف","14:00:00"),"%H:%M:%S").time() if _row_p and _row_p.get("وقت الانصراف") else time(14,0)
                        except: curr_dep = time(14,0)
                        p_dep = st.time_input("الوقت", value=curr_dep, key="permit_dep_time")
                        p_dep_str = p_dep.strftime("%H:%M:%S")
                        if st.button("🔵 حفظ الانصراف", use_container_width=True, key="btn_permit_dep"):
                            try:
                                if not _idx_p:
                                    st.error("❌ يجب تسجيل الحضور أولاً.")
                                else:
                                    safe_update(sheet, _idx_p, COL_DEPART, p_dep_str)
                                    safe_update(sheet, _idx_p, COL_DEPART_REASON, "تعديل يدوي بتصريح الأدمن")
                                    update_work_calculation(_idx_p,{**_row_p,"وقت الانصراف":p_dep_str})
                                    log_audit(_permit_id,_emp_permit.get("الاسم",""),"تعديل وقت يدوي بتصريح",f"تاريخ:{sel_date_str}|انصراف:{p_dep_str}")
                                    clear_caches()
                                    st.success(f"✅ تم حفظ الانصراف: {p_dep_str}")
                                    st.rerun()
                            except Exception as e:
                                st.error(f"❌ خطأ: {e}")

    # ══════════════════════════════════
    # كرت 4: العمليات (حضور/انصراف)
    # ══════════════════════════════════
    _permit_active = bool(get_active_permit(str((st.session_state.emp_data or {}).get("الرقم الشخصي","")).strip())) if st.session_state.emp_data else False
    if st.session_state.emp_verified and st.session_state.emp_data and (st.session_state.get("location_allowed") or trusted or _permit_active):
        emp    = st.session_state.emp_data
        emp_id = str(emp.get("الرقم الشخصي","")).strip()

        # تنفيذ العملية المؤجلة
        if st.session_state.get("operation_saving"):
            queued_op   = st.session_state.get("_queued_op","")
            queued_note = st.session_state.get("_queued_note","")
            with st.spinner("⏳ جارٍ حفظ العملية… يرجى الانتظار"):
                if queued_op:
                    register_operation(queued_op, emp_id, queued_note)
                else:
                    register_operation("عودة من استئذان", emp_id)
            st.session_state.operation_saving = False
            st.session_state._queued_op   = ""
            st.session_state._queued_note = ""
            st.rerun()

        data = get_sheet_data()
        _, today_row = find_today_row(data, today_str, emp_id)

        att_time    = today_row.get("وقت الحضور","—")   if today_row else "—"
        dep_time    = today_row.get("وقت الانصراف","—") if today_row else "—"
        exit_time   = today_row.get("خروج استئذان","—") if today_row else "—"
        return_time = today_row.get("عودة","—")          if today_row else "—"
        has_att     = bool(today_row and today_row.get("وقت الحضور","").strip())
        has_dep     = bool(today_row and today_row.get("وقت الانصراف","").strip())
        has_exit    = bool(today_row and today_row.get("خروج استئذان","").strip())
        has_return  = bool(today_row and today_row.get("عودة","").strip())

        if has_exit and not has_return and not has_dep:   status,sc = "استئذان مفتوح","#BA7517"
        elif has_exit and has_dep and "استئذان انصراف" in str(today_row.get("سبب الانصراف","")): status,sc = "انصراف باستئذان","#185FA5"
        elif has_exit and has_return and has_dep:         status,sc = "منصرف بعد الاستئذان ✓","#185FA5"
        elif has_dep:                                     status,sc = "منصرف ✓","#185FA5"
        elif has_att:                                     status,sc = "حاضر ✓","#3B6D11"
        else:                                             status,sc = "لم يُسجَّل","#A32D2D"

        if today_row and has_att and not has_dep and now_bh().time() >= time(13,30):
            st.warning("⚠️ لم يتم تسجيل الانصراف. يرجى تسجيله قبل المغادرة.")

        with st.container(border=True):
            if has_exit:
                st.markdown(f"""<div class="today-strip">
                    <div class="stat-cell"><span class="stat-val">{att_time}</span><span class="stat-lbl">حضور</span></div>
                    <div style="width:1px;background:#d3d1c7;margin:4px 0;"></div>
                    <div class="stat-cell"><span class="stat-val">{exit_time}</span><span class="stat-lbl">استئذان</span></div>
                    <div style="width:1px;background:#d3d1c7;margin:4px 0;"></div>
                    <div class="stat-cell"><span class="stat-val">{return_time if has_return else '—'}</span><span class="stat-lbl">عودة</span></div>
                    <div style="width:1px;background:#d3d1c7;margin:4px 0;"></div>
                    <div class="stat-cell"><span class="stat-val">{dep_time if has_dep else '—'}</span><span class="stat-lbl">انصراف</span></div>
                    <div style="width:1px;background:#d3d1c7;margin:4px 0;"></div>
                    <div class="stat-cell"><span class="stat-val" style="color:{sc};">{status}</span><span class="stat-lbl">الحالة</span></div>
                </div>""", unsafe_allow_html=True)
            else:
                st.markdown(f"""<div class="today-strip">
                    <div class="stat-cell"><span class="stat-val">{att_time}</span><span class="stat-lbl">حضور</span></div>
                    <div style="width:1px;background:#d3d1c7;margin:4px 0;"></div>
                    <div class="stat-cell"><span class="stat-val">{dep_time}</span><span class="stat-lbl">انصراف</span></div>
                    <div style="width:1px;background:#d3d1c7;margin:4px 0;"></div>
                    <div class="stat-cell"><span class="stat-val" style="color:{sc};">{status}</span><span class="stat-lbl">الحالة</span></div>
                </div>""", unsafe_allow_html=True)

            if today_row and has_dep and "رعاية" not in str(today_row.get("سبب الانصراف","")) and "رعاية" not in str(today_row.get("سبب التأخير","")):
                with st.expander("هل لديكِ رعاية لهذا اليوم؟", expanded=False):
                    st.info("اضغطي نعم ليُحتسب دوامك 5 ساعات رعاية.")
                    if st.button("نعم، لدي رعاية", use_container_width=True, key="btn_care"):
                        if mark_care_for_today(emp_id): st.rerun()

            _saving = st.session_state.get("operation_saving", False)
            col1,col2 = st.columns(2)
            with col1:
                if st.button("✅ تسجيل حضور", use_container_width=True, disabled=_saving or has_att, key="btn_att"):
                    if now_bh().time() > time(7,30):
                        st.session_state.pending_operation = "تسجيل حضور"
                        st.rerun()
                    else:
                        st.session_state._queued_op   = "تسجيل حضور"
                        st.session_state._queued_note = ""
                        st.session_state.operation_saving = True
                        st.rerun()
            with col2:
                if st.button("🔵 تسجيل انصراف", use_container_width=True, disabled=_saving or has_dep, key="btn_dep"):
                    if now_bh().time() < time(14,0):
                        st.session_state.pending_operation = "تسجيل انصراف"
                        st.rerun()
                    else:
                        st.session_state._queued_op   = "تسجيل انصراف"
                        st.session_state._queued_note = ""
                        st.session_state.operation_saving = True
                        st.rerun()
            col3,col4 = st.columns(2)
            with col3:
                if st.button("📤 خروج استئذان", use_container_width=True, disabled=_saving, key="btn_exit"):
                    st.session_state.pending_operation = "خروج استئذان"
                    st.rerun()
            with col4:
                if st.button("🔁 عودة من استئذان", use_container_width=True, disabled=_saving, key="btn_return"):
                    st.session_state._queued_op   = ""
                    st.session_state._queued_note = ""
                    st.session_state.operation_saving = True
                    st.rerun()

            if st.session_state.get("pending_operation") == "تسجيل حضور":
                with st.container(border=True):
                    st.markdown('<div class="card-title">سبب التأخير — اختياري</div>', unsafe_allow_html=True)
                    late_reason = st.selectbox("السبب",["اختاري السبب (اختياري)"]+reasons,key="late_reason")
                    late_other  = st.text_input("اكتبي السبب",key="late_other") if late_reason=="أخرى" else ""
                    final = "" if late_reason=="اختاري السبب (اختياري)" else (late_other.strip() if late_reason=="أخرى" else late_reason)
                    if st.button("تأكيد تسجيل الحضور", use_container_width=True, type="primary", key="btn_confirm_att"):
                        st.session_state.pending_operation = None
                        st.session_state._queued_op   = "تسجيل حضور"
                        st.session_state._queued_note = final
                        st.session_state.operation_saving = True
                        st.rerun()

            if st.session_state.get("pending_operation") == "تسجيل انصراف":
                with st.container(border=True):
                    st.markdown('<div class="card-title">سبب الانصراف قبل 2:00</div>', unsafe_allow_html=True)
                    reason = st.selectbox("السبب",reasons,key="early_reason")
                    other  = st.text_input("اكتبي السبب",key="early_other") if reason=="أخرى" else ""
                    final  = other.strip() if reason=="أخرى" else reason
                    if st.button("تأكيد تسجيل الانصراف", use_container_width=True, type="primary", key="btn_confirm_dep"):
                        if not final: st.error("السبب مطلوب")
                        else:
                            st.session_state.pending_operation = None
                            st.session_state._queued_op   = "تسجيل انصراف"
                            st.session_state._queued_note = final
                            st.session_state.operation_saving = True
                            st.rerun()

            if st.session_state.get("pending_operation") == "خروج استئذان":
                with st.container(border=True):
                    st.markdown('<div class="card-title">نوع وسبب الاستئذان</div>', unsafe_allow_html=True)
                    leave_kind   = st.radio("نوع الاستئذان",["استئذان مع عودة","استئذان انصراف"],horizontal=True,key="leave_kind")
                    reason       = st.selectbox("السبب",reasons,key="exit_reason")
                    other        = st.text_input("اكتبي السبب",key="exit_other") if reason=="أخرى" else ""
                    reason_final = other.strip() if reason=="أخرى" else reason
                    final        = f"{leave_kind} — {reason_final}" if reason_final else leave_kind
                    if st.button("تأكيد خروج الاستئذان", use_container_width=True, type="primary", key="btn_confirm_exit"):
                        if not reason_final: st.error("السبب مطلوب")
                        else:
                            st.session_state.pending_operation = None
                            st.session_state._queued_op   = "خروج استئذان"
                            st.session_state._queued_note = final
                            st.session_state.operation_saving = True
                            st.rerun()

    # ── زر "موظفة أخرى" للأجهزة الموثوقة ──
    if trusted and st.session_state.emp_verified and st.session_state.emp_data:
        st.markdown("---")
        if st.button("🚪 تسجيل موظفة أخرى", use_container_width=True, key="btn_next_emp"):
            _loc = st.session_state.get("location_allowed", True)
            ls_clear_emp_data()  # مسح LocalStorage
            st.session_state.clear()
            st.session_state.location_allowed = _loc
            st.session_state._trusted_cleared = True
            st.rerun()
    # ══════════════════════════════════
    with st.expander("🆘 مشكلة في التسجيل؟ اضغطي هنا", expanded=False):

        # ── بيانات الموظفة ──
        _sup_emp  = st.session_state.get("emp_data") or {}
        _sup_id   = str(_sup_emp.get("الرقم الشخصي","")).strip()
        _sup_name = str(_sup_emp.get("الاسم","")).strip()
        _sup_sch  = str(_sup_emp.get("المدرسة","")).strip()
        _sup_task = str(_sup_emp.get("المهمة","")).strip()

        if not _sup_id:
            _sup_raw = st.text_input("الرقم الشخصي", placeholder="أدخلي رقمك الشخصي", key="sup_emp_id")
            _sup_id  = ar_to_en_digits(_sup_raw).strip()
            if _sup_id:
                _sup_found = validate_employee(_sup_id)
                if _sup_found:
                    _sup_name = str(_sup_found.get("الاسم","")).strip()
                    _sup_sch  = str(_sup_found.get("المدرسة","")).strip()
                    _sup_task = str(_sup_found.get("المهمة","")).strip()

        # ── القسم 1: تسجيل بدون موقع ──
        st.markdown("#### 📋 تسجيل بدون موقع")
        st.caption("سيُعتمد وقت الإرسال حضوراً أو انصرافاً بعد موافقة الأدمن.")

        ex_att,_ = manual_request_exists_today(_sup_id,"حضور")  if _sup_id else (False,None)
        ex_dep,_ = manual_request_exists_today(_sup_id,"انصراف") if _sup_id else (False,None)

        col_a, col_b = st.columns(2)
        with col_a:
            if st.button(
                "✅ تم إرسال طلب الحضور" if ex_att else "📋 تسجيل حضور بدون موقع",
                use_container_width=True, key="btn_nogps_att",
                disabled=ex_att or st.session_state.get("nogps_saving"),
            ):
                if not _sup_id:
                    st.error("❌ أدخلي رقمك الشخصي أولاً.")
                else:
                    st.session_state.nogps_saving = True
                    ok = submit_manual_request(_sup_id,_sup_name,_sup_sch,_sup_task,"حضور","","","تعذر تحديد الموقع — GPS",f"تسجيل بدون GPS | {today_str}")
                    st.session_state.nogps_saving = False
                    if ok and ok != "duplicate":
                        log_audit(_sup_id,_sup_name,"تسجيل بدون GPS",f"حضور | {today_str}")
                        st.success("✅ تم إرسال طلب الحضور — بانتظار اعتماد الأدمن.")
                        st.rerun()
                    elif ok == "duplicate":
                        st.warning("⚠️ تم إرسال طلب سابق لهذا اليوم.")
                    else:
                        st.error("❌ تعذّر الإرسال.")
        with col_b:
            if st.button(
                "✅ تم إرسال طلب الانصراف" if ex_dep else "📋 تسجيل انصراف بدون موقع",
                use_container_width=True, key="btn_nogps_dep",
                disabled=ex_dep or st.session_state.get("nogps_saving"),
            ):
                if not _sup_id:
                    st.error("❌ أدخلي رقمك الشخصي أولاً.")
                else:
                    st.session_state.nogps_saving = True
                    ok = submit_manual_request(_sup_id,_sup_name,_sup_sch,_sup_task,"انصراف","","","تعذر تحديد الموقع — GPS",f"تسجيل بدون GPS | {today_str}")
                    st.session_state.nogps_saving = False
                    if ok and ok != "duplicate":
                        log_audit(_sup_id,_sup_name,"تسجيل بدون GPS",f"انصراف | {today_str}")
                        st.success("✅ تم إرسال طلب الانصراف — بانتظار اعتماد الأدمن.")
                        st.rerun()
                    elif ok == "duplicate":
                        st.warning("⚠️ تم إرسال طلب سابق لهذا اليوم.")
                    else:
                        st.error("❌ تعذّر الإرسال.")

        # ── القسم 2: تواصل مع الأدمن للتعديل ──
        st.markdown("---")
        st.markdown("#### 💬 تواصل مع الأدمن للتعديل")
        st.caption("لتصحيح وقت الحضور أو الانصراف أو أي تعديل.")

        data_wa  = get_sheet_data()
        _,row_wa = find_today_row(data_wa,today_str,_sup_id) if _sup_id else (None,None)
        att_wa   = row_wa.get("وقت الحضور","—")   if row_wa else "—"
        dep_wa   = row_wa.get("وقت الانصراف","—") if row_wa else "—"

        issue_choice = st.selectbox("نوع المشكلة",[
            "تصحيح وقت الحضور","تصحيح وقت الانصراف",
            "تعديل سبب التأخير أو الانصراف","مشكلة تقنية",
            "تعديل بيانات شخصية","أخرى"],key="wa_issue")
        issue_notes = st.text_input("تفاصيل إضافية (اختياري)", key="wa_notes")

        wa_msg = f"""مرحباً 👋
لدي طلب في نظام الحضور:
الاسم: {_sup_name}
الرقم الشخصي: {_sup_id}
المدرسة: {_sup_sch}
المهمة: {_sup_task}
التاريخ: {today_str} | الوقت: {now_bh().strftime('%H:%M:%S')}
وقت الحضور: {att_wa} | وقت الانصراف: {dep_wa}
نوع الطلب: {issue_choice}
{('التفاصيل: '+issue_notes) if issue_notes.strip() else ''}"""
        wa_link = "https://wa.me/97333738668?text=" + urllib.parse.quote(wa_msg)
        st.link_button("📞 فتح واتساب برسالة جاهزة", wa_link, use_container_width=True)

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
            "📑 التقارير",
            "🛠️ إصلاح شامل",
            "🆘 طلبات التسجيل اليدوي",
            "⚙️ إعدادات التسجيل اليدوي",
            "🔴 تسجيل الغياب",
            "📅 دوام الأقسام",
            "🧹 تنظيف التكرارات",
            "✏️ تعديل سجل",
            "➕ تسجيل يدوي",
            "📋 القائمة البيضاء",
            "🚫 محاولات التسجيل",
            "📡 تجاوز الموقع",
            "⚙️ قفل الجهاز",
            "📱 الأجهزة الموثوقة",
            "🔓 فتح قفل جهاز",
            "🔍 سجل التدقيق",
            "⚠️ تقرير الأجهزة",
            "⏰ تصاريح الوقت اليدوي",
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
            no_gps_rows=[r for r in today_rows if "بدون تحقق GPS" in str(r.get("سبب التأخير", "")) or "بدون تحقق GPS" in str(r.get("سبب الانصراف", "")) or "بدون تحقق GPS" in str(r.get("محاولة", ""))]

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
            c12.metric("بدون تحقق GPS",len(no_gps_rows))

            st.info("✅ الإحصائيات الأساسية أعلاه تعتمد على دوام الأقسام المحدد لهذا اليوم، مع فصل الدعم الخارجي غير الموجود في القائمة البيضاء.")

            # تنبيه بعد الساعة 10:00 للموظفات المطلوب دوامهن ولم يسجلن حضور ولم يسجل لهن غياب
            if now_bh().time() >= time(10, 0):
                attended_ids = set(str(r.get("الرقم الشخصي", "")).strip() for r in today_required_rows if r.get("وقت الحضور"))
                absent_ids = set(str(r.get("الرقم الشخصي", "")).strip() for r in abs_today)
                not_checked_in = {eid: emp for eid, emp in required_wl.items() if str(eid).strip() not in attended_ids and str(eid).strip() not in absent_ids}
                if not_checked_in:
                    st.markdown("#### 🚨 لم يسجلن حضور حتى الآن بعد الساعة 10:00")
                    st.caption("هذه القائمة تساعدك للتواصل معهن قبل اعتماد الغياب. تستثني من حضرن أو تم تسجيل غيابهن يدويًا.")
                    for eid, emp in not_checked_in.items():
                        st.markdown(f'<div class="warn-row">🚨 {emp.get("الاسم", "")} — #{eid} — {emp.get("المدرسة", "")} — {emp.get("المهمة", "")}</div>', unsafe_allow_html=True)
                        phone_raw = str(emp.get("رقم التواصل", "") or "").strip().replace(" ", "")
                        msg = f"""السلام عليكم 🌷
نلاحظ عدم تسجيل حضوركِ في نظام الحضور والانصراف لهذا اليوم.

يرجى الدخول للنظام الآن. إذا كنتِ في المركز ولم يعمل معكِ التسجيل، اختاري: 🆘 عندي مشكلة في التسجيل. سيتم إرسال وقت الطلب تلقائيًا للأدمن لاعتماده.

أما إذا لم تحضري بعد، يرجى تسجيل الحضور عند الوصول للمركز فقط.

رابط النظام:
{APP_URL}"""
                        cwa1, cwa2 = st.columns(2)
                        if phone_raw:
                            if not phone_raw.startswith("973"):
                                phone_raw = "973" + phone_raw.lstrip("0")
                            wa_url = "https://wa.me/" + phone_raw + "?text=" + urllib.parse.quote(msg)
                            with cwa1:
                                st.link_button("📩 إرسال تذكير واتساب", wa_url, use_container_width=True)
                        else:
                            with cwa1:
                                st.caption("لا يوجد رقم تواصل في القائمة البيضاء")
                        with cwa2:
                            if st.button("✅ تسجيل أنه تم إرسال تذكير", key=f"reminder_sent_{eid}", use_container_width=True):
                                log_audit(eid, emp.get("الاسم", ""), "إرسال تذكير عدم تسجيل", "تم فتح/تجهيز رسالة واتساب من الداشبورد")
                                st.success("تم تسجيل التذكير في سجل التدقيق")
                else:
                    st.success("✅ بعد الساعة 10:00: لا توجد أسماء مطلوبة لم تسجل حضور أو غياب.")

            if no_gps_rows:
                st.markdown("#### ⚠️ عمليات بدون تحقق GPS")
                for r in no_gps_rows[-50:]:
                    st.markdown(f'<div class="warn-row">⚠️ {r.get("الاسم الثلاثي","")} — #{r.get("الرقم الشخصي","")} — حضور: {r.get("وقت الحضور","") or "—"} — انصراف: {r.get("وقت الانصراف","") or "—"}</div>', unsafe_allow_html=True)

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


        # ── التقارير ──────────────────────────────────────────────
        elif admin_tab=="📑 التقارير":
            st.markdown("#### 📑 التقارير")

            # فلاتر
            col_f1, col_f2, col_f3 = st.columns(3)
            with col_f1:
                report_type = st.selectbox("نوع التقرير", ["يومي", "أسبوعي", "شهري", "نطاق مخصص"], key="rpt_type")
            with col_f2:
                if report_type == "يومي":
                    rpt_date = st.date_input("التاريخ", value=now_bh().date(), key="rpt_date_single")
                    date_from = date_to = rpt_date.strftime("%Y-%m-%d")
                elif report_type == "أسبوعي":
                    week_start = now_bh().date() - timedelta(days=now_bh().date().weekday())
                    rpt_date = st.date_input("بداية الأسبوع", value=week_start, key="rpt_week")
                    date_from = rpt_date.strftime("%Y-%m-%d")
                    date_to   = (rpt_date + timedelta(days=6)).strftime("%Y-%m-%d")
                elif report_type == "شهري":
                    rpt_month = st.selectbox("الشهر", [f"{now_bh().year}-{m:02d}" for m in range(1,13)],
                                             index=now_bh().month-1, key="rpt_month")
                    date_from = f"{rpt_month}-01"
                    date_to   = f"{rpt_month}-31"
                else:
                    rpt_date = st.date_input("من", value=now_bh().date(), key="rpt_from")
                    date_from = rpt_date.strftime("%Y-%m-%d")
                    date_to   = date_from
            with col_f3:
                if report_type == "نطاق مخصص":
                    rpt_date_to = st.date_input("إلى", value=now_bh().date(), key="rpt_to")
                    date_to = rpt_date_to.strftime("%Y-%m-%d")

            rpt_school = st.selectbox("المدرسة", ["الكل"] + schools, key="rpt_school")

            if st.button("📊 إنشاء التقرير", use_container_width=True, type="primary", key="btn_gen_report"):
                try:
                    data = get_sheet_data()

                    def normalize_date(d):
                        return str(d).strip().replace("/","-")

                    rows = [r for r in data
                            if date_from <= normalize_date(r.get("التاريخ","")) <= date_to
                            and (rpt_school == "الكل" or str(r.get("اسم المدرسة","")).strip() == rpt_school)]

                    if not rows:
                        st.warning("⚠️ لا توجد بيانات للنطاق المحدد.")
                    else:
                        st.success(f"✅ تم تحميل {len(rows)} سجل.")

                        # ── ملخص إجمالي ──
                        total     = len(rows)
                        attended  = len([r for r in rows if r.get("وقت الحضور","")])
                        departed  = len([r for r in rows if r.get("وقت الانصراف","")])
                        late      = len([r for r in rows if is_late_for_statistics(r)])
                        auto_cls  = len([r for r in rows if str(r.get("إغلاق تلقائي","")).strip()])
                        no_gps    = len([r for r in rows if "GPS" in str(r.get("محاولة","")) or "GPS" in str(r.get("سبب التأخير",""))])
                        extra_hrs_rows = [r for r in rows if r.get("الساعات الإضافية","") and str(r.get("الساعات الإضافية","")).strip() not in ["","0:00","00:00"]]

                        c1,c2,c3,c4 = st.columns(4)
                        c1.metric("إجمالي السجلات", total)
                        c2.metric("سجّلن حضور", attended)
                        c3.metric("سجّلن انصراف", departed)
                        c4.metric("حالات تأخير", late)
                        c5,c6,c7,c8 = st.columns(4)
                        c5.metric("إغلاق تلقائي", auto_cls)
                        c6.metric("بدون GPS", no_gps)
                        c7.metric("لديهن ساعات إضافية", len(extra_hrs_rows))
                        c8.metric("نطاق التاريخ", f"{date_from} → {date_to}")

                        st.markdown("---")

                        # ── ترتيب البيانات: المهمة ← المدرسة ← وقت الحضور ──
                        rows_sorted = sorted(rows, key=lambda r: (
                            str(r.get("اسم المدرسة","")).strip(),
                            str(r.get("المهمة","")).strip(),
                            str(r.get("وقت الحضور","")).strip(),
                        ))

                        # ── جدول تفصيلي ──
                        st.markdown("##### تفاصيل السجلات")
                        cols_show = ["التاريخ","اليوم","اسم المدرسة","المهمة","الاسم الثلاثي","الرقم الشخصي",
                                     "وقت الحضور","وقت الانصراف","ساعات العمل","الساعات الإضافية","حالة الدوام","نوع الدوام اليومي"]
                        df_rows = []
                        for r in rows_sorted:
                            row_d = {c: r.get(c,"") for c in cols_show}
                            row_d["الرقم الشخصي"] = str(r.get("الرقم الشخصي","")).strip()
                            df_rows.append(row_d)
                        df = pd.DataFrame(df_rows)
                        st.dataframe(df, use_container_width=True, hide_index=True)

                        # ── تصدير Excel منسق ──
                        st.markdown("##### تصدير")
                        try:
                            from openpyxl import load_workbook
                            from openpyxl.styles import (
                                Font, Alignment, PatternFill, Border, Side, GradientFill
                            )
                            from openpyxl.utils import get_column_letter

                            buf = BytesIO()
                            with pd.ExcelWriter(buf, engine="openpyxl") as writer:
                                df.to_excel(writer, index=False, sheet_name="التقرير")
                                # ── ملخص موظفة ──
                                emp_sum_rows = []
                                for r in rows:
                                    eid  = str(r.get("الرقم الشخصي","")).strip()
                                    name = str(r.get("الاسم الثلاثي","")).strip()
                                    if not eid: continue
                                    found = next((x for x in emp_sum_rows if x["الرقم الشخصي"]==eid), None)
                                    if not found:
                                        found = {"الرقم الشخصي": eid, "الاسم": name, "عدد الأيام": 0,
                                                 "أيام التأخير": 0, "إغلاق تلقائي": 0}
                                        emp_sum_rows.append(found)
                                    found["عدد الأيام"] += 1
                                    if is_late_for_statistics(r): found["أيام التأخير"] += 1
                                    if str(r.get("إغلاق تلقائي","")).strip(): found["إغلاق تلقائي"] += 1
                                if emp_sum_rows:
                                    pd.DataFrame(emp_sum_rows).to_excel(writer, index=False, sheet_name="ملخص الموظفات")

                            # ── تنسيق الملف ──
                            buf.seek(0)
                            wb = load_workbook(buf)

                            # ألوان
                            header_fill   = PatternFill("solid", fgColor="0C3460")   # أزرق داكن للهيدر
                            white_fill    = PatternFill("solid", fgColor="FFFFFF")
                            alt_fill      = PatternFill("solid", fgColor="F5F5F5")   # رمادي خفيف للصفوف الزوجية

                            header_font  = Font(name="Arial", bold=True, color="FFFFFF", size=11)
                            body_font    = Font(name="Arial", size=10)
                            center_align = Alignment(horizontal="center", vertical="center",
                                                     wrap_text=True, readingOrder=2)
                            right_align  = Alignment(horizontal="right",  vertical="center",
                                                     wrap_text=True, readingOrder=2)
                            thin = Side(style="thin", color="CCCCCC")
                            border = Border(left=thin, right=thin, top=thin, bottom=thin)

                            # عرض الأعمدة لكل شيت
                            col_widths = {
                                "التاريخ": 14, "اليوم": 10, "اسم المدرسة": 28,
                                "المهمة": 30, "الاسم الثلاثي": 28, "الرقم الشخصي": 16,
                                "وقت الحضور": 13, "وقت الانصراف": 13,
                                "ساعات العمل": 13, "الساعات الإضافية": 16,
                                "حالة الدوام": 20, "نوع الدوام اليومي": 20,
                            }

                            for sheet_name in wb.sheetnames:
                                ws = wb[sheet_name]
                                ws.sheet_view.rightToLeft = True  # RTL

                                # ارتفاع الهيدر
                                ws.row_dimensions[1].height = 30

                                # تنسيق الهيدر
                                for cell in ws[1]:
                                    cell.font      = header_font
                                    cell.fill      = header_fill
                                    cell.alignment = center_align
                                    cell.border    = border

                                # عرض الأعمدة تلقائياً
                                for col_idx, col_cells in enumerate(ws.columns, 1):
                                    col_letter = get_column_letter(col_idx)
                                    header_val = str(ws.cell(1, col_idx).value or "")
                                    ws.column_dimensions[col_letter].width = col_widths.get(header_val, 18)

                                # تنسيق صفوف البيانات
                                for row_idx, row_cells in enumerate(ws.iter_rows(min_row=2), 2):
                                    ws.row_dimensions[row_idx].height = 20
                                    row_fill = alt_fill if row_idx % 2 == 0 else white_fill

                                    for cell in row_cells:
                                        cell.font      = body_font
                                        cell.fill      = row_fill
                                        cell.border    = border
                                        h = str(ws.cell(1, cell.column).value or "")
                                        # الأعمدة الرقمية والوقت توسيط، الباقي يمين
                                        if h in ["وقت الحضور","وقت الانصراف","ساعات العمل",
                                                 "الساعات الإضافية","التاريخ","اليوم"]:
                                            cell.alignment = center_align
                                        else:
                                            cell.alignment = right_align
                                        # الرقم الشخصي نصي دائماً
                                        if h == "الرقم الشخصي" and cell.value:
                                            cell.value     = str(cell.value)
                                            cell.number_format = "@"

                                # تجميد الهيدر
                                ws.freeze_panes = "A2"

                                # إعدادات الطباعة
                                ws.page_setup.orientation      = "landscape"
                                ws.page_setup.fitToPage        = True
                                ws.page_setup.fitToWidth        = 1
                                ws.page_setup.fitToHeight       = 0
                                ws.page_setup.paperSize         = 9  # A4
                                ws.print_title_rows             = "1:1"
                                ws.page_margins.left            = 0.5
                                ws.page_margins.right           = 0.5
                                ws.page_margins.top             = 0.75
                                ws.page_margins.bottom          = 0.75
                                ws.sheet_properties.pageSetUpPr.fitToPage = True
                                ws.oddHeader.center.text = f"مركز جدحفص الثانوية للتصحيح المركزي\nنظام الحضور والانصراف — {date_from} إلى {date_to}"
                                ws.oddHeader.center.font = "Arial,Bold"
                                ws.oddHeader.right.text  = "تصميم وبرمجة: أ. عفاف حسين"
                                ws.oddHeader.right.font  = "Arial"
                                ws.oddFooter.right.text  = "صفحة &P من &N"
                                ws.oddFooter.left.text   = "رئيسة المركز: أ. خلود يعقوب بدو"
                                ws.oddFooter.left.font   = "Arial,Bold"

                            buf2 = BytesIO()
                            wb.save(buf2)
                            buf2.seek(0)
                            fname = f"تقرير_الحضور_{date_from}_{date_to}.xlsx"
                            st.download_button(
                                "📥 تحميل Excel — منسق وجاهز للطباعة",
                                data=buf2,
                                file_name=fname,
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                use_container_width=True,
                            )
                        except Exception as e:
                            st.warning(f"⚠️ تعذّر إنشاء ملف Excel: {e}")

                        # ── ملخص لكل موظفة (عرض في الصفحة) ──
                        st.markdown("---")
                        st.markdown("##### ملخص لكل موظفة")
                        emp_summary = {}
                        for r in rows_sorted:
                            eid  = str(r.get("الرقم الشخصي","")).strip()
                            name = str(r.get("الاسم الثلاثي","")).strip()
                            if not eid: continue
                            if eid not in emp_summary:
                                emp_summary[eid] = {"الاسم": name, "المهمة": str(r.get("المهمة","")).strip(), "أيام": 0, "تأخير": 0, "إغلاق تلقائي": 0}
                            emp_summary[eid]["أيام"] += 1
                            if is_late_for_statistics(r): emp_summary[eid]["تأخير"] += 1
                            if str(r.get("إغلاق تلقائي","")).strip(): emp_summary[eid]["إغلاق تلقائي"] += 1
                        df_emp = pd.DataFrame([{"الرقم": k, **v} for k,v in emp_summary.items()])
                        if not df_emp.empty:
                            st.dataframe(df_emp, use_container_width=True, hide_index=True)

                except Exception as e:
                    st.error(f"❌ خطأ في إنشاء التقرير: {e}")

        # ── إصلاح شامل ────────────────────────────────────────────
        elif admin_tab=="🛠️ إصلاح شامل":
            st.markdown("#### 🛠️ إصلاح شامل")
            st.warning("⚠️ هذه الأدوات تعدّل البيانات مباشرة. استخدميها بحذر.")

            # ── إعادة حساب الساعات ──
            with st.container(border=True):
                st.markdown("##### 🔄 إعادة حساب ساعات العمل")
                st.caption("يعيد احتساب ساعات العمل والساعات الإضافية وحالة الدوام لجميع السجلات أو لتاريخ محدد.")
                recalc_mode = st.radio("النطاق", ["تاريخ محدد", "كل السجلات"], horizontal=True, key="recalc_mode")
                if recalc_mode == "تاريخ محدد":
                    recalc_date = st.date_input("التاريخ", value=now_bh().date(), key="recalc_date")
                    recalc_date_str = recalc_date.strftime("%Y-%m-%d")
                else:
                    recalc_date_str = None

                if st.button("🔄 بدء إعادة الحساب", use_container_width=True, type="primary", key="btn_recalc"):
                    try:
                        data = get_sheet_data()
                        updated = 0
                        errors  = 0
                        progress = st.progress(0)
                        total_r = len(data)
                        for i, row in enumerate(data):
                            progress.progress((i+1)/max(total_r,1))
                            if recalc_date_str and str(row.get("التاريخ","")).strip() != recalc_date_str:
                                continue
                            if not row.get("وقت الحضور",""):
                                continue
                            try:
                                if update_work_calculation(i+2, row):
                                    updated += 1
                            except Exception:
                                errors += 1
                        clear_caches()
                        st.success(f"✅ تم إعادة حساب {updated} سجل. أخطاء: {errors}")
                        log_audit("—","أدمن","إعادة حساب شاملة",f"نطاق:{recalc_date_str or 'الكل'}|محدّث:{updated}|أخطاء:{errors}")
                    except Exception as e:
                        st.error(f"❌ خطأ: {e}")

            st.markdown("---")

            # ── تنظيف التكرارات لكل التواريخ ──
            with st.container(border=True):
                st.markdown("##### 🧹 تنظيف تكرارات كل التواريخ")
                st.caption("يفحص جميع التواريخ ويحذف السجلات المكررة تلقائياً — يحتفظ بالأكمل.")
                if st.button("🔍 فحص وتنظيف كل التكرارات", use_container_width=True, type="primary", key="btn_clean_all_dups"):
                    try:
                        groups = find_duplicate_attendance_groups()
                        if not groups:
                            st.success("✅ لا توجد تكرارات في أي تاريخ.")
                        else:
                            total_deleted = 0
                            for (date_val, emp_id_val), _ in groups.items():
                                deleted = auto_cleanup_duplicate_attendance_for_emp(date_val, emp_id_val, "إصلاح شامل")
                                total_deleted += deleted
                            clear_caches()
                            st.success(f"✅ تم حذف {total_deleted} سجل مكرر.")
                            log_audit("—","أدمن","تنظيف شامل للتكرارات",f"سجلات محذوفة:{total_deleted}")
                    except Exception as e:
                        st.error(f"❌ خطأ: {e}")

            st.markdown("---")

            # ── إغلاق السجلات المفتوحة ──
            with st.container(border=True):
                st.markdown("##### 🔒 إغلاق السجلات المفتوحة من أيام سابقة")
                st.caption("يغلق تلقائياً أي سجل من أيام سابقة لم يُسجَّل له انصراف.")
                if st.button("🔒 تنفيذ الإغلاق التلقائي الآن", use_container_width=True, key="btn_force_autoclose"):
                    try:
                        auto_close_previous_open_records()
                        clear_caches()
                        st.success("✅ تم تنفيذ الإغلاق التلقائي لجميع السجلات المفتوحة.")
                        log_audit("—","أدمن","إغلاق تلقائي يدوي","تنفيذ من لوحة الإصلاح الشامل")
                    except Exception as e:
                        st.error(f"❌ خطأ: {e}")
            st.markdown("#### ⚙️ إعدادات التسجيل اليدوي للموظفات")
            current_enabled = manual_requests_enabled()
            if current_enabled:
                st.success("✅ طلبات التسجيل اليدوي من واجهة الموظفة مفعّلة حاليًا.")
            else:
                st.warning("⚠️ طلبات التسجيل اليدوي من واجهة الموظفة معطّلة حاليًا. الموظفات سيظهر لهن تنبيه للتواصل مع الأدمن فقط.")

            new_enabled = st.radio(
                "حالة الخاصية",
                ["مفعّلة", "معطّلة"],
                index=0 if current_enabled else 1,
                horizontal=True,
                key="manual_requests_enabled_radio"
            )
            setting_note = st.text_input("ملاحظة/سبب التغيير", value="تغيير إعداد طلبات التسجيل اليدوي", key="manual_requests_setting_note")

            if st.button("💾 حفظ إعداد التسجيل اليدوي", use_container_width=True, type="primary"):
                value = "true" if new_enabled == "مفعّلة" else "false"
                if set_system_setting("manual_requests_enabled", value, setting_note):
                    log_audit("—", "أدمن", "تعديل إعداد التسجيل اليدوي", f"manual_requests_enabled={value}|{setting_note}")
                    clear_caches()
                    st.success("✅ تم حفظ الإعداد بنجاح.")
                    st.rerun()

            st.info("حتى عند تعطيل هذه الخاصية، يبقى قسم ➕ تسجيل يدوي في لوحة الأدمن شغالًا، وتستطيعين تسجيل الموظفة يدويًا بعد التواصل معها.")

        # ── طلبات التسجيل اليدوي ─────────────────────────────────
        elif admin_tab=="🆘 طلبات التسجيل اليدوي":
            st.markdown("#### 🆘 طلبات التسجيل اليدوي / مشاكل الموقع والمتصفح")

            # تهيئة قائمة الطلبات المعتمدة/المرفوضة محلياً لتجنب اختفائها بعد rerun
            if "approved_req_rows" not in st.session_state:
                st.session_state.approved_req_rows = set()

            reqs = get_manual_requests()
            pending = [(i+2, r) for i, r in enumerate(reqs)
                       if str(r.get("الحالة", "")).strip() in ["", "بانتظار الاعتماد"]
                       and (i+2) not in st.session_state.approved_req_rows]
            done = [(i+2, r) for i, r in enumerate(reqs)
                    if str(r.get("الحالة", "")).strip() not in ["", "بانتظار الاعتماد"]
                    or (i+2) in st.session_state.approved_req_rows]

            st.metric("طلبات بانتظار الاعتماد", len(pending))

            # زر تحديث يدوي
            if st.button("🔄 تحديث القائمة", key="btn_refresh_reqs"):
                st.session_state.approved_req_rows = set()
                get_manual_requests.clear()
                st.rerun()

            if not pending:
                st.success("✅ لا توجد طلبات معلقة حالياً.")
            else:
                for row_num, r in reversed(pending[-80:]):
                    eid = str(r.get("الرقم الشخصي", "")).strip()
                    title = f"{r.get('الاسم','')} — #{eid} — {r.get('نوع الطلب','')} — {r.get('نوع المشكلة','')}"
                    with st.expander(title, expanded=False):
                        st.markdown(f'<div class="warn-row"><b>تاريخ الطلب:</b> {r.get("تاريخ الطلب","")} — <b>وقت الإرسال المعتمد:</b> {r.get("وقت الطلب","")}<br><b>نوع الطلب:</b> {r.get("نوع الطلب","")}<br><b>المدرسة:</b> {r.get("المدرسة","")}<br><b>المهمة:</b> {r.get("المهمة","")}<br><b>الملاحظات:</b> {r.get("ملاحظات","") or "—"}</div>', unsafe_allow_html=True)
                        c1, c2, c3 = st.columns(3)
                        with c1:
                            if st.button("✅ اعتماد حضور", key=f"approve_att_{row_num}", use_container_width=True, type="primary"):
                                if approve_manual_request(row_num, r, "حضور", False):
                                    st.session_state.approved_req_rows.add(row_num)
                                    st.success("✅ تم اعتماد الحضور اليدوي")
                                    st.rerun()
                        with c2:
                            if st.button("🔵 اعتماد انصراف", key=f"approve_dep_{row_num}", use_container_width=True):
                                if approve_manual_request(row_num, r, "انصراف", False):
                                    st.session_state.approved_req_rows.add(row_num)
                                    st.success("✅ تم اعتماد الانصراف اليدوي")
                                    st.rerun()
                        with c3:
                            if st.button("❌ رفض الطلب", key=f"reject_req_{row_num}", use_container_width=True):
                                try:
                                    manual_requests_sheet.update_cell(row_num, 12, "مرفوض")
                                    manual_requests_sheet.update_cell(row_num, 14, now_bh().strftime("%Y-%m-%d %H:%M:%S"))
                                    manual_requests_sheet.update_cell(row_num, 15, "أدمن")
                                    log_audit(eid, r.get("الاسم", ""), "رفض طلب تسجيل يدوي", f"نوع المشكلة:{r.get('نوع المشكلة','')}|وقت الطلب:{r.get('وقت الطلب','')}")
                                    st.session_state.approved_req_rows.add(row_num)
                                    clear_caches()
                                    st.success("تم رفض الطلب")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"تعذر رفض الطلب: {e}")
            with st.expander("الطلبات المعتمدة/المرفوضة الأخيرة", expanded=False):
                for row_num, r in reversed(done[-40:]):
                    st.markdown(f'<div class="audit-row">{r.get("الحالة","")} — {r.get("الاسم","")} — #{r.get("الرقم الشخصي","")} — {r.get("تاريخ الطلب","")} {r.get("وقت الطلب","")}</div>', unsafe_allow_html=True)

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
                    st.markdown("#### تم تسجيل غيابهن / تعديل الحالة")
                    for eid,emp in already_absent.items():
                        rec=next((r for r in abs_records if str(r.get("الرقم الشخصي",""))==eid and r.get("التاريخ")==abs_date_str),{})
                        st.markdown(f'<div class="absent-row">🔴 {emp.get("الاسم","")} — {emp.get("المهمة","")} — سبب: {rec.get("سبب الغياب","")}</div>',unsafe_allow_html=True)
                        with st.expander(f"✏️ تعديل غياب / تحويل إلى حضور يدوي — {emp.get('الاسم','')}", expanded=False):
                            new_abs_reason = st.selectbox("تعديل سبب الغياب", abs_reasons, index=abs_reasons.index(rec.get("سبب الغياب","مرض")) if rec.get("سبب الغياب","") in abs_reasons else 0, key=f"edit_abs_reason_{eid}")
                            new_abs_note = st.text_input("ملاحظات الغياب", value=rec.get("ملاحظات", ""), key=f"edit_abs_note_{eid}")
                            c_abs1, c_abs2 = st.columns(2)
                            with c_abs1:
                                if st.button("💾 حفظ تعديل الغياب", key=f"save_abs_edit_{eid}", use_container_width=True):
                                    try:
                                        for i, rr in enumerate(abs_records):
                                            if str(rr.get("الرقم الشخصي", "")).strip() == eid and rr.get("التاريخ") == abs_date_str:
                                                absence_sheet.update_cell(i+2, 7, new_abs_reason)
                                                absence_sheet.update_cell(i+2, 8, new_abs_note)
                                                log_audit(eid, emp.get("الاسم", ""), "تعديل غياب", f"التاريخ:{abs_date_str}|السبب:{new_abs_reason}|ملاحظات:{new_abs_note}")
                                                st.success("✅ تم تعديل الغياب")
                                                st.rerun()
                                    except Exception as e:
                                        st.error(f"❌ تعذر تعديل الغياب: {e}")
                            with c_abs2:
                                st.caption("إذا كانت الموظفة موجودة لكن المتصفح لا يعمل، سجليها يدويًا وسيتم إلغاء الغياب.")

                            manual_att = st.text_input("وقت الحضور اليدوي", value="07:00:00", key=f"abs_manual_att_{eid}")
                            manual_dep = st.text_input("وقت الانصراف اليدوي (اختياري)", key=f"abs_manual_dep_{eid}")
                            manual_note = st.text_input("سبب التسجيل اليدوي", value="مشكلة في المتصفح / البرنامج لم يفتح", key=f"abs_manual_note_{eid}")
                            if st.button("✅ تحويل إلى تسجيل حضور يدوي وإلغاء الغياب", key=f"convert_abs_manual_{eid}", use_container_width=True, type="primary"):
                                if not manual_note.strip():
                                    st.error("❌ سبب التسجيل اليدوي مطلوب")
                                else:
                                    try:
                                        existing_matches = find_daily_rows_fresh(abs_date_str, eid)
                                        existing_idx, existing_row = pick_main_daily_row(existing_matches)
                                        full_name = normalize_name(emp.get("الاسم", ""))
                                        support_raw = str(emp.get("دعم", "")).strip()
                                        task = str(emp.get("المهمة", "")).strip()
                                        support_value = "نعم" if support_raw in ["نعم","yes","Yes","TRUE","true","1"] or "دعم" in task else "لا"
                                        if existing_idx:
                                            safe_update(sheet, existing_idx, COL_ATTEND, manual_att)
                                            safe_update(sheet, existing_idx, COL_LATE_REASON, f"[يدوي] {manual_note.strip()}")
                                            safe_update(sheet, existing_idx, COL_DEPART, manual_dep)
                                            existing_row["وقت الحضور"] = manual_att
                                            existing_row["وقت الانصراف"] = manual_dep
                                            update_work_calculation(existing_idx, existing_row)
                                        else:
                                            safe_append(sheet, [abs_date_str, abs_day_ar, emp.get("المدرسة", ""), task, support_value, full_name, eid, manual_att, f"[يدوي] {manual_note.strip()}", manual_dep, "", "", "", "", "", "", "", "", "", "", "", "", "تحويل غياب إلى تسجيل يدوي"])
                                            idx_after, row_after = find_today_row_fresh(abs_date_str, eid)
                                            if idx_after:
                                                update_work_calculation(idx_after, row_after)
                                        # حذف سجل الغياب لنفس التاريخ والرقم
                                        fresh_abs = absence_sheet.get_all_records()
                                        for i in range(len(fresh_abs)-1, -1, -1):
                                            rr = fresh_abs[i]
                                            if str(rr.get("الرقم الشخصي", "")).strip() == eid and rr.get("التاريخ") == abs_date_str:
                                                absence_sheet.delete_rows(i+2)
                                        log_audit(eid, full_name, "تحويل غياب إلى حضور يدوي", f"التاريخ:{abs_date_str}|حضور:{manual_att}|انصراف:{manual_dep}|السبب:{manual_note.strip()}")
                                        clear_caches()
                                        st.success("✅ تم تسجيل الحضور اليدوي وإلغاء الغياب")
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"❌ تعذر التحويل: {e}")

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
                        records = daily_schedule_sheet.get_all_records()
                        # نجمع كل التحديثات في batch واحد
                        batch_updates = []
                        for i, r in enumerate(records):
                            if str(r.get("التاريخ","")).strip() == daily_date_str:
                                batch_updates.append({
                                    "range": f"C{i+2}",
                                    "values": [["لا"]]
                                })
                        if batch_updates:
                            daily_schedule_sheet.batch_update(batch_updates)
                        import time as _t; _t.sleep(1)
                        for t in daily_tasks_selected:
                            daily_schedule_sheet.append_row([daily_date_str, t, "نعم", daily_note], value_input_option="USER_ENTERED")
                            _t.sleep(0.3)
                        get_daily_schedule_records.clear()
                        st.success("✅ تم حفظ دوام التاريخ المحدد.")
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
                            batch_updates = []
                            for i, r in enumerate(records):
                                if str(r.get("التاريخ","")).strip() == daily_date_str:
                                    batch_updates.append({"range": f"C{i+2}", "values": [["لا"]]})
                            if batch_updates:
                                daily_schedule_sheet.batch_update(batch_updates)
                            get_daily_schedule_records.clear()
                            st.success("✅ تم تعطيل دوام هذا التاريخ.")
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

            emp_preview = validate_employee(m_id) if m_id else None
            manual_support_mode = False
            if m_id and not emp_preview:
                st.warning("⚠️ الرقم غير موجود في القائمة البيضاء. إذا كانت الموظفة دعم خارجي، فعّلي الخيار التالي وأدخلي بياناتها يدويًا.")
                manual_support_mode = st.checkbox("تسجيل كدعم خارجي غير موجود في القائمة البيضاء", key="manual_support_mode")
            if m_id and emp_preview:
                st.success(f"✅ تم العثور على البيانات: {emp_preview.get('الاسم','')} — {emp_preview.get('المدرسة','')} — {emp_preview.get('المهمة','')}")

            if manual_support_mode:
                m_support_name = st.text_input("اسم الدعم", key="manual_support_name")
                school_choice = st.selectbox("مدرسة الدعم", schools + ["أخرى"], key="manual_support_school_choice")
                if school_choice == "أخرى":
                    m_support_school = st.text_input("اكتبي اسم المدرسة", key="manual_support_school_other").strip()
                else:
                    m_support_school = school_choice
                m_support_task = st.selectbox("مهمة الدعم", TASKS_SUPPORT, key="manual_support_task")

            if st.button("تسجيل يدوي",use_container_width=True,type="primary"):
                if not m_id:
                    st.error("❌ الرقم الشخصي مطلوب")
                elif not m_note.strip():
                    st.error("❌ سبب الإضافة اليدوية مطلوب")
                else:
                    emp=validate_employee(m_id)
                    if not emp and not manual_support_mode:
                        st.error("❌ الرقم غير موجود في القائمة البيضاء. إذا كانت الموظفة دعم خارجي فعّلي خيار تسجيل كدعم خارجي.")
                    else:
                        if not emp and manual_support_mode:
                            if not m_support_name.strip() or not m_support_school.strip():
                                st.error("❌ اسم الدعم والمدرسة مطلوبان")
                                st.stop()
                            emp = {"الاسم": normalize_name(m_support_name), "المدرسة": m_support_school, "المهمة": m_support_task, "دعم": "نعم"}
                        date_str=str(m_date)
                        day_name=m_date.strftime("%A")
                        task=str(emp.get("المهمة","")).strip()

                        # تحديد قيمة عمود دعم من القائمة البيضاء أو من اسم المهمة أو خيار الدعم اليدوي
                        support_raw=str(emp.get("دعم","")).strip()
                        support_value="نعم" if manual_support_mode or support_raw in ["نعم","yes","Yes","TRUE","true","1"] or "دعم" in task else "لا"
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
                            "",                             # N محاولة
                            "", "", "", "", "", "", "", "", # O:V احتسابات لاحقة
                            "تسجيل يدوي" if support_value != "نعم" else "تسجيل دعم يدوي"  # W نوع التسجيل
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

            # ── تنظيف تكرارات القائمة البيضاء ──
            with st.container(border=True):
                st.markdown("##### 🧹 تنظيف تكرارات القائمة البيضاء")
                st.caption("يبحث عن الأرقام الشخصية المكررة ويحذف النسخ الزائدة — يبقي آخر صف لكل رقم.")

                try:
                    all_wl = whitelist_sheet.get_all_records()
                    dup_ids = {}
                    for i, r in enumerate(all_wl):
                        eid = str(r.get("الرقم الشخصي","")).strip()
                        if eid:
                            dup_ids.setdefault(eid, []).append(i+2)
                    dups = {k:v for k,v in dup_ids.items() if len(v)>1}

                    if not dups:
                        st.success("✅ لا توجد تكرارات في القائمة البيضاء.")
                    else:
                        total_dup = sum(len(v)-1 for v in dups.values())
                        st.warning(f"⚠️ وجد {len(dups)} رقم مكرر — إجمالي الصفوف الزائدة: {total_dup}")
                        for eid, rows in list(dups.items())[:5]:
                            name = str(all_wl[rows[0]-2].get("الاسم","")).strip()
                            st.markdown(f"- **{name}** (#{eid}) — {len(rows)} مرة")
                        if len(dups) > 5:
                            st.markdown(f"- ... و{len(dups)-5} آخرين")

                        if st.button("🗑️ حذف التكرارات — إبقاء الصف الأكمل بياناتً لكل رقم",
                                     use_container_width=True, type="primary", key="btn_clean_wl_dups"):
                            rows_to_delete = []
                            for eid, rows in dups.items():
                                # احسب اكتمال كل صف (عدد الخلايا غير الفارغة)
                                scored = []
                                for rn in rows:
                                    r = all_wl[rn-2]
                                    score = sum(1 for v in r.values() if str(v).strip())
                                    scored.append((score, rn))
                                # ابقي الصف الأكمل، احذف الباقي
                                best_rn = max(scored, key=lambda x: x[0])[1]
                                rows_to_delete.extend([rn for rn in rows if rn != best_rn])
                            # نحذف من الأكبر للأصغر عشان ما تتأثر الأرقام
                            rows_to_delete = sorted(set(rows_to_delete), reverse=True)
                            deleted = 0
                            errors  = 0
                            prog = st.progress(0)
                            for j, rn in enumerate(rows_to_delete):
                                prog.progress((j+1)/len(rows_to_delete))
                                try:
                                    whitelist_sheet.delete_rows(rn)
                                    deleted += 1
                                except Exception:
                                    errors += 1
                            get_whitelist.clear()
                            log_audit("—","أدمن","تنظيف تكرارات القائمة البيضاء",
                                      f"محذوف:{deleted}|أخطاء:{errors}")
                            st.success(f"✅ تم حذف {deleted} صف مكرر. أخطاء: {errors}")
                            st.rerun()
                except Exception as e:
                    st.error(f"❌ خطأ: {e}")

            st.markdown("---")
            st.markdown("#### إضافة موظفة")
            wl_id=ar_to_en_digits(st.text_input("الرقم الشخصي",key="wlid")).strip()
            wl_name=st.text_input("الاسم",key="wlname")
            wl_school=st.selectbox("المدرسة",schools + ["أخرى"],key="wlschool")
            if wl_school == "أخرى":
                wl_school_final = st.text_input("اكتبي اسم المدرسة", key="wlschool_other").strip()
            else:
                wl_school_final = wl_school
            wl_task=st.selectbox("المهمة",TASKS_ALL,key="wltask")
            wl_job=st.selectbox("المسمى الوظيفي",JOB_TITLES,key="wljob")
            wl_phone=st.text_input("رقم التواصل", key="wlphone")
            wl_email=st.text_input("البريد الإلكتروني", key="wlemail")
            if st.button("إضافة",use_container_width=True):
                if not wl_id.strip() or not wl_name.strip() or not wl_school_final.strip():
                    st.error("الرقم والاسم والمدرسة مطلوبة")
                else:
                    ok=safe_append(whitelist_sheet,[wl_id,normalize_name(wl_name),wl_school_final,wl_task,"نعم" if "دعم" in wl_task else "لا",wl_phone,wl_email,wl_job,"نعم"])
                    get_whitelist.clear()
                    if ok:
                        log_audit(wl_id, normalize_name(wl_name), "إضافة للقائمة البيضاء", f"المدرسة:{wl_school_final}|المهمة:{wl_task}")
                        st.success("✅ تمت الإضافة")
                    else: st.error("❌ تعذرت الإضافة")

            st.markdown("---")
            st.markdown("#### ✏️ بحث وتعديل بيانات موظفة")
            search_wl = st.text_input("ابحثي بالرقم الشخصي أو الاسم", key="wl_search_edit")
            wl_records_full = []
            try:
                wl_records_full = whitelist_sheet.get_all_records()
            except Exception:
                wl_records_full = []

            matches = []
            if search_wl.strip():
                q = normalize_name(search_wl)
                for i, r in enumerate(wl_records_full, start=2):
                    eid = str(r.get("الرقم الشخصي", "")).strip()
                    nm = normalize_name(r.get("الاسم", ""))
                    if q in normalize_name(eid) or q in nm:
                        matches.append((i, r))
            else:
                matches = list(enumerate(wl_records_full[-30:], start=max(2, len(wl_records_full)-28)))
                st.caption("يعرض آخر 30 سجل. للبحث الدقيق اكتبي الرقم الشخصي أو جزءًا من الاسم.")

            if not matches:
                st.info("لا توجد نتائج مطابقة.")
            else:
                for row_num, emp in matches[:20]:
                    eid = str(emp.get("الرقم الشخصي", "")).strip()
                    with st.expander(f"✏️ {emp.get('الاسم','')} — #{eid} — {emp.get('المدرسة','')}", expanded=False):
                        edit_name = st.text_input("الاسم", value=emp.get("الاسم", ""), key=f"edit_wl_name_{row_num}")
                        school_current = emp.get("المدرسة", "") if emp.get("المدرسة", "") in schools else "أخرى"
                        edit_school_choice = st.selectbox("المدرسة", schools + ["أخرى"], index=(schools + ["أخرى"]).index(school_current), key=f"edit_wl_school_{row_num}")
                        if edit_school_choice == "أخرى":
                            edit_school = st.text_input("اكتبي اسم المدرسة", value=emp.get("المدرسة", ""), key=f"edit_wl_school_other_{row_num}").strip()
                        else:
                            edit_school = edit_school_choice
                        task_list = TASKS_ALL
                        task_current = emp.get("المهمة", "") if emp.get("المهمة", "") in task_list else task_list[0]
                        edit_task = st.selectbox("المهمة", task_list, index=task_list.index(task_current), key=f"edit_wl_task_{row_num}")
                        edit_support = st.selectbox("دعم", ["لا", "نعم"], index=1 if is_yes(emp.get("دعم", "")) or "دعم" in str(emp.get("المهمة", "")) else 0, key=f"edit_wl_support_{row_num}")
                        edit_phone = st.text_input("رقم التواصل", value=emp.get("رقم التواصل", ""), key=f"edit_wl_phone_{row_num}")
                        edit_email = st.text_input("البريد الإلكتروني", value=emp.get("البريد الإلكتروني", ""), key=f"edit_wl_email_{row_num}")
                        job_current = emp.get("المسمى الوظيفي", "") if emp.get("المسمى الوظيفي", "") in JOB_TITLES else JOB_TITLES[0]
                        edit_job = st.selectbox("المسمى الوظيفي", JOB_TITLES, index=JOB_TITLES.index(job_current), key=f"edit_wl_job_{row_num}")
                        edit_active = st.selectbox("نشط", ["نعم", "لا"], index=0 if is_yes(emp.get("نشط", "")) else 1, key=f"edit_wl_active_{row_num}")
                        update_today = st.checkbox("تحديث سجل اليوم تلقائيًا أيضًا", value=True, key=f"edit_wl_update_today_{row_num}")
                        edit_reason = st.text_input("سبب التعديل", value="تصحيح بيانات الموظفة", key=f"edit_wl_reason_{row_num}")

                        if st.button("💾 حفظ تعديل بيانات الموظفة", key=f"save_wl_edit_{row_num}", use_container_width=True, type="primary"):
                            if not edit_name.strip() or not edit_school.strip() or not edit_reason.strip():
                                st.error("❌ الاسم والمدرسة وسبب التعديل مطلوبة")
                            else:
                                try:
                                    values = [
                                        eid,
                                        normalize_name(edit_name),
                                        edit_school,
                                        edit_task,
                                        edit_support,
                                        edit_phone,
                                        edit_email,
                                        edit_job,
                                        edit_active
                                    ]
                                    whitelist_sheet.update(f"A{row_num}:I{row_num}", [values], value_input_option="USER_ENTERED")
                                    get_whitelist.clear()
                                    details = f"الاسم:{emp.get('الاسم','')}→{normalize_name(edit_name)}|المدرسة:{emp.get('المدرسة','')}→{edit_school}|المهمة:{emp.get('المهمة','')}→{edit_task}|دعم:{edit_support}|نشط:{edit_active}|السبب:{edit_reason}"

                                    if update_today:
                                        today_matches = find_daily_rows_fresh(today_str, eid)
                                        for idx_today, row_today in today_matches:
                                            safe_update(sheet, idx_today, COL_SCHOOL, edit_school)
                                            safe_update(sheet, idx_today, COL_TASK, edit_task)
                                            safe_update(sheet, idx_today, COL_SUPPORT, edit_support)
                                            safe_update(sheet, idx_today, COL_NAME, normalize_name(edit_name))
                                        if today_matches:
                                            details += f"|تم تحديث سجل اليوم للصفوف:{[x[0] for x in today_matches]}"

                                    log_audit(eid, normalize_name(edit_name), "تعديل القائمة البيضاء", details)
                                    clear_caches()
                                    st.success("✅ تم تعديل بيانات الموظفة وتحديث سجل اليوم تلقائيًا")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"❌ تعذر حفظ التعديل: {e}")

            st.markdown("---")
            st.markdown("#### الموظفات المسجّلات")
            wl_all=get_whitelist()
            for eid,emp in list(wl_all.items())[-50:]:
                st.markdown(f'<div class="audit-row"><b>{emp.get("الاسم","")}</b> — #{eid} — {emp.get("المدرسة","")} — {emp.get("المهمة","")}</div>',unsafe_allow_html=True)

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

        # ── إدارة قفل الجهاز ────────────────────────────────────────
        elif admin_tab=="⚙️ قفل الجهاز":
            st.markdown("#### ⚙️ إدارة قفل الجهاز")
            st.info("الوضع الطبيعي: نفس الجهاز/المتصفح يسجل لشخص واحد فقط طوال اليوم. يمكن تعطيله مؤقتًا للجميع أو استثناء رقم معيّن.")

            global_off, global_end = get_device_lock_global_override()
            if global_off and global_end:
                remaining = max(0, int((global_end - now_bh()).total_seconds() // 60))
                st.warning(f"⚠️ قفل الجهاز معطّل للجميع مؤقتًا حتى {global_end.strftime('%H:%M')} — المتبقي {remaining} دقيقة")
                if st.button("🔒 إعادة تفعيل قفل الجهاز للجميع الآن", use_container_width=True, type="primary"):
                    if disable_device_lock_global_override():
                        log_audit("—", "أدمن", "تفعيل قفل الجهاز", "إلغاء التعطيل العام لقفل الجهاز")
                        st.success("✅ تم إعادة تفعيل قفل الجهاز.")
                        st.rerun()
            else:
                st.success("✅ قفل الجهاز مفعّل حاليًا للجميع.")
                mins = st.selectbox("مدة تعطيل قفل الجهاز للجميع", [15, 30, 60, 90, 120, 180], key="dev_global_minutes")
                note = st.text_input("سبب تعطيل قفل الجهاز للجميع", key="dev_global_note")
                if st.button("🔓 تعطيل قفل الجهاز للجميع مؤقتًا", use_container_width=True):
                    if not note.strip():
                        st.error("❌ السبب مطلوب")
                    else:
                        ok, end_dt = set_device_lock_global_override(mins, note.strip())
                        if ok:
                            log_audit("—", "أدمن", "تعطيل قفل الجهاز للجميع", f"حتى:{end_dt.strftime('%Y-%m-%d %H:%M:%S')}|السبب:{note.strip()}")
                            st.success(f"✅ تم تعطيل قفل الجهاز للجميع حتى {end_dt.strftime('%H:%M')}")
                            st.rerun()

            st.markdown("---")
            st.markdown("#### 👤 استثناء رقم شخصي من قفل الجهاز")
            ex_id = ar_to_en_digits(st.text_input("الرقم الشخصي للاستثناء", key="dev_ex_id")).strip()
            ex_emp = validate_employee(ex_id) if ex_id else None
            ex_name = ex_emp.get("الاسم", "") if ex_emp else ""
            if ex_id and ex_emp:
                st.success(f"الموظفة: {ex_name} — {ex_emp.get('المدرسة','')} — {ex_emp.get('المهمة','')}")
            elif ex_id:
                st.warning("الرقم غير موجود في القائمة البيضاء، يمكن إضافة الاستثناء بالرقم فقط إذا لزم.")
                ex_name = st.text_input("اسم الموظفة للاستثناء", key="dev_ex_name_manual")
            ex_minutes = st.selectbox("مدة الاستثناء", [15, 30, 60, 90, 120, 180, 240], key="dev_ex_minutes")
            ex_note = st.text_input("سبب الاستثناء", key="dev_ex_note")
            cex1, cex2 = st.columns(2)
            with cex1:
                if st.button("➕ إضافة/تفعيل استثناء", use_container_width=True, type="primary"):
                    if not ex_id or not ex_note.strip():
                        st.error("❌ الرقم الشخصي وسبب الاستثناء مطلوبان")
                    else:
                        ok, end_dt = add_device_exception_for_employee(ex_id, ex_name, ex_minutes, ex_note.strip())
                        if ok:
                            log_audit(ex_id, ex_name or "—", "استثناء قفل الجهاز", f"حتى:{end_dt.strftime('%Y-%m-%d %H:%M:%S')}|السبب:{ex_note.strip()}")
                            st.success(f"✅ تم إضافة الاستثناء حتى {end_dt.strftime('%H:%M')}")
                            st.rerun()
            with cex2:
                if st.button("🛑 تعطيل استثناءات هذا الرقم", use_container_width=True):
                    if not ex_id:
                        st.error("❌ أدخلي الرقم الشخصي")
                    else:
                        changed = disable_device_exception_for_employee(ex_id)
                        log_audit(ex_id, ex_name or "—", "تعطيل استثناء قفل الجهاز", f"عدد الاستثناءات المعطلة:{changed}")
                        st.success(f"✅ تم تعطيل {changed} استثناء/استثناءات لهذا الرقم")
                        st.rerun()

            st.markdown("---")
            st.markdown("#### الاستثناءات النشطة")
            active_ex = []
            for r in get_device_exceptions():
                if is_yes(r.get("نشط", "")):
                    end_dt = parse_bahrain_datetime(r.get("تاريخ_الانتهاء", ""))
                    if end_dt and now_bh() < end_dt:
                        active_ex.append((r, end_dt))
            if not active_ex:
                st.success("لا توجد استثناءات نشطة حاليًا.")
            else:
                for r, end_dt in active_ex[-50:]:
                    st.markdown(f'<div class="audit-row">🔓 {r.get("الاسم","")} — #{r.get("الرقم الشخصي","")} — حتى {end_dt.strftime("%H:%M")}<br><small>{r.get("ملاحظات","")}</small></div>', unsafe_allow_html=True)


        # ── الأجهزة الموثوقة ───────────────────────────────────────
        elif admin_tab=="📱 الأجهزة الموثوقة":
            st.markdown("#### 📱 الأجهزة الموثوقة")
            st.info("افتحي هذه الصفحة من جهاز الحضور الاحتياطي داخل المركز، ثم اعتمديه. الجهاز الموثوق يسمح بتسجيل أكثر من موظفة من نفس الجهاز بدون قفل الجهاز.")
            current_fp = get_device_fingerprint()
            trusted_now, trusted_row = is_current_device_trusted()
            if trusted_now:
                st.success(f"✅ هذا الجهاز موثوق حاليًا: {trusted_row.get('اسم الجهاز','جهاز موثوق')}")
            else:
                st.warning("⚠️ هذا الجهاز غير معتمد كجهاز موثوق.")
            dev_name = st.text_input("اسم الجهاز", value="جهاز الحضور الاحتياطي", key="trusted_dev_name")
            dev_note = st.text_input("ملاحظات", value="جهاز مخصص للتسجيل داخل المركز", key="trusted_dev_note")
            if st.button("⭐ اعتماد هذا الجهاز كجهاز موثوق", use_container_width=True, type="primary"):
                if approve_current_device_as_trusted(dev_name, dev_note):
                    log_audit("—", "أدمن", "اعتماد جهاز موثوق", f"اسم الجهاز:{dev_name}|بصمة:{current_fp[:8]}...")
                    st.success("✅ تم اعتماد هذا الجهاز كجهاز موثوق.")
                    st.rerun()
            st.markdown("---")
            st.markdown("#### قائمة الأجهزة الموثوقة")
            rows = get_trusted_devices()
            active_rows = [r for r in rows if is_yes(r.get("نشط", ""))]
            if not active_rows:
                st.info("لا توجد أجهزة موثوقة نشطة.")
            else:
                for idx, r in enumerate(active_rows, start=1):
                    fp = str(r.get("بصمة الجهاز", "")).strip()
                    with st.expander(f"📱 {r.get('اسم الجهاز','جهاز موثوق')} — آخر استخدام: {r.get('آخر استخدام','')}"):
                        st.write(f"ملاحظات: {r.get('ملاحظات','')}")
                        st.code(fp)
                        if st.button("🛑 تعطيل هذا الجهاز", key=f"disable_trusted_{idx}", use_container_width=True):
                            if disable_trusted_device(fp):
                                log_audit("—", "أدمن", "تعطيل جهاز موثوق", f"اسم الجهاز:{r.get('اسم الجهاز','')}|بصمة:{fp[:8]}...")
                                st.success("✅ تم تعطيل الجهاز.")
                                st.rerun()

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

        # ── تصاريح الوقت اليدوي ──────────────────────────────────
        elif admin_tab=="⏰ تصاريح الوقت اليدوي":
            st.markdown("#### ⏰ تصاريح الوقت اليدوي")
            st.info("تسمح للموظفة بتعديل وقت الحضور أو الانصراف يدوياً لتواريخ محددة، بدون GPS وبدون انتظار اعتماد.")

            # ── إضافة تصريح جديد ──
            with st.container(border=True):
                st.markdown("##### ➕ إضافة تصريح جديد")

                permit_scope = st.radio("التصريح لـ", ["موظفة محددة","كل الموظفات"], horizontal=True, key="permit_scope")
                if permit_scope == "موظفة محددة":
                    permit_id_raw = st.text_input("الرقم الشخصي", key="permit_emp_id")
                    permit_id = ar_to_en_digits(permit_id_raw).strip()
                    if permit_id:
                        found_emp = validate_employee(permit_id)
                        if found_emp:
                            st.success(f"✅ {found_emp.get('الاسم','')} — {found_emp.get('المدرسة','')}")
                        else:
                            st.warning("⚠️ الرقم غير موجود في القائمة البيضاء")
                else:
                    permit_id = "الكل"
                    st.warning("⚠️ سيُفعَّل التصريح لجميع الموظفات")

                permit_type = st.selectbox("نوع التصريح", ["كليهما","حضور","انصراف"], key="permit_type")

                st.markdown("**نطاق التاريخ**")
                col_d1, col_d2 = st.columns(2)
                with col_d1:
                    permit_date_from = st.date_input("من تاريخ", value=now_bh().date(), key="permit_from")
                with col_d2:
                    permit_date_to   = st.date_input("إلى تاريخ", value=now_bh().date(), key="permit_to")

                st.markdown("**نافذة الوقت** (اتركيها فارغة ليكون مفتوحاً طول اليوم)")
                col_t1, col_t2 = st.columns(2)
                with col_t1:
                    all_day = st.checkbox("يوم كامل (بدون قيد وقت)", value=True, key="permit_allday")
                with col_t2:
                    permit_note = st.text_input("ملاحظة", key="permit_note")

                if not all_day:
                    col_t3, col_t4 = st.columns(2)
                    with col_t3:
                        permit_open  = st.time_input("وقت الفتح",  value=time(6,0),  key="permit_open")
                    with col_t4:
                        permit_close = st.time_input("وقت الإغلاق", value=time(15,0), key="permit_close")
                    t_open  = permit_open.strftime("%H:%M")
                    t_close = permit_close.strftime("%H:%M")
                else:
                    t_open = t_close = ""

                if permit_date_from > permit_date_to:
                    st.error("❌ تاريخ البداية يجب أن يكون قبل تاريخ النهاية.")
                elif st.button("✅ تفعيل التصريح", use_container_width=True, type="primary", key="btn_add_permit"):
                    if not permit_id:
                        st.error("❌ أدخل الرقم الشخصي أولاً.")
                    else:
                        add_time_permit(
                            permit_id, permit_type,
                            permit_date_from.strftime("%Y-%m-%d"),
                            permit_date_to.strftime("%Y-%m-%d"),
                            t_open, t_close, permit_note
                        )
                        log_audit("—","أدمن","تفعيل تصريح وقت يدوي",
                                  f"رقم:{permit_id}|نوع:{permit_type}|من:{permit_date_from}|إلى:{permit_date_to}|وقت:{t_open or 'يوم كامل'}")
                        scope_lbl = "كل الموظفات" if permit_id=="الكل" else permit_id
                        time_lbl  = "يوم كامل" if all_day else f"{t_open}–{t_close}"
                        st.success(f"✅ تم التفعيل — {scope_lbl} — {permit_type} — {permit_date_from} إلى {permit_date_to} — {time_lbl}")
                        st.rerun()

            # ── التصاريح النشطة ──
            st.markdown("---")
            st.markdown("##### 📋 التصاريح الحالية")
            permits = get_time_permits()
            today_s = now_bh().strftime("%Y-%m-%d")
            for i, p in enumerate(permits):
                is_active = str(p.get("نشط","")).strip() in ["نعم","yes","1","TRUE","true"]
                if not is_active: continue
                p_id    = str(p.get("الرقم الشخصي","")).strip() or "الكل"
                p_type  = str(p.get("نوع التصريح","")).strip()
                d_from  = str(p.get("تاريخ البداية","")).strip()
                d_to    = str(p.get("تاريخ النهاية","")).strip()
                t_open  = str(p.get("وقت الفتح","")).strip()
                t_close = str(p.get("وقت الإغلاق","")).strip()
                p_note  = str(p.get("ملاحظات","")).strip()
                expired = d_to and d_to < today_s
                color   = "#F8D7DA" if expired else "#D4EDDA"
                status  = "منتهي ❌" if expired else "نشط ✅"
                time_w  = f"{t_open}–{t_close}" if t_open else "يوم كامل"
                st.markdown(f"""
                <div style="background:{color};border-radius:10px;padding:10px 14px;margin-bottom:8px;direction:rtl;">
                <b>{'كل الموظفات' if p_id in ['الكل','','*'] else f'#{p_id}'}</b> —
                {p_type} — {d_from} إلى {d_to} — {time_w} — {status}
                {f'<br><small>ملاحظة: {p_note}</small>' if p_note else ''}
                </div>
                """, unsafe_allow_html=True)
                if st.button("🚫 إلغاء", key=f"revoke_{i+2}"):
                    revoke_time_permit_row(i+2)
                    log_audit("—","أدمن","إلغاء تصريح وقت يدوي",f"رقم:{p_id}|نوع:{p_type}")
                    st.success("✅ تم إلغاء التصريح.")
                    st.rerun()

        if st.button("🚪 تسجيل خروج الأدمن",use_container_width=True):
            st.session_state.admin_logged_in=False; st.session_state.admin_last_active=None; st.rerun()


# ─── Footer ─────────────────────────────────────────────────────
st.markdown("""
<div class="footer-bar">
    <span>تصميم وبرمجة: <span class="hl">أ. عفاف حسين</span></span>
    <span>رئيسة المركز: <span class="hl">أ. خلود يعقوب بدو</span></span>
</div>
""", unsafe_allow_html=True)
