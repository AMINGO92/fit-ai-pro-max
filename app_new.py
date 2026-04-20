import streamlit as st
import pandas as pd
import sqlite3
import datetime
import matplotlib.pyplot as plt
import google.generativeai as genai
import openai

# ================================
# 🎨 UI CONFIG
# ================================
st.set_page_config(page_title="Fit AI Pro MAX", layout="wide")

st.markdown("""
<style>
.stApp {background: linear-gradient(to right, #eef2ff, #f8fafc);}
h1 {color: #4f46e5; text-align: center;}
.card {background: white; padding: 20px; border-radius: 15px; box-shadow: 0px 4px 12px rgba(0,0,0,0.1);}
.metric {font-size: 22px; font-weight: bold; color: #4f46e5;}
</style>
""", unsafe_allow_html=True)

# ================================
# 🌐 LANGUAGE
# ================================
language = st.selectbox("🌐 Select Language", ["English", "मराठी", "हिंदी"])

def t(en, mr, hi):
    if language == "मराठी":
        return mr
    elif language == "हिंदी":
        return hi
    return en

# ================================
# 🧠 MEMORY
# ================================
if "user_memory" not in st.session_state:
    st.session_state.user_memory = []

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# ================================
# DATABASE
# ================================
conn = sqlite3.connect("health.db", check_same_thread=False)
c = conn.cursor()

food_df = pd.read_csv("indian_food.csv")

c.execute("CREATE TABLE IF NOT EXISTS users(username TEXT PRIMARY KEY,password TEXT)")
c.execute("CREATE TABLE IF NOT EXISTS tracking(username TEXT,date TEXT,weight REAL,steps REAL,calories REAL,sleep REAL)")
conn.commit()

# ================================
# LOGIN
# ================================
st.sidebar.title("🔐 Account")

mode = st.sidebar.radio("Select", ["Login","Signup"])

if mode == "Signup":
    u = st.sidebar.text_input("Username")
    p = st.sidebar.text_input("Password", type="password")

    if st.sidebar.button("Create"):
        try:
            c.execute("INSERT INTO users VALUES (?,?)",(u,p))
            conn.commit()
            st.sidebar.success("Account Created")
        except:
            st.sidebar.error("Username Exists")

username = st.sidebar.text_input("Username",key="login_user")
password = st.sidebar.text_input("Password", type="password")

user = c.execute(
    "SELECT * FROM users WHERE username=? AND password=?",
    (username,password)
).fetchone()

if not user:
    st.warning(t("Login required","लॉगिन आवश्यक आहे","लॉगिन जरूरी है"))
    st.stop()

# ================================
# HEADER
# ================================
st.title(t("🔥 Fit AI Pro MAX","🔥 फिट एआय प्रो","🔥 फिट एआई प्रो"))

# ================================
# INPUT
# ================================
col1, col2 = st.columns(2)
    
with col1:
    age = st.number_input(t("Age","वय","उम्र"),33)
    height = st.number_input(t("Height","उंची","ऊंचाई"),170)
    weight = st.number_input(t("Weight","वजन","वजन"),70)
    waist = st.number_input("Waist (cm)",90)

with col2:
    steps = st.number_input(
        t("Steps","पावले","कदम"),
        min_value=0,
        max_value=100000,
        value=7000,
        step=100
    )

    calories = st.number_input(t("Calories","कॅलरी","कैलोरी"),1800)

    sleep = st.number_input(t("Sleep","झोप","नींद"),7.0)

    goal = st.selectbox(
    t("Goal","लक्ष्य","लक्ष्य"),
    ["Fat Loss","Muscle Gain","Maintain"]
)


# ================================
# CALCULATIONS
# ================================
bmi = weight / ((height/100)**2)

body_fat = (waist * 0.74) - (weight * 0.082) - 44.74
st.subheader("🔥 Body Fat %")
st.write(round(body_fat,2))


bmr = 10*weight + 6.25*height - 5*age + 5
burn = bmr + steps*0.04


# ================================
# 🧬 DIGITAL TWIN
# ================================
daily_deficit = burn - calories

pred7 = max(weight - (daily_deficit*7/7700), 30)
pred30 = max(weight - (daily_deficit*30/7700), 30)

st.subheader("🧬 Prediction")
st.write(f"📉 7 Days: {round(pred7,2)} kg")
st.write(f"📉 30 Days: {round(pred30,2)} kg")


