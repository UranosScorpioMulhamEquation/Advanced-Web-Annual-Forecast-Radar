import streamlit as st
import pandas as pd
import uuid
from supabase import create_client, Client

# 1. إعدادات الصفحة الأساسية
st.set_page_config(
    page_title="المنظومة الفلكية المطورة",
    page_icon="🪐",
    layout="wide",
    initial_sidebar_state="expanded"
)

if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False

# دالة الاتصال بـ Supabase
@st.cache_resource
def init_supabase() -> Client:
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        return create_client(url, key)
    except Exception as e:
        st.error(f"خطأ في الاتصال بقاعدة البيانات: {e}")
        return None

supabase = init_supabase()

# دالة التوليد والتحقق الرياضي بناءً على رقم الهاتف
def generate_password(customer_id):
    digits = ''.join(filter(str.isdigit, customer_id))
    num = int(digits[:8]) if digits else int(customer_id.encode().hex(), 16)
    return str(round(abs(num / 2 * 3.14)))[:6]

# قراءة معاملات الرابط
query_params = st.query_params
url_phone = query_params.get("phone", "")
url_key = query_params.get("key", "")
url_device = query_params.get("device", "")

# 2. التحقق من صحة المفتاح وقفل الجهاز سحابياً عبر Supabase
if url_phone and url_key:
    expected_pwd = generate_password(url_phone)
    if url_key == expected_pwd:
        
        # إذا لم يكن هناك معرّف جهاز في الرابط بعد، نقوم بتوليده وحقنه تلقائياً في الرابط
        if not url_device:
            new_device_id = uuid.uuid4().hex[:12]
            st.query_params["phone"] = url_phone
            st.query_params["key"] = url_key
            st.query_params["device"] = new_device_id
            st.rerun()
        else:
            # التحقق السحابي من Supabase لمنع مشاركة الرابط مع جهاز آخر
            if supabase is not None:
                try:
                    response = supabase.table("licenses").select("*").eq("phone", url_phone).execute()
                    rows = response.data
                    
                    if len(rows) > 0:
                        customer = rows[0]
                        registered_device = str(customer.get("device_id", "") or "").strip()
                        
                        if registered_device in ["", "None", "nan", "EMPTY"]:
                            # أول جهاز يفتح الرابط -> نربط بصمة الجهاز في Supabase ونقفله للأبد!
                            supabase.table("licenses").update({"device_id": url_device}).eq("phone", url_phone).execute()
                            st.session_state['authenticated'] = True
                        elif registered_device == url_device:
                            # نفس الجهاز الأصلي المعتمد للزبون
                            st.session_state['authenticated'] = True
                        else:
                            # محاولة اختراق أو تشغيل من جهاز آخر!
                            st.markdown("""
                            <div style="background-color: #fee2e2; border: 2px solid #ef4444; padding: 30px; border-radius: 12px; text-align: center; direction: rtl; margin-top: 50px;">
                                <h2 style="color: #991b1b;">⚠️ تنبيه أمني: رابط غير مصرح به</h2>
                                <p style="font-size: 18px; color: #7f1d1d;">عذراً، هذا الرابط مسجل ومقفل حصرياً على جهاز مستخدم آخر ولا يمكن تشغيله من أجهزة متعددة.</p>
                                <p style="font-size: 14px; color: #6b7280;">إذا كنت تواجه مشكلة، يرجى مراسلة المبرمج لتحديث بيانات الترخيص الخاصة بك.</p>
                            </div>
                            """, unsafe_allow_html=True)
                            st.stop()
                    else:
                        # إذا لم يتم إضافته لجدول البيانات بعد، نسمح له بالمرور مؤقتاً بالتحقق الرياضي
                        st.session_state['authenticated'] = True
                except Exception:
                    st.session_state['authenticated'] = True
            else:
                st.session_state['authenticated'] = True

