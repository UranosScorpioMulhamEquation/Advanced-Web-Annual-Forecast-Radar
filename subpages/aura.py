from datetime import date, datetime, time, timedelta, timezone
import base64
import datetime
import numpy as np
import pandas as pd
import streamlit as st
import swisseph as swe
import os

# ---------------------------------------------------------
# إعدادات صفحة الستريملิต
# ---------------------------------------------------------
st.set_page_config(
    page_title="نظام التوافقية الفلكية المتقدم (التحليل الصارم للأطراف)",
    page_icon="✨",
    layout="wide",
)

# ==================== إعدادات Swiss Ephemeris ====================
swe.set_ephe_path('')  # استخدام وضع Moshier الافتراضي للتقويم الفلكي الدقيق

# ---------------------------------------------------------
# 1. القواميس الأساسية (الكواكب العشرة كاملة)
# ---------------------------------------------------------
PLANETS = {
    swe.SUN: {"name": "الشمس", "type": "شخصي", "desc": "الهوية/الجوهر/الوعي"},
    swe.MOON: {"name": "القمر", "type": "شخصي", "desc": "العاطفة/النفس/اللاوعي"},
    swe.MERCURY: {"name": "عطارد", "type": "شخصي", "desc": "الفكر/التواصل/المنطق"},
    swe.VENUS: {"name": "الزهرة", "type": "شخصي", "desc": "الحب/الانسجام/القيم"},
    swe.MARS: {"name": "المريخ", "type": "شخصي", "desc": "الطاقة/الدافع/الحماسة"},
    swe.JUPITER: {"name": "المشتري", "type": "اجتماعي", "desc": "الحظ/التوسع/الفرص"},
    swe.SATURN: {"name": "زحل", "type": "اجتماعي", "desc": "الضغط/المسؤولية/القيود"},
    swe.URANUS: {"name": "أورانوس", "type": "خارجي", "desc": "المفاجآت/التغيير/التمرد"},
    swe.NEPTUNE: {"name": "نبتون", "type": "خارجي", "desc": "الخيال/الوهم/الروحانية"},
    swe.PLUTO: {"name": "بلوتو", "type": "خارجي", "desc": "التحول/السيطرة/العمق"},
}

# ---------------------------------------------------------
# 2. دوال الحسابات الفلكية وتحليل البيوت والتفسيرات الشاملة
# ---------------------------------------------------------
def get_planet_positions(year, month, day, hour=12.0):
    jd = swe.julday(year, month, day, hour)
    positions = {}
    for p_id in PLANETS.keys():
        try:
            res, _ = swe.calc_ut(jd, p_id)
            positions[p_id] = res[0]
        except Exception:
            positions[p_id] = 0.0
    return positions

