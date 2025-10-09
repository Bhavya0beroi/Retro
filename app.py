import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import io
from PIL import Image

# --- 1. App Configuration ---
st.set_page_config(layout="wide", page_title="Zero1 Retro Studio")

# --- 2. Database Initialization ---
def init_db():
    """Initializes the SQLite database and creates tables if they don't exist."""
    with sqlite3.connect('retro_studio.db') as conn:
        c = conn.cursor()
        # Pods Table - Added live_upload_id to track the live session
        c.execute('''
            CREATE TABLE IF NOT EXISTS pods (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                live_upload_id INTEGER DEFAULT NULL 
            )
        ''')
        # Uploads Table
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
        # Interactions Table
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
    """
    Reusable function to display uploaded content.
    Plays videos directly or provides a download for other file types.
    """
    if upload_data['upload_type'] == 'Video':
        st.video(upload_data['file_data'])
    else:
        st.info(f"Content placeholder for {upload_data['upload_type']}: {upload_data['file_name']}.")
        st.download_button(f"Download {upload_data['file_name']}", upload_data['file_data'], upload_data['file_name'])

# --- 4. State Management ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'page' not in st.session_state:
    st.session_state.page = 'login'
if 'selected_pod_id' not in st.session_state:
    st.session_state.selected_pod_id = None
if 'user_name' not in st.session_state:
    st.session_state.user_name = ''

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
            selected_pod_id = pods[pods['name'] == selected_pod_name]['id'].iloc[0]
            st.session_state.logged_in = True
            st.session_state.user_name = user_name_input
            st.session_state.selected_pod_id = selected_pod_id
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
    pod_id = st.session_state.selected_pod_id
    with get_db_connection() as conn:
        pod_df = pd.read_sql_query("SELECT name FROM pods WHERE id = ?", conn, params=(pod_id,))
        if pod_df.empty:
            st.error("Selected pod not found. Please log out and try again.")
            return
        pod_name = pod_df.iloc[0]['name']
    
    st.title(f"Pod Channel: {pod_name}")
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
                        (pod_id, st.session_state.user_name, upload_type, file_data, uploaded_file.name, timestamp)
                    )
                st.success("File uploaded successfully!")

    st.header("Pod Feed")
    with get_db_connection() as conn:
        uploads = pd.read_sql_query("SELECT * FROM uploads WHERE pod_id = ? ORDER BY timestamp DESC", conn, params=(pod_id,))

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

# == Page 3: Host Review & Voting ==
def page_host_review():
    st.title("Host Review Session")
    pod_id = st.session_state.selected_pod_id
    
    with get_db_connection() as conn:
        live_upload_id_df = pd.read_sql_query("SELECT live_upload_id FROM pods WHERE id = ?", conn, params=(pod_id,))
        if live_upload_id_df.empty:
            st.error("Selected pod not found. Please log out and try again.")
            return
        live_upload_id = live_upload_id_df.iloc[0]['live_upload_id']

    if live_upload_id:
        # --- ATTENDEE VIEW ---
        st.success("🟢 A retro session is LIVE! Join in and give your feedback.")
        with get_db_connection() as conn:
            live_upload_data_df = pd.read_sql_query("SELECT * FROM uploads WHERE id = ?", conn, params=(int(live_upload_id),))
            if live_upload_data_df.empty:
                st.warning("The live session content is not available. Please wait for the host.")
                return
            live_upload_data = live_upload_data_df.iloc[0]

        st.header(f"Presenting: {live_upload_data['file_name']} by {live_upload_data['user_name']}")
        display_uploaded_content(live_upload_data)
        
        # --- ENHANCEMENT: Added interaction elements for all members ---
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
            votes = interactions[interactions['interaction_type'] == 'vote']['content'].value_counts()
            reactions = interactions[interactions['interaction_type'] == 'reaction']['content'].value_counts()
            v_col, r_col = st.columns(2)
            with v_col:
                st.write("**Voting Results**")
                st.bar_chart(votes)
            with r_col:
                st.write("**Reaction Summary**")
                st.bar_chart(reactions)
    else:
        # --- HOST VIEW (when no session is live) ---
        st.write("As the host, select an upload to present to the team.")
        with get_db_connection() as conn:
            uploads = pd.read_sql_query("SELECT * FROM uploads WHERE pod_id = ?", conn, params=(pod_id,))

        if uploads.empty:
            st.warning("No uploads found for this pod to present.")
            return

        upload_options = uploads.set_index('id')['file_name'].to_dict()
        selected_upload_id = st.selectbox("Select an Upload to Present", options=list(upload_options.keys()), format_func=lambda x: upload_options[x])
        
        if st.button("🚀 Go Live with this Upload"):
            with get_db_connection() as conn:
                conn.execute("UPDATE pods SET live_upload_id = ? WHERE id = ?", (selected_upload_id, pod_id))
            st.rerun()

# == Page 4: Retro Summary ==
def page_retro_summary():
    st.title("Retro Summary Library")
    st.write("Review past retro sessions and learnings for your pod.")
    
    pod_id = st.session_state.selected_pod_id
    with get_db_connection() as conn:
        pod_df = pd.read_sql_query("SELECT name FROM pods WHERE id = ?", conn, params=(pod_id,))
        if pod_df.empty:
            st.error("Selected pod not found. Please log out and try again.")
            return
        pod_name = pod_df.iloc[0]['name']
        uploads = pd.read_sql_query("SELECT * FROM uploads WHERE pod_id = ?", conn, params=(pod_id,))
    
    st.header(f"Summaries for {pod_name}")
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
if not st.session_state.logged_in:
    page_login()
else:
    # --- Sidebar for logged-in users ---
    st.sidebar.title("Zero1 Retro Studio")
    with get_db_connection() as conn:
        pod_df = pd.read_sql_query("SELECT name FROM pods WHERE id = ?", conn, params=(st.session_state.selected_pod_id,))
        if not pod_df.empty:
            pod_name = pod_df.iloc[0]['name']
            st.sidebar.info(f"User: **{st.session_state.user_name}**\n\nPod: **{pod_name}**")
        else:
            st.sidebar.error("Pod not found. Please log out.")
    
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
        if st.session_state.selected_pod_id:
            with get_db_connection() as conn:
                conn.execute("UPDATE pods SET live_upload_id = NULL WHERE id = ?", (st.session_state.selected_pod_id,))
        for key in st.session_state.keys():
            del st.session_state[key]
        st.rerun()

    # --- Page routing for logged-in users ---
    if st.session_state.page == 'user_upload_interaction':
        page_user_upload_interaction()
    elif st.session_state.page == 'host_review':
        page_host_review()
    elif st.session_state.page == 'retro_summary':
        page_retro_summary()
    else:
        # Default to login page if something goes wrong
        page_login()