# 3. إذا لم يتم التفعيل بعد: إخفاء الشريط الجانبي تماماً وإظهار شاشة الدخول
if not st.session_state['authenticated']:
    
    # حقن CSS لإخفاء الشريط الجانبي بالكامل
    st.markdown("""
    <style>
    [data-testid="stSidebar"] {
        display: none !important;
    }
    html, body, [class*="css"] {
        direction: rtl;
        text-align: right;
        font-family: 'Cairo', Tahoma, sans-serif;
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("<h2 style='text-align: center;'>🔑 تفعيل المنظومة الفلكية الخاصة بك</h2>", unsafe_allow_html=True)
    st.info("الرجاء مراسلة المبرمج لمرة واحدة فقط على البريد الالكتروني - mulham81ahmed@gmail.com")
    st.info("الرجاء إدخال رقم هاتفك ومفتاح التفعيل المستلم، أو فتح الرابط المخصص الخاص بك.")

    customer_id_input = st.text_input("رقم الهاتف أو المعرّف الخاص بك (مثل 00971...):")
    pwd_input = st.text_input("مفتاح التفعيل (Activation Key):", type="password")
    
    if st.button("تفعيل ودخول النظام"):
        if customer_id_input and pwd_input:
            expected_pwd = generate_password(customer_id_input)
            
            if pwd_input == expected_pwd:
                st.success("تم التفعيل بنجاح! جاري قفل الرابط على جهازك ودخول المنظومة...")
                device_id = uuid.uuid4().hex[:12]
                
                # تحديث أو إضافة بصمة الجهاز في Supabase عند التفعيل اليدوي
                if supabase is not None:
                    try:
                        res = supabase.table("licenses").select("*").eq("phone", customer_id_input).execute()
                        if len(res.data) > 0:
                            supabase.table("licenses").update({"device_id": device_id}).eq("phone", customer_id_input).execute()
                        else:
                            supabase.table("licenses").insert({
                                "phone": customer_id_input,
                                "key": pwd_input,
                                "device_id": device_id
                            }).execute()
                    except Exception:
                        pass
                        
                st.query_params["phone"] = customer_id_input
                st.query_params["key"] = pwd_input
                st.query_params["device"] = device_id
                st.session_state['authenticated'] = True
                st.rerun()
            else:
                st.error("مفتاح التفعيل غير صحيح لهذا المعرّف. تأكد من البيانات المرسلة لك.")
        else:
            st.warning("الرجاء إدخال المعرّف ومفتاح التفعيل معاً.")
    st.stop()

# ==========================================================
# 🚀 [هنا يبدأ تطبيقك الأساسي وصفحاتك - لا تظهر إلا بعد التفعيل الناجح]
# ==========================================================

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;800&display=swap');

html, body, [class*="css"] {
    direction: rtl;
    text-align: right;
    font-family: 'Cairo', Tahoma, sans-serif;
}

/* توسيع الشريط الجانبي (Sidebar) ليناسب العناوين الطويلة */
[data-testid="stSidebar"] {
    min-width: 500px !important;
    max-width: 500px !important;
}

.stDownloadButton button {
    background-color: #1e3a8a !important;
    color: white !important;
    font-weight: bold;
    font-size: 16px;
}

.stButton button {
    background-color: #6D28D9;
    color: white;
    font-weight: bold;
}
</style>
""", unsafe_allow_html=True)

# تعريف وتسمية الصفحات باللغة العربية
pg = st.navigation([
    st.Page("pages/home.py", title="الرئيسية", icon="🏠"),
    st.Page("pages/solar.py", title="برنامج خريطة السنوية للأفراد و الشركات و الدول", icon="🔭"),
    st.Page("pages/matrix.py", title="مصفوفة القدر للأفراد", icon="📊"),
    st.Page("pages/aura.py", title="برنامج الكشف الطاقي و علاج الهالة الطاقية", icon="✨"),
    st.Page("pages/dan.py", title="نظرية استرو رادار المطورة لكشف سنوات الخطر للأفراد و الشركات و الدول", icon="📁"),
    st.Page("pages/divorce.py", title="برنامج كشف سنوات الأزمات الزوجية و الشراكة التجارية", icon="⚖️"),
    st.Page("pages/fullastro.py", title="المنظومة الفلكية الشاملة لتحليل الخارطة الميلادية و السنوية و توقعات 5 سنوات للأفراد", icon="🔭"),
    st.Page("pages/graph.py", title="برنامج التنجيم الجغرافي", icon="📈"),
    st.Page("pages/intmatrix.py", title="مصفوفة القدر المدمج مع السنوات الخطرة الدول", icon="🔢"),
    st.Page("pages/mrg.py", title="برنامج كشف سنوات الزواج و صفات الشريك المحتملة", icon="🔗"),
    st.Page("pages/nhe.py", title="نظرية استرو رادار المطورة لكشف سنوات التغيير للأفراد و الشركات و الدول", icon="🌌"),
])

pg.run()