# ================================
# 🔮 FUTURE PREDICTION
# ================================
days = st.slider("Days", 1, 365, 30)

future = max(weight - (daily_deficit*days/7700), 30)

st.write(f"📅 After {days} days: {round(future,2)} kg")

target = st.number_input(
    "Target Weight",
    min_value=30.0,
    max_value=200.0,
    value=60.0,
    step=1.0
)

if target > weight:
    st.warning("Target weight should be below current weight for fat loss")

remaining = weight-target

progress=((weight-target)/weight)*100

st.subheader("🎯 Goal Tracker")

st.write(f"Remaining: {round(remaining,2)} kg")

st.progress(
int(max(0,min(progress,100)))
)

# ================================
# 🧠 NLP
# ================================
def detect_intent(text):
    text = text.lower()
    if "diet" in text or "food" in text:
        return "diet"
    elif "weight" in text:
        return "weight"
    elif "gym" in text:
        return "fitness"
    return "general"

# ================================
# 🤖 SMART REPLY
# ================================
def smart_reply(user_input, bmi, burn, calories):
    intent = detect_intent(user_input)

    if intent == "diet":
        return t("👉 Increase protein","👉 प्रोटीन वाढवा","👉 प्रोटीन बढ़ाओ")

    if intent == "weight":
        if burn > calories:
            return t("🔥 Fat loss","🔥 फॅट कमी","🔥 फैट कम")
        else:
            return t("⚠️ Fat gain","⚠️ वजन वाढ","⚠️ वजन बढ़ेगा")

    return t("👍 Maintain balance","👍 संतुलन ठेवा","👍 संतुलन बनाए रखें")

# ================================
# 🧠 AI BRAIN
# ================================

def smart_ai_brain(df, weight, steps, calories, sleep, bmi, burn):
    insights = []
    score = 100

    if bmi > 25:
        insights.append("⚠️ High BMI → Fat loss needed")
        score -= 10

    if calories > burn:
        insights.append("⚠️ Calorie surplus → Fat gain risk")
        score -= 10

    if sleep < 6:
        insights.append("⚠️ Low sleep → Recovery low")
        score -= 10

    if steps < 5000:
        insights.append("⚠️ Low activity")
        score -= 10

    # history based
    if not df.empty and len(df) >= 3:
        change = df["weight"].iloc[-1] - df["weight"].iloc[-3]

        if change > 1:
            insights.append("🚨 Sudden weight gain detected")
            score -= 10
        elif change < -1:
            insights.append("🔥 Good fat loss trend")

    return insights, score

# ================================
# HEALTH RISK
# ================================
def health_risk(bmi, sleep, calories, burn):
    risk = 0
    if bmi > 27: risk += 30
    if sleep < 6: risk += 20
    if calories > burn: risk += 20
    return risk

# ================================
# SAVE
# ================================
if st.button("💾 Save"):
    c.execute(
        "INSERT INTO tracking VALUES (?,?,?,?,?,?)",
        (username,str(datetime.date.today()),weight,steps,calories,sleep)
    )
    conn.commit()
    st.success("Saved")

# ================================
# 🧪 MEDICAL AI
# ================================

st.subheader("🧪 Medical AI")

api_key = "AIzaSyBA2uNTCBqWPdkngRs9EuLqhmsBR2OJeO8"

medical_files = st.file_uploader(
    "Upload Medical Report",
    accept_multiple_files=True,
    key="medical_upload"
)

if medical_files and len(medical_files) > 12:
    st.error("Maximum 12 files only")
    st.stop()

if medical_files:
    for file in medical_files:
        try:
            genai.configure(api_key=api_key)

            model = genai.GenerativeModel("models/gemini-2.5-flash")

            res = model.generate_content([
                {"mime_type": file.type, "data": file.read()},
                "Analyze this medical report and give abnormalities, risks, and suggestions in short bullet points"
            ])

            st.success("🧪 Medical Analysis")
            st.write(res.text)

        except Exception as e:
            st.error(e)

