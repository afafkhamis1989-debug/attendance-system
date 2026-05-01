import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, time, timedelta
from streamlit_geolocation import streamlit_geolocation
from streamlit_local_storage import LocalStorage
import math
import hashlib
import json

st.set_page_config(
    page_title="نظام الحضور والانصراف",
    page_icon="🕘",
    layout="centered"
)

localS = LocalStorage()

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
    "الهيئة الإدارية", "الإشراف التربوي"
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

def hash_password(pw):
    return hashlib.sha256(Afaf1234.encode()).hexdigest()

def get_device_fingerprint():
    """تولّد بصمة للجهاز تُخزّن في LocalStorage وتبقى ثابتة."""
    fp = localS.getItem("device_fp")
    if not fp:
        import random, string
        fp = ''.join(random.choices(string.ascii_letters + string.digits, k=32))
        localS.setItem("device_fp", fp, key="set_device_fp")
    return fp or "unknown"

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
    emp    = validate_employee(emp_id)
    if not emp:
        st.error("❌ الرقم الشخصي غير مسجّل في النظام، تواصلي مع الأدمن")
        return False

    full_name = normalize_name(emp.get("الاسم",""))
    school    = emp.get("المدرسة", st.session_state.get("school_input", schools[0]))
    section   = emp.get("القسم",   st.session_state.get("section_input", sections[0]))

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
}.items():
    if k not in st.session_state:
        st.session_state[k] = v

# انتهاء جلسة الأدمن بعد 30 دقيقة خمول
if st.session_state.admin_logged_in and st.session_state.admin_last_active:
    idle = (datetime.now() - st.session_state.admin_last_active).seconds // 60
    if idle >= 30:
        st.session_state.admin_logged_in = False
        st.session_state.admin_last_active = None
        st.warning("⏱️ انتهت جلسة الأدمن بسبب الخمول")

today_str = datetime.now().strftime("%Y-%m-%d")
fp        = get_device_fingerprint()

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
    with st.container(border=False):
        st.markdown('<div class="pro-card"><div class="card-head"><div class="card-ico" style="background:#e6f1fb;">📍</div><b style="color:#0c3460;font-size:15px;">التحقق من الموقع</b></div>', unsafe_allow_html=True)
        location = streamlit_geolocation()
        dist_val = None

        if location:
            lat = location.get("latitude")
            lon = location.get("longitude")
            if lat is not None and lon is not None:
                try:
                    dist_val = distance_m(float(lat), float(lon), SCHOOL_LAT, SCHOOL_LON)
                    if dist_val <= ALLOWED_RADIUS:
                        st.session_state.location_allowed = True
                        st.markdown(f'<div class="loc-ok"><div class="loc-dot-g"></div><div class="loc-txt-g">داخل نطاق المدرسة ✓ — المسافة: {int(dist_val)} م</div></div>', unsafe_allow_html=True)
                    else:
                        st.session_state.location_allowed = False
                        st.markdown(f'<div class="loc-err"><div class="loc-dot-r"></div><div class="loc-txt-r">خارج النطاق ✗ — المسافة: {int(dist_val)} م</div></div>', unsafe_allow_html=True)
                except Exception:
                    st.session_state.location_allowed = False
                    st.markdown('<div class="loc-err"><div class="loc-dot-r"></div><div class="loc-txt-r">خطأ في قراءة الموقع</div></div>', unsafe_allow_html=True)
            else:
                st.session_state.location_allowed = False
                st.markdown('<div class="loc-err"><div class="loc-dot-r"></div><div class="loc-txt-r">اضغطي زر تحديد الموقع أولاً</div></div>', unsafe_allow_html=True)
        else:
            st.session_state.location_allowed = False
            st.markdown('<div class="loc-err"><div class="loc-dot-r"></div><div class="loc-txt-r">لم يتم تحديد الموقع بعد</div></div>', unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)

    # ── كارد الرقم الشخصي ────────────────────────────────────────
    with st.container(border=False):
        st.markdown('<div class="pro-card"><div class="card-head"><div class="card-ico" style="background:#faeeda;">🪪</div><b style="color:#0c3460;font-size:15px;">الرقم الشخصي</b></div>', unsafe_allow_html=True)

        emp_id_input = st.text_input(
            "أدخلي رقمك الشخصي",
            placeholder="مثال: 20241234",
            max_chars=20,
            key="emp_id_field"
        )

        if st.button("تحقق من الرقم", use_container_width=True):
            emp = validate_employee(emp_id_input)
            if emp:
                st.session_state.emp_verified = True
                st.session_state.emp_data     = emp

                # تحقق من الشيت هل سجّل اليوم
                data = sheet.get_all_records()
                _, row = find_today_row(data, today_str, emp_id_input)
                st.session_state.today_row = row
            else:
                st.session_state.emp_verified = False
                st.session_state.emp_data     = None
                st.error("❌ الرقم الشخصي غير موجود، تواصلي مع الأدمن")

        if st.session_state.emp_verified and st.session_state.emp_data:
            emp = st.session_state.emp_data
            locked_class = "locked" if st.session_state.get("today_row") and st.session_state.today_row.get("وقت الحضور") else ""
            st.markdown(f"""
            <div class="field-lbl">الاسم</div>
            <div class="field-val {locked_class}">{emp.get('الاسم','')}</div>
            <div class="field-lbl">المدرسة</div>
            <div class="field-val">{emp.get('المدرسة','')}</div>
            <div class="field-lbl">القسم</div>
            <div class="field-val">{emp.get('القسم','')}</div>
            """, unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)

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
            correct_hash = st.secrets.get("admin_password_hash", "")
            if hash_password(pw) == correct_hash:
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
            "✏️ تعديل سجل",
            "➕ تسجيل يدوي",
            "📋 القائمة البيضاء",
            "🔍 سجل التدقيق",
            "⚠️ تقرير الأجهزة"
        ])

        # ── إحصائيات اليوم ──────────────────────────────────────
        if admin_tab == "📊 إحصائيات اليوم":
            data = sheet.get_all_records()
            today_rows = [r for r in data if r.get("التاريخ") == today_str]

            total     = len(today_rows)
            attended  = sum(1 for r in today_rows if r.get("وقت الحضور"))
            departed  = sum(1 for r in today_rows if r.get("وقت الانصراف"))
            late_list = [r for r in today_rows if r.get("وقت الحضور","") > "07:30:00"]
            early_dep = [r for r in today_rows if r.get("وقت الانصراف","") and r.get("وقت الانصراف","") < "14:00:00"]
            on_leave  = [r for r in today_rows if r.get("خروج استئذان") and not r.get("عودة")]

            c1,c2,c3 = st.columns(3)
            c1.metric("إجمالي المسجّلين", total)
            c2.metric("حاضرون الآن", attended)
            c3.metric("منصرفون", departed)

            c4,c5,c6 = st.columns(3)
            c4.metric("متأخرون", len(late_list))
            c5.metric("انصراف مبكر", len(early_dep))
            c6.metric("استئذان مفتوح", len(on_leave))

            if late_list:
                st.markdown('<div class="admin-section">المتأخرون اليوم</div>', unsafe_allow_html=True)
                for r in late_list:
                    st.markdown(f'<div class="warn-row">⏰ {r.get("الاسم الثلاثي","")} — وصل {r.get("وقت الحضور","")}</div>', unsafe_allow_html=True)

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
