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
import hashlib
import json

st.set_page_config(
    page_title="نظام الحضور والانصراف",
    page_icon="🕘",
    layout="centered"
)


# ─── إعدادات المدرسة ───────────────────────────────────────────
SCHOOL_LAT = 26.216371784473964
SCHOOL_LON = 50.54035843289093
ALLOWED_RADIUS = 150

# حد زمني بين تسجيلين حضور من نفس الجهاز (بالدقائق)
DEVICE_COOLDOWN_MINUTES = 10

# ─── Google Sheets ──────────────────────────────────────────────
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]
creds = ServiceAccountCredentials.from_json_keyfile_dict(
    st.secrets["gcp_service_account"], scope
)
client = gspread.authorize(creds)
spreadsheet = client.open_by_key("1svkfgRq4-osKr86_2WJQFZShuoy8Ek5DOiUaaHKL-6Y")
sheet       = spreadsheet.sheet1  # ورقة الحضور الرئيسية

def get_or_create_sheet(name, headers):
    """تجيب ورقة موجودة أو تنشئها بالهيدرز المحددة."""
    try:
        return spreadsheet.worksheet(name)
    except gspread.WorksheetNotFound:
        ws = spreadsheet.add_worksheet(title=name, rows=1000, cols=len(headers))
        ws.append_row(headers)
        return ws

# أوراق إضافية
audit_sheet     = get_or_create_sheet("سجل_التدقيق", [
    "التاريخ", "الوقت", "المستخدم", "الرقم الشخصي",
    "نوع العملية", "التفاصيل", "بصمة الجهاز"
])
whitelist_sheet = get_or_create_sheet("القائمة_البيضاء", [
    "الرقم الشخصي", "الاسم", "المدرسة", "القسم", "نشط"
])
# ─── بيانات الموظفات من ملفات Excel (محمّلة مسبقاً) ──────────────
# مهام كل قسم في الكنترول
TASK_MAP = {
    "اللغة الانجليزية":      "مصححة — اللغة الإنجليزية / Examiner — English",
    "الرياضيات":              "مصححة — الرياضيات / Examiner — Maths",
    "العلوم-فيز":             "مصححة — الفيزياء / Examiner — Physics",
    "العلوم-كيم":             "مصححة — الكيمياء / Examiner — Chemistry",
    "العلوم-حيا":             "مصححة — الأحياء / Examiner — Biology",
    "اللغة العربية":          "مصححة — اللغة العربية / Examiner — Arabic",
    "العلوم التجارية":        "مصححة — العلوم التجارية / Examiner — Commerce",
    "المواد الاجتماعية":      "مصححة — المواد الاجتماعية / Examiner — Social Studies",
    "التربية الاسلامية":      "مصححة — التربية الإسلامية / Examiner — Islamic Studies",
    "التربية الأسرية":        "مصححة — التربية الأسرية / Examiner — Home Economics",
    "التربية الفنية":         "مصححة — التربية الفنية / Examiner — Art",
    "التقن":                  "مصححة — الحاسب الآلي / Examiner — Computer",
    "التربية البدنية ":       "مصححة — التربية البدنية / Examiner — PE",
    " الكنترول الخارجي الدعم الفني":       "كنترول خارجي — دعم فني / External Control — IT Support",
    " الكنترول الخارجي رصد الدرجات":      "كنترول خارجي — رصد الدرجات / External Control — Grade Entry",
    " الكنترول الخارجي الضبط المركزي":    "كنترول خارجي — ضبط مركزي / External Control — Central Control",
}

@st.cache_data(ttl=3600)
def load_excel_employees():
    """تقرأ ملفات Excel وتبني قاموس الموظفات بمهامهن."""
    import os
    import pandas as pd

    excel_files = [
        "كشف_المعلمات_المصححات_وعضوات_الكنترول_الخارجي__الفصل_الدراسي_الثاني_للعام_الدراسي_20252026.xlsx",
        "كشف_المعلمات_المصححات_وعضوات_الكنترول_الخارجي__الفصل_الدراسي_الثاني_للعام_الدراسي_20252026_1.xlsx",
        "كشف_المعلمات_المصححات_وعضوات_الكنترول_الخارجي__الفصل_الدراسي_الثاني_للعام_الدراسي_20252026_2.xlsx",
        "كشف_المعلمات_المصححات_وعضوات_الكنترول_الخارجي__الفصل_الدراسي_الثاني_للعام_الدراسي_20252026_1_1.xlsx",
    ]

    subject_sheets = [
        "اللغة الانجليزية","الرياضيات","العلوم-فيز","العلوم-كيم","العلوم-حيا",
        "اللغة العربية","العلوم التجارية","المواد الاجتماعية","التربية الاسلامية",
        "التربية الأسرية","التربية الفنية","التقن","التربية البدنية ",
    ]
    control_sheets = [
        " الكنترول الخارجي الدعم الفني",
        " الكنترول الخارجي رصد الدرجات",
        " الكنترول الخارجي الضبط المركزي",
    ]

    employees = {}

    for fpath in excel_files:
        if not os.path.exists(fpath):
            continue
        try:
            xl = pd.ExcelFile(fpath)
            school_df = pd.read_excel(fpath, sheet_name="بيانات المدرسة", header=None)
            school_name = str(school_df.iloc[3, 1]).strip() if pd.notna(school_df.iloc[3, 1]) else ""

            # شيتات المصححات
            for sheet_name in subject_sheets:
                if sheet_name not in xl.sheet_names:
                    continue
                task = TASK_MAP.get(sheet_name, "مصححة / Examiner")
                df = pd.read_excel(fpath, sheet_name=sheet_name, header=None)
                for _, row in df.iloc[6:].iterrows():
                    emp_id = str(row.iloc[3]).strip() if pd.notna(row.iloc[3]) else ""
                    name   = str(row.iloc[1]).strip() if pd.notna(row.iloc[1]) else ""
                    phone  = str(row.iloc[4]).strip() if pd.notna(row.iloc[4]) else ""
                    job    = str(row.iloc[2]).strip() if pd.notna(row.iloc[2]) else ""
                    skip   = ["nan","NaN","","لا يوجد","لايوجد","_"]
                    if emp_id in skip or name in skip or not emp_id.isdigit():
                        continue
                    if emp_id not in employees:
                        employees[emp_id] = {
                            "الرقم الشخصي": emp_id, "الاسم": name,
                            "المدرسة": school_name, "رقم التواصل": phone,
                            "المسمى الوظيفي": job, "المهمة": task,
                        }
                    else:
                        existing_task = employees[emp_id]["المهمة"]
                        if task not in existing_task:
                            employees[emp_id]["المهمة"] = existing_task + "\n" + task

            # شيتات الكنترول الخارجي
            for sheet_name in control_sheets:
                if sheet_name not in xl.sheet_names:
                    continue
                task = TASK_MAP.get(sheet_name, "كنترول خارجي / External Control")
                df = pd.read_excel(fpath, sheet_name=sheet_name, header=None)
                for _, row in df.iloc[7:].iterrows():
                    emp_id = str(row.iloc[5]).strip() if pd.notna(row.iloc[5]) else ""
                    name   = str(row.iloc[2]).strip() if pd.notna(row.iloc[2]) else ""
                    phone  = str(row.iloc[6]).strip() if pd.notna(row.iloc[6]) else ""
                    job    = str(row.iloc[3]).strip() if pd.notna(row.iloc[3]) else ""
                    skip   = ["nan","NaN","","لا يوجد","لايوجد","_"]
                    if emp_id in skip or name in skip or not emp_id.isdigit():
                        continue
                    if emp_id not in employees:
                        employees[emp_id] = {
                            "الرقم الشخصي": emp_id, "الاسم": name,
                            "المدرسة": school_name, "رقم التواصل": phone,
                            "المسمى الوظيفي": job, "المهمة": task,
                        }
                    else:
                        existing_task = employees[emp_id]["المهمة"]
                        if task not in existing_task:
                            employees[emp_id]["المهمة"] = existing_task + "\n" + task
        except Exception:
            continue

    return employees

