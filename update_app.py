import streamlit as st
import pandas as pd
import sqlite3
import datetime
import google.generativeai as genai
import os

st.set_page_config(page_title="Fit AI Pro MAX", layout="wide")

API_KEY = os.getenv("GEMINI_API_KEY")

# ================= DATABASE =================
conn = sqlite3.connect("health.db", check_same_thread=False)
c = conn.cursor()

c.execute("CREATE TABLE IF NOT EXISTS users(username TEXT PRIMARY KEY,password TEXT)")
c.execute("CREATE TABLE IF NOT EXISTS user_steps(username TEXT,age REAL,height REAL,weight REAL,sleep REAL,goal TEXT,date TEXT)")
c.execute("CREATE TABLE IF NOT EXISTS daily_log(username TEXT,date TEXT,steps REAL,calories REAL,sleep REAL,notes TEXT)")
c.execute("CREATE TABLE IF NOT EXISTS food_log(username TEXT,date TEXT,food TEXT,calories REAL)")
conn.commit()

# ================= LOGIN =================
st.sidebar.title("🔐 Account")
mode = st.sidebar.radio("Select", ["Login", "Signup"])

if mode == "Signup":
    u = st.sidebar.text_input("Username")
    p = st.sidebar.text_input("Password", type="password")
    if st.sidebar.button("Create"):
        try:
            c.execute("INSERT INTO users VALUES (?,?)",(u,p))
            conn.commit()
            st.sidebar.success("Created")
        except:
            st.sidebar.error("Exists")

username = st.sidebar.text_input("Username")
password = st.sidebar.text_input("Password", type="password")

user = c.execute("SELECT * FROM users WHERE username=? AND password=?",(username,password)).fetchone()

if not user:
    st.warning("Login required")
    st.stop()

# ================= STEP =================
if "step" not in st.session_state:
    st.session_state.step = 1

st.title("🔥 Fit AI Pro MAX")

# ================= FLOW =================
if st.session_state.step == 1:
    sleep = st.number_input("Sleep",7.0)
    if st.button("Next"):
        st.session_state.sleep = sleep
        st.session_state.step = 2

elif st.session_state.step == 2:
    age = st.number_input("Age",25)
    height = st.number_input("Height",170)
    weight = st.number_input("Weight",70.0)

    if st.button("Next"):
        st.session_state.age = age
        st.session_state.height = height
        st.session_state.weight = weight
        st.session_state.step = 3

elif st.session_state.step == 3:
    goal = st.selectbox("Goal",["Fat Loss","Muscle Gain"])

    if st.button("Save"):
        c.execute("INSERT INTO user_steps VALUES (?,?,?,?,?,?,?)",
                  (username,
                   st.session_state.age,
                   st.session_state.height,
                   st.session_state.weight,
                   st.session_state.sleep,
                   goal,
                   str(datetime.date.today())))
        conn.commit()
        st.session_state.step = 4

elif st.session_state.step == 4:

    st.header("📊 Dashboard")

    data = pd.read_sql("SELECT * FROM user_steps WHERE username=?",conn,params=(username,))

    if not data.empty:
        latest = data.iloc[-1]

        st.subheader("📌 Summary")
        st.write(f"Weight: {latest['weight']} kg")
        st.write(f"Goal: {latest['goal']}")

        weight_now = latest['weight']
        height = st.session_state.height
        age = st.session_state.age

        # BODY ENGINE
        bmi = weight_now / ((height/100)**2)
        bmr = 10*weight_now + 6.25*height - 5*age + 5
        body_fat = (1.2*bmi) + (0.23*age) - 16.2

        st.subheader("🧠 Body")
        st.write("BMI:", round(bmi,2))
        st.write("BMR:", round(bmr))
        st.write("Body Fat:", round(body_fat,2))

        st.line_chart(data[["weight","sleep"]])

    # DAILY LOG
    st.subheader("📝 Daily")

    steps = st.number_input("Steps",0)
    cal = st.number_input("Calories",0)
    sl = st.number_input("Sleep",0.0)

    if st.button("Save Today"):
        c.execute("DELETE FROM daily_log WHERE username=? AND date=?",(username,str(datetime.date.today())))
        c.execute("INSERT INTO daily_log VALUES (?,?,?,?,?,?)",
                  (username,str(datetime.date.today()),steps,cal,sl,""))
        conn.commit()

    df = pd.read_sql("SELECT * FROM daily_log WHERE username=?",conn,params=(username,))

    if not df.empty:
        avg_steps = int(df["steps"].mean())
        avg_cal = int(df["calories"].mean())
        avg_sleep = round(df["sleep"].mean(),1)

        # BURN
        burn = avg_steps * 0.04
        st.subheader("🔥 Burn")
        st.write("Burn:", burn)
        st.write("Calories:", avg_cal)

        # DIGITAL TWIN
        st.subheader("🧬 Prediction")
        deficit = burn - avg_cal
        days = st.slider("Days",1,90,30)
        future = weight_now - (deficit*days/7700)

        st.write("Future Weight:", round(future,2))

        # GOAL
        st.subheader("🎯 Goal")
        target = st.number_input("Target",60.0)
        st.write("Remaining:", round(weight_now-target,2))

        # DIET
        st.subheader("🥗 Diet")
        maintenance = weight_now * 30

        if latest['goal']=="Fat Loss":
            total = maintenance - 400
        else:
            total = maintenance + 400

        protein = weight_now * 2
        carbs = total/4
        fat = total*0.25/9

        st.write("Calories:", round(total))
        st.write("Protein:", round(protein))
        st.write("Carbs:", round(carbs))
        st.write("Fat:", round(fat))

    # FOOD AI
    st.subheader("🍔 Food AI")
    file = st.file_uploader("Upload food")

    if file and API_KEY:
        genai.configure(api_key=API_KEY)
        model = genai.GenerativeModel("models/gemini-2.5-flash")

        res = model.generate_content([
            {"mime_type": file.type, "data": file.read()},
            "Give calories and macros"
        ])

        st.write(res.text)

    # MEDICAL AI
    st.subheader("🧪 Medical AI")
    files = st.file_uploader("Upload report",accept_multiple_files=True)

    if files and API_KEY:
        genai.configure(api_key=API_KEY)
        model = genai.GenerativeModel("models/gemini-2.5-flash")

        for f in files:
            res = model.generate_content([
                {"mime_type": f.type, "data": f.read()},
                "Explain report simply"
            ])
            st.write(res.text)

conn.close()
