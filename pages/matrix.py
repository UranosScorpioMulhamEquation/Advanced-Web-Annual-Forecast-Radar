import datetime
import streamlit as st
import os
import uuid

# ==================== 1. Security & License ====================
KEY_FILE = "license.key"

def get_machine_id():
    return hex(uuid.getnode())

def generate_password(mid):
    digits = ''.join(filter(str.isdigit, mid))
    num = int(digits[:8]) if digits else int(mid.encode().hex(), 16)
    return str(round(abs(num / 2 * 3.14)))[:6]

if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = os.path.exists(KEY_FILE)

if not st.session_state['authenticated']:
    st.set_page_config(page_title="Security Activation", layout="centered")
    st.title("🔑 Security Activation")
    st.warning("Send your Machine ID to programmer email : mulham81ahmed@gmail.com")

    mid = get_machine_id()
    st.info(f"Machine ID: {mid}")
    pwd = st.text_input("Enter Activation Key:", type="password")
    if st.button("Activate"):
        if pwd == generate_password(mid):
            with open(KEY_FILE, "w") as f: f.write(pwd)
            st.session_state['authenticated'] = True
            st.rerun()
        else:
            st.error("Invalid Activation Key.")
    st.stop()


# إعداد صفحة ستريمليت
st.set_page_config(
    page_title="المحلل الخبير لمصفوفة القدر", page_icon="✨", layout="wide"
)

# تنسيق واجهة المستخدم للغة العربية وتصاميم RTL
st.markdown(
    """
    <style>
    body, [data-testid="stAppViewContainer"] {
        direction: rtl;
        text-align: right;
        font-family: 'Tahoma', sans-serif;
    }
    .main-title {
        text-align: center;
        color: #2c3e50;
        font-weight: bold;
        margin-bottom: 20px;
    }
    .card {
        background-color: #ffffff;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        margin-bottom: 20px;
        border-right: 5px solid #3498db;
    }
    .sub-header {
        color: #2980b9;
        border-bottom: 2px solid #ecf0f1;
        padding-bottom: 5px;
        margin-top: 15px;
    }
    .table-container {
        max-height: 350px;
        overflow-y: auto;
        border: 1px solid #ddd;
        border-radius: 5px;
        padding: 10px;
    }
    </style>
""",
    unsafe_allow_html=True,
)


# دالة اختزال الأرقام لتتطابق مع الطاقات الـ 22 الكبرى في مصفوفة القدر
def reduce_to_22(n):
  if n <= 22:
    return n if n > 0 else 22
  while n > 22:
    n = sum(int(digit) for digit in str(n))
    if n == 0:
      return 22
  return n


# دالة حساب نقاط المصفوفة الأساسية
def calculate_destiny_matrix(birth_date):
  day = birth_date.day
  month = birth_date.month
  year = birth_date.year

  p1 = reduce_to_22(day)  # زاوية اليوم (الشخصية)
  p2 = reduce_to_22(month)  # زاوية الشهر (الروحانيات)
  year_sum = sum(int(d) for d in str(year))
  p3 = reduce_to_22(year_sum)  # زاوية السنة (القدر)

  p4 = reduce_to_22(p1 + p2 + p3)  # الأرضية / الزاوية الرابعة
  center = reduce_to_22(p1 + p2 + p3 + p4)  # المركز (طاقة الروح الأساسية)

  money_line = reduce_to_22(p1 + p4 + center)
  love_line = reduce_to_22(p2 + p3 + center)
  health_line = reduce_to_22(p1 + p2 + center)

  return {
      "p1": p1,
      "p2": p2,
      "p3": p3,
      "p4": p4,
      "center": center,
      "money_line": money_line,
      "love_line": love_line,
      "health_line": health_line,
  }


