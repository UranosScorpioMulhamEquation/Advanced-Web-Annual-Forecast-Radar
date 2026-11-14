import streamlit as st
import pandas as pd
from supabase import create_client, Client

# 1. إعدادات الصفحة الأساسية
st.set_page_config(
    page_title="المنظومة الفلكية المطورة - استرو رادار",
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

# قراءة معاملات الرابط
query_params = st.query_params
url_token = query_params.get("token", "")

# 2. التحقق الأمني من التوكن المؤقت في حال لم يتم المصادقة بعد
if not st.session_state['authenticated']:
    if url_token and supabase is not None:
        try:
            # البحث عن السجل المطابق للتوكن في السحابة
            response = supabase.table("licenses").select("*").eq("token", url_token).execute()
            rows = response.data
            
            if len(rows) > 0:
                customer = rows[0]
                phone_num = customer.get("phone")
                
                # مسح التوكن من القاعدة فوراً لمنع إعادة استخدام الرابط أو مشاركته
                supabase.table("licenses").update({"token": None}).eq("phone", phone_num).execute()
                
                # توثيق الجلسة وفتح التطبيق
                st.session_state['authenticated'] = True
                st.query_params.clear()
                st.rerun()
            else:
                # توكن وهمي أو تم استخدامه من قبل
                st.markdown("""
                <div style="background-color: #fee2e2; border: 2px solid #ef4444; padding: 40px; border-radius: 12px; text-align: center; direction: rtl; margin-top: 50px;">
                    <h2 style="color: #991b1b;">⚠️ تنبيه أمني: رابط غير صالح أو منتهي الصلاحية</h2>
                    <p style="font-size: 18px; color: #7f1d1d; margin-top: 15px;">هذا الرابط تم استخدامه مسبقاً أو غير مصرح به.</p>
                    <p style="font-size: 16px; color: #6b7280;">الرجاء تشغيل ملف التفعيل الخاص بك (launcher.bat) لفتح المنظومة.</p>
                    <p style="font-size: 16px; color: #991b1b;">تنويه : المنظومة محمية بشهادة ملكية فكرية رقم 2026-4630.</p>
                </div>
                """, unsafe_allow_html=True)
                st.stop()
        except Exception as e:
            st.error(f"حدث خطأ أثناء التحقق من الأمان: {e}")
            st.stop()
    else:
        # في حال فتح الرابط العام مباشرة بدون ملف التفعيل
        st.markdown("""
        <style>
        [data-testid="stSidebar"] { display: none !important; }
        html, body, [class*="css"] {
            direction: rtl;
            text-align: right;
            font-family: 'Cairo', Tahoma, sans-serif;
        }
        </style>
        """, unsafe_allow_html=True)

        st.markdown("""
        <div style="background-color: #fef3c7; border: 2px solid #f59e0b; padding: 40px; border-radius: 12px; text-align: center; direction: rtl; margin-top: 50px;">
            <h2 style="color: #b45309;">🔒 وصول غير مصرح به</h2>
            <p style="font-size: 18px; color: #92400e; margin-top: 15px;">لا يمكن تشغيل المنظومة الفلكية مباشرة عبر هذا الرابط العام.</p>
            <p style="font-size: 16px; color: #78350f;">الرجاء تشغيل ملف التفعيل الخاص بك (launcher.bat) للوصول إلى البرنامج.</p>
            <p style="font-size: 16px; color: #991b1b;">تنويه : المنظومة محمية بشهادة ملكية فكرية رقم 2026-4630.</p>

        </div>
        """, unsafe_allow_html=True)
        
        # --- بوابة دخول المبرمج السرية من الهاتف ---
        st.markdown("<br><hr><br>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown("<h4 style='text-align: center; color: #4b5563;'>🛠️ بوابة دخول المبرمج</h4>", unsafe_allow_html=True)
            admin_pass = st.text_input("أدخل كلمة مرور المبرمج السرية:", type="password", key="admin_secret_input")
            if st.button("دخول المشرف", use_container_width=True):
                if admin_pass and admin_pass == st.secrets.get("ADMIN_PASSWORD"):
                    st.session_state['authenticated'] = True
                    st.success("تم التحقق بنجاح! جاري فتح المنظومة...")
                    st.rerun()
                else:
                    st.error("كلمة المرور غير صحيحة!")
        st.stop()

# ==========================================================
# 🚀 [التطبيق الرئيسي الموحد - يعمل فقط بعد نجاح المصادقة الأمنية]
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

# القائمة الجانبية للمنظومة الفلكية
st.sidebar.title("🪐 منظومة استرو رادار")
menu = st.sidebar.radio("اختر البرنامج:", [
    "🏠 الرئيسية",
    "📊 برنامج تحليل الخريطة الساعية",
    "🔭 السنوية للأفراد و الشركات و الدول",
    "✨ التوافقية العاطفية للشخصيات",
    "📁 نظريتي لكشف سنوات الخطر أفراد/دول",
    "⚖️ كشف سنوات الأزمات الزوجية / التجارية",
    "🔭 منظومة تحليل ميلادية/سنوية/توقعات",
    "📈 برنامج التنجيم الجغرافي",
    "🔢 برنامج خريطة الحدث العاطفية",
    "🔗 كشف سنوات الزواج-الإنجاب/صفات الشريك",
    "🌌 نظريتي لكشف سنوات التغيير أفراد/دول"
])

# تشغيل الملف الفرعي مباشرة دون أي تعديل بداخله
if menu == "🏠 الرئيسية":
    with open("subpages/home.py", encoding="utf-8") as f:
        exec(f.read())
elif menu == "📊 برنامج تحليل الخريطة الساعية":
    with open("subpages/matrix.py", encoding="utf-8") as f:
        exec(f.read())
elif menu == "🔭 السنوية للأفراد و الشركات و الدول":
    with open("subpages/solar.py", encoding="utf-8") as f:
        exec(f.read())
elif menu == "✨ التوافقية العاطفية للشخصيات":
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
elif menu == "🔢 برنامج خريطة الحدث العاطفية":
    with open("subpages/intmatrix.py", encoding="utf-8") as f:
        exec(f.read())
elif menu == "🔗 كشف سنوات الزواج-الإنجاب/صفات الشريك":
    with open("subpages/mrg.py", encoding="utf-8") as f:
        exec(f.read())
elif menu == "🌌 نظريتي لكشف سنوات التغيير أفراد/دول":
    with open("subpages/nhe.py", encoding="utf-8") as f:
        exec(f.read())
