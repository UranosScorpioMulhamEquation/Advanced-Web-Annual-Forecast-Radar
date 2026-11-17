import streamlit as st

# ==========================================================
# 🪐 واجهة الصفحة الرئيسية المطورة - استرو رادار
# ==========================================================

# تصميم الـ CSS الخاص بالصفحة الرئيسية - نمط داكن كوني فاخر (Dark Cosmic Luxury)
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;500;600;700;800;900&family=Tajawal:wght@400;500;700;800&display=swap');

/* --- لوحة الهيرو الكونية الفاخرة --- */
.hero-container {
    background: linear-gradient(135deg, rgba(17, 24, 39, 0.85) 0%, rgba(30, 18, 55, 0.7) 50%, rgba(10, 14, 26, 0.9) 100%);
    border: 1px solid rgba(139, 92, 246, 0.3);
    border-radius: 24px;
    padding: 45px 35px;
    margin-bottom: 30px;
    position: relative;
    overflow: hidden;
    box-shadow: 0 20px 50px -10px rgba(0, 0, 0, 0.6), inset 0 1px 0 rgba(255, 255, 255, 0.12);
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
}

.hero-container::before {
    content: '';
    position: absolute;
    top: -50%;
    left: -20%;
    width: 140%;
    height: 200%;
    background: radial-gradient(circle at 30% 30%, rgba(139, 92, 246, 0.15) 0%, transparent 40%),
                radial-gradient(circle at 70% 60%, rgba(245, 158, 11, 0.1) 0%, transparent 40%);
    pointer-events: none;
}

.hero-pill {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    background: rgba(139, 92, 246, 0.18);
    border: 1px solid rgba(139, 92, 246, 0.4);
    color: #c4b5fd;
    padding: 6px 18px;
    border-radius: 30px;
    font-size: 13px;
    font-weight: 700;
    margin-bottom: 18px;
    box-shadow: 0 0 15px rgba(139, 92, 246, 0.25);
}

.hero-title {
    font-size: 38px !important;
    font-weight: 900 !important;
    background: linear-gradient(135deg, #ffffff 0%, #e2e8f0 50%, #c4b5fd 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 15px !important;
    line-height: 1.3 !important;
    text-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
}

.hero-subtitle {
    font-size: 18px;
    color: #cbd5e1;
    line-height: 1.8;
    max-width: 900px;
    font-weight: 500;
    margin-bottom: 15px;
}

/* --- بطاقات الإحصائيات السريعة --- */
.stat-card {
    background: rgba(15, 23, 42, 0.65);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 18px;
    padding: 22px 20px;
    text-align: center;
    transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
    box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.4);
    backdrop-filter: blur(10px);
}

.stat-card:hover {
    transform: translateY(-5px);
    border-color: rgba(139, 92, 246, 0.4);
    box-shadow: 0 15px 35px -5px rgba(124, 58, 237, 0.25);
    background: rgba(22, 30, 52, 0.75);
}

.stat-icon {
    font-size: 32px;
    margin-bottom: 10px;
    display: inline-block;
    filter: drop-shadow(0 0 10px rgba(139, 92, 246, 0.4));
}

.stat-value {
    font-size: 20px;
    font-weight: 800;
    color: #ffffff;
    margin-bottom: 5px;
}

.stat-desc {
    font-size: 13px;
    color: #94a3b8;
    font-weight: 500;
}

/* --- بطاقات البرامج العشرة --- */
.program-card {
    background: rgba(17, 24, 39, 0.75);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 20px;
    padding: 24px 22px;
    height: 100%;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
    box-shadow: 0 8px 30px rgba(0, 0, 0, 0.35);
    position: relative;
    overflow: hidden;
}