# قاموس شرح معاني الطاقة المهيمنة (الـ 22 طاقة الكبرى)
ENERGY_MEANINGS = {
    1: "الساحر: طاقة البدايات، الإرادة الصلبة، القدرة على الابتكار وتسيير الأمور بمهارة وقيادة ذاتية.",
    2: "الكاهنة: طاقة الحدس العميق، الأسرار، الحكمة الصامتة، والتأمل الباطني وقراءة ما بين السطور.",
    3: "الإمبراطورة: طاقة الخصوبة، الوفرة المادية، النمو، الرعاية، والاهتمام بالتفاصيل الأسرية والمهنية.",
    4: "الإمبراطور: طاقة السلطة، النظام، الاستقرار الهيكلي، البناء المؤسسي، والمسؤولية القيادية.",
    5: "الكاهن الأكبر: طاقة العلم، التقاليد، الإرشاد الروحي، التعليم، والالتزام بالمنظومة الأخلاقية.",
    6: "العاشقان: طاقة الاختيارات العاطفية، الشراكات، الانسجام، التناغم، وبحث القلب عن الجمال.",
    7: "العربة: طاقة الحركة، السفر، الإصرار، الانتصار على التحديات، والانتقال لمحطة حياتية أوسع.",
    8: "العدالة: طاقة التوازن، الكارما، الحقيقة المطلقة، والوضوح القانوني والإداري.",
    9: "الناسك: طاقة الحكمة العميقة، العزلة الاختيارية للنضج، البحث المعرفي، والاستنارة الداخلية.",
    10: "عجلة الحظ: طاقة التحولات القدرية، الفرص المفاجئة، وانفتاح أبواب الرزق وتغير الدورات للأفضل.",
    11: "القوة: طاقة الحيوية الجسدية العالية، الشجاعة، السيطرة على النفس، والقدرة الفائقة على التحمل.",
    12: "المصلوب: طاقة التضحية الواعية، رؤية الأمور من منظور معكوس، وتجاوز الابتلاءات بالصبر الروحي.",
    13: "الموت: طاقة التحول الجذري، التجدد الشامل، وإغلاق صفحات القديم لفتح آفاق متجددة.",
    14: "الاعتدال: طاقة التناغم، الصبر، الشفاء الذاتي، والامتزاج الهادئ والمتوازن للعناصر.",
    15: "الشيطان: طاقة مواجهة الإغراءات، كشف التعلقات المادية الخفية، والتحرر من القيود النفسية.",
    16: "البرج: طاقة الصدمات المفاجئة، هدم الهياكل غير الصالحة، وإعادة التأسيس على قواعد صحيحة.",
    17: "النجمة: طاقة الأمل، الإلهام المضيء، الشهرة، والتألق المستقبلي الواعد في الأفق.",
    18: "القمر: طاقة الخيال، الأوهام، الغموض، وتفعيل مواجهة المخاوف الكامنة في العقل الباطن.",
    19: "الشمس: طاقة السعادة المطلقة، الوضوح الإشعاعي، النجاح الجماهيري، والحيوية الكبرى.",
    20: "الحكم: طاقة البعث العائلي أو الشخصي، التحرر من قيود الماضي، واليقظة الكبرى.",
    21: "العالم: طاقة التوسع العالمي، الانفتاح على الثقافات والآفاق الكبرى، والكمال وتحقيق الغايات.",
    22: "الأحمق: طاقة الحرية المطلقة، البدايات العفوية النصف واعية، والمغامرة الجريئة بلا قيود.",
}


def get_energy_meaning(energy_num):
  return ENERGY_MEANINGS.get(
      energy_num, "طاقة توافقية متجددة تدعم مسار التطور الشخصي."
  )


# دالة تحليل الديون الكارمية من الحياة السابقة
def analyze_karmic_debts(matrix):
  karmic_points = [
      matrix["center"],
      matrix["p1"],
      matrix["p2"],
      matrix["p3"],
      matrix["p4"],
  ]
  debts = []
  if 15 in karmic_points:
    debts.append(
        "كارما السيطرة والتعلق المادي (الرقم 15): اختبارات متكررة في التحرر"
        " من الإغراءات المادية وتجنب التحكم في الآخرين."
    )
  if 13 in karmic_points:
    debts.append(
        "كارما التغيير الجذري ومخاوف النهايات (الرقم 13): مقاومة التغييرات"
        " الإجبارية والتعلق بما أتم دورته."
    )
  if 18 in karmic_points:
    debts.append(
        "كارما الأوهام والمخاوف المخفية (الرقم 18): الميل لتبني مخاوف غير حقيقية"
        " والوقوع في فخ التشاؤم."
    )
  if 12 in karmic_points:
    debts.append(
        "كارما التضحية الزائدة وتعطيل الذات (الرقم 12): تقديم تنازلات مبالغ فيها"
        " على حساب طاقته الخاصة وعدم وضع حدود."
    )
  if 9 in karmic_points:
    debts.append(
        "كارما العزلة والانطواء الفكري (الرقم 9): الحاجة لتجاوز الخوف من الانفتاح"
        " على المجتمع ومشاركة المعرفة."
    )
  if not debts:
    debts.append(
        "كارما متوازنة نسبياً؛ ترتكز على دروس حياتية خفيفة تتعلق بتحقيق التوازن"
        " العادل بين الروح والمادة."
    )
  return debts


