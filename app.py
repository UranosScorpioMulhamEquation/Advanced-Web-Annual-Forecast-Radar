import streamlit as st
import extra_streamlit_components as st_components

# 1. تهيئة مدير الكوكيز
cookie_manager = st_components.CookieManager()

# 2. التحقق من كوكي التفعيل السابق في متصفح الزبون (صالح لمدة 5 سنوات)
auth_cookie = cookie_manager.get(cookie="app_authenticated")
if auth_cookie == "true":
    st.session_state['authenticated'] = True

if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False

# دالة التوليد والتحقق الرياضي بناءً على معرّف الزبون (مثل رقم هاتفه)
def generate_password(customer_id):
    digits = ''.join(filter(str.isdigit, customer_id))
    num = int(digits[:8]) if digits else int(customer_id.encode().hex(), 16)
    return str(round(abs(num / 2 * 3.14)))[:6]

# 3. شاشة التفعيل (تظهر فقط عند أول فتح لمتصفح الزبون)
if not st.session_state['authenticated']:
    st.set_page_config(page_title="تفعيل النسخة الخاصة", layout="centered")
    
    st.markdown("<h2 style='text-align: center;'>🔑 تفعيل المنظومة الفلكية الخاصة بك</h2>", unsafe_allow_html=True)
    st.info("الرجاء إدخال رقم هاتفك (أو المعرّف الخاص بك) ومفتاح التفعيل المستلم من المبرمج لمرة واحدة فقط.")

    # حقول إدخال بيانات الزبون
    customer_id_input = st.text_input("رقم الهاتف أو المعرّف الخاص بك:")
    pwd_input = st.text_input("مفتاح التفعيل (Activation Key):", type="password")
    
    if st.button("تفعيل ودخول النظام"):
        if customer_id_input and pwd_input:
            # حساب الكود المتوقع رياضياً بناءً على معرّف هذا الزبون بالذات
            expected_pwd = generate_password(customer_id_input)
            
            if pwd_input == expected_pwd:
                st.success("تم التفعيل بنجاح! جاري الدخول للمنظومة...")
                
                # حفظ حالة التفعيل في متصفح الزبون لمدة 5 سنوات (157,680,000 ثانية)
                cookie_manager.set("app_authenticated", "true", max_age=157680000)
                
                st.session_state['authenticated'] = True
                st.rerun()
            else:
                st.error("مفتاح التفعيل غير صحيح لهذا المعرّف. تأكد من البيانات المرسلة لك.")
        else:
            st.warning("الرجاء إدخال المعرّف ومفتاح التفعيل معاً.")
    st.stop()

# ==========================================================
# 🚀 [هنا يبدأ تطبيقك الأساسي وصفحاتك ومحرك المنظومة الفلكية]
# ==========================================================
# إعدادات الصفحة الرئيسية والتصميم العام
st.set_page_config(
    page_title="المنظومة الفلكية المطورة",
    page_icon="🪐",
    layout="wide",
    initial_sidebar_state="expanded"
)

# تطبيق اتجاه اليمين، الخط العربي، وتوسيع الشريط الجانبي
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
    st.Page("pages/intmatrix.py", title="مصفوفة القدر المدمج مع السنوات الخطرة للدول", icon="🔢"),
    st.Page("pages/mrg.py", title="برنامج كشف سنوات الزواج و صفات الشريك المحتملة", icon="🔗"),
    st.Page("pages/nhe.py", title="نظرية استرو رادار المطورة لكشف سنوات التغيير للأفراد و الشركات و الدول", icon="🌌"),
])

pg.run()