EXCEL_EMPLOYEES = load_excel_employees()

def get_excel_employee(emp_id):
    """تجيب بيانات الموظفة من Excel مباشرة بالرقم الشخصي."""
    return EXCEL_EMPLOYEES.get(str(emp_id).strip())



# ─── بيانات ثابتة ───────────────────────────────────────────────
schools = [
    "مدرسة النور الثانوية للبنات",
    "مدرسة المعرفة الثانوية للبنات",
    "مدرسة الرفاع الغربي الثانوية للبنات",
    "مدرسة جدحفص الثانوية للبنات"
]
sections = [
    "قسم اللغة العربية", "قسم اللغة الانجليزية", "قسم الرياضيات",
    "قسم العلوم", "قسم الحاسب الآلي", "قسم التربية الإسلامية",
    "قسم التربية الأسرية", "قسم التربية الفنية", "قسم التربية البدنية",
    "قسم المواد التجارية", "قسم المواد الإجتماعية والإنسانية",
    "الهيئة الإدارية", "الإشراف التربوي",
    "قسم اللغة العربية — دعم", "قسم اللغة الانجليزية — دعم",
    "قسم الرياضيات — دعم", "قسم العلوم — دعم",
    "قسم الحاسب الآلي — دعم", "قسم التربية الإسلامية — دعم",
    "قسم التربية الأسرية — دعم", "قسم التربية الفنية — دعم",
    "قسم التربية البدنية — دعم", "قسم المواد التجارية — دعم",
    "قسم المواد الإجتماعية والإنسانية — دعم",
    "الهيئة الإدارية — دعم", "الإشراف التربوي — دعم"
]
reasons = ["دوام مرن", "موعد", "مهمة رسمية", "رعاية", "أخرى"]

# ─── CSS الاحترافي ───────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;900&display=swap');

html, body, [class*="css"] {
    direction: rtl;
    text-align: right;
    font-family: 'Cairo', Tahoma, sans-serif;
}

.block-container { max-width: 620px; padding-top: 0px; padding-bottom: 40px; }

