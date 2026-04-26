import streamlit as st
import pandas as pd
import sqlite3
import datetime
import google.generativeai as genai
import os
import numpy as np

st.set_page_config(page_title="Fit AI Pro MAX", layout="wide")

API_KEY = os.getenv("GEMINI_API_KEY")

# ================= UI STYLE =================
st.markdown("""
<style>
.stApp {
    background: linear-gradient(135deg,#eef2ff,#f8fafc);
}
.block-container {
    padding-top: 1rem;
}
h1 {
    text-align: center;
    color: #4f46e5;
}
.section {
    background: white;
    padding: 18px;
    border-radius: 14px;
    box-shadow: 0px 3px 10px rgba(0,0,0,0.06);
    margin-bottom: 15px;
}
</style>
""", unsafe_allow_html=True)

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

# ================= NLP =================
def detect_intent(text):
    text = text.lower()
    if "diet" in text: return "diet"
    if "weight" in text: return "weight"
    if "calorie" in text: return "calorie"
    return "general"

def smart_reply(q, bmi, burn, cal):
    intent = detect_intent(q)

    if intent == "diet":
        return "Increase protein, reduce sugar"
    if intent == "weight":
        return "Fat loss mode" if burn > cal else "Weight gain risk"
    return "Maintain balance"

# ================= STEP =================
if "step" not in st.session_state:
    st.session_state.step = 1

st.title("🔥 Fit AI Pro MAX")

# ================= FLOW =================
if st.session_state.step == 1:
    st.markdown("### 😴 Sleep")

    # ✅ First time default
    sleep_default = st.session_state.get("sleep", 7.0)

    # ✅ Input with saved value
    sleep = st.number_input("Hours", value=sleep_default)

    # ✅ Save on Next
    if st.button("Next ➡"):
        st.session_state.sleep = sleep
        st.session_state.step = 2

elif st.session_state.step == 2:
    st.markdown("### 📏 Body Details")

    # 👉 FORM START (IMPORTANT)
    with st.form("body_form"):

        age_default = st.session_state.get("age", 25)
        height_default = st.session_state.get("height", 170)
        weight_default = st.session_state.get("weight", 70.0)

        col1, col2, col3 = st.columns(3)

        age = col1.number_input("Age", value=age_default)
        height = col2.number_input("Height", value=height_default)
        weight = col3.number_input("Weight", value=weight_default)

        # 👉 ONLY this button works
        submit = st.form_submit_button("Next ➡")

        if submit:
            st.session_state.age = age
            st.session_state.height = height
            st.session_state.weight = weight
            st.session_state.step = 3

    # ✅ Inputs (user change = auto update)
    age = col1.number_input("Age", value=age_default, step=1)
    height = col2.number_input("Height (cm)", value=height_default, step=1)
    weight = col3.number_input("Weight (kg)", value=weight_default, step=0.5)

    # ✅ Save ONLY when Next clicked
    if st.button("Next ➡"):
        st.session_state.age = age
        st.session_state.height = height
        st.session_state.weight = weight
        st.session_state.step = 3

elif st.session_state.step == 3:
    st.markdown("### 🎯 Goal")
    goal = st.selectbox("Select Goal",["Fat Loss","Muscle Gain"])

    if st.button("Save & Continue"):
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

