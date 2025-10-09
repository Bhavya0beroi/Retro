import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# --- 1. App Configuration ---
st.set_page_config(layout="wide", page_title="Zero1 Retro Studio")

# --- 2. Database Initialization ---
def init_db():
    """Initializes the SQLite database and creates tables if they don't exist."""
    with sqlite3.connect('retro_studio.db') as conn:
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS pods (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                live_upload_id INTEGER DEFAULT NULL 
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS uploads (
                id INTEGER PRIMARY KEY,
                pod_id INTEGER,
                user_name TEXT,
                upload_type TEXT,
                file_data BLOB,
                file_name TEXT,
                timestamp TEXT,
                FOREIGN KEY (pod_id) REFERENCES pods(id)
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS interactions (
                id INTEGER PRIMARY KEY,
                upload_id INTEGER,
                user_name TEXT,
                interaction_type TEXT,
                content TEXT,
                timestamp TEXT,
                FOREIGN KEY (upload_id) REFERENCES uploads(id)
            )
        ''')
        conn.commit()

init_db()

# --- 3. Helper Functions ---
def get_db_connection():
    """Returns a connection object to the SQLite database."""
    return sqlite3.connect('retro_studio.db')

def get_pods():
    """Fetches all pods from the database."""
    with get_db_connection() as conn:
        return pd.read_sql_query("SELECT * FROM pods", conn)

def add_interaction(upload_id, user_name, interaction_type, content):
    """Adds a user interaction to the database."""
    if not user_name:
        st.warning("User not identified. Please log in again.")
        return
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute(
            "INSERT INTO interactions (upload_id, user_name, interaction_type, content) VALUES (?, ?, ?, ?)",
            (upload_id, user_name, interaction_type, content)
        )
        conn.commit()
    st.toast(f"Your {interaction_type} has been recorded!")

def generate_ai_summary(upload_id):
    """Placeholder for AI summary. Generates a summary from comments."""
    with get_db_connection() as conn:
        comments_df = pd.read_sql_query(
            "SELECT content FROM interactions WHERE upload_id = ? AND interaction_type = 'comment'", conn, params=(upload_id,)
        )
    if comments_df.empty:
        return "No comments available to generate a summary."
    
    summary = "Key takeaways from comments:\n"
    unique_comments = comments_df['content'].unique()
    for comment in unique_comments:
        summary += f"- {comment}\n"
    return summary

def display_uploaded_content(upload_data):
    """Reusable function to display uploaded content."""
    if upload_data['upload_type'] == 'Video':
        st.video(upload_data['file_data'])
    else:
        st.info(f"Content placeholder for {upload_data['upload_type']}: {upload_data['file_name']}.")
        st.download_button(f"Download {upload_data['file_name']}", upload_data['file_data'], upload_data['file_name'])

# --- 4. State Management Initialization ---
if 'page' not in st.session_state:
    st.session_state.page = 'login'

# --- 5. UI Rendering ---

# == Page 1: Login Page ==
def page_login():
    st.title("Join Your Pod Channel")
    st.write("This is the starting point. Select your pod and enter your name to begin.")
    
    pods = get_pods()
    pod_names = [""] + pods['name'].tolist() if not pods.empty else [""]
    selected_pod_name = st.selectbox("Select your Pod Name", pod_names)
    user_name_input = st.text_input("Enter your Name")

    if st.button("Login to Channel"):
        if selected_pod_name and user_name_input:
            selected_pod = pods[pods['name'] == selected_pod_name]
            if not selected_pod.empty:
                st.session_state.logged_in = True
                st.session_state.user_name = user_name_input
                st.session_state.selected_pod_id = int(selected_pod.iloc[0]['id'])
                st.session_state.selected_pod_name = selected_pod.iloc[0]['name']
                st.session_state.page = 'user_upload_interaction'
                st.rerun()
        else:
            st.error("Please select a pod and enter your name.")

    with st.expander("Or, Create a New Pod"):
        with st.form("create_pod", clear_on_submit=True):
            new_pod_name = st.text_input("New Pod Name")
            if st.form_submit_button("Create Pod"):
                if new_pod_name:
                    with get_db_connection() as conn:
                        conn.execute("INSERT INTO pods (name) VALUES (?)", (new_pod_name,))
                    st.success(f"Pod '{new_pod_name}' created successfully!")
                    st.rerun()

# == Page 2: User Upload & Interaction ==
def page_user_upload_interaction():
    if 'selected_pod_name' not in st.session_state:
        st.error("Session expired. Please log out and log back in.")
        return

    st.title(f"Pod Channel: {st.session_state.selected_pod_name}")
    st.write("Upload your work, view submissions from your team, and provide feedback asynchronously.")

    with st.expander("⬆️ Upload Your Work"):
        with st.form("upload_form", clear_on_submit=True):
            upload_type = st.selectbox("Select upload type", ["Video", "PPT", "Recording"])
            uploaded_file = st.file_uploader("Choose a file")
            if st.form_submit_button("Upload") and uploaded_file:
                file_data = uploaded_file.getvalue()
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
                with get_db_connection() as conn:
                    conn.execute(
                        "INSERT INTO uploads (pod_id, user_name, upload_type, file_data, file_name, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
                        (st.session_state.selected_pod_id, st.session_state.user_name, upload_type, file_data, uploaded_file.name, timestamp)
                    )
                st.success("File uploaded successfully!")

    st.header("Pod Feed")
    with get_db_connection() as conn:
        uploads = pd.read_sql_query("SELECT * FROM uploads WHERE pod_id = ? ORDER BY timestamp DESC", conn, params=(st.session_state.selected_pod_id,))

    if uploads.empty:
        st.info("No uploads in this pod yet. Be the first!")
    else:
        for _, upload in uploads.iterrows():
            with st.container(border=True):
                st.subheader(f"{upload['file_name']} by {upload['user_name']}")
                st.caption(f"Type: {upload['upload_type']} | Uploaded: {upload['timestamp']}")
                display_uploaded_content(upload)
                with st.expander("View AI Summary & All Feedback"):
                    st.write("**AI-Generated Summary**")
                    st.code(generate_ai_summary(upload['id']), language='text')
                
                cols = st.columns(2)
                with cols[0]: 
                    st.write("**React**")
                    reaction_emojis = ["👍", "💡", "🔥", "🤔"]
                    r_cols = st.columns(4)
                    for i, emoji in enumerate(reaction_emojis):
                        if r_cols[i].button(emoji, key=f"react_{emoji}_{upload['id']}"):
                             add_interaction(upload['id'], st.session_state.user_name, 'reaction', emoji)
                    st.write("**Vote on Insight**")
                    v_cols = st.columns(2)
                    if v_cols[0].button("👍 Keep", key=f"vote_keep_{upload['id']}"):
                        add_interaction(upload['id'], st.session_state.user_name, 'vote', 'Keep')
                    if v_cols[1].button("👎 Kill", key=f"vote_kill_{upload['id']}"):
                        add_interaction(upload['id'], st.session_state.user_name, 'vote', 'Kill')
                with cols[1]:
                    st.write("**Comment**")
                    with st.form(f"comment_form_{upload['id']}", clear_on_submit=True):
                        comment_text = st.text_area("Add your thoughts...", height=100, label_visibility="collapsed")
                        if st.form_submit_button("Post Comment"):
                            add_interaction(upload['id'], st.session_state.user_name, 'comment', comment_text)

# == Page 3: Host Review & Voting (REWRITTEN FOR STABILITY) ==
def page_host_review():
    st.title("Live Review Session")

    if 'selected_pod_id' not in st.session_state or st.session_state.selected_pod_id is None:
        st.error("Could not identify the pod. Please log out and select your pod again.")
        return
        
    pod_id = st.session_state.selected_pod_id
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT live_upload_id FROM pods WHERE id = ?", (int(pod_id),))
        result = cursor.fetchone()
        live_upload_id = result[0] if result else None

    # --- RENDER PAGE BASED ON WHETHER A SESSION IS LIVE ---

    if live_upload_id:
        # STATE 1: SESSION IS LIVE (View for everyone, including host)
        with get_db_connection() as conn:
            live_upload_data_df = pd.read_sql_query("SELECT * FROM uploads WHERE id = ?", conn, params=(int(live_upload_id),))
        
        if live_upload_data_df.empty:
            st.warning("The live session content is not available. Waiting for host...")
            return

        live_upload_data = live_upload_data_df.iloc[0]

        st.success("🟢 A retro session is LIVE! Join in and give your feedback.")
        st.header(f"Presenting: {live_upload_data['file_name']} by {live_upload_data['user_name']}")
        display_uploaded_content(live_upload_data)
        
        # Interaction UI for all members
        st.subheader("Live Interaction")
        cols = st.columns(2)
        with cols[0]:
            st.write("**React**")
            reaction_emojis = ["👍", "💡", "🔥", "🤔"]
            r_cols = st.columns(4)
            for i, emoji in enumerate(reaction_emojis):
                if r_cols[i].button(emoji, key=f"live_react_{emoji}_{live_upload_data['id']}"):
                    add_interaction(live_upload_data['id'], st.session_state.user_name, 'reaction', emoji)
        with cols[1]:
            st.write("**Comment**")
            with st.form(f"live_comment_form_{live_upload_data['id']}", clear_on_submit=True):
                comment_text = st.text_area("Add your live thoughts...", height=100, label_visibility="collapsed")
                if st.form_submit_button("Post Comment"):
                    add_interaction(live_upload_data['id'], st.session_state.user_name, 'comment', comment_text)
        
        st.subheader("Live Feedback Dashboard")
        with get_db_connection() as conn:
            interactions = pd.read_sql_query("SELECT * FROM interactions WHERE upload_id = ?", conn, params=(int(live_upload_id),))
        if not interactions.empty:
            # Display feedback...
            pass # UI for feedback dashboard can go here

        # Host-only button to end the session
        if st.button("🔴 End Live Session"):
            with get_db_connection() as conn:
                conn.execute("UPDATE pods SET live_upload_id = NULL WHERE id = ?", (int(pod_id),))
            st.rerun()

    else:
        # STATE 2: SESSION IS NOT LIVE (View for everyone)
        st.info("No session is currently live. Any member can start a new session.")
        st.write("Select an upload to present to the team.")
        
        with get_db_connection() as conn:
            uploads = pd.read_sql_query("SELECT * FROM uploads WHERE pod_id = ?", conn, params=(pod_id,))

        if uploads.empty:
            st.warning("No uploads found in this pod to present.")
            return

        upload_options = uploads.set_index('id')['file_name'].to_dict()
        selected_upload_id = st.selectbox("Select an Upload to Present", options=list(upload_options.keys()), format_func=lambda x: upload_options[x])
        
        if st.button("🚀 Go Live with this Upload"):
            with get_db_connection() as conn:
                conn.execute("UPDATE pods SET live_upload_id = ? WHERE id = ?", (selected_upload_id, pod_id))
            st.rerun()

# == Page 4: Retro Summary ==
def page_retro_summary():
    if 'selected_pod_name' not in st.session_state:
        st.error("Session expired. Please log out and log back in.")
        return

    st.title("Retro Summary Library")
    st.write(f"Review past retro sessions and learnings for {st.session_state.selected_pod_name}.")
    
    with get_db_connection() as conn:
        uploads = pd.read_sql_query("SELECT * FROM uploads WHERE pod_id = ?", conn, params=(st.session_state.selected_pod_id,))
    
    if uploads.empty:
        st.info("No uploads found for this pod, so no summaries are available.")
    else:
        for _, upload in uploads.iterrows():
            with st.container(border=True):
                st.subheader(f"Summary for '{upload['file_name']}'")
                st.caption(f"Presented by: {upload['user_name']} on {upload['timestamp']}")
                st.write("**AI-Generated Key Takeaways:**")
                st.code(generate_ai_summary(upload['id']), language='text')
                
                with get_db_connection() as conn:
                     votes = pd.read_sql_query("SELECT content FROM interactions WHERE upload_id = ? AND interaction_type='vote'", conn, params=(upload['id'],))['content'].value_counts()
                st.write("**Final Vote:**")
                if not votes.empty:
                    st.bar_chart(votes)
                else:
                    st.write("No votes were recorded.")

# --- Main App Router ---
if 'logged_in' in st.session_state and st.session_state.logged_in:
    st.sidebar.title("Zero1 Retro Studio")
    if 'user_name' in st.session_state and 'selected_pod_name' in st.session_state:
        st.sidebar.info(f"User: **{st.session_state.user_name}**\n\nPod: **{st.session_state.selected_pod_name}**")
    
    st.sidebar.header("Navigation")
    if st.sidebar.button("Current Pod Channel"):
        st.session_state.page = 'user_upload_interaction'
        st.rerun()
    if st.sidebar.button("Host/Live Review Session"):
        st.session_state.page = 'host_review'
        st.rerun()
    if st.sidebar.button("Retro Summary Library"):
        st.session_state.page = 'retro_summary'
        st.rerun()
    if st.sidebar.button("Logout"):
        pod_id = st.session_state.get('selected_pod_id')
        if pod_id:
            with get_db_connection() as conn:
                conn.execute("UPDATE pods SET live_upload_id = NULL WHERE id = ?", (int(pod_id),))
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

    page_to_show = st.session_state.get('page', 'user_upload_interaction')
    if page_to_show == 'user_upload_interaction':
        page_user_upload_interaction()
    elif page_to_show == 'host_review':
        page_host_review()
    elif page_to_show == 'retro_summary':
        page_retro_summary()
    else:
        page_user_upload_interaction()

else:
    page_login()

