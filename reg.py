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

try:
    from streamlit_local_storage import LocalStorage
    localS = LocalStorage()
    LOCAL_STORAGE_OK = True
except Exception:
    localS = None
    LOCAL_STORAGE_OK = False

st.set_page_config(page_title="نظام الحضور والانصراف", page_icon="🕘", layout="centered")

# ─── إعدادات ───────────────────────────────────────────────────
SHEET_ID       = "1svkfgRq4-osKr86_2WJQFZShuoy8Ek5DOiUaaHKL-6Y"
SCHOOL_LAT     = 26.216371784473964
SCHOOL_LON     = 50.54035843289093
ALLOWED_RADIUS = 150
ADMIN_PASSWORD = "Afaf1234"
DEVICE_COOLDOWN_MINUTES = 10

# أعمدة sheet1
COL_DATE=1; COL_DAY=2; COL_SCHOOL=3; COL_TASK=4; COL_SUPPORT=5
COL_NAME=6; COL_ID=7; COL_ATTEND=8; COL_LATE_REASON=9
COL_DEPART=10; COL_DEPART_REASON=11; COL_EXIT=12; COL_RETURN=13; COL_ATTEMPT=14

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
reasons       = ["دوام مرن","موعد","مهمة رسمية","رعاية","أخرى"]
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

@st.cache_resource
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
        "whitelist":   _get_or_create("القائمة_البيضاء",         ["الرقم الشخصي","الاسم","المدرسة","المهمة","رقم التواصل","البريد الإلكتروني","المسمى الوظيفي","نشط"]),
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

@st.cache_data(ttl=120)
def get_sheet_data():
    try: return sheet.get_all_records()
    except: return []

@st.cache_data(ttl=300)
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

@st.cache_data(ttl=120)
def get_device_locks():
    try: return device_sheet.get_all_records()[-200:]
    except: return []

@st.cache_data(ttl=60)
def get_settings_records():
    try: return settings_sheet.get_all_records()
    except: return []

def clear_caches():
    get_sheet_data.clear(); get_device_locks.clear(); get_settings_records.clear()

def validate_employee(emp_id):
    return get_whitelist().get(str(emp_id).strip())

def find_today_row(data, today, emp_id):
    for i,row in enumerate(data):
        if str(row.get("التاريخ","")).strip()==str(today).strip() and \
           str(row.get("الرقم الشخصي","")).strip()==str(emp_id).strip():
            return i+2, row
    return None, None

def get_location_override():
    try:
        for r in get_settings_records():
            if str(r.get("المفتاح","")).strip()=="location_override":
                val=str(r.get("القيمة","")).strip()
                end_time=str(r.get("تاريخ_الانتهاء","")).strip()
                if val=="true" and end_time:
                    try:
                        end_dt=datetime.strptime(end_time,"%Y-%m-%d %H:%M")
                        if now_bh()<end_dt: return True,end_dt
                    except: pass
    except: pass
    return False, None

def set_location_override(minutes, note=""):
    end_dt=now_bh()+timedelta(minutes=minutes)
    end_str=end_dt.strftime("%Y-%m-%d %H:%M")
    try:
        records=settings_sheet.get_all_records(); row_found=None
        for i,r in enumerate(records):
            if str(r.get("المفتاح","")).strip()=="location_override": row_found=i+2; break
        if row_found: settings_sheet.update(f"A{row_found}:D{row_found}",[["location_override","true",end_str,note]])
        else: safe_append(settings_sheet,["location_override","true",end_str,note])
        get_settings_records.clear(); return True,end_dt
    except: return False,None

def disable_location_override():
    try:
        records=settings_sheet.get_all_records()
        for i,r in enumerate(records):
            if str(r.get("المفتاح","")).strip()=="location_override":
                settings_sheet.update_cell(i+2,2,"false"); break
        get_settings_records.clear()
    except: pass

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

    data=get_sheet_data(); row_index,row=find_today_row(data,today,emp_id)

    if operation=="تسجيل حضور":
        if row and row.get("وقت الحضور"): st.error("❌ تم تسجيل الحضور مسبقاً لهذا اليوم."); return False
        if row_index:
            safe_update(sheet,row_index,COL_ATTEND,time_now)
            safe_update(sheet,row_index,COL_LATE_REASON,note)
        else:
            ok=safe_append(sheet,[today,day_name,school,task,is_support,full_name,emp_id,time_now,note,"","","","",""])
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
        log_audit(emp_id,full_name,"تسجيل انصراف",f"الوقت:{time_now}|السبب:{note or 'بدون'}")
        clear_caches(); st.success("✅ تم تسجيل الانصراف بنجاح."); return True

    if operation=="خروج استئذان":
        if not row_index or not row or not row.get("وقت الحضور"): st.error("❌ يجب تسجيل الحضور أولاً."); return False
        if row.get("خروج استئذان") and not row.get("عودة"): st.error("❌ يوجد خروج استئذان مفتوح."); return False
        if row.get("خروج استئذان"): st.error("❌ تم تسجيل خروج الاستئذان مسبقاً."); return False
        safe_update(sheet,row_index,COL_EXIT,time_now); safe_update(sheet,row_index,COL_DEPART_REASON,note)
        log_audit(emp_id,full_name,"خروج استئذان",f"الوقت:{time_now}|السبب:{note}")
        clear_caches(); st.success("✅ تم تسجيل خروج الاستئذان بنجاح."); return True

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