df = pd.read_sql(
    "SELECT * FROM tracking WHERE username=?",
    conn,
    params=(username,)
)
# ================================
# 📊 WEEKLY INSIGHT
# ================================
if not df.empty and len(df) >= 3:
    st.subheader("📊 Weekly Insight")

    last7 = df.tail(7)

    st.write(f"👣 Avg Steps: {int(last7['steps'].mean())}")
    st.write(f"🔥 Avg Calories: {int(last7['calories'].mean())}")
    st.write(f"😴 Avg Sleep: {round(last7['sleep'].mean(),2)}")

# ================================
# TABS
# ================================
tab1,tab2,tab3,tab4,tab5,tab6 = st.tabs([
    t("📊 Dashboard","📊 डॅशबोर्ड","📊 डैशबोर्ड"),
    t("🧠 AI Coach","🧠 मार्गदर्शक","🧠 कोच"),
    t("📈 Reports","📈 अहवाल","📈 रिपोर्ट"),
    t("📸 Food Scanner","📸 अन्न स्कॅनर","📸 स्कैनर"),
    t("🤖 Chatbot","🤖 चॅटबॉट","🤖 चैटबॉट"),
    t("🩺 Care Pathway","🩺 केअर पाथवे","🩺 केयर पाथवे")
    
])

# ================================
# DASHBOARD
# ================================

with tab1:
    st.metric("BMI", round(bmi,2))
    ideal_min = 18.5 * ((height/100)**2)
    ideal_max = 24.9 * ((height/100)**2)

    st.write(
    f"Ideal Weight Range: {round(ideal_min,1)} - {round(ideal_max,1)} kg"
)
    st.metric("BMR", round(bmr))
    st.metric("Burn", round(burn))

    if not df.empty:
        df["date"] = pd.to_datetime(df["date"])
        st.line_chart(df.set_index("date")["weight"])

# ================================
# AI COACH
# ================================

with tab2:
    insights, score = smart_ai_brain(df,weight,steps,calories,sleep,bmi,burn)

    st.metric("Score", score)
    st.metric("Body Fat", round(body_fat,2))

    risk = health_risk(bmi,sleep,calories,burn)
    st.metric("Risk", f"{risk}%")

    if burn > calories:
        st.success("🔥 In Calorie Deficit")
    else:
        st.warning("⚠️ In Surplus")

    for i in insights:
        st.warning(i)


# ================================
# REPORT
# ================================


with tab3:

    st.subheader("📈 Summary Report")

    st.write(f"BMI: {round(bmi,2)}")
    st.write(f"Body Fat: {round(body_fat,2)}")
    st.write(f"30 Day Prediction: {round(pred30,2)} kg")

    if not df.empty:
        st.line_chart(df["weight"])

    st.subheader("📄 PDF Export")

    if st.button("Generate PDF"):

        report = f"""
        Health Report

        BMI: {round(bmi,2)}
        Body Fat: {round(body_fat,2)}
        Prediction: {round(pred30,2)} kg
        Water: {round(weight/20,2)} L
        """

        st.download_button(
        "Download Report",
        report,
        file_name="health_report.txt"
    )
# ================================
# FOOD SCANNER
# ================================


with tab4:

    st.subheader("📸 Food Scanner")

    st.info("Upload food photo → get calories, protein, carbs, fat")

    api_key = "AIzaSyBA2uNTCBqWPdkngRs9EuLqhmsBR2OJeO8"

    files = st.file_uploader(
        "Upload",
        accept_multiple_files=True,
        key="food_upload"
    )

    if files and len(files) > 12:
        st.error("Maximum 12 files only")
        st.stop()

    if api_key and files:
        for file in files:
            try:
                genai.configure(api_key=api_key)

                model = genai.GenerativeModel("models/gemini-2.5-flash")

                res = model.generate_content([
                    {"mime_type": file.type, "data": file.read()},
                    "Return only calories, protein, carbs, fat in short bullet points"
                ])

                st.success("✅ Done")
                st.write(res.text)

            except Exception as e:
                st.error(e)


    st.subheader("🍛 Food Search")

    food_name = st.text_input("Enter food name")

    if food_name:

        result = food_df[
            food_df.iloc[:,0].astype(str).str.lower().str.contains(
                food_name.lower()
            )
        ]

        if not result.empty:
            st.write(result)


    st.subheader("🛢 Oil Recommender")

    goal = st.selectbox(
        "Goal",
        ["Fat Loss","Heart Health","General"]
    )

    if goal == "Fat Loss":
        st.write("- Mustard Oil")
        st.write("- Olive Oil")

    elif goal == "Heart Health":
        st.write("- Olive Oil")
        st.write("- Groundnut Oil")

    elif goal == "General":
        st.write("- Groundnut Oil")

    st.write("Suggested Quantity:")
    st.write("20-30 ml/day")