.program-card::after {
    content: '';
    position: absolute;
    bottom: 0;
    right: 0;
    left: 0;
    height: 3px;
    background: linear-gradient(90deg, #7c3aed, #38bdf8);
    opacity: 0;
    transition: opacity 0.3s ease;
}

.program-card:hover {
    transform: translateY(-6px);
    border-color: rgba(139, 92, 246, 0.45);
    box-shadow: 0 18px 40px -10px rgba(124, 58, 237, 0.3);
    background: rgba(26, 32, 54, 0.85);
}

.program-card:hover::after {
    opacity: 1;
}

.program-header {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 14px;
}

.program-icon-box {
    width: 50px;
    height: 50px;
    border-radius: 14px;
    background: rgba(139, 92, 246, 0.15);
    border: 1px solid rgba(139, 92, 246, 0.3);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 24px;
    flex-shrink: 0;
}

.program-title {
    font-size: 17px;
    font-weight: 800;
    color: #f8fafc;
    line-height: 1.4;
}

.program-desc {
    font-size: 13.5px;
    color: #94a3b8;
    line-height: 1.7;
    margin-bottom: 16px;
    flex-grow: 1;
}

.program-tag {
    display: inline-block;
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.1);
    color: #38bdf8;
    font-size: 11.5px;
    font-weight: 600;
    padding: 4px 12px;
    border-radius: 20px;
    align-self: flex-start;
}

/* --- بطاقة المطور والملكية الفكرية --- */
.developer-card {
    background: linear-gradient(135deg, rgba(20, 16, 35, 0.8) 0%, rgba(13, 17, 30, 0.85) 100%);
    border: 1px solid rgba(245, 158, 11, 0.3);
    border-radius: 22px;
    padding: 30px;
    margin-top: 35px;
    text-align: center;
    box-shadow: 0 15px 40px -10px rgba(0, 0, 0, 0.5);
    backdrop-filter: blur(12px);
}

.dev-badge {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    background: rgba(245, 158, 11, 0.12);
    border: 1px solid rgba(245, 158, 11, 0.35);
    color: #fde68a;
    padding: 6px 20px;
    border-radius: 30px;
    font-size: 13px;
    font-weight: 700;
    margin-bottom: 12px;
}

.section-headline {
    font-size: 24px;
    font-weight: 800;
    color: #ffffff;
    margin: 35px 0 20px 0;
    display: flex;
    align-items: center;
    gap: 10px;
}
</style>
""", unsafe_allow_html=True)

# 1. لوحة الترحيب الرئيسية الفاخرة (Hero Section)
st.markdown("""
<div class="hero-container">
    <div class="hero-pill">
        <span>✨</span>
        <span>المنصة الفلكية الاحترافية المتكاملة • الإصدار v2.6</span>
    </div>
    <h1 class="hero-title">🪐 المنظومة الفلكية المركزية المطورة</h1>
    <p class="hero-subtitle">
        تحوي هذه المنظومة الفلكية على 10 برامج فرعية تغطي معظم الخدمات الأساسية لعلوم الاسترولوجي، مصممة وفق أحدث خوارزميات الرصد الفلكي الدقيق للأفراد، والشركات، والعلاقات، والدول.
    </p>
</div>
""", unsafe_allow_html=True)

# 2. بطاقات المؤشرات والمميزات السريعة (Highlights Grid)
col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)

with col_stat1:
    st.markdown("""
    <div class="stat-card">
        <div class="stat-icon">🔟</div>
        <div class="stat-value">10 برامج متخصصة</div>
        <div class="stat-desc">تغطية استرولوجية شاملة</div>
    </div>
    """, unsafe_allow_html=True)

with col_stat2:
    st.markdown("""
    <div class="stat-card">
        <div class="stat-icon">⚡</div>
        <div class="stat-value">خوارزميات رادار دقيقة</div>
        <div class="stat-desc">تحليل حسابي وفلكي فوري</div>
    </div>
    """, unsafe_allow_html=True)

with col_stat3:
    st.markdown("""
    <div class="stat-card">
        <div class="stat-icon">🌐</div>
        <div class="stat-value">أفراد • شركات • دول</div>
        <div class="stat-desc">توقعات شاملة ومتعددة الأبعاد</div>
    </div>
    """, unsafe_allow_html=True)

with col_stat4:
    st.markdown("""
    <div class="stat-card">
        <div class="stat-icon">🛡️</div>
        <div class="stat-value">ملكية فكرية موثقة</div>
        <div class="stat-desc">اعتماد رسمي 2026-4630</div>
    </div>
    """, unsafe_allow_html=True)

# 3. عرض البرامج الفلكية العشرة المضمنة في المنظومة (The 10 Programs Showcase)
st.markdown("""
<div class="section-headline">
    <span>🧭</span>
    <span>دليل البرامج والمنظومات الفرعية المتاحة</span>
