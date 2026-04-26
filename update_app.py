import streamlit as st
import pandas as pd
import sqlite3
import datetime
import google.generativeai as genai
import os

# ================================
# CONFIG
# ================================
st.set_page_config(page_title="Fit AI Pro MAX", layout="wide")

# ================================
# API KEY (SAFE)
# ================================
API_KEY = os.getenv("GEMINI_API_KEY")

# ================================
# DATABASE
# ================================
conn = sqlite3.connect("health.db", check_same_thread=False)
c = conn.cursor()

c.execute("CREATE TABLE IF NOT EXISTS users(username TEXT PRIMARY KEY,password TEXT)")
c.execute("CREATE TABLE IF NOT EXISTS user_steps(username TEXT,age REAL,height REAL,weight REAL,sleep REAL,goal TEXT,date TEXT)")
c.execute("CREATE TABLE IF NOT EXISTS daily_log(username TEXT,date TEXT,steps REAL,calories REAL,sleep REAL,notes TEXT)")
conn.commit()


c.execute("""
CREATE TABLE IF NOT EXISTS food_log(
    username TEXT,
    date TEXT,
    food TEXT,
    calories REAL
)
""")
conn.commit()
# ================================
# LOGIN / SIGNUP
# ================================
st.sidebar.title("🔐 Account")

mode = st.sidebar.radio("Select", ["Login", "Signup"])

if mode == "Signup":
    new_user = st.sidebar.text_input("New Username")
    new_pass = st.sidebar.text_input("New Password", type="password")

    if st.sidebar.button("Create Account"):
        try:
            c.execute("INSERT INTO users VALUES (?,?)", (new_user, new_pass))
            conn.commit()
            st.sidebar.success("Account Created ✅")
        except:
            st.sidebar.error("Username exists")

username = st.sidebar.text_input("Username")
password = st.sidebar.text_input("Password", type="password")

user = c.execute(
    "SELECT * FROM users WHERE username=? AND password=?",
    (username, password)
).fetchone()

if not user:
    st.warning("Login required")
    st.stop()

st.session_state.username = username

# ================================
# STEP CONTROL
# ================================
if "step" not in st.session_state:
    st.session_state.step = 1

# ================================
# TITLE
# ================================
st.title("🔥 Fit AI Pro MAX")

# ================================
# STEP FLOW
# ================================

# STEP 1
if st.session_state.step == 1:
    st.header("Step 1: Sleep")

    sleep = st.number_input("Sleep Hours", min_value=0.0, value=7.0)

    if st.button("Next"):
        st.session_state.sleep = sleep
        st.session_state.step = 2

# STEP 2
elif st.session_state.step == 2:
    st.header("Step 2: Body Details")

    age = st.number_input("Age", min_value=0, value=25)
    height = st.number_input("Height (cm)", min_value=0, value=170)
    weight = st.number_input("Weight (kg)", min_value=0.0, value=70.0)

    if st.button("Next"):
        st.session_state.age = age
        st.session_state.height = height
        st.session_state.weight = weight
        st.session_state.step = 3

# STEP 3
elif st.session_state.step == 3:
    st.header("Step 3: Goal")

    goal = st.selectbox("Goal", ["Fat Loss", "Muscle Gain"])

    if st.button("Save & Continue"):
        c.execute(
            "INSERT INTO user_steps VALUES (?,?,?,?,?,?,?)",
            (
                username,
                st.session_state.age,
                st.session_state.height,
                st.session_state.weight,
                st.session_state.sleep,
                goal,
                str(datetime.date.today())
            )
        )
        conn.commit()

        st.success("Data Saved")
        st.session_state.step = 4

# STEP 4 (DASHBOARD)
elif st.session_state.step == 4:

    st.header("📊 Dashboard")

    # =====================
    # LOAD USER DATA
    # =====================
    data = pd.read_sql(
        "SELECT * FROM user_steps WHERE username=?",
        conn,
        params=(username,)
    )

    if not data.empty:
        latest = data.iloc[-1]

        st.subheader("📌 Latest Summary")
        st.write(f"Weight: {latest['weight']} kg")
        st.write(f"Sleep: {latest['sleep']} hrs")
        st.write(f"Goal: {latest['goal']}")
