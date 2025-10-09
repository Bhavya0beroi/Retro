import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
from streamlit_extras.switch_page_button import switch_page
from PIL import Image
import io

# --- DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect('retro_tool.db')
    c = conn.cursor()
    # Retros table
    c.execute('''
        CREATE TABLE IF NOT EXISTS retros (
            id INTEGER PRIMARY KEY,
            title TEXT NOT NULL,
            date TEXT NOT NULL,
            host TEXT
        )
    ''')
    # Insights table
    c.execute('''
        CREATE TABLE IF NOT EXISTS insights (
            id INTEGER PRIMARY KEY,
            retro_id INTEGER,
            title TEXT NOT NULL,
            explanation TEXT,
            confidence TEXT,
            next_steps TEXT,
            status TEXT DEFAULT 'Hypothesis',
            media BLOB,
            FOREIGN KEY (retro_id) REFERENCES retros(id)
        )
    ''')
    # Comments table
    c.execute('''
        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY,
            insight_id INTEGER,
            author TEXT,
            comment TEXT,
            timestamp TEXT,
            FOREIGN KEY (insight_id) REFERENCES insights(id)
        )
    ''')
    # Votes table
    c.execute('''
        CREATE TABLE IF NOT EXISTS votes (
            id INTEGER PRIMARY KEY,
            insight_id INTEGER,
            user_id TEXT,
            depth INTEGER,
            usefulness TEXT,
            decision TEXT,
            FOREIGN KEY (insight_id) REFERENCES insights(id)
        )
    ''')
    conn.commit()
    conn.close()

# Initialize the database
init_db()

# --- HELPER FUNCTIONS ---
def get_db_connection():
    return sqlite3.connect('retro_tool.db')

def add_retro(title, date, host):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("INSERT INTO retros (title, date, host) VALUES (?, ?, ?)", (title, date, host))
    conn.commit()
    conn.close()

def add_insight(retro_id, title, explanation, confidence, next_steps, media):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("INSERT INTO insights (retro_id, title, explanation, confidence, next_steps, media) VALUES (?, ?, ?, ?, ?, ?)",
              (retro_id, title, explanation, confidence, next_steps, media))
    conn.commit()
    conn.close()

def add_comment(insight_id, author, comment):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("INSERT INTO comments (insight_id, author, comment, timestamp) VALUES (?, ?, ?, ?)",
              (insight_id, author, comment, timestamp))
    conn.commit()
    conn.close()

def add_vote(insight_id, user_id, depth, usefulness, decision):
    conn = get_db_connection()
    c = conn.cursor()
    # Check if user has already voted
    c.execute("SELECT * FROM votes WHERE insight_id = ? AND user_id = ?", (insight_id, user_id))
    if c.fetchone() is None:
        c.execute("INSERT INTO votes (insight_id, user_id, depth, usefulness, decision) VALUES (?, ?, ?, ?, ?)",
                  (insight_id, user_id, depth, usefulness, decision))
    else:
        c.execute("UPDATE votes SET depth = ?, usefulness = ?, decision = ? WHERE insight_id = ? AND user_id = ?",
                  (depth, usefulness, decision, insight_id, user_id))
    conn.commit()
    conn.close()

# --- APP LAYOUT ---
st.set_page_config(layout="wide", page_title="Zero1 Retro Studio")

# Custom CSS for styling
st.markdown("""
<style>
    .st-emotion-cache-18ni7ap, .st-emotion-cache-10trblm {
        background-color: #1a1a2e;
    }
    .st-emotion-cache-16txtl3 {
        padding: 2rem 1rem;
    }
    h1, h2, h3 {
        color: #e0e0e0;
    }
    .stButton>button {
        background-color: #0f3460;
        color: white;
        border-radius: 20px;
        border: 1px solid #16213e;
    }
    .stButton>button:hover {
        background-color: #1a1a2e;
        color: white;
        border: 1px solid #0f3460;
    }
    .st-emotion-cache-1v0mbdj, .st-emotion-cache-1r6slb0 {
        background-color: #16213e;
        border-radius: 10px;
        padding: 1rem;
        border: 1px solid #0f3460;
    }
</style>
""", unsafe_allow_html=True)


