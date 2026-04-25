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
# USER STEPS TABLE FIX
# ================================
c.execute("""
CREATE TABLE IF NOT EXISTS user_steps(
    username TEXT,
    age REAL,
    height REAL,
    weight REAL,
    sleep REAL,
    goal TEXT,
    date TEXT
)
""")
conn.commit()
# ================================
# LOGIN
# ================================
st.sidebar.title("🔐 Account")

mode = st.sidebar.radio("Select", ["Login","Signup"])

if mode == "Signup":
    u = st.sidebar.text_input("Username", key="signup_user")
    p = st.sidebar.text_input("Password", type="password", key="singup_pass")

    if st.sidebar.button("Create"):
        try:
            c.execute("INSERT INTO users VALUES (?,?)",(u,p))
            conn.commit()
            st.sidebar.success("Account Created")
        except:
            st.sidebar.error("Username Exists")

username = st.sidebar.text_input("Username", key="login_user")
password = st.sidebar.text_input("Password", type="password", key="login_pass")

user = c.execute(
    "SELECT * FROM users WHERE username=? AND password=?",
    (username,password)
).fetchone()

if not user:
    st.session_state.username = username
    st.warning(t("Login required","लॉगिन आवश्यक आहे","लॉगिन जरूरी है"))
    st.stop()

# ================================
# STEP CONTROL
# ================================
if "step" not in st.session_state:
    st.session_state.step = 1

# ================================
# HEADER
# ================================
st.title(t("🔥 Fit AI Pro MAX","🔥 फिट एआय प्रो","🔥 फिट एआई प्रो"))

# ================================
# FLOW
# ================================

if st.session_state.step == 1:
    st.header("Step 1: Routine")

    sleep = st.number_input("Sleep Hours", 7.0)

    if st.button("Next"):
        st.session_state.sleep = sleep
        st.session_state.step = 2


elif st.session_state.step == 2:
    st.header("Step 2: Basic Details")

    age = st.number_input("Age", 25)
    height = st.number_input("Height", 170)
    weight = st.number_input("Weight", 70)

    if st.button("Next"):
        st.session_state.age = age
        st.session_state.height = height
        st.session_state.weight = weight
        st.session_state.step = 3


elif st.session_state.step == 3:
    st.header("Step 3: Medical")

    bp = st.checkbox("BP")
    sugar = st.checkbox("Diabetes")

    if st.button("Next"):
        st.session_state.bp = bp
        st.session_state.sugar = sugar
        st.session_state.step = 4


elif st.session_state.step == 4:
    st.header("Step 4: Diet")

    goal = st.selectbox("Goal", ["Fat Loss", "Muscle Gain"])

    if st.button("Generate Plan"):
        st.session_state.goal = goal

        # ✅ SAVE DATA (IMPORTANT)
        c.execute(
            "INSERT INTO user_steps VALUES (?,?,?,?,?,?,?)",
            (
                st.session_state.username,
                st.session_state.age,
                st.session_state.height,
                st.session_state.weight,
                st.session_state.sleep,
                goal,
                str(datetime.date.today())
            )
        )
        conn.commit()

        st.success("✅ Data Saved")

        st.session_state.step = 5


elif st.session_state.step == 5:
    st.header("🔥 AI Result")

    weight = st.session_state.weight
    height = st.session_state.height

    bmi = weight / ((height/100)**2)

    st.metric("BMI", round(bmi,2))

    if bmi > 25:
        st.warning("Fat loss needed")
    else:
        st.success("Good shape")

    st.write("Diet Plan: High protein")
    st.write("Workout: Walking")

    if st.button("Go to Dashboard"):
        st.session_state.step = 6


elif st.session_state.step == 6:
    st.header("📊 Dashboard")

    username = st.session_state.get("username", None)

    if username is None:
        st.error("Login required")
        st.stop()

    data = pd.read_sql(
        "SELECT * FROM user_steps WHERE username=?",
        conn,
        params=(username,)
    )

    if not data.empty:
        st.success("✅ Data Loaded")

        st.write(data)
        st.line_chart(data["weight"])
    else:
        st.warning("No data yet")
        
    st.write("Welcome to your dashboard")

# ================================
# INPUT
# ================================



# ================================
# CALCULATIONS
# ================================
# bmi = weight / ((height/100)**2)

# body_fat = (waist * 0.74) - (weight * 0.082) - 44.74
# st.subheader("🔥 Body Fat %")
# st.write(round(body_fat,2))


# bmr = 10*weight + 6.25*height - 5*age + 5
# burn = bmr + steps*0.04


# ================================
# 🧬 DIGITAL TWIN
# ================================
# daily_deficit = burn - calories

# pred7 = max(weight - (daily_deficit*7/7700), 30)
# pred30 = max(weight - (daily_deficit*30/7700), 30)

# st.subheader("🧬 Prediction")
# st.write(f"📉 7 Days: {round(pred7,2)} kg")
# st.write(f"📉 30 Days: {round(pred30,2)} kg")


# ================================
# 🔮 FUTURE PREDICTION
# ================================
# days = st.slider("Days", 1, 365, 30)

# future = max(weight - (daily_deficit*days/7700), 30)

# st.write(f"📅 After {days} days: {round(future,2)} kg")

# target = st.number_input(
#     "Target Weight",
#     min_value=30.0,
#     max_value=200.0,
#     value=60.0,
#     step=1.0
# )

# if target > weight:
#     st.warning("Target weight should be below current weight for fat loss")

# remaining = weight-target

# progress=((weight-target)/weight)*100

# st.subheader("🎯 Goal Tracker")

# st.write(f"Remaining: {round(remaining,2)} kg")

# st.progress(
# int(max(0,min(progress,100)))
# )

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

# ================================
# 🧪 MEDICAL AI
# ================================

st.subheader("🧪 Medical AI")

api_key = "AIzaSyDwctXJJU83_R44QkblvypDOVjWSY3DFu4"

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


# ================================
# FINAL
# ================================
if "weight" in st.session_state:
    st.info(f"💧 Water: {round(st.session_state.weight/20,2)}L")

# if burn > calories:
#     st.success("🔥 Fat Loss Mode")
# else:
#     st.warning("⚠️ Surplus")

# conn.close()