try: st.image("logo.png", use_container_width=True)
except: pass

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
        remaining=int((ov_end-now_bh()).seconds/60)
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
        else:
            emp_id_raw=st.text_input("الرقم الشخصي", placeholder="أدخلي رقمك الشخصي", max_chars=20)
            emp_id=ar_to_en_digits(emp_id_raw).strip()
            if emp_id:
                existing=validate_employee(emp_id)
                if existing:
                    is_prev_support = str(existing.get("دعم","")).strip() in ["نعم","yes","Yes","TRUE","true","1"] or "دعم" in str(existing.get("المهمة",""))

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
        status="حاضر ✓" if today_row and today_row.get("وقت الحضور") else "لم يُسجَّل"
        stat_col="#3B6D11" if today_row and today_row.get("وقت الحضور") else "#A32D2D"

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
                st.markdown('<div class="card-title">سبب التأخير بعد 7:30 — اختياري</div>',unsafe_allow_html=True)
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
                st.markdown('<div class="card-title">سبب خروج الاستئذان</div>',unsafe_allow_html=True)
                reason=st.selectbox("السبب",reasons,key="exit_reason")
                other=""
                if reason=="أخرى": other=st.text_input("اكتبي السبب",key="exit_other")
                final=other.strip() if reason=="أخرى" else reason
                if st.button("تأكيد خروج الاستئذان",use_container_width=True,type="primary"):
                    if not final: st.error("السبب مطلوب")
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
            try: abs_today=[r for r in absence_sheet.get_all_records() if r.get("التاريخ")==today_str]
            except: abs_today=[]
            attended=[r for r in today_rows if r.get("وقت الحضور")]
            late_list=[r for r in today_rows if r.get("وقت الحضور","")>"07:30:00"]
            early_dep=[r for r in today_rows if r.get("وقت الانصراف","") and r.get("وقت الانصراف","")< "14:00:00"]
            on_leave=[r for r in today_rows if r.get("خروج استئذان") and not r.get("عودة")]
            c1,c2,c3=st.columns(3)
            c1.metric("إجمالي المسجّلين",len(today_rows))
            c2.metric("حاضرون",len(attended))
            c3.metric("غائبات",len(abs_today))
            c4,c5,c6=st.columns(3)
            c4.metric("متأخرون",len(late_list))
            c5.metric("انصراف مبكر",len(early_dep))
            c6.metric("استئذان مفتوح",len(on_leave))
            if abs_today:
                st.markdown("#### الغائبات")
                for r in abs_today:
                    st.markdown(f'<div class="absent-row">🔴 {r.get("الاسم","")} — {r.get("المدرسة","")} — سبب: {r.get("سبب الغياب","")}</div>',unsafe_allow_html=True)
            if late_list:
                st.markdown("#### المتأخرون")
                for r in late_list:
                    st.markdown(f'<div class="warn-row">⏰ {r.get("الاسم الثلاثي","")} — وصل {r.get("وقت الحضور","")}</div>',unsafe_allow_html=True)

        # ── تسجيل الغياب ────────────────────────────────────────
        elif admin_tab=="🔴 تسجيل الغياب":
            abs_date=st.date_input("تاريخ الغياب",value=now_bh().date(),key="abs_date")
            abs_date_str=str(abs_date)
            wl_all=get_whitelist()
            if not wl_all: st.warning("⚠️ القائمة البيضاء فارغة")
            else:
                data=get_sheet_data()
                attended_ids=set(str(r.get("الرقم الشخصي","")).strip() for r in data if r.get("التاريخ")==abs_date_str and r.get("وقت الحضور"))
                try: abs_records=absence_sheet.get_all_records(); absent_ids=set(str(r.get("الرقم الشخصي","")).strip() for r in abs_records if r.get("التاريخ")==abs_date_str)
                except: abs_records=[]; absent_ids=set()
                not_registered={eid:emp for eid,emp in wl_all.items() if eid not in attended_ids and eid not in absent_ids}
                already_absent={eid:emp for eid,emp in wl_all.items() if eid in absent_ids}
                c1,c2,c3=st.columns(3)
                c1.metric("إجمالي الموظفات",len(wl_all)); c2.metric("حاضرات",len(attended_ids)); c3.metric("لم يسجّلن",len(not_registered))
                if already_absent:
                    st.markdown("#### تم تسجيل غيابهن")
                    for eid,emp in already_absent.items():
                        rec=next((r for r in abs_records if str(r.get("الرقم الشخصي",""))==eid and r.get("التاريخ")==abs_date_str),{})
                        st.markdown(f'<div class="absent-row">🔴 {emp.get("الاسم","")} — سبب: {rec.get("سبب الغياب","")}</div>',unsafe_allow_html=True)
                if not_registered:
                    st.markdown("#### لم يسجّلن بعد")
                    for eid,emp in not_registered.items():
                        with st.expander(f"🔴 {emp.get('الاسم','')} — {emp.get('المدرسة','')}"):
                            sel=st.selectbox("سبب الغياب",abs_reasons,key=f"ar_{eid}")
                            other_txt=""
                            if sel=="أخرى": other_txt=st.text_input("اكتبي السبب",key=f"ao_{eid}")
                            note_txt=st.text_input("ملاحظات (اختياري)",key=f"an_{eid}")
                            final_r=other_txt.strip() if sel=="أخرى" else sel
                            if st.button("تسجيل غياب",key=f"ab_{eid}",use_container_width=True):
                                day_ar={"Saturday":"السبت","Sunday":"الأحد","Monday":"الاثنين","Tuesday":"الثلاثاء","Wednesday":"الأربعاء","Thursday":"الخميس","Friday":"الجمعة"}.get(abs_date.strftime("%A"),abs_date.strftime("%A"))
                                absence_sheet.append_row([abs_date_str,day_ar,eid,emp.get("الاسم",""),emp.get("المدرسة",""),emp.get("المهمة",""),final_r,note_txt,"أدمن"])
                                log_audit(eid,emp.get("الاسم",""),"تسجيل غياب",f"التاريخ:{abs_date_str}|السبب:{final_r}")
                                st.success(f"✅ تم تسجيل غياب {emp.get('الاسم','')}"); st.rerun()
                else: st.success("✅ تم تسجيل وضع جميع الموظفات لهذا اليوم")

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
                        log_audit(search_id,row.get("الاسم الثلاثي",""),"تعديل أدمن",f"حضور:{row.get('وقت الحضور','')}→{new_att}|انصراف:{row.get('وقت الانصراف','')}→{new_dep}|السبب:{edit_reason}")
                        clear_caches(); st.success("✅ تم الحفظ"); st.session_state.edit_row=None

        # ── تسجيل يدوي ──────────────────────────────────────────
        elif admin_tab=="➕ تسجيل يدوي":
            m_id=st.text_input("الرقم الشخصي",key="mid")
            m_date=st.date_input("التاريخ",value=now_bh().date(),key="mdate")
            m_att=st.text_input("وقت الحضور",value="07:00:00",key="matt")
            m_dep=st.text_input("وقت الانصراف (اختياري)",key="mdep")
            m_note=st.text_input("سبب الإضافة اليدوية (مطلوب)",key="mnote")
            if st.button("تسجيل يدوي",use_container_width=True):
                if not m_note.strip(): st.error("السبب مطلوب")
                elif not m_id.strip(): st.error("الرقم مطلوب")
                else:
                    emp=validate_employee(m_id)
                    if not emp: st.error("الرقم غير موجود في القائمة البيضاء")
                    else:
                        date_str=str(m_date); day_name=m_date.strftime("%A")
                        sheet.append_row([date_str,day_name,emp.get("المدرسة",""),emp.get("المهمة",""),normalize_name(emp.get("الاسم","")),m_id,m_att,f"[يدوي] {m_note}",m_dep,"","","",""])
                        log_audit(m_id,emp.get("الاسم",""),"تسجيل يدوي",f"التاريخ:{date_str}|حضور:{m_att}|انصراف:{m_dep}|السبب:{m_note}")
                        clear_caches(); st.success("✅ تم التسجيل اليدوي")

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
                    ok=safe_append(whitelist_sheet,[ar_to_en_digits(wl_id).strip(),normalize_name(wl_name),wl_school,wl_task,"","",wl_job,"نعم"])
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
            active,end_dt=get_location_override()
            if active and end_dt:
                st.warning(f"تجاوز الموقع مفعّل حتى {end_dt.strftime('%H:%M')}")
                if st.button("إيقاف تجاوز الموقع",use_container_width=True):
                    disable_location_override(); st.success("تم الإيقاف."); st.rerun()
            else:
                duration=st.selectbox("مدة التجاوز",[30,60,90,120,180])
                reason=st.text_input("سبب التجاوز")
                if st.button("تفعيل تجاوز الموقع",use_container_width=True):
                    if not reason.strip(): st.error("السبب مطلوب")
                    else:
                        ok,end_dt=set_location_override(duration,reason)
                        if ok: st.success(f"تم التفعيل حتى {end_dt.strftime('%H:%M')}"); st.rerun()
                        else: st.error("تعذر التفعيل")

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

# ─── Footer ─────────────────────────────────────────────────────
st.markdown("""
<div class="footer-bar">
    <span>تصميم وبرمجة: <span class="hl">أ. عفاف حسين</span></span>
    <span>رئيسة المركز: <span class="hl">أ. خلود يعقوب بدو</span></span>
</div>
""", unsafe_allow_html=True)