# --- STATE MANAGEMENT ---
if 'page' not in st.session_state:
    st.session_state.page = 'Home'
if 'user_id' not in st.session_state:
    st.session_state.user_id = f"user_{int(datetime.now().timestamp())}"
if 'current_retro' not in st.session_state:
    st.session_state.current_retro = None
if 'current_insight_index' not in st.session_state:
    st.session_state.current_insight_index = 0

# --- PAGE NAVIGATION ---
st.sidebar.title("Navigation")
if st.sidebar.button("Home"):
    st.session_state.page = "Home"
if st.sidebar.button("Host a Retro"):
    st.session_state.page = "Host"
if st.sidebar.button("Live Retro"):
    st.session_state.page = "Live"
if st.sidebar.button("Playbook"):
    st.session_state.page = "Playbook"


# --- PAGE RENDERING ---
if st.session_state.page == 'Home':
    st.title("Welcome to Zero1 Retro Studio")
    st.subheader("Collaborative insights review for content creation teams")
    st.write("Use the navigation on the left to host a new retro, join a live session, or review past insights in the playbook.")

elif st.session_state.page == 'Host':
    st.title("Host a New Retro")

    with st.form("new_retro_form"):
        retro_title = st.text_input("Retro Title")
        retro_date = st.date_input("Date")
        host_name = st.text_input("Host Name")
        submitted = st.form_submit_button("Create Retro")
        if submitted:
            add_retro(retro_title, retro_date.strftime("%Y-%m-%d"), host_name)
            st.success(f"Retro '{retro_title}' created!")

    st.header("Add Insights to a Retro")
    conn = get_db_connection()
    retros_df = pd.read_sql_query("SELECT * FROM retros", conn)
    conn.close()

    if not retros_df.empty:
        retro_choice = st.selectbox("Choose a Retro", options=retros_df['title'])
        retro_id = retros_df[retros_df['title'] == retro_choice]['id'].iloc[0]

        with st.form("new_insight_form", clear_on_submit=True):
            insight_title = st.text_input("Insight Title")
            explanation = st.text_area("Explanation")
            confidence = st.select_slider("Confidence Level", options=['Low', 'Medium', 'High'])
            next_steps = st.text_area("Next Steps (Optional)")
            uploaded_file = st.file_uploader("Upload Media (Image)", type=['png', 'jpg', 'jpeg'])

            insight_submitted = st.form_submit_button("Add Insight")
            if insight_submitted:
                media_data = None
                if uploaded_file:
                    media_data = uploaded_file.getvalue()
                add_insight(retro_id, insight_title, explanation, confidence, next_steps, media_data)
                st.success(f"Insight '{insight_title}' added to '{retro_choice}'!")