# ================= DASHBOARD =================
elif st.session_state.step == 4:

    tab1, tab2, tab3 = st.tabs(["📊 Dashboard","🍔 Food","🤖 AI Coach"])

    data = pd.read_sql("SELECT * FROM user_steps WHERE username=?",conn,params=(username,))
    log = pd.read_sql("SELECT * FROM daily_log WHERE username=?",conn,params=(username,))
    food_df = pd.read_sql("SELECT * FROM food_log WHERE username=?",conn,params=(username,))

    latest = data.iloc[-1]
    weight_now = latest['weight']
    height = st.session_state.height
    age = st.session_state.age

    # ================= TAB 1 =================
    with tab1:

        st.markdown('<div class="section">', unsafe_allow_html=True)

        bmi = weight_now / ((height/100)**2)
        bmr = 10*weight_now + 6.25*height - 5*age + 5
        body_fat = (1.2*bmi) + (0.23*age) - 16.2

        st.subheader("🧠 Body Metrics")

        col1, col2, col3 = st.columns(3)
        col1.metric("BMI",round(bmi,2))
        col2.metric("BMR",round(bmr))
        col3.metric("Body Fat %",round(body_fat,2))

        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="section">', unsafe_allow_html=True)

        st.subheader("📝 Daily Log")
        col1, col2 = st.columns(2)
        steps = col1.number_input("Steps",0)
        cal = col2.number_input("Calories",0)

        if st.button("💾 Save Today"):
            today = str(datetime.date.today())
            c.execute("DELETE FROM daily_log WHERE username=? AND date=?",(username,today))
            c.execute("INSERT INTO daily_log VALUES (?,?,?,?,?,?)",
                      (username,today,steps,cal,0,""))
            conn.commit()
            st.success("Saved")

        st.markdown('</div>', unsafe_allow_html=True)

        if not log.empty:

    avg_steps = int(log["steps"].mean())
    avg_cal = int(log["calories"].mean())

    burn = avg_steps * 0.04
    deficit = burn - avg_cal

    st.subheader("🔥 Burn vs Intake")
    st.write("Burn:", burn)
    st.write("Calories:", avg_cal)

    if deficit < 0:
        st.error("⚠️ Weight वाढतो आहे (Calorie जास्त आहे)")
    else:
        st.success("🔥 Weight कमी होतो आहे (Fat Loss Mode)")

            

            st.markdown('<div class="section">', unsafe_allow_html=True)

            st.subheader("🔥 Burn vs Intake")
            col1, col2 = st.columns(2)
            col1.metric("Burn",round(burn))
            col2.metric("Calories",avg_cal)

            st.progress(min(100,int((burn/(avg_cal+1))*100)))

            st.subheader("🧬 Prediction")
            st.info(f"7 Days → {round(weight_now-(deficit*7/7700),2)} kg")
            st.info(f"30 Days → {round(weight_now-(deficit*30/7700),2)} kg")

            days = st.slider("Days",1,90,30)
            st.success(f"Future → {round(weight_now-(deficit*days/7700),2)} kg")

            st.markdown('</div>', unsafe_allow_html=True)

            st.markdown('<div class="section">', unsafe_allow_html=True)

            st.subheader("🥗 Diet Plan")

            maintenance = weight_now * 30
            total = maintenance - 400 if latest['goal']=="Fat Loss" else maintenance + 400

            st.write(f"Calories: {round(total)}")
            st.write(f"Protein: {round(weight_now*2)}g")

            st.markdown('</div>', unsafe_allow_html=True)

    # ================= TAB 2 =================
    with tab2:

        st.markdown('<div class="section">', unsafe_allow_html=True)

        st.subheader("🍔 Food Scanner")

        file = st.file_uploader("Upload food")

        if file and API_KEY:
            with st.spinner("Analyzing..."):
                genai.configure(api_key=API_KEY)
                model = genai.GenerativeModel("models/gemini-2.5-flash")

                res = model.generate_content([
                    {"mime_type": file.type, "data": file.read()},
                    "Give calories number only"
                ])

                st.success("Done")
                st.write(res.text)

                if st.button("Save Food"):
                    c.execute("INSERT INTO food_log VALUES (?,?,?,?)",
                              (username,str(datetime.date.today()),res.text,200))
                    conn.commit()

        if not food_df.empty:
            st.metric("Total Calories",int(food_df["calories"].sum()))

        st.markdown('</div>', unsafe_allow_html=True)

    # ================= TAB 3 =================
    with tab3:

        st.markdown('<div class="section">', unsafe_allow_html=True)

        st.subheader("🤖 AI Coach")

        user_q = st.text_input("Ask anything")

        if user_q and API_KEY:
            with st.spinner("Thinking..."):
                genai.configure(api_key=API_KEY)
                model = genai.GenerativeModel("models/gemini-2.5-flash")

                context = f"BMI:{round(bmi,2)} Steps:{avg_steps if not log.empty else 0}"

                res = model.generate_content(context + user_q)

                st.success("Answer")
                st.write(res.text)

                st.info("Tip: " + smart_reply(user_q,bmi,burn,avg_cal))

        st.subheader("🧪 Medical AI")

        files = st.file_uploader("Upload report",accept_multiple_files=True)

        if files and API_KEY:
            for f in files:
                res = model.generate_content([
                    {"mime_type": f.type, "data": f.read()},
                    "Explain report, risks"
                ])
                st.write(res.text)

        st.markdown('</div>', unsafe_allow_html=True)

conn.close()
