import streamlit as st

# إعدادات الصفحة الرئيسية والتصميم العام
st.set_page_config(
    page_title="المنظومة الفلكية المركزية",
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
    min-width: 600px !important;
    max-width: 600px !important;
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
    st.Page("pages/aura.py", title="برنامج الكشف الطاقي و علاج الهالة", icon="✨"),
    st.Page("pages/dan.py", title="نظرية الدكتور ملهم احمد المطورة لكشف سنوات الخطر للأفراد و الشركات و الدول", icon="📁"),
    st.Page("pages/divorce.py", title="برنامج كشف سنوات الأزمات الزوجية و الشراكة التجارية", icon="⚖️"),
    st.Page("pages/fullastro.py", title="المنظومة الفلكية الشاملة لتحليل الخارطة الميلادية و السنوية و توقعات خمسة سنوات للأفراد", icon="🔭"),
    st.Page("pages/graph.py", title="برنامج التنجيم الجغرافي", icon="📈"),
    st.Page("pages/intmatrix.py", title="مصفوفة القدر المدمج مع السنوات الخطرة للدول", icon="🔢"),
    st.Page("pages/mrg.py", title="برنامج كشف سنوات الزواج و صفات الشريك المحتمله", icon="🔗"),
    st.Page("pages/nhe.py", title="نظرية الدكتور ملهم احمد المطورة لكشف سنوات التغيير للأفراد و الشركات و الدول", icon="🌌"),
])

pg.run()
