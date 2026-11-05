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

# دالة التوليد والتحقق الرياضي بناءً على رقم الهاتف كاملاً لتكون فريدة 100% لكل زبون
def generate_password(customer_id):
    digits = ''.join(filter(str.isdigit, customer_id))
    num = int(digits) if digits else int(customer_id.encode().hex(), 16)
    return str(round(abs(num / 2 * 3.14)))[:6]

# 🛡️ توليد بصمة جهاز ثابتة في الرابط تلقائياً عبر بايثون (تتحسس المتصفح وتمنع الأخطاء)
if "device" not in st.query_params or not st.query_params["device"]:
    st.query_params["device"] = uuid.uuid4().hex[:12]
    st.rerun()

# قراءة معاملات الرابط وبصمة الجهاز الثابتة
query_params = st.query_params
url_phone = query_params.get("phone", "")
url_key = query_params.get("key", "")
client_device_id = query_params.get("device", "")

# 2. التحقق من صحة المفتاح عبر الرابط المباشر مع فحص بصمة الجهاز في السحابة
if url_phone and url_key:
    expected_pwd = generate_password(url_phone)
    if url_key == expected_pwd:
        if supabase is not None:
            try:
                response = supabase.table("licenses").select("*").eq("phone", url_phone).execute()
                rows = response.data
                if len(rows) > 0:
                    customer = rows[0]
                    registered_device = str(customer.get("device_id", "") or "").strip()
                    
                    # إذا كانت خانة الجهاز فارغة في السحابة -> نسجل بصمة هذا المتصفح فوراً
                    if registered_device in ["", "None", "nan", "EMPTY"]:
                        supabase.table("licenses").update({"device_id": client_device_id}).eq("phone", url_phone).execute()
                        st.session_state['authenticated'] = True
                    elif registered_device == client_device_id:
                        # تطابق تام (يعمل بسلاسة عند عمل Refresh)
                        st.session_state['authenticated'] = True
                    else:
                        # محاولة استخدام من جهاز/متصفح مختلف!
                        st.markdown("""
                        <div style="background-color: #fee2e2; border: 2px solid #ef4444; padding: 30px; border-radius: 12px; text-align: center; direction: rtl; margin-top: 50px;">
                            <h2 style="color: #991b1b;">⚠️ تنبيه أمني صارم: ترخيص مقفل</h2>
                            <p style="font-size: 18px; color: #7f1d1d;">عذراً، هذا الرقم مسجل ومقفل حصرياً على جهاز وزبون آخر ولا يمكن تشغيله من جهاز جديد.</p>
                            <p style="font-size: 14px; color: #6b7280;">إذا كنت صاحب الحساب وتغيرت بياناتك، يرجى مراسلة المبرمج لتحديث بصمة جهازك.</p>
                        </div>
                        """, unsafe_allow_html=True)
                        st.stop()
                else:
                    st.session_state['authenticated'] = True
            except Exception:
                st.session_state['authenticated'] = True
        else:
            st.session_state['authenticated'] = True

        if st.session_state['authenticated']:
            st.query_params.clear()
            st.rerun()

# 3. شاشة الدخول والتفعيل (اليدوي)
if not st.session_state['authenticated']:
    
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
    st.info("الرجاء إدخال رقم هاتفك ومفتاح التفعيل المستلم.")

    customer_id_input = st.text_input("رقم الهاتف أو المعرّف الخاص بك (مثل 12345678...):")
    pwd_input = st.text_input("مفتاح التفعيل (Activation Key):", type="password")
    
    if st.button("تفعيل ودخول النظام"):
        if customer_id_input and pwd_input:
            expected_pwd = generate_password(customer_id_input)
            
            if pwd_input == expected_pwd:
                if supabase is not None:
                    try:
                        res = supabase.table("licenses").select("*").eq("phone", customer_id_input).execute()
                        if len(res.data) > 0:
                            customer = res.data[0]
                            registered_device = str(customer.get("device_id", "") or "").strip()
                            
                            # فحص هل الجهاز مقفل لشخص آخر
                            if registered_device not in ["", "None", "nan", "EMPTY"]:
                                if registered_device != client_device_id:
                                    st.error("⚠️ عذراً، هذا الرقم مسجل ومقفل بالفعل على جهاز مستخدم آخر ولا يمكن تشغيله يدوياً من مكان جديد.")
                                    st.stop()
                            else:
                                # تسجيل بصمة هذا الجهاز لأول مرة في السحابة
                                supabase.table("licenses").update({"device_id": client_device_id}).eq("phone", customer_id_input).execute()
                        else:
                            # إذا لم يكن موجوداً من الأساس في الجدول، نضيفه مع بصمته
                            supabase.table("licenses").insert({
                                "phone": customer_id_input,
                                "key": pwd_input,
                                "device_id": client_device_id
                            }).execute()
                    except Exception as e:
                        pass
                
                st.success("تم التفعيل بنجاح! جاري دخول المنظومة...")
                st.session_state['authenticated'] = True
                st.query_params.clear()
                st.rerun()
            else:
                st.error("مفتاح التفعيل غير صحيح لهذا المعرّف. تأكد من البيانات المرسلة لك.")
        else:
            st.warning("الرجاء إدخال المعرّف ومفتاح التفعيل معاً.")
    st.stop()