elif st.session_state.page == 'Live':
    st.title("Live Retro Session")

    conn = get_db_connection()
    retros_df = pd.read_sql_query("SELECT * FROM retros", conn)
    conn.close()

    if not retros_df.empty:
        retro_choice = st.selectbox("Select a Retro to Start", options=retros_df['title'])
        if st.button("Start Retro"):
            st.session_state.current_retro = retros_df[retros_df['title'] == retro_choice]['id'].iloc[0]
            st.session_state.current_insight_index = 0

    if st.session_state.current_retro:
        conn = get_db_connection()
        insights_df = pd.read_sql_query(f"SELECT * FROM insights WHERE retro_id = {st.session_state.current_retro}", conn)
        conn.close()

        if not insights_df.empty:
            total_insights = len(insights_df)
            current_index = st.session_state.current_insight_index
            insight = insights_df.iloc[current_index]

            st.header(f"Insight {current_index + 1}/{total_insights}: {insight['title']}")

            col1, col2 = st.columns([2, 1])

            with col1:
                st.subheader("Insight Details")
                st.markdown(f"**Explanation:** {insight['explanation']}")
                st.markdown(f"**Confidence:** {insight['confidence']}")
                st.markdown(f"**Next Steps:** {insight['next_steps']}")
                if insight['media']:
                    try:
                        image = Image.open(io.BytesIO(insight['media']))
                        st.image(image, caption="Uploaded Media")
                    except Exception as e:
                        st.error(f"Could not display image: {e}")


            with col2:
                st.subheader("Team Feedback")

                # Voting
                depth = st.slider("Insight Depth (1-10)", 1, 10, 5)
                usefulness = st.radio("Usefulness for team", ["We'll reuse this", "Good, not for us", "Needs clarity"])
                decision = st.radio("Decision", ["GOOD (Useful)", "KILL (Not Useful)"])

                if st.button("Submit Vote"):
                    add_vote(int(insight['id']), st.session_state.user_id, depth, usefulness, decision)
                    st.success("Your vote has been recorded!")

                # Comments
                st.subheader("Comments")
                author = st.text_input("Your Name")
                comment_text = st.text_area("Add a comment...")
                if st.button("Post Comment"):
                    if author and comment_text:
                        add_comment(int(insight['id']), author, comment_text)
                        st.success("Comment posted!")

                conn = get_db_connection()
                comments_df = pd.read_sql_query(f"SELECT * FROM comments WHERE insight_id = {insight['id']}", conn)
                conn.close()

                for _, row in comments_df.iterrows():
                    st.text(f"{row['author']} ({row['timestamp']}): {row['comment']}")

            # Navigation
            nav_col1, nav_col2, nav_col3 = st.columns([1,1,1])
            with nav_col1:
                if st.button("Previous Insight") and current_index > 0:
                    st.session_state.current_insight_index -= 1
                    st.experimental_rerun()
            with nav_col2:
                 if st.button("Next Insight") and current_index < total_insights - 1:
                    st.session_state.current_insight_index += 1
                    st.experimental_rerun()
            with nav_col3:
                if st.button("End Retro"):
                    st.session_state.current_retro = None
                    st.session_state.current_insight_index = 0
                    st.experimental_rerun()


elif st.session_state.page == 'Playbook':
    st.title("Insights Playbook")
    conn = get_db_connection()
    insights_df = pd.read_sql_query("SELECT i.*, r.title as retro_title FROM insights i JOIN retros r ON i.retro_id = r.id", conn)
    conn.close()

    if not insights_df.empty:
        search_term = st.text_input("Search insights...")
        if search_term:
            insights_df = insights_df[insights_df['title'].str.contains(search_term, case=False)]

        for _, insight in insights_df.iterrows():
            with st.container():
                st.header(insight['title'])
                st.caption(f"From Retro: {insight['retro_title']}")
                st.write(insight['explanation'])
                if st.button("View Details", key=f"details_{insight['id']}"):
                    st.session_state.selected_insight = insight['id']

    if 'selected_insight' in st.session_state:
        conn = get_db_connection()
        votes_df = pd.read_sql_query(f"SELECT * FROM votes WHERE insight_id = {st.session_state.selected_insight}", conn)
        comments_df = pd.read_sql_query(f"SELECT * FROM comments WHERE insight_id = {st.session_state.selected_insight}", conn)
        conn.close()

        st.subheader("Voting Summary")
        if not votes_df.empty:
            avg_depth = votes_df['depth'].mean()
            st.metric("Average Depth", f"{avg_depth:.1f}/10")
            st.bar_chart(votes_df['usefulness'].value_counts())
            st.bar_chart(votes_df['decision'].value_counts())
        else:
            st.write("No votes yet.")

        st.subheader("Comments")
        if not comments_df.empty:
            for _, row in comments_df.iterrows():
                st.text(f"{row['author']} ({row['timestamp']}): {row['comment']}")
        else:
            st.write("No comments yet.")