# =====================
# BODY ENGINE
# =====================
	st.subheader("🧠 Body Analysis")

	weight_now = latest['weight']
	height = st.session_state.height
	age = st.session_state.age

	bmi = weight_now / ((height/100)**2)
	bmr = 10*weight_now + 6.25*height - 5*age + 5
	body_fat = (1.2*bmi) + (0.23*age) - 16.2

	st.write(f"BMI: {round(bmi,2)}")
	st.write(f"BMR: {round(bmr)} kcal")
	st.write(f"Body Fat: {round(body_fat,2)}%")



        st.line_chart(data[["weight", "sleep"]])

    # =====================
    # DAILY LOG
    # =====================
    st.subheader("📝 Daily Log")

    today = str(datetime.date.today())

    steps = st.number_input("Steps", min_value=0)
    cal = st.number_input("Calories", min_value=0)
    sleep_today = st.number_input("Sleep Today", min_value=0.0)
    notes = st.text_input("Notes")

    if st.button("Save Today"):
        # remove duplicate same day
        c.execute("DELETE FROM daily_log WHERE username=? AND date=?", (username, today))

        c.execute(
            "INSERT INTO daily_log VALUES (?,?,?,?,?,?)",
            (username, today, steps, cal, sleep_today, notes)
        )
        conn.commit()
        st.success("Saved")

    # =====================
    # LOAD LOG DATA
    # =====================
    log_df = pd.read_sql(
        "SELECT * FROM daily_log WHERE username=? ORDER BY date DESC LIMIT 30",
        conn,
        params=(username,)
    )

    if not log_df.empty:
        st.subheader("📅 Last 30 Days")
        st.line_chart(log_df.set_index("date")[["steps", "calories", "sleep"]])

        avg_steps = int(log_df["steps"].mean())
        avg_cal = int(log_df["calories"].mean())
        avg_sleep = round(log_df["sleep"].mean(), 1)

# =====================
# CALORIE BURN
# =====================
	burn = avg_steps * 0.04

	st.subheader("🔥 Burn vs Intake")

	st.write(f"Burn: {round(burn)} kcal")
	st.write(f"Calories: {avg_cal} kcal")

	if burn > avg_cal:
    		st.success("Fat Loss Mode")
	else:
    		st.warning("Calorie Surplus")

# =====================
# DIGITAL TWIN
# =====================
	st.subheader("🧬 Future Prediction")

	deficit = burn - avg_cal

	days = st.slider("Days Prediction", 1, 90, 30)

	future_weight = max(weight_now - (deficit * days / 7700), 30)

	st.write(f"After {days} days: {round(future_weight,2)} kg")

	st.write("📉 7 Days:", round(weight_now - (deficit*7/7700),2))
	st.write("📉 30 Days:", round(weight_now - (deficit*30/7700),2))

# =====================
# GOAL TRACKER
# =====================
	st.subheader("🎯 Goal Tracker")

	target = st.number_input("Target Weight", value=60.0)

	remaining = weight_now - target
	progress = ((weight_now - target)/weight_now)*100

	st.write(f"Remaining: {round(remaining,2)} kg")

	st.progress(int(max(0, min(progress,100))))

        	score = 100
        	if avg_steps < 5000: score -= 20
        	if avg_sleep < 6: score -= 20
        	if avg_cal > 2500: score -= 20

        st.subheader("🏆 Health Score")
        st.metric("Score", score)

# =====================
# DIET PLANNER
# =====================
	st.subheader("🥗 Smart Diet Plan")

	weight_now = latest['weight']

	goal_type = latest['goal']

# calories logic
	maintenance = weight_now * 30

	if goal_type == "Fat Loss":
    		total_cal = maintenance - 400
	elif goal_type == "Muscle Gain":
    		total_cal = maintenance + 400
	else:
    		total_cal = maintenance

# macros
	protein = weight_now * 2
	fat = (total_cal * 0.25) / 9
	carbs = (total_cal - (protein*4 + fat*9)) / 4

	st.write(f"🔥 Calories: {round(total_cal)} kcal")
	st.write(f"🥩 Protein: {round(protein)} g")
	st.write(f"🍚 Carbs: {round(carbs)} g")
	st.write(f"🥑 Fat: {round(fat)} g")

# =====================
# INDIAN DIET PLAN
# =====================
	st.subheader("🇮🇳 Sample Indian Diet")

if goal_type == "Fat Loss":
    	
	st.write("Breakfast: Poha / Upma + Tea")
    	st.write("Lunch: 2 Roti + Dal + Sabji")
    	st.write("Snack: Fruits / Sprouts")
    	st.write("Dinner: Light Khichdi")