</div>
""", unsafe_allow_html=True)

programs_row1_col1, programs_row1_col2 = st.columns(2)

with programs_row1_col1:
    st.markdown("""
    <div class="program-card">
        <div class="program-header">
            <div class="program-icon-box">📊</div>
            <div class="program-title">برنامج تحليل الخريطة الساعية</div>
        </div>
        <div class="program-desc">
            إجابات دقيقة وحاسمة عن الأسئلة اللحظية واستخراج أدلة البيوت الفلكية والاتصالات الكوكبية الساعية.
        </div>
        <div class="program-tag">استرولوجي ساعي (Horary)</div>
    </div>
    """, unsafe_allow_html=True)

with programs_row1_col2:
    st.markdown("""
    <div class="program-card">
        <div class="program-header">
            <div class="program-icon-box">🔭</div>
            <div class="program-title">السنوية التفصيلية للأفراد أو الشركات أو الدول</div>
        </div>
        <div class="program-desc">
            رصد ومطابقة طوالع التحويل الشمسي وتحليل مسارات العام وتحديد التحديات والفرص السنوية بدقة.
        </div>
        <div class="program-tag">التحويل الشمسي (Solar Return)</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<div style='height: 15px;'></div>", unsafe_allow_html=True)
programs_row2_col1, programs_row2_col2 = st.columns(2)

with programs_row2_col1:
    st.markdown("""
    <div class="program-card">
        <div class="program-header">
            <div class="program-icon-box">✨</div>
            <div class="program-title">التوافقية العاطفية للشخصيات</div>
        </div>
        <div class="program-desc">
            تحليل كيمياء العلاقات الإنسانية والشراكات، فحص التناغم القمري والكوكبي وكشف نقاط القوة والتوتر.
        </div>
        <div class="program-tag">خريطة التوافق (Synastry)</div>
    </div>
    """, unsafe_allow_html=True)