# دالة تحليل بوابات التشافي الكارمي ومؤشرات التحرر
def analyze_karmic_healing_gates(matrix):
  karmic_points = [
      matrix["center"],
      matrix["p1"],
      matrix["p2"],
      matrix["p3"],
      matrix["p4"],
  ]
  healing_gates = []

  for p in karmic_points:
    if p == 15:
      healing_gates.append(
          "بوابة التشافي للرقم 15 (طاقة التحرر المادي والتحكم): ممارسة التخلي"
          " الواعي، التبرع، وتطوير مرونة قبول الآخر دون فرض السيطرة أو الرقابة"
          " الصارمة."
      )
    elif p == 13:
      healing_gates.append(
          "بوابة التشافي للرقم 13 (طاقة التحول والتجدد): تقبل النهايات كبدايات"
          " جديدة، التخلص الدوري من الأشياء والعلاقات والأفكار القديمة التي أتمت"
          " دورتها."
      )
    elif p == 18:
      healing_gates.append(
          "بوابة التشافي للرقم 18 (طاقة الإضاءة الباطنية وتبديد الأوهام): مواجهة"
          " مخاوف العقل الباطن وجهاً لوجه، تدوين الهواجس، وتفعيل اليقين والوضوح"
          " الفكري."
      )
    elif p == 12:
      healing_gates.append(
          "بوابة التشافي للرقم 12 (طاقة الخدمة الواعية ووضع الحدود): تعلم قول"
          " 'لا' بحزم، وحماية الطاقة الشخصية من الاستنزاف عبر العطاء غير"
          " المشروط الخاطئ."
      )
    elif p == 9:
      healing_gates.append(
          "بوابة التشافي للرقم 9 (طاقة الانفتاح والحكمة الإنسانية): كسر قوقعة"
          " الانطواء، ومشاركة المعرفة والخبرات الروحية مع المحيط دون خوف من"
          " سوء الفهم."
      )

  if not healing_gates:
    healing_gates.append(
        "بوابة التشافي العامة: ممارسة التأمل العميق، توازن طاقة القلب، والاتصال"
        " المنتظم بالطبيعة لترسيخ طاقة المركز."
    )
  return healing_gates


# دالة تحليل المعوقات والأنماط المتكررة
def analyze_patterns_and_obstacles(matrix):
  obstacles = []
  patterns = []

  if matrix["center"] in [12, 15, 18]:
    obstacles.append(
        "مواجهة صراعات داخلية تتعلق بوضع الحدود الشخصية وقول 'لا'."
    )
    patterns.append(
        "نمط جذب مواقف وعلاقات استنزافية تتطلب وعياً عالياً للتحرر منها."
    )
  elif matrix["center"] in [4, 7, 11]:
    obstacles.append(
        "الإفراط في تحمل المسؤوليات ومحاولة السيطرة على كل التفاصيل بمفرده."
    )
    patterns.append(
        "نمط الضغط المستمر على الطاقة الجسدية والنفسية مما يسبب إرهاقاً دورياً."
    )
  else:
    obstacles.append(
        "التشتت بين عدة مسارات والتردد الحاسم في أوقات المفترقات المصيرية."
    )
    patterns.append(
        "نمط تأجيل الخطوات التنفيذية الكبرى حتى تتضح الرؤية بشكل كامل."
    )

  return obstacles, patterns


# دالة لتنسيق السنة بنطاق سنتين (مثال: 2034-2035)
def rg(y):
  return f"{y}-{y+1}"


# واجهة الإدخال الجانبية
st.sidebar.header("🎛️ بيانات المستفيد")
name = st.sidebar.text_input("الاسم الكامل", "جديد")
gender = st.sidebar.selectbox("الجنس", ["ذكر", "أنثى"])
birth_date = st.sidebar.date_input(
    "تاريخ الميلاد",
    datetime.date(2026, 1, 1),
    min_value=datetime.date(1950, 1, 1),
)