# ================================
# CHATBOT
# ================================

with tab5:
    user_input = st.text_input("Ask")

    if st.button("Ask", key="chat_btn"):
        if user_input:
            context = f" BMI:{bmi} Burn:{burn} Calories:{calories}"
            reply = smart_reply(user_input + context, bmi, burn, calories)

            st.session_state.chat_history.append(("You", user_input))
            st.session_state.chat_history.append(("AI", reply))

    # Chat display
    st.write(f"Chat Memory: {len(st.session_state.chat_history)} messages")

    for sender, msg in st.session_state.chat_history:
        st.write(f"{sender}: {msg}")


with tab6:

    st.subheader("🩺 Care Pathway")

    symptom = st.selectbox(
        "Main Symptom",
        ["Fatigue","Body Pain","Weakness","Back Pain", "Kidney Stone","Weight Gain"]

    )

    severity = st.selectbox(
    "Severity",
    ["Mild","Moderate","Severe"]
)

    if severity == "Severe":
        st.error("🚨 High Priority - Review urgently")

    elif severity == "Moderate":
        st.warning("⚠️ Monitor and follow pathway")

    elif severity == "Mild":
        st.success("✅ Routine follow-up")

    days = st.number_input(
        "Symptoms since how many days?",
        min_value=1,
        value=5
)

    if days > 14:
        st.warning("⚠️ Persistent symptoms - review advised")


    score = 0

    if severity == "Severe":
        score += 2

    if days > 14:
        score += 1

    st.write(f"Urgency Score: {score}/3")

    if score >= 3:
        st.error("🚨 High attention suggested")

    elif score == 2:
        st.warning("⚠️ Monitor closely")
    else:
        st.success("✅ Low urgency")

    if score >= 2:
        st.write("Recommendation:")
        st.write("- Review pending tests")
        st.write("- Track symptoms daily")

        st.write(
        f"Summary: {symptom} | {severity} | {days} days | Score {score}/3"
)

        st.write("Confidence: Preliminary decision support")


    if symptom == "Fatigue":
        st.write("Investigation:")
        st.write("- Ferritin")
        st.write("- Iron Profile")

        st.write("Action Plan:")
        st.write("- Improve sleep")
        st.write("- Track calories")

        st.write("Follow-up:")
        st.write("Recheck in 5 days")

        st.write("Treatment Progress:")
        st.write("Day 5 reassess")
        st.write("Day 30 review")

        st.write("Re-Test:")
        st.write("- Repeat Ferritin")
        st.write("- Repeat CRP if needed")

    if symptom == "Body Pain":
        st.write("Investigation:")
        st.write("- CRP")
        st.write("- ESR")
        st.write("Treatment Progress:")
        st.write("Day 5 reassess")
        st.write("Repeat CRP/ESR if symptoms persist")
    

    if symptom == "Weakness":
        st.write("Investigation:")
        st.write("- Ferritin")
        st.write("- Iron Profile")

    if symptom == "Back Pain":
        st.write("Investigation:")
        st.write("- X-ray Review")
        st.write("- CRP")
        st.write("- Iron Profile")


        st.write("🚨 Red Flags:")
        st.write("- Severe pain")
        st.write("- Blood in urine")
        st.write("- High fever")

    if symptom == "Kidney Stone":
        st.write("Investigation:")
        st.write("- KUB Follow-up")
        st.write("- Hydration Review")

        st.write("Action Plan:")
        st.write("- Increase water")
        st.write("- Monitor pain")

        st.write("Red Flags:")
        st.write("- Severe flank pain")
        st.write("- Fever")


    if symptom == "Weight Gain":
        st.write("Investigation:")
        st.write("- Calorie Review")
        st.write("- Activity Review")

        st.write("Action Plan:")
        st.write("- Increase steps")
        st.write("- Reduce surplus")


# ================================
# FINAL
# ================================
st.info(f"💧 Water: {round(weight/20,2)}L")

if burn > calories:
    st.success("🔥 Fat Loss Mode")
else:
    st.warning("⚠️ Surplus")

conn.close()