with programs_row2_col2:
    st.markdown("""
    <div class="program-card">
        <div class="program-header">
            <div class="program-icon-box">📁</div>
            <div class="program-title">نظريتي لكشف سنوات الخطر أفراد/دول</div>
        </div>
        <div class="program-desc">
            منهجية خاصة لرصد الدورات الفلكية الحساسة والتنبؤ المسبق بفترات التراجع والأزمات المفصلية الكبرى.
        </div>
        <div class="program-tag">دورات الخطر (Risk Cycles)</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<div style='height: 15px;'></div>", unsafe_allow_html=True)
programs_row3_col1, programs_row3_col2 = st.columns(2)

with programs_row3_col1:
    st.markdown("""
    <div class="program-card">
        <div class="program-header">
            <div class="program-icon-box">⚖️</div>
            <div class="program-title">كشف سنوات الأزمات الزوجية / التجارية</div>
        </div>
        <div class="program-desc">
            رصد زوايا الشقاق ومؤشرات التفكك أو الخلافات الحادة في عقود الزواج والشراكات التجارية المهنية.
        </div>
        <div class="program-tag">تحليل النزاعات والأزمات</div>
    </div>
    """, unsafe_allow_html=True)

with programs_row3_col2:
    st.markdown("""
    <div class="program-card">
        <div class="program-header">
            <div class="program-icon-box">🔭</div>
            <div class="program-title">منظومة تحليل ميلادية/سنوية/توقعات</div>
        </div>
        <div class="program-desc">
            تشخيص فلكي متكامل لهيئة الولادة يجمع بين طالع الميلاد والعبور الكوكبي المباشر والتوقعات الزمنية.
        </div>
        <div class="program-tag">التحليل الشامل (Natal & Transits)</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<div style='height: 15px;'></div>", unsafe_allow_html=True)
programs_row4_col1, programs_row4_col2 = st.columns(2)

with programs_row4_col1:
    st.markdown("""
    <div class="program-card">
        <div class="program-header">
            <div class="program-icon-box">📈</div>
            <div class="program-title">برنامج التنجيم الجغرافي</div>
        </div>
        <div class="program-desc">
            إسقاط الخارطة الفلكية على خريطة العالم لاكتشاف أفضل المدن والدول للنجاح، المال، والشهرة، والاستقرار.
        </div>
        <div class="program-tag">التنجيم المكاني (Astrocartography)</div>
    </div>
    """, unsafe_allow_html=True)

with programs_row4_col2:
    st.markdown("""
    <div class="program-card">
        <div class="program-header">
            <div class="program-icon-box">🔢</div>
            <div class="program-title">برنامج خريطة الحدث العاطفية</div>
        </div>
        <div class="program-desc">
            مصفوفة فلكية لاكتشاف دلالات توقيت اللقاءات وبدايات المشاعر والارتباطات العاطفية ونتائجها المستقبلية.
        </div>
        <div class="program-tag">مصفوفة الأحداث (Event Matrix)</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<div style='height: 15px;'></div>", unsafe_allow_html=True)
programs_row5_col1, programs_row5_col2 = st.columns(2)

with programs_row5_col1:
    st.markdown("""
    <div class="program-card">
        <div class="program-header">
            <div class="program-icon-box">🔗</div>
            <div class="program-title">كشف سنوات الزواج-الإنجاب/صفات الشريك</div>
        </div>
        <div class="program-desc">
            تحليل دلالات البيت السابع والخامس لتعيين أوقات النصيب والإنجاب ورسم الملامح الفلكية لشريك العمر.
        </div>
        <div class="program-tag">أقدار العلاقات والنسل</div>
    </div>
    """, unsafe_allow_html=True)

with programs_row5_col2:
    st.markdown("""
    <div class="program-card">
        <div class="program-header">
            <div class="program-icon-box">🌌</div>
            <div class="program-title">نظريتي لكشف سنوات التغيير أفراد/دول</div>
        </div>
        <div class="program-desc">
            رصد التحولات الجذرية والنقلات النوعية في مسارات الأفراد والدول والتنبؤ بمواعيد التغيير الكبرى.
        </div>
        <div class="program-tag">طفرات المصير والتحول</div>
    </div>
    """, unsafe_allow_html=True)

# 4. بطاقة المطور والملكية الفكرية والتوجيه
st.markdown("""
<div class="developer-card">
    <div class="dev-badge">
        <span>⭐</span>
        <span>المطور المعتمد</span>
    </div>
    <h3 style="color: #ffffff; font-size: 22px; font-weight: 800; margin-bottom: 10px;">
        تم تطوير هذه المنظومة بواسطة الفلكي - استرو رادار
    </h3>
    <p style="color: #94a3b8; font-size: 15px; max-width: 750px; margin: 0 auto 18px auto; line-height: 1.8;">
        تم بناء وتطوير هذه البرمجيات الفلكية بعد أبحاث وتطبيقات متقدمة في علم الفلك والتنجيم الراداري. المنظومة محمية ومسجلة رسمياً بموجب 
        <strong style="color: #fde68a;">شهادة ملكية فكرية رقم 2026-4630</strong>.
    </p>
    <div style="display: inline-flex; align-items: center; gap: 8px; color: #a78bfa; font-size: 14px; font-weight: 700; background: rgba(139, 92, 246, 0.12); padding: 8px 22px; border-radius: 20px; border: 1px solid rgba(139, 92, 246, 0.25);">
        <span>👈</span>
        <span>للبدء، يرجى اختيار البرنامج المطلوب من القائمة الجانبية في اليمين</span>
    </div>
</div>
""", unsafe_allow_html=True)