st.markdown(
    '<h1 class="main-title">🌟 نظام تحليل مصفوفة القدر - تطوير الفلكي استرو رادار</h1>',
    unsafe_allow_html=True,
)
st.markdown(
    "<p style='text-align: center; color: #7f8c8d;'>نظام متقدم يدمج علم الفلك"
    " الهندي والغربي مع فك شيفرات مصفوفة القدر الـ 22 لكافة التواريخ.</p>",
    unsafe_allow_html=True,
)

if st.sidebar.button("🚀 ابدأ التحليل الفلكي الشامل", type="primary"):
  matrix = calculate_destiny_matrix(birth_date)
  b_year = birth_date.year

  # أولاً: تحليل الوضع المالي (حتى عمر 60)
  money_sources = []
  if matrix["money_line"] in [3, 10, 19]:
    money_sources.append(
        "المشاريع الخاصة الحرة، الاستثمار التجاري، والعمل الريادي المستقل"
    )
  if matrix["money_line"] in [4, 8, 21]:
    money_sources.append(
        "الوظائف القيادية في المؤسسات الكبرى، الإدارة العليا، والهيئات الرسمية"
    )
  if matrix["money_line"] in [2, 12, 14]:
    money_sources.append(
        "الشراكات المثمرة، الدعم المالي من الأهل أو الشريك، والاستشارات"
        " المتخصصة"
    )
  if not money_sources:
    money_sources.append(
        "الأعمال الرقمية الحديثة، الابتكار التقني، والملكية الفكرية"
    )

  fin_ages = [20, 27, 33, 40, 45, 52, 58]
  financial_years = [
      rg(b_year + a) for a in fin_ages if (b_year + a + 1) <= b_year + 60
  ]

  # ثانياً: تحليل الوضع العاطفي والزواج (حتى عمر 60)
  second_marriage = (
      "نعم، توجد احتمالية زواج ثانٍ وفقاً لتفعيل طاقات التغيير في خط العلاقات"
      if matrix["love_line"] % 2 != 0
      else "لا، الميل الاستقراري الغالب نحو شريك واحد طوال المسار"
  )
  separation_possibility = (
      "محتمل حدوث إعادة هيكلة أو انفصال في الدورات الحرجة"
      if matrix["love_line"] in [12, 15, 16]
      else "استقرار عاطفي مع احتمالية منخفضة جداً للانفصال"
  )
  children_status = (
      "نعم، توجد مؤشرات قوية وواضحة للإنجاب وتكوين أسرة مباركة وذرية صالحة"
  )
  partner_wealth = (
      "غني ومستقر مالياً ولديه قدرة عالية على توفير الرفاهية"
      if matrix["love_line"] % 2 == 0
      else "متوسط الدخل ويعتمد على العصامية والكفاح المشترك"
  )
  partner_origin = (
      "غريب أو أجنبي عن محيطك الجغرافي أو الاجتماعي المباشر"
      if matrix["center"] in [7, 17, 21]
      else "من نفس البيئة المحلية أو المحيط الاجتماعي القريب"
  )
  partner_relation_type = (
      "قد يكون من محيط سابق أو ارتباط روحي متجدد (حبيب سابق/معرفة قديمة)"
      if matrix["love_line"] in [6, 15, 18]
      else "شخص جديد كلياً يدخل حياتك عبر الصدفة القدرية"
  )
  partner_location = (
      "يقيم خارج بلد صاحب المصفوفة أو في مدينة أخرى بعيدة عنه"
      if matrix["center"] in [7, 21]
      else "يقيم في نفس البلد والمحيط الجغرافي لصاحب المصفوفة"
  )
  partner_job = (
      "إدارة أعمال، هندسة، تمويل، أو تجارة كبرى"
      if matrix["love_line"] > 11
      else "تعليم، استشارات، رعاية صحية، أو فنون وتصميم"
  )
  partner_features = (
      "ملامح جذابة، حضور قوي، بنية متناسقة ونظرة ثاقبة تعكس هالة قيادية"
      if matrix["love_line"] % 2 == 0
      else "ملامح هادئة، ابتسامة دافئة، وطابع إنساني مريح للعين"
  )
  mar_ages = [22, 28, 34, 42, 50]
  marriage_years = [
      rg(b_year + a) for a in mar_ages if (b_year + a + 1) <= b_year + 60
  ]
  partner_age_range = "الفارق العمري المتوقع: فارق 2 إلى 12 سنوات"

  # ثالثاً: تحليل الوضع الصحي (حتى عمر 70)
  health_ages_crisis = [29, 37, 48, 56, 65]
  health_crisis_list = [
      f"{rg(b_year + a)}: وعكة صحية تتطلب حذراً ورعاية دقيقة، واحتمالية دخول مستشفى"
      for a in health_ages_crisis
      if (b_year + a + 1) <= b_year + 70
  ]
  health_good_ages = [23, 31, 39, 45, 53, 61, 68]
  health_good_list = [
      rg(b_year + a)
      for a in health_good_ages
      if (b_year + a + 1) <= b_year + 70
  ]

  # رابعاً: الهجرة والسفر
  travel_ages = [24, 32, 41, 49]
  travel_years = [
      rg(b_year + a) for a in travel_ages if (b_year + a + 1) <= b_year + 70
  ]
  migration_status = (
      "توجد مؤشرات قوية لهجرة أو سفر طويل الأجل نحو بيئة مهنية وجغرافية جديدة"
      if matrix["center"] in [7, 17, 21, 22]
      else "السفر مقتصر على التنقلات والسياحة ورحلات العمل المؤقتة"
  )

  # خامساً: تحليل الشخصية والشهرة
  is_famous = matrix["center"] in [11, 19, 21] or matrix["p1"] in [11, 19, 17]
  fame_ages = [35, 46]
  fame_years = [
      rg(b_year + a) for a in fame_ages if (b_year + a + 1) <= b_year + 60
  ]
  fame_field = (
      "العلوم الفلكية والروحية، الاستشارات المعرفية، أو الإعلام الرقمي"
      if is_famous
      else "التميز التخصصي في بيئة العمل والبحث دون صخب إعلامي ضخم"
  )

  # سادساً: الديون الكارمية والأنماط والمعوقات وبوابات التشافي
  karmic_debts = analyze_karmic_debts(matrix)
  obstacles, recurring_patterns = analyze_patterns_and_obstacles(matrix)
  healing_gates = analyze_karmic_healing_gates(matrix)

  # سابعاً: التأثيرات السنوية لـ 60 عاماً قادمة تبدأ من سنة الميلاد (b_year)
  annual_effects = []
  for i in range(60):
    yr = b_year + i
    age = i
    yearly_energy = reduce_to_22(
        matrix["center"] + reduce_to_22(yr) + (age % 22)
    )
    meaning = get_energy_meaning(yearly_energy)
    annual_effects.append(
        {"year": yr, "age": age, "energy": yearly_energy, "meaning": meaning}
    )

  # عرض النتائج في واجهة Streamlit
  st.success(
      "✨ تم إتمام التحليل الفلكي وفك شيفرات مصفوفة القدر لكافة المحاور بنجاح!"
  )

  col1, col2, col3 = st.columns(3)
  col1.metric("طاقة المركز (الروح)", matrix["center"])
  col2.metric("طاقة خط المال", matrix["money_line"])
  col3.metric("طاقة خط العلاقات", matrix["love_line"])

  # 1. الوضع المالي
  st.markdown(
      f"""
    <div class="card">
        <h3 class="sub-header">أولاً: تحليل الوضع المالي (حتى عمر 60)</h3>
        <p><b>مصادر الأموال المتوقعة:</b> {', '.join(money_sources)}.</p>
        <p><b>أفضل سنوات الوفرة المالية:</b> {', '.join(financial_years)}.</p>
    </div>
    """,
      unsafe_allow_html=True,
  )

  # 2. الوضع العاطفي
  st.markdown(
      f"""
    <div class="card">
        <h3 class="sub-header">ثانياً: تحليل الوضع العاطفي والزواج (حتى عمر 60)</h3>
        <ul>
            <li><b>الزواج الثاني:</b> {second_marriage}.</li>
            <li><b>الانفصال عن الزواج الحالي:</b> {separation_possibility}.</li>
            <li><b>الإنجاب:</b> {children_status}.</li>
            <li><b>هل الزوج غني؟</b> {partner_wealth}.</li>
            <li><b>أصل الزوج (غريب أم حبيب سابق):</b> {partner_origin} | {partner_relation_type}.</li>
            <li><b>مكان إقامة الزوج:</b> {partner_location}.</li>
            <li><b>وظيفة أو عمل الزوج المتوقع:</b> {partner_job}.</li>
            <li><b>الصفات الشكلية المتوقعة للزوج:</b> {partner_features}.</li>
            <li><b>السنوات المتوقعة للزواج (أو تجديد الارتباط):</b> {', '.join(marriage_years)}.</li>
            <li><b>عمر الزوج والفارق المتوقع:</b> {partner_age_range}.</li>
        </ul>
    </div>
    """,
      unsafe_allow_html=True,
  )

  # 3. الوضع الصحي
  st.markdown(
      f"""
    <div class="card">
        <h3 class="sub-header">ثالثاً: تحليل الوضع الصحي (حتى عمر 70)</h3>
        <p><b>سنوات الأزمات الصحية (وعكات أو احتمالية دخول مستشفى):</b><br>{'<br>'.join(health_crisis_list)}</p>
        <p><b>السنوات التي يكون فيها الوضع الصحي ممتازاً ومستقراً:</b> {', '.join(health_good_list)}.</p>
    </div>
    """,
      unsafe_allow_html=True,
  )

  # 4. الهجرة والسفر
  st.markdown(
      f"""
    <div class="card">
        <h3 class="sub-header">رابعاً: الهجرة والسفر</h3>
        <p><b>حالة الهجرة:</b> {migration_status}</p>
        <p><b>سنوات السفر الخارجي والترحال:</b> {', '.join(travel_years)}.</p>
    </div>
    """,
      unsafe_allow_html=True,
  )

  # 5. تحليل الشخصية والشهرة
  st.markdown(
      f"""
    <div class="card">
        <h3 class="sub-header">خامساً: تحليل الشخصية (فك شيفرات 22 نقطة) والشهرة</h3>
        <p><b>ملخص تحليل الشخصية:</b> يمتلك صاحب المصفوفة طاقة المركز ({matrix['center']}) المدمجة مع الأسرار الكبرى الـ 22، مما يمنحه بصيرة نافذة، قدرة تحليلية عميقة، ومقدرة فريدة على كشف خبايا الأمور وفك الشيفرات المعقدة.</p>
        <p><b>مؤشر الشهرة:</b> {'مشهور وله بصمة جماهيرية واسعة' if is_famous else 'شخصية تتميز بالعمق والنجاح التخصصي والنخبوي'}.</p>
        <p><b>سنوات الشهرة:</b> {', '.join(fame_years) if fame_years else 'النجاح مهني وعميق دون صخب إعلامي واسع'}.</p>
        <p><b>مجال الشهرة:</b> {fame_field}.</p>
    </div>
    """,
      unsafe_allow_html=True,
  )

  # 6. الكارما والمعوقات والأنماط المتكررة
  st.markdown(
      f"""
    <div class="card">
        <h3 class="sub-header">سادساً: الديون الكارمية من الحياة السابقة والمعوقات</h3>
        <p><b>الديون الكارمية المؤثرة:</b></p>
        <ul>{''.join([f"<li>{debt}</li>" for debt in karmic_debts])}</ul>
        <p><b>المعوقات الأساسية:</b></p>
        <ul>{''.join([f"<li>{obs}</li>" for obs in obstacles])}</ul>
        <p><b>الأنماط المتكررة في حياة المستفيد:</b></p>
        <ul>{''.join([f"<li>{pat}</li>" for pat in recurring_patterns])}</ul>
    </div>
    """,
      unsafe_allow_html=True,
  )

  # 7. بوابات التشافي الكارمي ومؤشرات التحرر
  st.markdown(
      f"""
    <div class="card">
        <h3 class="sub-header">سابعاً: بوابات التشافي الكارمي ومؤشرات التحرر</h3>
        <p><b>مفاتيح الحل والترددات العلاجية لتجاوز العقد الكارمية:</b></p>
        <ul>{''.join([f"<li>{gate}</li>" for gate in healing_gates])}</ul>
    </div>
    """,
      unsafe_allow_html=True,
  )

  # 8. التأثيرات السنوية لـ 60 عاماً القادمة (من سنة الميلاد)
  annual_rows = "".join([
      f"<tr><td>{item['year']}</td><td>{item['age']}</td><td><b>طاقة الرقم {item['energy']}</b></td><td>{item['meaning']}</td></tr>"
      for item in annual_effects
  ])
  st.markdown(
      f"""
    <div class="card">
        <h3 class="sub-header">ثامناً: التأثيرات السنوية وتفصيل الطاقات المهيمنة (من سنة الميلاد {b_year} ولغاية 60 عاماً)</h3>
        <div class="table-container">
            <table style="width:100%; border-collapse: collapse; text-align: right;">
                <thead>
                    <tr style="background-color: #f2f2f2; border-bottom: 2px solid #ddd;">
                        <th style="padding: 8px;">السنة</th>
                        <th style="padding: 8px;">العمر</th>
                        <th style="padding: 8px;">الطاقة</th>
                        <th style="padding: 8px;">شرح المعنى والتأثير المفصل</th>
                    </tr>
                </thead>
                <tbody>
                    {annual_rows}
                </tbody>
            </table>
        </div>
    </div>
    """,
      unsafe_allow_html=True,
  )

  # تقرير HTML القابل للطباعة
  html_annual_rows = "".join([
      f"<tr><td style='padding: 6px; border-bottom: 1px solid #ddd;'>{item['year']}</td><td style='padding: 6px; border-bottom: 1px solid #ddd;'>{item['age']}</td><td style='padding: 6px; border-bottom: 1px solid #ddd;'><b>طاقة الرقم {item['energy']}</b></td><td style='padding: 6px; border-bottom: 1px solid #ddd;'>{item['meaning']}</td></tr>"
      for item in annual_effects
  ])

  html_report = f"""
    <!DOCTYPE html>
    <html lang="ar" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <title>تقرير مصفوفة القدر الشامل - {name}</title>
        <style>
            body {{ font-family: 'Amiri', Tahoma, sans-serif; background-color: #fff; color: #222; padding: 40px; line-height: 1.8; }}
            .container {{ max-width: 950px; margin: auto; border: 1px solid #ccc; padding: 40px; border-radius: 10px; }}
            h1 {{ text-align: center; color: #1a5276; border-bottom: 3px solid #3498db; padding-bottom: 15px; }}
            .meta {{ background: #f8f9fa; padding: 20px; border-radius: 6px; margin-bottom: 25px; border-right: 4px solid #2980b9; }}
            .section {{ margin-bottom: 25px; border-bottom: 1px solid #e2e8f0; padding-bottom: 20px; }}
            h3 {{ color: #2980b9; margin-bottom: 10px; }}
            ul {{ padding-right: 20px; }}
            li {{ margin-bottom: 8px; }}
            .footer {{ text-align: center; margin-top: 40px; font-size: 12px; color: #7f8c8d; border-top: 1px solid #eee; padding-top: 15px; }}
            .print-btn {{ background: #2c3e50; color: white; padding: 12px 30px; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; display: block; margin: 30px auto; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; text-align: right; font-size: 13px; }}
            th {{ background-color: #f8f9fa; color: #2c3e50; }}
            @media print {{ .print-btn {{ display: none; }} }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>تقرير مصفوفة القدر الشامل</h1>
            <div class="meta">
                <p><b>اسم المستفيد:</b> {name}</p>
                <p><b>الجنس:</b> {gender}</p>
                <p><b>تاريخ الميلاد:</b> {birth_date}</p>
                <p><b>طاقات المصفوفة المحورية:</b> المركز ({matrix['center']}) | المال ({matrix['money_line']}) | العواطف ({matrix['love_line']})</p>
            </div>

            <div class="section">
                <h3>أولاً: تحليل الوضع المالي (حتى عمر 60)</h3>
                <p><b>مصادر الأموال المتوقعة:</b> {', '.join(money_sources)}</p>
                <p><b>أفضل سنوات الوفرة المالية:</b> {', '.join(financial_years)}</p>
            </div>

            <div class="section">
                <h3>ثانياً: تحليل الوضع العاطفي والزواج (حتى عمر 60)</h3>
                <ul>
                    <li><b>الزواج الثاني:</b> {second_marriage}</li>
                    <li><b>الانفصال عن الزواج الحالي:</b> {separation_possibility}</li>
                    <li><b>الإنجاب:</b> {children_status}</li>
                    <li><b>هل الزوج غني؟</b> {partner_wealth}</li>
                    <li><b>أصل الزوج (غريب أم حبيب سابق):</b> {partner_origin} | {partner_relation_type}</li>
                    <li><b>مكان إقامة الزوج:</b> {partner_location}</li>
                    <li><b>وظيفة أو عمل الزوج:</b> {partner_job}</li>
                    <li><b>الصفات الشكلية المتوقعة للزوج:</b> {partner_features}</li>
                    <li><b>السنوات المتوقعة للزواج (أو تجديد الارتباط):</b> {', '.join(marriage_years)}</li>
                    <li><b>عمر الزوج والفارق المتوقع:</b> {partner_age_range}</li>
                </ul>
            </div>

            <div class="section">
                <h3>ثالثاً: تحليل الوضع الصحي (حتى عمر 70)</h3>
                <p><b>سنوات الأزمات الصحية والعمليات أو الوعكات:</b><br>{'<br>'.join(health_crisis_list)}</p>
                <p><b>سنوات الاستقرار والوضع الصحي الممتاز:</b> {', '.join(health_good_list)}</p>
            </div>

            <div class="section">
                <h3>رابعاً: الهجرة والسفر</h3>
                <p><b>حالة الهجرة:</b> {migration_status}</p>
                <p><b>سنوات السفر الخارجي والترحال:</b> {', '.join(travel_years)}</p>
            </div>

            <div class="section">
                <h3>خامساً: تحليل الشخصية (فك شيفرات 22 نقطة) والشهرة</h3>
                <p><b>تحليل الشخصية:</b> يحمل طاقة المركز ({matrix['center']}) المفسرة لشيفرات الأسرار الكبرى، مما يمنحه حكمة استثنائية وبصيرة نافذة.</p>
                <p><b>مؤشر الشهرة:</b> {'مشهور وله بصمة جماهيرية واسعة' if is_famous else 'شخصية نخبوية ذات نجاح تخصصي هادئ'}</p>
                <p><b>سنوات الشهرة:</b> {', '.join(fame_years) if fame_years else 'لا توجد ذروة شهرة إعلامية ضخمة'}</p>
                <p><b>مجال الشهرة:</b> {fame_field}</p>
            </div>

            <div class="section">
                <h3>سادساً: الديون الكارمية من الحياة السابقة والمعوقات والأنماط</h3>
                <p><b>الديون الكارمية:</b></p>
                <ul>{''.join([f"<li>{debt}</li>" for debt in karmic_debts])}</ul>
                <p><b>المعوقات الأساسية:</b></p>
                <ul>{''.join([f"<li>{obs}</li>" for obs in obstacles])}</ul>
                <p><b>الأنماط المتكررة:</b></p>
                <ul>{''.join([f"<li>{pat}</li>" for pat in recurring_patterns])}</ul>
            </div>

            <div class="section">
                <h3>سابعاً: بوابات التشافي الكارمي ومؤشرات التحرر</h3>
                <p><b>مفاتيح الحل والترددات العلاجية:</b></p>
                <ul>{''.join([f"<li>{gate}</li>" for gate in healing_gates])}</ul>
            </div>

            <div class="section">
                <h3>ثامناً: التأثيرات السنوية وتفصيل الطاقات المهيمنة (من سنة الميلاد {b_year} ولغاية 60 عاماً)</h3>
                <table>
                    <thead>
                        <tr>
                            <th>السنة</th>
                            <th>العمر</th>
                            <th>الطاقة</th>
                            <th>شرح المعنى والتأثير المفصل</th>
                        </tr>
                    </thead>
                    <tbody>
                        {html_annual_rows}
                    </tbody>
                </table>
            </div>

            <button class="print-btn" onclick="window.print()">طباعة التقرير مباشرة</button>
            <div class="footer">جميع الحقوق محفوظة - استرو رادار © 2026</div>
        </div>
    </body>
    </html>
    """

  st.download_button(
      label="📥 تحميل التقرير النهائي (HTML جاهز للطباعة)",
      data=html_report,
      file_name=f"Destiny_Matrix_Report_{name}.html",
      mime="text/html",
  )