def get_zodiac_sign(degrees):
    signs = [
        "الحمل", "الثور", "الجوزاء", "السرطان",
        "الأسد", "العذراء", "الميزان", "العقرب",
        "القوس", "الجدي", "الدلو", "الحوت"
    ]
    sign_index = int(degrees // 30) % 12
    return signs[sign_index], sign_index + 1

def get_solar_house(planet_deg, partner_sun_deg):
    planet_sign = int(planet_deg // 30) % 12
    partner_sun_sign = int(partner_sun_deg // 30) % 12
    house = ((planet_sign - partner_sun_sign) % 12) + 1
    return house

def analyze_house_overlay(planet_id, planet_name, house_num, target_name):
    warning = None
    effect_type = "neutral"
    
    interpretations = {
        swe.SATURN: {
            8: f"⚠️ **تحذير خطير:** زحل في البيت الثامن لـ {target_name} (ضغط مالي، مخاوف عميقة، وثقل نفسي وموارد مشتركة مقيدة ومؤذية جداً).",
            7: f"⚠️ **تنبيه:** زحل في البيت السابع لـ {target_name} (يفرض التزامات رسمية لكنه يسبّب بروداً عاطفياً وثقلاً في العلاقة).",
            4: f"⚠️ **تنبيه:** زحل في البيت الرابع لـ {target_name} (ضغط عائلي وجفاف عاطفي وصعوبة في الاستقرار المعيشي).",
            1: f"⚠️ **تنبيه:** زحل في البيت الأول لـ {target_name} (يفرض رقابة وثقلاً على شخصية وطاقة الشريك).",
        },
        swe.PLUTO: {
            8: f"🔥 **تنبيه شديد:** بلوتو في البيت الثامن لـ {target_name} (طاقة سيطرة، غيرة جارفة، وصراعات على السلطة وتحولات جذرية قاسية).",
            7: f"🔥 **تنبيه:** بلوتو في البيت السابع لـ {target_name} (علاقة مكثفة جداً تحمل طابع السيطرة أو التحول الجذري العنيف).",
            1: f"🔥 **تنبيه:** بلوتو في البيت الأول لـ {target_name} (تأثير مغناطيسي قوي لكنه قد يتحول إلى فرض سيطرة وهيمنة).",
        },
        swe.MARS: {
            8: f"⚡ **تنبيه:** المريخ في البيت الثامن لـ {target_name} (كيمياء وجاذبية جسدية هائلة، لكنه يثير احتكاكات ونزاعات حادة).",
            1: f"⚡ **تنبيه:** المريخ في البيت الأول لـ {target_name} (طاقة عالية وتنافس أو اصطدام مباشر في المبادرات والآراء).",
            7: f"⚡ **تنبيه:** المريخ في البيت السابع لـ {target_name} (شعلة جذب قوية قد تشتعل على شكل خلافات ونقاشات حادة متكررة).",
        }
    }

    if planet_id in interpretations and house_num in interpretations[planet_id]:
        warning = interpretations[planet_id][house_num]
        effect_type = "conflict"
    
    general_notes = {
        swe.SUN: f"يسلط ضوء الوعي والهوية على شؤون البيت {house_num} لـ {target_name}.",
        swe.MOON: f"يثير مشاعر عميقة وتجاوباً وجدانياً في شؤون البيت {house_num} لـ {target_name}.",
        swe.MERCURY: f"ينشط الحوار وتبادل الأفكار في شؤون البيت {house_num} لـ {target_name}.",
        swe.VENUS: f"يجلب الانسجام والمودة والراحة في شؤون البيت {house_num} لـ {target_name}.",
        swe.MARS: f"ينشط طاقة وحماسة في شؤون البيت {house_num} لـ {target_name}.",
        swe.JUPITER: f"🌟 يجلب الحظ والتوسع والدعم في شؤون البيت {house_num} لـ {target_name}.",
        swe.SATURN: f"يفرض مسؤوليات ودروساً جادة في شؤون البيت {house_num} لـ {target_name}.",
        swe.URANUS: f"يجلب مفاجآت ورغبة في التحرر في شؤون البيت {house_num} لـ {target_name}.",
        swe.NEPTUNE: f"يضفي مسحة خيالية أو غموضاً في شؤون البيت {house_num} لـ {target_name}.",
        swe.PLUTO: f"يحدث تأثيراً عميقاً وتحولياً في شؤون البيت {house_num} لـ {target_name}."
    }

    note = warning if warning else general_notes.get(planet_id, f"تأثير في البيت {house_num} لـ {target_name}.")
    return warning, effect_type, note

def calculate_aspect(deg1, deg2, planet1_id, planet2_id):
    diff = abs(deg1 - deg2)
    if diff > 180:
        diff = 360 - diff

    aspect_result = None
    score = 0
    nature = "neutral"

    if diff <= 6:
        aspect_result = "اقتران (دمج طاقات وتأثير مباشر)"
        score = +3
        nature = "harmonious"
    elif abs(diff - 60) <= 6:
        aspect_result = "تسديس (فرصة وتناغم سلس)"
        score = +2
        nature = "harmonious"
    elif abs(diff - 90) <= 6:
        aspect_result = "تربيع (تحدي واحتكاك ضاغط)"
        score = -3
        nature = "conflict"
    elif abs(diff - 120) <= 6:
        aspect_result = "تثليث (تدفق وتوافق طبيعي عالي)"
        score = +4
        nature = "harmonious"
    elif abs(diff - 180) <= 6:
        aspect_result = "معارضة (شد وجذب وتكامل أو صراع)"
        score = -2
        nature = "conflict"

    return aspect_result, score, nature

# ---------------------------------------------------------
# 3. واجهة المستخدم الرئيسية (Streamlit UI)
# ---------------------------------------------------------
st.title("✨ النظام المطور للخرائط الفلكية التوافقية (التحديد الدقيق للمسؤوليات)")
st.markdown("تطوير الخبير الفلكي: استرو رادار")
st.markdown("تم اعتماد البرج الشمسي كبرج طالع")
st.markdown("---")

col1, col2 = st.columns(2)

with col1:
    st.subheader("👤 بيانات الشريك الأول")
    name1 = st.text_input("اسم الشريك الأول", "أحمد")
    gender1 = st.selectbox("جنس الشريك الأول", ["ذكر", "أنثى"], index=0, key="g1")
    dob1 = st.date_input("تاريخ ميلاد الشريك الأول", min_value=date(1950, 1, 1), max_value=date(2040, 1, 1), value=date(1990, 1, 1))

with col2:
    st.subheader("❤️ بيانات الشريك الثاني")
    name2 = st.text_input("اسم الشريك الثاني", "سارة")
    gender2 = st.selectbox("جنس الشريك الثاني", ["أنثى", "ذكر"], index=0, key="g2")
    dob2 = st.date_input("تاريخ ميلاد الشريك الثاني", min_value=date(1950, 1, 1), max_value=date(2040, 1, 1), value=date(1990, 1, 1))

if st.button("🚀 تشغيل التحليل التوافقي الشامل وتحديد المسؤوليات بدقة", type="primary"):
    with st.spinner("جاري حساب مواقع الكواكب، تفصيل المسؤوليات، وحساب النسب بدقة صارمة..."):

        pos1 = get_planet_positions(dob1.year, dob1.month, dob1.day)
        pos2 = get_planet_positions(dob2.year, dob2.month, dob2.day)

        total_score = 0
        aspect_records = []
        overlay_records = []
        warnings_list = []
        marriage_support_score = 0
        
        # تتبعات دقيقة لكل طرف
        p1_financial_score = 0
        p2_financial_score = 0
        p1_pressure_score = 0
        p2_pressure_score = 0
        p1_positive_hits = 0
        p2_positive_hits = 0
        
        harmony_hits = 0
        conflict_hits = 0
        emotional_hits = 0
        mental_hits = 0
        hurt_hits = 0

        seen_aspect_pairs = set()

        # 1. حساب الاتصالات الفلكية
        for p1, info1 in PLANETS.items():
            for p2, info2 in PLANETS.items():
                asp, sc, nat = calculate_aspect(pos1[p1], pos2[p2], p1, p2)
                if asp:
                    pair_key = tuple(sorted([info1["name"], info2["name"]]))
                    
                    if pair_key not in seen_aspect_pairs:
                        seen_aspect_pairs.add(pair_key)
                        total_score += sc
                        
                        if sc > 0:
                            harmony_hits += 1
                            p1_positive_hits += 1
                            p2_positive_hits += 1
                        else:
                            conflict_hits += 1

                        # قياس الدعم المادي لكل طرف منفصلاً
                        if p1 in [swe.SUN, swe.MARS] and sc > 0:
                            p1_financial_score += sc
                        if p2 in [swe.SUN, swe.MARS] and sc > 0:
                            p2_financial_score += sc

                        # قياس مصادر الضغط (زحل وبلوتو)
                        if p1 in [swe.SATURN, swe.PLUTO] and sc < 0:
                            p1_pressure_score += abs(sc)
                        if p2 in [swe.SATURN, swe.PLUTO] and sc < 0:
                            p2_pressure_score += abs(sc)

                        if (p1 in [swe.VENUS, swe.MOON, swe.MARS] or p2 in [swe.VENUS, swe.MOON, swe.MARS]):
                            if sc > 0:
                                emotional_hits += 1
                            else:
                                hurt_hits += 1

                        if (p1 in [swe.MERCURY, swe.JUPITER, swe.SUN] or p2 in [swe.MERCURY, swe.JUPITER, swe.SUN]) and sc > 0:
                            mental_hits += 1

                        if (p1 in [swe.SUN, swe.MOON, swe.VENUS] and p2 in [swe.SUN, swe.MOON, swe.VENUS, swe.MARS]) and sc > 0:
                            marriage_support_score += sc

                        if sc < 0:
                            if p1 == swe.MARS or p2 == swe.MARS:
                                warnings_list.append(f"⚠️ صراعات حادة أو طاقة عدائية بسبب ارتباط ({info1['name']} و {info2['name']})")
                            elif p1 == swe.VENUS or p2 == swe.VENUS:
                                warnings_list.append(f"💔 جرح عاطفي أو إحباط وجداني بين ({info1['name']} و {info2['name']})")
                            elif p1 == swe.SATURN or p2 == swe.SATURN:
                                warnings_list.append(f"⚖️ ضغط زحلي يفرضه كوكب {info1['name'] if p1 in PLANETS else info2['name']} ويعيق المرونة")

                        aspect_records.append({
                            f"كوكب {name1}": info1["name"],
                            "البرج": get_zodiac_sign(pos1[p1])[0],
                            "الاتصال الفلكي": asp,
                            f"كوكب {name2}": info2["name"],
                            "برج الشريك": get_zodiac_sign(pos2[p2])[0],
                            "نوع التأثير": "إيجابي (توافق)" if sc > 0 else "سلبي (تحدي)",
                        })

        # 2. تحليل البيوت (House Overlays)
        sun_pos_1 = pos1[swe.SUN]
        sun_pos_2 = pos2[swe.SUN]

        for p1, info1 in PLANETS.items():
            house_in_2 = get_solar_house(pos1[p1], sun_pos_2)
            warn, eff, note = analyze_house_overlay(p1, info1["name"], house_in_2, name2)
            if warn:
                warnings_list.append(warn)
                if p1 in [swe.SATURN, swe.PLUTO]:
                    p1_pressure_score += 5
            overlay_records.append({
                "صاحب الكوكب": name1,
                "الكوكب": info1["name"],
                "يسقط في بيت الشريك": f"البيت {house_in_2}",
                "الملاحظة والتأثير الفلكي": note
            })

        for p2, info2 in PLANETS.items():
            house_in_1 = get_solar_house(pos2[p2], sun_pos_1)
            warn, eff, note = analyze_house_overlay(p2, info2["name"], house_in_1, name1)
            if warn:
                warnings_list.append(warn)
                if p2 in [swe.SATURN, swe.PLUTO]:
                    p2_pressure_score += 5
            overlay_records.append({
                "صاحب الكوكب": name2,
                "الكوكب": info2["name"],
                "يسقط في بيت الشريك": f"البيت {house_in_1}",
                "الملاحظة والتأثير الفلكي": note
            })

        # 3. تحديد المسؤوليات بدقة صارمة وبأسماء صريحة
        # أ) تحديد الداعم المادي ونسبته
        total_fin = p1_financial_score + p2_financial_score
        if total_fin > 0:
            p1_fin_pct = int((p1_financial_score / total_fin) * 100)
            p2_fin_pct = int((p2_financial_score / total_fin) * 100)
        else:
            p1_fin_pct = 50
            p2_fin_pct = 50

        if p1_financial_score > p2_financial_score:
            material_supporter = f"{name1} (بنسبة مساهمة {p1_fin_pct}%)"
            supporter_name_only = name1
        elif p2_financial_score > p1_financial_score:
            material_supporter = f"{name2} (بنسبة مساهمة {p2_fin_pct}%)"
            supporter_name_only = name2
        else:
            material_supporter = f"مشترك بالتساوي بين {name1} و {name2} (50% لكل منهما)"
            supporter_name_only = "الشريكان بالتساوي"

        # ب) تحديد مصدر الضغط والمتضرر النفسي صراحة
        if p1_pressure_score > p2_pressure_score:
            pressure_source = name1
            psych_sufferer = name2
        elif p2_pressure_score > p1_pressure_score:
            pressure_source = name2
            psych_sufferer = name1
        else:
            pressure_source = f"متبادل بين {name1} و {name2}"
            psych_sufferer = f"كلا الطرفين ({name1} و {name2})"

        # ج) تحديد المستفيد والمتضرر العام
        if total_score >= 10:
            beneficiary = f"{name1} و {name2} (بشكل متوازن)"
            sufferer = "لا يوجد طرف متضرر جوهرياً"
        elif total_score >= 0:
            beneficiary = name1 if p1_positive_hits >= p2_positive_hits else name2
            sufferer = psych_sufferer
        else:
            beneficiary = "لا يوجد مستفيد (علاقة استنزافية)"
            sufferer = f"الطرف الأكثر تضرراً هو {psych_sufferer} بسبب ثقل كواكب {pressure_source}"

        # د) المسؤول عن عدم دعم الأطفال
        if p1_pressure_score > p2_pressure_score + 2:
            children_blocker = f"{name1} (بسبب هيمنة كواكب الضغط والثقل الفلكي لديه)"
        elif p2_pressure_score > p1_pressure_score + 2:
            children_blocker = f"{name2} (بسبب هيمنة كواكب الضغط والثقل الفلكي لديه)"
        else:
            children_blocker = f"لا يوجد معيق فردي؛ المسؤولية مشتركة أو محايدة بين {name1} و {name2}"

        # 4. حساب النسب المئوية الدقيقة مع تحديد من المسؤول عن كل نسبة
        total_aspects = max(1, (harmony_hits + conflict_hits))
        comfort_pct = int(min(100, max(10, (harmony_hits / total_aspects) * 100 + (total_score * 2))))
        emotional_pct = int(min(100, max(10, 50 + (emotional_hits * 6) - (hurt_hits * 8))))
        happiness_pct = int(min(100, max(5, comfort_pct * 0.7 + (marriage_support_score * 2))))
        conflict_pct = int(min(100, max(5, (conflict_hits / total_aspects) * 100 + ((p1_pressure_score + p2_pressure_score) * 2))))
        hurt_pct = int(min(100, max(5, (hurt_hits / total_aspects) * 100 + ((p1_pressure_score + p2_pressure_score) * 1.5))))
        mental_pct = int(min(100, max(15, (mental_hits / max(1, total_aspects)) * 100 + 30)))
        continuity_pct = int(min(100, max(10, (comfort_pct + emotional_pct - conflict_pct) / 1.2)))

        driver_party = name1 if p1_positive_hits >= p2_positive_hits else name2

        relationship_verdict = ""
        v_color = "green"
        if total_score >= 15 and marriage_support_score >= 10:
            relationship_verdict = f"💍 **تصلح بامتياز للزواج والاستقرار** بين {name1} و {name2}."
        elif total_score >= 8:
            relationship_verdict = f"🤝 **تصلح لصداقة أو زمالة عمل** وتحتاج وعياً مشتركاً."
        elif 0 <= total_score < 8:
            relationship_verdict = "⚖️ **علاقة متوسطة تتطلب جهداً شاقاً وتنازلات**."
        else:
            relationship_verdict = f"❌ **لا تصلح لشيء (تحذير صارم من الارتباط)** نظراً للاستنزاف العالي."
            v_color = "red"

        # ---------------------------------------------------------
        # 5. واجهة العرض والمخرجات في الـ UI
        # ---------------------------------------------------------
        st.markdown("---")
        st.header("📊 التقرير التوافقي الشامل وتحديد المسؤوليات بدقة صارمة")

        col_res1, col_res2 = st.columns(2)
        with col_res1:
            st.markdown(f"### خلاصة العلاقة:")
            st.markdown(f":{v_color}[{relationship_verdict}]")
            st.markdown(f"**المجموع الحسابي للنقاط:** {total_score}")
            st.markdown(f"**الشريك الداعم ماديّاً:** **{material_supporter}**")
            st.markdown(f"**المستفيد الأساسي من العلاقة:** **{beneficiary}**")

        with col_res2:
            st.markdown(f"**مصدر الضغط الهيكلي/الزحلي:** **{pressure_source}**")
            st.markdown(f"**الطرف الأكثر تضرراً نفسياً:** **{psych_sufferer}**")
            st.markdown(f"**المسؤول عن تعطيل أو ضعف دعم الأطفال:** **{children_blocker}**")

        st.markdown("---")
        st.subheader("📈 مؤشرات ونسب التوافق مع تسمية المسؤول عنها صراحةً")
        
        m_col1, m_col2, m_col3, m_col4 = st.columns(4)
        m_col1.metric("الراحة النفسية", f"{comfort_pct}%", f"الداعم: {driver_party}")
        m_col2.metric("الحميمية العاطفية", f"{emotional_pct}%", f"مشترك بين الطرفين")
        m_col3.metric("نسبة السعادة", f"{happiness_pct}%", f"مرتبطة بتناغم {name1} و {name2}")
        m_col4.metric("التفاهم العقلي", f"{mental_pct}%", f"محركها: {driver_party}")

        m_col5, m_col6, m_col7 = st.columns(3)
        m_col5.metric("نسبة الصراعات", f"{conflict_pct}%", f"المسؤول: {pressure_source}")
        m_col6.metric("الجروح الحرمان", f"{hurt_pct}%", f"المتأثر: {psych_sufferer}")
        m_col7.metric("نسبة الاستمرار", f"{continuity_pct}%", f"بناءً على ميزان القوى")

        st.markdown("---")
        st.subheader("⚠️ التنبيهات والتحذيرات الفلكية الهامة")
        if warnings_list:
            for w in set(warnings_list):
                st.warning(w)
        else:
            st.success("لم يتم رصد تحذيرات خطيرة أو اتصالات هدامة قوية.")

        st.subheader("🏠 تحليل البيوت التوافقية (House Overlays)")
        st.dataframe(pd.DataFrame(overlay_records), width='stretch')

        st.subheader("🔗 تفاصيل اتصالات الكواكب (بدون تكرار)")
        df_aspects = pd.DataFrame(aspect_records) if aspect_records else pd.DataFrame(columns=["ملاحظة"])
        st.dataframe(df_aspects, width='stretch')

        # ---------------------------------------------------------
        # 6. تصدير وتنزيل التقرير HTML (شاملاً تفصيل المسؤوليات صراحةً)
        # ---------------------------------------------------------
        st.markdown("---")
        st.subheader("🖨️ طباعة وتصدير التقرير النهائي")

        aspects_html_rows = "".join([
            f"<tr><td>{row.get(f'كوكب {name1}', '-')}</td><td>{row.get('البرج', '-')}</td><td><b>{row.get('الاتصال الفلكي', '-')}</b></td><td>{row.get(f'كوكب {name2}', '-')}</td><td>{row.get('برج الشريك', '-')}</td><td>{row.get('نوع التأثير', '-')}</td></tr>"
            for _, row in df_aspects.iterrows()
        ])

        overlays_html_rows = "".join([
            f"<tr><td>{row['صاحب الكوكب']}</td><td>{row['الكوكب']}</td><td>{row['يسقط في بيت الشريك']}</td><td>{row['الملاحظة والتأثير الفلكي']}</td></tr>"
            for _, row in pd.DataFrame(overlay_records).iterrows()
        ])

        warnings_html = "".join([f"<li>{w}</li>" for w in set(warnings_list)]) if warnings_list else "<li>لا توجد تحذيرات جوهرية مسجلة.</li>"

        html_report = f"""
        <!DOCTYPE html>
        <html lang="ar" dir="rtl">
        <head>
            <meta charset="UTF-8">
            <title>التقرير الفلكي التوافقي الصارم - {name1} & {name2}</title>
            <style>
                body {{ font-family: Tahoma, Arial, sans-serif; margin: 40px; color: #333; background: #fff; line-height: 1.6; }}
                h1, h2, h3 {{ color: #2c3e50; text-align: center; }}
                .header-box {{ background: #f8f9fa; padding: 20px; border-radius: 8px; border: 1px solid #ddd; margin-bottom: 20px; }}
                .metrics-box {{ display: flex; justify-content: space-around; background: #e9ecef; padding: 15px; border-radius: 8px; margin-bottom: 20px; text-align: center; flex-wrap: wrap; }}
                .metric-item {{ margin: 5px; font-size: 14px; }}
                table {{ width: 100%; border-collapse: collapse; margin-top: 20px; margin-bottom: 30px; font-size: 14px; }}
                th, td {{ border: 1px solid #bdc3c7; padding: 10px; text-align: center; }}
                th {{ background: #2c3e50; color: white; }}
                tr:nth-child(even) {{ background: #f9f9f9; }}
                .footer {{ text-align: center; margin-top: 50px; font-size: 12px; color: #7f8c8d; border-top: 1px solid #eee; padding-top: 10px; }}
                @media print {{ body {{ margin: 10px; }} .no-print {{ display: none; }} }}
            </style>
        </head>
        <body>
            <h1>✨ التقرير الفلكي التوافقي وتحديد الأطراف والمسؤوليات صراحةً</h1>
            <div class="header-box">
                <p><b>الشريك الأول:</b> {name1} ({gender1}) - تاريخ الميلاد: {dob1}</p>
                <p><b>الشريك الثاني:</b> {name2} ({gender2}) - تاريخ الميلاد: {dob2}</p>
                <p><b>خلاصة العلاقة والقرار:</b> {relationship_verdict}</p>
                <p><b>الشريك الداعم ماديّاً:</b> <b>{material_supporter}</b></p>
                <p><b>مصدر الضغط الهيكلي والزحلي:</b> <b>{pressure_source}</b> | <b>الطرف المتضرر نفسياً:</b> <b>{psych_sufferer}</b></p>
                <p><b>المستفيد من العلاقة:</b> {beneficiary} | <b>المسؤول عن تعطيل الأطفال:</b> {children_blocker}</p>
            </div>

            <div class="metrics-box">
                <div class="metric-item"><b>الراحة النفسية:</b> {comfort_pct}% <br><small>الداعم: {driver_party}</small></div>
                <div class="metric-item"><b>الحميمية:</b> {emotional_pct}% <br><small>مشترك</small></div>
                <div class="metric-item"><b>السعادة:</b> {happiness_pct}% <br><small>مرتبط بالتناغم</small></div>
                <div class="metric-item"><b>التفاهم العقلي:</b> {mental_pct}% <br><small>المحرك: {driver_party}</small></div>
                <div class="metric-item"><b>الصراعات:</b> {conflict_pct}% <br><small>المسؤول: {pressure_source}</small></div>
                <div class="metric-item"><b>الجروح العاطفية:</b> {hurt_pct}% <br><small>المتأثر: {psych_sufferer}</small></div>
                <div class="metric-item"><b>الاستمرار:</b> {continuity_pct}% <br><small>حسب الميزان</small></div>
            </div>

            <h2>⚠️ التنبيهات والتحذيرات الفلكية</h2>
            <ul>{warnings_html}</ul>

            <h2>🏠 جدول تحليلات البيوت التوافقية (House Overlays)</h2>
            <table>
                <thead><tr><th>صاحب الكوكب</th><th>الكوكب</th><th>يسقط في بيت الشريك</th><th>طبيعة التأثير والتحذير</th></tr></thead>
                <tbody>{overlays_html_rows}</tbody>
            </table>

            <h2>🔗 تفاصيل الاتصالات الفلكية (بدون تكرار)</h2>
            <table>
                <thead><tr><th>كوكب {name1}</th><th>البرج</th><th>الاتصال</th><th>كوكب {name2}</th><th>برج الشريك</th><th>التأثير</th></tr></thead>
                <tbody>{aspects_html_rows}</tbody>
            </table>

            <div class="footer"><p>تم إعداد التقرير عبر نظام الحسابات الفلكية المتقدم بالاعتماد على Swiss Ephemeris والبيوت الشمسية التوافقية.</p></div>

            <div style="text-align: center; margin-top: 30px;" class="no-print">
                <button onclick="window.print()" style="padding: 12px 25px; background: #2980b9; color: white; border: none; border-radius: 5px; cursor: pointer; font-size: 16px;">🖨️ طباعة أو حفظ التقرير PDF</button>
            </div>
        </body>
        </html>
        """

        b64 = base64.b64encode(html_report.encode("utf-8")).decode("utf-8")
        href = f'<a href="data:text/html;base64,{b64}" download="synastry_strict_parties_report.html" style="text-decoration: none;"><button style="padding: 10px 20px; background-color: #27ae60; color: white; border: none; border-radius: 5px; cursor: pointer; font-size: 15px;">📥 تنزيل تقرير HTML الشامل والمدقق</button></a>'
        st.markdown(href, unsafe_allow_html=True)
        st.success("تم تحديث الكود وتضمين أسماء المسؤولين عن كل نسبة وضغط ودعم مادي بشكل قاطع في واجهة المستخدم وتقرير الطباعة.")