/* ── هيدر ── */
.app-header {
    background: linear-gradient(135deg, #0c3460 0%, #1a5276 60%, #1f6fa3 100%);
    border-radius: 0 0 28px 28px;
    padding: 28px 24px 32px;
    text-align: center;
    margin: -1rem -1rem 20px -1rem;
    position: relative;
}
.app-header .sub { color: rgba(255,255,255,0.78); font-size: 12px; font-weight: 600; margin-bottom: 6px; }
.app-header .title { color: #fff; font-size: 22px; font-weight: 900; }
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

/* ── كارد ── */
.pro-card {
    background: #fff;
    border-radius: 20px;
    padding: 18px 20px;
    box-shadow: 0 2px 14px rgba(12,52,96,0.07);
    margin-bottom: 14px;
}
.card-head {
    display: flex; align-items: center; gap: 10px; margin-bottom: 14px;
}
.card-ico {
    width: 36px; height: 36px; border-radius: 10px;
    display: flex; align-items: center; justify-content: center; font-size: 17px; flex-shrink: 0;
}

/* ── حقول ── */
.field-lbl { font-size: 11px; font-weight: 700; color: #888780; margin-bottom: 3px; }
.field-val {
    background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 12px;
    padding: 10px 14px; font-size: 14px; font-weight: 700; color: #0c3460;
    margin-bottom: 10px;
}
.field-val.locked { background: #eaf3de; border-color: #c0dd97; color: #27500A; }

/* ── موقع ── */
.loc-ok  { display:flex;align-items:center;gap:10px;background:#eaf3de;border-radius:12px;padding:11px 14px;margin-bottom:8px; }
.loc-err { display:flex;align-items:center;gap:10px;background:#fcebeb;border-radius:12px;padding:11px 14px;margin-bottom:8px; }
.loc-dot-g { width:10px;height:10px;border-radius:50%;background:#3B6D11;flex-shrink:0;box-shadow:0 0 0 3px rgba(59,109,17,.2); }
.loc-dot-r { width:10px;height:10px;border-radius:50%;background:#A32D2D;flex-shrink:0; }
.loc-txt-g { font-size:13px;font-weight:700;color:#27500A; }
.loc-txt-r { font-size:13px;font-weight:700;color:#791F1F; }

/* ── شريط اليوم ── */
.today-strip {
    display:flex; justify-content:space-around;
    background:#f0f4f8; border-radius:12px; padding:12px 8px; margin-bottom:14px;
}
.stat-cell { text-align:center; }
.stat-val  { font-size:17px; font-weight:900; color:#0c3460; display:block; }
.stat-lbl  { font-size:10px; font-weight:600; color:#888780; }

/* ── أزرار العمليات ── */
.ops-grid { display:grid; grid-template-columns:1fr 1fr; gap:10px; }
.op-btn {
    border-radius:16px; padding:16px 8px; border:none; cursor:pointer;
    display:flex; flex-direction:column; align-items:center; gap:6px;
    font-family:'Cairo',sans-serif; width:100%;
}
.op-btn .op-lbl { font-size:13px; font-weight:800; text-align:center; color:#fff; }
.op-attend { background: linear-gradient(135deg,#3B6D11,#639922); }
.op-depart { background: linear-gradient(135deg,#185FA5,#378ADD); }
.op-exit   { background: linear-gradient(135deg,#854F0B,#BA7517); }
.op-return { background: linear-gradient(135deg,#3C3489,#7F77DD); }

/* ── تحذير جهاز ── */
.device-warn {
    background:#faeeda; border:1px solid #EF9F27; border-radius:12px;
    padding:11px 14px; font-size:12px; font-weight:700; color:#633806; margin-bottom:10px;
}

/* ── أدمن ── */
.admin-header {
    background: linear-gradient(135deg,#26215C,#3C3489);
    border-radius:16px; padding:16px 20px; margin-bottom:14px; text-align:center;
}
.admin-header .t { color:#fff; font-size:18px; font-weight:900; }
.admin-header .s { color:rgba(255,255,255,.75); font-size:12px; }

.admin-section { font-size:11px;font-weight:700;color:#888780;letter-spacing:.5px;margin:16px 0 8px; }

.audit-row {
    background:#f8fafc; border-radius:10px; padding:10px 14px;
    border-right:3px solid #378ADD; margin-bottom:6px; font-size:12px; color:#0c3460;
}
.audit-row .ar-op  { font-weight:900; font-size:13px; }
.audit-row .ar-det { color:#5F5E5A; font-weight:600; margin-top:2px; }
.audit-row .ar-time{ color:#888780; font-size:11px; float:left; }

.warn-row {
    background:#faeeda; border-radius:10px; padding:10px 14px;
    border-right:3px solid #BA7517; margin-bottom:6px; font-size:12px; color:#633806; font-weight:700;
}

/* ── فوتر ── */
.footer-bar {
    background:#0c3460; border-radius:14px; padding:12px 18px;
    display:flex; justify-content:space-between; align-items:center; margin-top:6px;
}
.footer-bar span { font-size:11px; font-weight:600; color:rgba(255,255,255,.7); }
.footer-bar .hl  { color:#fff; }

label, .stSelectbox label, .stTextInput label {
    font-size:15px !important; font-weight:700 !important; color:#0c3460 !important;
}
.stSelectbox div[data-baseweb="select"] > div, .stTextInput input {
    border-radius:12px !important; font-size:14px !important; background-color:#f8fafc !important;
}
.stButton button {
    border-radius:14px !important; font-size:15px !important;
    font-weight:800 !important; font-family:'Cairo',sans-serif !important;
}
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


def get_device_fingerprint():
    """تولّد بصمة للجهاز — تحاول LocalStorage أولاً ثم session_state."""
    import random, string
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
    """تجيب قيمة من LocalStorage بأمان."""
    if LOCAL_STORAGE_OK:
        try:
            return localS.getItem(key)
        except Exception:
            pass
    return st.session_state.get(f"ls_{key}")

def ls_set(key, value, ls_key=None):
    """تحفظ قيمة في LocalStorage بأمان."""
    if LOCAL_STORAGE_OK:
        try:
            localS.setItem(key, value, key=ls_key or f"set_{key}")
            return
        except Exception:
            pass
    st.session_state[f"ls_{key}"] = value

def get_whitelist():
    """تجيب قائمة الأرقام الشخصية المسموح لها."""
    try:
        records = whitelist_sheet.get_all_records()
        return {str(r["الرقم الشخصي"]): r for r in records if str(r.get("نشط","")).strip() == "نعم"}
    except Exception:
        return {}

def validate_employee(emp_id):
    """تتحقق من الرقم الشخصي في القائمة البيضاء."""
    wl = get_whitelist()
    return wl.get(str(emp_id).strip())

def find_today_row(data, today, emp_id):
    for i, row in enumerate(data):
        if str(row.get("الرقم الشخصي","")).strip() == str(emp_id).strip() \
           and row.get("التاريخ") == today:
            return i + 2, row
    return None, None

def get_device_last_attendance(today):
    """تجيب آخر وقت سُجّل فيه حضور من هذا الجهاز اليوم."""
    fp = get_device_fingerprint()
    try:
        records = audit_sheet.get_all_records()
        times = []
        for r in records:
            if r.get("التاريخ") == today \
               and str(r.get("بصمة الجهاز","")) == fp \
               and r.get("نوع العملية") == "تسجيل حضور":
                times.append(r.get("الوقت",""))
        if times:
            return max(times)
    except Exception:
        pass
    return None

def get_device_registrations_today(today):
    """تجيب كل الأرقام الشخصية التي سجّلت حضوراً من هذا الجهاز اليوم."""
    fp = get_device_fingerprint()
    ids = []
    try:
        records = audit_sheet.get_all_records()
        for r in records:
            if r.get("التاريخ") == today \
               and str(r.get("بصمة الجهاز","")) == fp \
               and r.get("نوع العملية") == "تسجيل حضور":
                ids.append(str(r.get("الرقم الشخصي","")))
    except Exception:
        pass
    return ids

def log_audit(emp_id, emp_name, operation, details):
    now = datetime.now()
    fp  = get_device_fingerprint()
    audit_sheet.append_row([
        now.strftime("%Y-%m-%d"),
        now.strftime("%H:%M:%S"),
        emp_name,
        str(emp_id),
        operation,
        details,
        fp
    ])

def register_operation(operation, emp_id, note=""):
    if not st.session_state.get("location_allowed", False):
        st.error("❌ لا يمكن التسجيل خارج نطاق المدرسة")
        return False

    emp_id = str(emp_id).strip()
    if not emp_id:
        st.error("❌ الرقم الشخصي مطلوب")
        return False

    # جيب بيانات الموظفة — من القائمة البيضاء أو من session_state (موظفة جديدة)
    emp = validate_employee(emp_id)
    if not emp:
        emp = st.session_state.get("emp_data")
        if not emp or str(emp.get("الرقم الشخصي","")).strip() != emp_id:
            st.error("❌ بيانات غير مكتملة")
            return False

        # احفظ الموظفة الجديدة في القائمة البيضاء (إلا دعم)
        is_support = emp.get("دعم", False)
        if not is_support:
            try:
                whitelist_sheet.append_row([
                    emp_id,
                    emp.get("الاسم",""),
                    emp.get("المدرسة",""),
                    emp.get("القسم",""),
                    "نعم"
                ])
                log_audit(emp_id, emp.get("الاسم",""), "تسجيل موظفة جديدة",
                          f"مدرسة: {emp.get('المدرسة','')} | قسم: {emp.get('القسم','')}")
            except Exception as e:
                st.warning(f"⚠️ تعذّر الحفظ في القائمة البيضاء: {e}")

    full_name = normalize_name(emp.get("الاسم",""))
    school    = emp.get("المدرسة", schools[0])
    section   = emp.get("القسم",   sections[0])

    now      = datetime.now()
    today    = now.strftime("%Y-%m-%d")
    day_name = now.strftime("%A")
    time_now = now.strftime("%H:%M:%S")

    data = sheet.get_all_records()
    row_index, row = find_today_row(data, today, emp_id)

    # ── فحص بصمة الجهاز (حضور فقط) ──
    if operation == "تسجيل حضور":
        last_att = get_device_last_attendance(today)
        if last_att:
            last_dt = datetime.strptime(f"{today} {last_att}", "%Y-%m-%d %H:%M:%S")
            diff_min = (now - last_dt).seconds // 60
            if diff_min < DEVICE_COOLDOWN_MINUTES:
                remaining = DEVICE_COOLDOWN_MINUTES - diff_min
                st.error(f"⚠️ تم تسجيل حضور من هذا الجهاز منذ {diff_min} دقيقة فقط. "
                         f"يجب الانتظار {remaining} دقيقة أخرى.")
                return False

        if row_index and row.get("وقت الحضور"):
            st.error("❌ تم تسجيل الحضور مسبقاً لهذا الرقم الشخصي اليوم")
            return False

        if row_index:
            sheet.update_cell(row_index, 7, time_now)
            sheet.update_cell(row_index, 8, note)
        else:
            sheet.append_row([
                today, day_name, school, section,
                full_name, emp_id,
                time_now, note,
                "", "", "", "", ""
            ])
        log_audit(emp_id, full_name, "تسجيل حضور", f"الوقت: {time_now} | السبب: {note or 'بدون'}")

    elif operation == "تسجيل انصراف":
        if not row_index or not row.get("وقت الحضور"):
            st.error("❌ لا يوجد تسجيل حضور لهذا الرقم اليوم")
            return False
        if row.get("وقت الانصراف"):
            st.error("❌ تم تسجيل الانصراف مسبقاً")
            return False
        sheet.update_cell(row_index, 9, time_now)
        sheet.update_cell(row_index, 10, note)
        log_audit(emp_id, full_name, "تسجيل انصراف", f"الوقت: {time_now} | السبب: {note or 'بدون'}")

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
        sheet.update_cell(row_index, 11, time_now)
        sheet.update_cell(row_index, 13, note)
        log_audit(emp_id, full_name, "خروج استئذان", f"الوقت: {time_now} | السبب: {note}")

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
        sheet.update_cell(row_index, 12, time_now)
        log_audit(emp_id, full_name, "عودة من استئذان", f"الوقت: {time_now}")

    st.session_state.pending_operation = None
    st.success(f"✅ تم {operation} بنجاح")

    # ── احفظ بيانات الموظفة لتثبيتها طول اليوم ──
    if operation == "تسجيل حضور":
        # احفظ في session_state كـ lock دائم
        st.session_state.data_locked_today = True
        st.session_state.locked_emp = {
            "الرقم الشخصي": emp_id,
            "الاسم": full_name,
            "المدرسة": school,
            "القسم": section,
            "دعم": emp.get("دعم", False)
        }
        st.session_state.locked_date = today
        # احفظ في LocalStorage أيضاً للاستمرارية بين الجلسات
        ls_set("saved_date",    today,     "sv_date")
        ls_set("saved_id",      emp_id,    "sv_id")
        ls_set("saved_name",    full_name, "sv_name")
        ls_set("saved_school",  school,    "sv_school")
        ls_set("saved_section", section,   "sv_section")
        ls_set("saved_support", "نعم" if emp.get("دعم") else "لا", "sv_support")

    return True

# ══════════════════════════════════════════════════════════════════
#  SESSION STATE
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
}.items():
    if k not in st.session_state:
        st.session_state[k] = v

today_str = datetime.now().strftime("%Y-%m-%d")
fp        = get_device_fingerprint()

# ── تحميل البيانات المحفوظة من LocalStorage ──
_saved_date    = ls_get("saved_date")
_saved_id      = ls_get("saved_id")
_saved_name    = ls_get("saved_name")
_saved_school  = ls_get("saved_school")
_saved_section = ls_get("saved_section")
_saved_support = ls_get("saved_support")

# هل البيانات مقفلة؟ — نتحقق من session_state أولاً ثم LocalStorage
_session_locked = (
    st.session_state.get("data_locked_today", False)
    and st.session_state.get("locked_date") == today_str
    and not st.session_state.get("data_unlocked", False)
)

_data_locked = _session_locked or (
    _saved_date == today_str
    and _saved_id and str(_saved_id).strip() != ""
    and not st.session_state.get("data_unlocked", False)
)

# لو مقفل — حمّل emp_data من session_state أو LocalStorage
if _data_locked and not st.session_state.emp_verified:
    locked_emp = st.session_state.get("locked_emp") or {
        "الرقم الشخصي": _saved_id,
        "الاسم": _saved_name or "",
        "المدرسة": _saved_school or (schools[0] if schools else ""),
        "القسم": _saved_section or (sections[0] if sections else ""),
        "نشط": "نعم",
        "دعم": _saved_support == "نعم"
    }
    st.session_state.emp_verified = True
    st.session_state.emp_data = locked_emp

# انتهاء جلسة الأدمن بعد 30 دقيقة خمول
if st.session_state.admin_logged_in and st.session_state.admin_last_active:
    idle = (datetime.now() - st.session_state.admin_last_active).seconds // 60
    if idle >= 30:
        st.session_state.admin_logged_in = False
        st.session_state.admin_last_active = None
        st.warning("⏱️ انتهت جلسة الأدمن بسبب الخمول")

# ══════════════════════════════════════════════════════════════════
#  HEADER
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

# ══════════════════════════════════════════════════════════════════
#  وضع الأدمن / المستخدم
# ══════════════════════════════════════════════════════════════════
mode = st.radio("", ["👤 موظفة", "🛡️ أدمن"], horizontal=True, label_visibility="collapsed")

# ══════════════════════════════════════════════════════════════════
#  ══ واجهة الموظفة ══
# ══════════════════════════════════════════════════════════════════
if mode == "👤 موظفة":

    # ── كارد الموقع ──────────────────────────────────────────────
    with st.container(border=True):
        st.markdown('<div class="card-head"><div class="card-ico" style="background:#e6f1fb;">📍</div><b style="color:#0c3460;font-size:15px;">التحقق من الموقع — Location Check</b></div>', unsafe_allow_html=True)
        location = streamlit_geolocation()
        dist_val = None

        if location:
            lat   = location.get("latitude")
            lon   = location.get("longitude")
            error = location.get("error", "")

            if error:
                st.session_state.location_allowed = False
                st.markdown("""
<div style="background:#fcebeb;border:1px solid #f09595;border-radius:12px;padding:14px 16px;font-size:13px;line-height:1.9;">
<b style="color:#791F1F;font-size:14px;">📵 الموقع غير مفعّل — Location Disabled</b><br><br>
<b style="color:#A32D2D;">📱 iPhone (iOS):</b><br>
الإعدادات ← الخصوصية وأمن المعلومات ← خدمات الموقع ← Safari / المتصفح ← <b>أثناء الاستخدام</b><br>
<span style="color:#5F5E5A;font-size:12px;">Settings → Privacy &amp; Security → Location Services → Safari/Browser → <b>While Using</b></span>
<br><br>
<b style="color:#A32D2D;">🤖 Android:</b><br>
الإعدادات ← التطبيقات ← المتصفح ← الأذونات ← الموقع ← <b>السماح أثناء الاستخدام</b><br>
<span style="color:#5F5E5A;font-size:12px;">Settings → Apps → Browser → Permissions → Location → <b>Allow while using</b></span>
<br><br>
<span style="color:#791F1F;font-size:12px;">⚡ بعد التفعيل أغلقي المتصفح وافتحيه من جديد — After enabling, close &amp; reopen the browser</span>
</div>
""", unsafe_allow_html=True)

            elif lat is not None and lon is not None:
                try:
                    dist_val = distance_m(float(lat), float(lon), SCHOOL_LAT, SCHOOL_LON)
                    if dist_val <= ALLOWED_RADIUS:
                        st.session_state.location_allowed = True
                        st.success(f"✅ داخل نطاق المدرسة — Inside school zone | {int(dist_val)} م")
                    else:
                        st.session_state.location_allowed = False
                        st.error(f"❌ خارج النطاق — Outside zone | {int(dist_val)} م")
                except Exception:
                    st.session_state.location_allowed = False
                    st.error("❌ خطأ في قراءة الموقع — Location read error")
            else:
                st.session_state.location_allowed = False
                st.markdown("""
<div style="background:#faeeda;border:1px solid #EF9F27;border-radius:12px;padding:12px 16px;font-size:13px;line-height:1.9;">
<b style="color:#633806;">⚠️ اضغطي زر تحديد الموقع — Press location button first</b><br><br>
إذا لم يظهر طلب الإذن، فعّلي الموقع من الإعدادات:<br>
<span style="color:#5F5E5A;font-size:12px;">If no permission prompt appears, enable location in settings:</span><br><br>
<b>📱 iPhone:</b> الإعدادات ← الخصوصية ← خدمات الموقع ← تفعيل<br>
<span style="color:#5F5E5A;font-size:12px;">Settings → Privacy → Location Services → Enable</span><br><br>
<b>🤖 Android:</b> الإعدادات ← الموقع ← تفعيل<br>
<span style="color:#5F5E5A;font-size:12px;">Settings → Location → Turn On</span>
</div>
""", unsafe_allow_html=True)
        else:
            st.session_state.location_allowed = False
            st.info("⚠️ اضغطي زر تحديد الموقع — Tap location button above")

    # ── كارد البيانات الشخصية ────────────────────────────────────
    with st.container(border=True):
        st.markdown('<div class="card-head"><div class="card-ico" style="background:#faeeda;">🪪</div><b style="color:#0c3460;font-size:15px;">البيانات الشخصية</b></div>', unsafe_allow_html=True)

        if _data_locked:
            # ── وضع مقفل — البيانات محفوظة من اليوم ──
            emp = st.session_state.emp_data
            locked_id = emp.get('الرقم الشخصي','')
            locked_excel = get_excel_employee(locked_id)
            locked_task  = locked_excel.get("المهمة","") if locked_excel else emp.get('القسم','')
            locked_lines  = locked_task.replace("\n","<br>")
            badge_color   = "#185FA5" if "كنترول" in locked_task else "#3B6D11"
            badge_bg      = "#e6f1fb" if "كنترول" in locked_task else "#eaf3de"
            st.markdown(f"""
            <div class="field-lbl">الرقم الشخصي</div>
            <div class="field-val locked">{locked_id}</div>
            <div class="field-lbl">الاسم</div>
            <div class="field-val locked">{emp.get('الاسم','')}</div>
            <div class="field-lbl">المدرسة</div>
            <div class="field-val locked">{emp.get('المدرسة','')}</div>
            <div class="field-lbl">المهمة في الكنترول / Role</div>
            <div class="field-val locked" style="background:{badge_bg};border-color:{badge_color};color:{badge_color};font-size:12px;line-height:1.8;">{locked_lines}</div>
            <div style="font-size:11px;color:#3B6D11;font-weight:700;margin-top:4px;">🔒 بياناتك محفوظة لهذا اليوم — Data locked for today</div>
            """, unsafe_allow_html=True)

        else:
            # ── وضع مفتوح — إدخال البيانات ──
            emp_id_input = st.text_input(
                "الرقم الشخصي",
                placeholder="أدخلي رقمك الشخصي",
                max_chars=20,
                key="emp_id_field"
            )

            # البحث: أولاً في Excel، ثم في القائمة البيضاء
            if emp_id_input.strip():
                excel_emp   = get_excel_employee(emp_id_input.strip())
                whitelist_emp = validate_employee(emp_id_input.strip())
                existing    = whitelist_emp or (excel_emp and {
                    "الرقم الشخصي": excel_emp["الرقم الشخصي"],
                    "الاسم":         excel_emp["الاسم"],
                    "المدرسة":       excel_emp["المدرسة"],
                    "القسم":         excel_emp.get("المهمة", ""),
                    "نشط":           "نعم",
                })
            else:
                excel_emp   = None
                existing    = None

            if existing:
                emp_name_input    = existing.get("الاسم","")
                emp_school_input  = existing.get("المدرسة", schools[0])
                emp_section_input = existing.get("القسم", "")
                is_support        = "دعم" in emp_section_input
                task_display      = excel_emp.get("المهمة","") if excel_emp else emp_section_input
                task_lines        = task_display.replace("\n","<br>")
                badge_color       = "#185FA5" if "كنترول" in task_display else "#3B6D11"
                badge_bg          = "#e6f1fb" if "كنترول" in task_display else "#eaf3de"
                st.markdown(f"""
                <div class="field-lbl">الاسم</div>
                <div class="field-val locked">{emp_name_input}</div>
                <div class="field-lbl">المدرسة</div>
                <div class="field-val locked">{emp_school_input}</div>
                <div class="field-lbl">المهمة في الكنترول / Role</div>
                <div class="field-val locked" style="background:{badge_bg};border-color:{badge_color};color:{badge_color};font-size:12px;line-height:1.8;">{task_lines}</div>
                <div style="font-size:11px;color:#3B6D11;font-weight:700;margin-top:4px;">✓ موظفة مسجّلة — Registered</div>
                """, unsafe_allow_html=True)

            else:
                emp_name_input    = "" if not emp_id_input.strip() else st.session_state.get("_tmp_name","")
                emp_name_input    = st.text_input("الاسم الثلاثي", placeholder="اكتبي اسمك الثلاثي", key="emp_name_field")
                emp_school_input  = st.selectbox("المدرسة", schools, key="emp_school_field")

                emp_type = st.radio(
                    "نوع التسجيل",
                    ["👩‍🏫 عضوة في المركز", "🔄 دعم"],
                    horizontal=True,
                    key="emp_type_radio"
                )
                is_support = emp_type == "🔄 دعم"

                sections_permanent = [s for s in sections if "دعم" not in s]
                sections_support   = [s for s in sections if "دعم" in s]

                if is_support:
                    st.warning("🔄 دعم — سيُسجّل حضورك لهذا اليوم فقط ولن تُحفظي في القائمة الدائمة")
                    emp_section_input = st.selectbox("القسم الذي تدعمينه", sections_support, key="emp_section_field")
                else:
                    st.info("💾 عضوة في المركز — ستُحفظين في القائمة تلقائياً عند أول تسجيل")
                    emp_section_input = st.selectbox("القسم", sections_permanent, key="emp_section_field")

            # حفّظ في session_state
            if existing:
                st.session_state.emp_verified = True
                st.session_state.emp_data = existing
            elif emp_id_input.strip() and emp_name_input.strip():
                st.session_state.emp_verified = True
                st.session_state.emp_data = {
                    "الرقم الشخصي": emp_id_input.strip(),
                    "الاسم": normalize_name(emp_name_input.strip()),
                    "المدرسة": emp_school_input,
                    "القسم": emp_section_input,
                    "نشط": "نعم",
                    "جديد": True,
                    "دعم": is_support
                }
            else:
                st.session_state.emp_verified = False
                st.session_state.emp_data = None

        # تحقق من سجل اليوم
        if st.session_state.emp_verified and st.session_state.emp_data:
            data = sheet.get_all_records()
            _, row = find_today_row(data, today_str, st.session_state.emp_data.get("الرقم الشخصي",""))
            st.session_state.today_row = row

    # ── كارد العمليات ────────────────────────────────────────────
    if st.session_state.emp_verified and st.session_state.emp_data:
        emp    = st.session_state.emp_data
        emp_id = str(emp.get("الرقم الشخصي", "")).strip()

        # شريط حالة اليوم
        data = sheet.get_all_records()
        _, today_row = find_today_row(data, today_str, emp_id)

        att_time  = today_row.get("وقت الحضور","—")  if today_row else "—"
        dep_time  = today_row.get("وقت الانصراف","—") if today_row else "—"
        status    = "حاضر ✓" if today_row and today_row.get("وقت الحضور") else "لم يُسجَّل"
        stat_col  = "#3B6D11" if today_row and today_row.get("وقت الحضور") else "#A32D2D"

        # تحذير بصمة الجهاز
        device_regs = get_device_registrations_today(today_str)
        if len(device_regs) > 0 and emp_id not in device_regs:
            st.markdown(f'<div class="device-warn">⚠️ تم تسجيل حضور موظفة أخرى من هذا الجهاز اليوم. يجب الانتظار {DEVICE_COOLDOWN_MINUTES} دقيقة بين كل تسجيل.</div>', unsafe_allow_html=True)

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
                    st.session_state.pending_operation = None
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

        # ── نوافذ السبب ──────────────────────────────────────────
        if st.session_state.pending_operation == "تسجيل حضور":
            with st.container(border=True):
                st.markdown("**سبب التأخير بعد الساعة 7:30 — اختياري**")
                late_reason = st.selectbox("السبب", ["بدون سبب"] + reasons, key="late_reason")
                late_other  = ""
                if late_reason == "أخرى":
                    late_other = st.text_input("اكتبي السبب", key="late_other")
                final = "" if late_reason == "بدون سبب" else (late_other.strip() if late_reason == "أخرى" else late_reason)
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
#  ══ واجهة الأدمن ══
# ══════════════════════════════════════════════════════════════════
else:
    if not st.session_state.admin_logged_in:
        st.markdown('<div class="pro-card"><div class="card-head"><div class="card-ico" style="background:#EEEDFE;">🛡️</div><b style="color:#26215C;font-size:15px;">دخول الأدمن</b></div>', unsafe_allow_html=True)
        pw = st.text_input("كلمة المرور", type="password", key="admin_pw")
        if st.button("دخول", use_container_width=True):
            ADMIN_PASSWORD = st.secrets.get("admin_password", "Afaf1234")
            if pw.strip() == ADMIN_PASSWORD:
                st.session_state.admin_logged_in   = True
                st.session_state.admin_last_active = datetime.now()
                st.rerun()
            else:
                st.error("❌ كلمة المرور غير صحيحة")
        st.markdown('</div>', unsafe_allow_html=True)

    else:
        st.session_state.admin_last_active = datetime.now()

        st.markdown("""
        <div class="admin-header">
            <div class="t">🛡️ لوحة الأدمن</div>
            <div class="s">صلاحيات كاملة — جلسة تنتهي بعد 30 دقيقة خمول</div>
        </div>
        """, unsafe_allow_html=True)

        admin_tab = st.selectbox("القسم", [
            "📊 إحصائيات اليوم",
            "🔴 تسجيل الغياب",
            "✏️ تعديل سجل",
            "➕ تسجيل يدوي",
            "📋 القائمة البيضاء",
            "📥 استيراد Excel",
            "🔍 سجل التدقيق",
            "⚠️ تقرير الأجهزة"
        ])

        # ── إحصائيات اليوم ──────────────────────────────────────
        if admin_tab == "📊 إحصائيات اليوم":
            data       = sheet.get_all_records()
            today_rows = [r for r in data if r.get("التاريخ") == today_str]

            # بيانات الغياب
            try:
                abs_sheet_stats = get_or_create_sheet("سجل_الغياب", [
                    "التاريخ","اليوم","الرقم الشخصي","الاسم",
                    "المدرسة","القسم","سبب الغياب","ملاحظات","سجّله"
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
            absent    = len(abs_today)

            # صف 1
            c1,c2,c3 = st.columns(3)
            c1.metric("إجمالي المسجّلين", total)
            c2.metric("حاضرون الآن", attended)
            c3.metric("منصرفون", departed)

            # صف 2
            c4,c5,c6 = st.columns(3)
            c4.metric("متأخرون", len(late_list))
            c5.metric("انصراف مبكر", len(early_dep))
            c6.metric("استئذان مفتوح", len(on_leave))

            # صف 3 - الغياب
            c7,c8,_ = st.columns(3)
            c7.metric("غائبات اليوم", absent)
            c8.metric("إجمالي الموظفات", len(get_whitelist()) or "—")

            # قائمة الغائبات
            if abs_today:
                st.markdown('<div class="admin-section">الغائبات اليوم</div>', unsafe_allow_html=True)
                for r in abs_today:
                    reason = r.get("سبب الغياب","")
                    name   = r.get("الاسم","")
                    school = r.get("المدرسة","")
                    st.markdown(
                        f'<div class="audit-row" style="border-right-color:#E24B4A;">'
                        f'<span class="ar-op">🔴 {name}</span>'
                        f'<div class="ar-det">{school} — سبب: {reason}</div>'
                        f'</div>',
                        unsafe_allow_html=True
                    )

            if late_list:
                st.markdown('<div class="admin-section">المتأخرون اليوم</div>', unsafe_allow_html=True)
                for r in late_list:
                    st.markdown(f'<div class="warn-row">⏰ {r.get("الاسم الثلاثي","")} — وصل {r.get("وقت الحضور","")}</div>', unsafe_allow_html=True)

        # ── تسجيل الغياب ────────────────────────────────────────
        elif admin_tab == "🔴 تسجيل الغياب":
            absence_reasons = ["مرض", "إجازة اعتيادية", "إجازة طارئة", "بدون عذر", "مهمة رسمية", "أخرى"]

            abs_date = st.date_input("تاريخ الغياب", value=datetime.now().date(), key="abs_date")
            abs_date_str = str(abs_date)

            # جيب كل الموظفات من القائمة البيضاء
            wl_all = get_whitelist()
            if not wl_all:
                st.warning("⚠️ القائمة البيضاء فارغة — أضيفي الموظفات أولاً من قسم القائمة البيضاء")
            else:
                # جيب من سجّل حضور في هذا التاريخ
                data = sheet.get_all_records()
                attended_ids = set(
                    str(r.get("الرقم الشخصي","")).strip()
                    for r in data
                    if r.get("التاريخ") == abs_date_str and r.get("وقت الحضور")
                )

                # جيب من سجّل غياب مسبقاً في هذا التاريخ
                try:
                    abs_sheet = get_or_create_sheet("سجل_الغياب", [
                        "التاريخ", "اليوم", "الرقم الشخصي", "الاسم",
                        "المدرسة", "القسم", "سبب الغياب", "ملاحظات", "سجّله"
                    ])
                    abs_records = abs_sheet.get_all_records()
                    absent_ids = set(
                        str(r.get("الرقم الشخصي","")).strip()
                        for r in abs_records
                        if r.get("التاريخ") == abs_date_str
                    )
                except Exception:
                    abs_sheet = None
                    absent_ids = set()

                # الغائبون = كل القائمة البيضاء - الحاضرون - المسجّل غيابهم
                not_registered = {
                    eid: emp for eid, emp in wl_all.items()
                    if eid not in attended_ids and eid not in absent_ids
                }
                already_absent = {
                    eid: emp for eid, emp in wl_all.items()
                    if eid in absent_ids
                }

                # إحصائيات
                c1, c2, c3 = st.columns(3)
                c1.metric("إجمالي الموظفات", len(wl_all))
                c2.metric("حاضرات", len(attended_ids))
                c3.metric("لم يسجّلن بعد", len(not_registered))

                # من سجّل غيابهم مسبقاً
                if already_absent:
                    st.markdown('<div class="admin-section">تم تسجيل غيابهن</div>', unsafe_allow_html=True)
                    for eid, emp in already_absent.items():
                        rec = next((r for r in abs_records if str(r.get("الرقم الشخصي","")) == eid and r.get("التاريخ") == abs_date_str), {})
                        st.markdown(f'<div class="audit-row" style="border-color:#E24B4A;"><span class="ar-op">🔴 {emp.get("الاسم","")}</span><div class="ar-det">#{eid} — سبب: {rec.get("سبب الغياب","")}</div></div>', unsafe_allow_html=True)

                # من لم يسجّل بعد
                if not_registered:
                    st.markdown('<div class="admin-section">لم يسجّلن بعد — حدّدي من هي غائبة</div>', unsafe_allow_html=True)

                    for eid, emp in not_registered.items():
                        with st.expander(f"🔴 {emp.get('الاسم','')} — {emp.get('المدرسة','')}"):
                            reason_key = f"abs_reason_{eid}"
                            other_key  = f"abs_other_{eid}"
                            note_key   = f"abs_note_{eid}"
                            btn_key    = f"abs_btn_{eid}"

                            sel_reason = st.selectbox("سبب الغياب", absence_reasons, key=reason_key)
                            other_txt  = ""
                            if sel_reason == "أخرى":
                                other_txt = st.text_input("اكتبي السبب", key=other_key)
                            note_txt = st.text_input("ملاحظات إضافية (اختياري)", key=note_key)

                            final_reason = other_txt.strip() if sel_reason == "أخرى" else sel_reason

                            if st.button(f"تسجيل غياب", key=btn_key, use_container_width=True):
                                if not final_reason:
                                    st.error("سبب الغياب مطلوب")
                                elif abs_sheet is None:
                                    st.error("خطأ في الاتصال بالشيت")
                                else:
                                    day_ar = {
                                        "Saturday":"السبت","Sunday":"الأحد","Monday":"الاثنين",
                                        "Tuesday":"الثلاثاء","Wednesday":"الأربعاء",
                                        "Thursday":"الخميس","Friday":"الجمعة"
                                    }.get(abs_date.strftime("%A"), abs_date.strftime("%A"))

                                    abs_sheet.append_row([
                                        abs_date_str, day_ar,
                                        eid, emp.get("الاسم",""),
                                        emp.get("المدرسة",""), emp.get("القسم",""),
                                        final_reason, note_txt,
                                        "أدمن"
                                    ])
                                    log_audit(eid, emp.get("الاسم",""), "تسجيل غياب",
                                              f"التاريخ: {abs_date_str} | السبب: {final_reason}")
                                    st.success(f"✅ تم تسجيل غياب {emp.get('الاسم','')} بسبب: {final_reason}")
                                    st.rerun()
                else:
                    st.success("✅ تم تسجيل وضع جميع الموظفات لهذا اليوم")

        # ── تعديل سجل ────────────────────────────────────────────
        elif admin_tab == "✏️ تعديل سجل":
            st.markdown('<div class="admin-section">ابحث بالرقم الشخصي</div>', unsafe_allow_html=True)
            search_id = st.text_input("الرقم الشخصي", key="edit_id")
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

                new_att = st.text_input("وقت الحضور (HH:MM:SS)", value=row.get("وقت الحضور",""), key="new_att")
                new_dep = st.text_input("وقت الانصراف (HH:MM:SS)", value=row.get("وقت الانصراف",""), key="new_dep")
                edit_reason = st.text_input("سبب التعديل (مطلوب)", key="edit_reason")

                if st.button("حفظ التعديل", use_container_width=True):
                    if not edit_reason.strip():
                        st.error("سبب التعديل مطلوب")
                    else:
                        sheet.update_cell(idx, 7, new_att)
                        sheet.update_cell(idx, 9, new_dep)
                        log_audit(
                            search_id,
                            row.get("الاسم الثلاثي",""),
                            "تعديل أدمن",
                            f"حضور: {row.get('وقت الحضور','')} → {new_att} | "
                            f"انصراف: {row.get('وقت الانصراف','')} → {new_dep} | "
                            f"السبب: {edit_reason}"
                        )
                        st.success("✅ تم حفظ التعديل وتسجيله في سجل التدقيق")
                        st.session_state.edit_row = None

        # ── تسجيل يدوي ──────────────────────────────────────────
        elif admin_tab == "➕ تسجيل يدوي":
            st.markdown('<div class="admin-section">إضافة حضور يدوي لموظفة نسيت التسجيل</div>', unsafe_allow_html=True)
            m_id   = st.text_input("الرقم الشخصي", key="manual_id")
            m_date = st.date_input("التاريخ", value=datetime.now().date(), key="manual_date")
            m_att  = st.text_input("وقت الحضور", value="07:00:00", key="manual_att")
            m_dep  = st.text_input("وقت الانصراف (اختياري)", key="manual_dep")
            m_note = st.text_input("سبب الإضافة اليدوية (مطلوب)", key="manual_note")

            if st.button("تسجيل يدوي", use_container_width=True):
                if not m_note.strip():
                    st.error("سبب الإضافة مطلوب")
                elif not m_id.strip():
                    st.error("الرقم الشخصي مطلوب")
                else:
                    emp = validate_employee(m_id)
                    if not emp:
                        st.error("الرقم الشخصي غير موجود في القائمة البيضاء")
                    else:
                        date_str = str(m_date)
                        day_name = m_date.strftime("%A")
                        sheet.append_row([
                            date_str, day_name,
                            emp.get("المدرسة",""), emp.get("القسم",""),
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
            wl_section = st.selectbox("القسم", sections, key="wl_section")

            if st.button("إضافة للقائمة", use_container_width=True):
                if not wl_id.strip() or not wl_name.strip():
                    st.error("الرقم والاسم مطلوبان")
                else:
                    wl = get_whitelist()
                    if wl_id.strip() in wl:
                        st.error("الرقم الشخصي موجود مسبقاً")
                    else:
                        whitelist_sheet.append_row([wl_id.strip(), wl_name.strip(), wl_school, wl_section, "نعم"])
                        log_audit(wl_id, wl_name, "إضافة للقائمة البيضاء", f"مدرسة: {wl_school} | قسم: {wl_section}")
                        st.success(f"✅ تمت إضافة {wl_name} للقائمة")

            st.markdown('<div class="admin-section">الموظفات المسجّلات</div>', unsafe_allow_html=True)
            wl_all = get_whitelist()
            for eid, emp in wl_all.items():
                st.markdown(f'<div class="audit-row"><span class="ar-op">{emp.get("الاسم","")}</span><div class="ar-det">#{eid} — {emp.get("المدرسة","")}</div></div>', unsafe_allow_html=True)

        # ── استيراد Excel ────────────────────────────────────────
        elif admin_tab == "📥 استيراد Excel":
            st.markdown('<div class="admin-section">استيراد بيانات المعلمات من ملفات Excel إلى القائمة البيضاء</div>', unsafe_allow_html=True)

            total_excel = len(EXCEL_EMPLOYEES)
            wl_now      = get_whitelist()
            new_count   = sum(1 for eid in EXCEL_EMPLOYEES if eid not in wl_now)
            already     = sum(1 for eid in EXCEL_EMPLOYEES if eid in wl_now)

            c1, c2, c3 = st.columns(3)
            c1.metric("موظفات في Excel", total_excel)
            c2.metric("موجودات مسبقاً", already)
            c3.metric("جديدات للاستيراد", new_count)

            if new_count == 0:
                st.success("✅ جميع الموظفات موجودات في القائمة البيضاء")
            else:
                st.info(f"سيتم إضافة {new_count} موظفة جديدة من ملفات Excel")
                if st.button(f"استيراد {new_count} موظفة الآن", use_container_width=True, key="btn_import_excel"):
                    imported = 0
                    errors   = 0
                    wl_now   = get_whitelist()
                    for eid, emp in EXCEL_EMPLOYEES.items():
                        if eid in wl_now:
                            continue
                        try:
                            whitelist_sheet.append_row([
                                eid,
                                emp.get("الاسم",""),
                                emp.get("المدرسة",""),
                                emp.get("المهمة",""),
                                "نعم"
                            ])
                            imported += 1
                        except Exception:
                            errors += 1
                    log_audit("أدمن", "النظام", "استيراد Excel",
                              f"تم استيراد {imported} موظفة | أخطاء: {errors}")
                    if errors == 0:
                        st.success(f"✅ تم استيراد {imported} موظفة بنجاح")
                    else:
                        st.warning(f"⚠️ تم استيراد {imported} | فشل {errors}")
                    st.rerun()

            # عرض جدول الموظفات من Excel
            st.markdown('<div class="admin-section">جميع الموظفات في ملفات Excel</div>', unsafe_allow_html=True)
            for eid, emp in EXCEL_EMPLOYEES.items():
                is_in_wl  = eid in wl_now
                badge_txt = "✓ مضافة" if is_in_wl else "⬆ جديدة"
                badge_col = "#3B6D11" if is_in_wl else "#185FA5"
                task_short = emp.get("المهمة","").split("/")[0].strip()
                st.markdown(
                    f'<div class="audit-row" style="border-right-color:{badge_col};">' +
                    f'<span class="ar-op">{emp.get("الاسم","")}' +
                    f' <span style="font-size:10px;color:{badge_col};font-weight:700;">{badge_txt}</span></span>' +
                    f'<div class="ar-det">#{eid} — {emp.get("المدرسة","")} — {task_short}</div>' +
                    f'</div>',
                    unsafe_allow_html=True
                )

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
                    </div>
                    """, unsafe_allow_html=True)
            except Exception as e:
                st.error(f"خطأ في تحميل سجل التدقيق: {e}")

        # ── تقرير الأجهزة ────────────────────────────────────────
        elif admin_tab == "⚠️ تقرير الأجهزة":
            st.markdown('<div class="admin-section">أجهزة سجّلت أكثر من موظفة اليوم</div>', unsafe_allow_html=True)
            try:
                audit_data = audit_sheet.get_all_records()
                device_map = {}
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
                    st.success("✅ لا يوجد تسجيل مشبوه اليوم — كل جهاز سجّل موظفة واحدة فقط")
            except Exception as e:
                st.error(f"خطأ: {e}")

        st.markdown("---")
        st.markdown("**🔓 فتح قفل بيانات موظفة**")
        unlock_id = st.text_input("الرقم الشخصي للموظفة المراد فتح قفلها", key="unlock_id")
        if st.button("فتح القفل", use_container_width=True, key="btn_unlock"):
            if unlock_id.strip():
                # امسح بيانات LocalStorage لهذا المستخدم — نسجّل في التدقيق فقط
                log_audit(unlock_id.strip(), "—", "فتح قفل الأدمن",
                          f"الأدمن فتح قفل بيانات الرقم {unlock_id.strip()} ليوم {today_str}")
                st.success(f"✅ تم تسجيل فتح القفل للرقم {unlock_id.strip()} — على الموظفة تفتح البرنامج من جديد")
            else:
                st.error("أدخلي الرقم الشخصي")

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