# ==========================================================
# 🚀 [التطبيق الرئيسي الموحد]
# ==========================================================

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;800&display=swap');

html, body, [class*="css"] {
    direction: rtl;
    text-align: right;
    font-family: 'Cairo', Tahoma, sans-serif;
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

# القائمة الجانبية لتنقل المستخدم
st.sidebar.title("🪐 المنظومة الفلكية")
menu = st.sidebar.radio("اختر البرنامج:", [
    "🏠 الرئيسية",
    "📊 مصفوفة القدر للأفراد",
    "🔭 السنوية للأفراد و الشركات و الدول",
    "✨ الكشف الطاقي و علاج الهالة الطاقية",
    "📁 نظريتي لكشف سنوات الخطر أفراد/دول",
    "⚖️ كشف سنوات الأزمات الزوجية / التجارية",
    "🔭 منظومة تحليل ميلادية/سنوية/توقعات",
    "📈 برنامج التنجيم الجغرافي",
    "🔢 مصفوفة القدر المدمجة بسنوات الخطرة للدول",
    "🔗 كشف سنوات الزواج و صفات الشريك المحتملة",
    "🌌 نظريتي لكشف سنوات التغيير أفراد/دول"
])

# تشغيل الملف الفرعي مباشرة دون أي تعديل بداخله
if menu == "🏠 الرئيسية":
    with open("subpages/home.py", encoding="utf-8") as f:
        exec(f.read())
elif menu == "📊 مصفوفة القدر للأفراد":
    with open("subpages/matrix.py", encoding="utf-8") as f:
        exec(f.read())
elif menu == "🔭 السنوية للأفراد و الشركات و الدول":
    with open("subpages/solar.py", encoding="utf-8") as f:
        exec(f.read())
elif menu == "✨ الكشف الطاقي و علاج الهالة الطاقية":
    with open("subpages/aura.py", encoding="utf-8") as f:
        exec(f.read())
elif menu == "📁 نظريتي لكشف سنوات الخطر أفراد/دول":
    with open("subpages/dan.py", encoding="utf-8") as f:
        exec(f.read())
elif menu == "⚖️ كشف سنوات الأزمات الزوجية / التجارية":
    with open("subpages/divorce.py", encoding="utf-8") as f:
        exec(f.read())
elif menu == "🔭 منظومة تحليل ميلادية/سنوية/توقعات":
    with open("subpages/fullastro.py", encoding="utf-8") as f:
        exec(f.read())
elif menu == "📈 برنامج التنجيم الجغرافي":
    with open("subpages/graph.py", encoding="utf-8") as f:
        exec(f.read())
elif menu == "🔢 مصفوفة القدر المدمجة بسنوات الخطرة للدول":
    with open("subpages/intmatrix.py", encoding="utf-8") as f:
        exec(f.read())
elif menu == "🔗 كشف سنوات الزواج و صفات الشريك المحتملة":
    with open("subpages/mrg.py", encoding="utf-8") as f:
        exec(f.read())
elif menu == "🌌 نظريتي لكشف سنوات التغيير أفراد/دول":
    with open("subpages/nhe.py", encoding="utf-8") as f:
        exec(f.read())