elif goal_type == "Muscle Gain":
    	st.write("Breakfast: Eggs + Toast + Milk")
    	st.write("Lunch: Chicken / Paneer + Rice")
    	st.write("Snack: Nuts + Banana")
    	st.write("Dinner: Protein rich meal")

# =====================
# ROOT CAUSE ENGINE
# =====================
	st.subheader("🧠 Problem Finder (AI)")

	issues = []
	solutions = []

	if avg_steps < 5000:
    		issues.append("Low activity")
    		solutions.append("Walk at least 8000 steps daily")

	if avg_sleep < 6:
    		issues.append("Low sleep")
    		solutions.append("Sleep at least 7 hours")

	if avg_cal > 2500:
    		issues.append("High calorie intake")
    		solutions.append("Reduce oily & junk food")

	if not issues:
    		st.success("✅ Everything looks good!")
	else:
    		st.warning("⚠️ Issues Detected:")

    		for i in issues:
        	st.write(f"❌ {i}")

    		st.subheader("💡 Solutions")

    	for s in solutions:
        	st.write(f"✔ {s}")

    
    # =====================
    # FOOD SCANNER PRO
    # =====================
    st.subheader("🍔 Food Scanner PRO")

    food_file = st.file_uploader("Upload food image", key="food")

    if food_file and API_KEY:
        genai.configure(api_key=API_KEY)

        model = genai.GenerativeModel("models/gemini-2.5-flash")

        res = model.generate_content([
            {"mime_type": food_file.type, "data": food_file.read()},
            """
            Identify all food items in the image.
            Give:
            - Food name
            - Estimated calories
            - Protein, carbs, fat
            - Is it healthy or junk?
            - Give 1-2 diet suggestions
            """
        ])

        st.success("🍽️ Food Analysis")
        st.write(res.text)

# =====================
# SAVE FOOD BUTTON
# =====================
    if st.button("Save Food"):
        today = str(datetime.date.today())

        c.execute(
            "INSERT INTO food_log VALUES (?,?,?,?)",
            (username, today, res.text, 200)
        )
        conn.commit()

        st.success("Food Saved ✅")



    # =====================
    # MEDICAL AI
    # =====================
    st.subheader("🧪 Medical AI")

    files = st.file_uploader("Upload Report", accept_multiple_files=True)

    if files and API_KEY:
        genai.configure(api_key=API_KEY)

        model = genai.GenerativeModel("models/gemini-2.5-flash")

        for f in files:
            res = model.generate_content([
            {"mime_type": f.type, "data": f.read()},
            "Explain this report in very simple language. Highlight abnormal values and give basic suggestions. Do not give diagnosis."
            ])
            st.write(res.text)

# =====================
# HEALTH RISK AI
# =====================
st.subheader("🚨 Health Risk & Suggestions")

risk_flags = []
tests = []

# conditions
if avg_sleep < 6:
    risk_flags.append("Low sleep → recovery problem")

if avg_cal > 2500:
    risk_flags.append("High calorie intake → weight gain risk")

if avg_steps < 4000:
    risk_flags.append("Low activity → health risk")

# test suggestions
tests.append("Lipid Profile")
tests.append("Blood Sugar")
tests.append("CBC")
tests.append("Vitamin D")

# output
if risk_flags:
    for r in risk_flags:
        st.warning(f"⚠️ {r}")
else:
    st.success("✅ No major risk")

st.subheader("🧪 Recommended Tests")

for t in tests:
    st.write(f"✔ {t}")


# =====================
# FOOD HISTORY
# =====================
    st.subheader("📅 Today Food History")

    # =====================
    # TOTAL CALORIES
    # =====================
    if not food_df.empty:
        total_cal = food_df["calories"].sum()

        st.subheader("🔥 Total Calories Today")
        st.write(f"{total_cal} kcal")

        today = str(datetime.date.today())

        food_df = pd.read_sql(
            "SELECT * FROM food_log WHERE username=? AND date=?",
            conn,
            params=(username, today)
        )

    if not food_df.empty:
        for i, row in food_df.iterrows():
            st.write("🍽️", row["food"])
    else:
        st.info("No food logged today")

        st.markdown("---")
	st.write("🚀 Fit AI Pro MAX")
	conn.close()
