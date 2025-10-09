
# --- 2. Database Initialization ---
def init_db():
    """
    Initializes the SQLite database. This function connects to a local DB file 
    and creates the necessary tables if they don't already exist.
    """
    """Initializes the SQLite database and creates tables if they don't exist."""
with sqlite3.connect('retro_studio.db') as conn:
c = conn.cursor()
        # Pods Table
c.execute('''
           CREATE TABLE IF NOT EXISTS pods (
               id INTEGER PRIMARY KEY,
               name TEXT NOT NULL UNIQUE,
                description TEXT
                live_upload_id INTEGER DEFAULT NULL 
           )
       ''')
        # Uploads Table
c.execute('''
           CREATE TABLE IF NOT EXISTS uploads (
               id INTEGER PRIMARY KEY,
@@ -35,6 +34,7 @@ def init_db():
               FOREIGN KEY (pod_id) REFERENCES pods(id)
           )
       ''')
        # Interactions Table
c.execute('''
           CREATE TABLE IF NOT EXISTS interactions (
               id INTEGER PRIMARY KEY,
@@ -56,12 +56,12 @@ def get_db_connection():
return sqlite3.connect('retro_studio.db')

def get_pods():
    """Fetches all pods from the database and returns them as a pandas DataFrame."""
    """Fetches all pods from the database."""
with get_db_connection() as conn:
return pd.read_sql_query("SELECT * FROM pods", conn)

def add_interaction(upload_id, user_name, interaction_type, content):
    """Adds a new interaction (comment, vote, reaction) to the database."""
    """Adds a user interaction to the database."""
if not user_name:
st.warning("User not identified. Please log in again.")
return
@@ -75,7 +75,6 @@ def add_interaction(upload_id, user_name, interaction_type, content):
conn.commit()
st.toast(f"Your {interaction_type} has been recorded!")


def generate_ai_summary(upload_id):
"""Placeholder for AI summary. Generates a summary from comments."""
with get_db_connection() as conn:
@@ -91,8 +90,18 @@ def generate_ai_summary(upload_id):
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
# Added 'logged_in' to control access to the main app.
if 'logged_in' not in st.session_state:
st.session_state.logged_in = False
if 'page' not in st.session_state:
@@ -110,26 +119,20 @@ def page_login():
st.write("This is the starting point. Select your pod and enter your name to begin.")

pods = get_pods()
    if pods.empty:
        st.info("No pods exist yet. Create the first one below.")
    else:
        pod_names = [""] + pods['name'].tolist()
        selected_pod_name = st.selectbox("Select your Pod Name", pod_names)
        
        user_name_input = st.text_input("Enter your Name")
    pod_names = [""] + pods['name'].tolist() if not pods.empty else [""]
    selected_pod_name = st.selectbox("Select your Pod Name", pod_names)
    user_name_input = st.text_input("Enter your Name")

        if st.button("Login to Channel"):
            if selected_pod_name and user_name_input:
                selected_pod_id = pods[pods['name'] == selected_pod_name]['id'].iloc[0]
                
                # Set session state upon successful login
                st.session_state.logged_in = True
                st.session_state.user_name = user_name_input
                st.session_state.selected_pod_id = selected_pod_id
                st.session_state.page = 'user_upload_interaction' # Go directly to the pod channel
                st.rerun()
            else:
                st.error("Please select a pod and enter your name.")
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
@@ -138,7 +141,7 @@ def page_login():
if new_pod_name:
with get_db_connection() as conn:
conn.execute("INSERT INTO pods (name) VALUES (?)", (new_pod_name,))
                    st.success(f"Pod '{new_pod_name}' created successfully! You can now select it from the list.")
                    st.success(f"Pod '{new_pod_name}' created successfully!")
st.rerun()

# == Page 2: User Upload & Interaction ==
@@ -150,13 +153,11 @@ def page_user_upload_interaction():
st.title(f"Pod Channel: {pod_name}")
st.write("Upload your work, view submissions from your team, and provide feedback asynchronously.")

    with st.expander("⬆️ Upload Your Work (Video, PPT, or Recording)"):
    with st.expander("⬆️ Upload Your Work"):
with st.form("upload_form", clear_on_submit=True):
upload_type = st.selectbox("Select upload type", ["Video", "PPT", "Recording"])
uploaded_file = st.file_uploader("Choose a file")
            
            submitted = st.form_submit_button("Upload")
            if submitted and uploaded_file is not None:
            if st.form_submit_button("Upload") and uploaded_file:
file_data = uploaded_file.getvalue()
timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
with get_db_connection() as conn:
@@ -178,22 +179,14 @@ def page_user_upload_interaction():
st.subheader(f"{upload['file_name']} by {upload['user_name']}")
st.caption(f"Type: {upload['upload_type']} | Uploaded: {upload['timestamp']}")

                if upload['upload_type'] == 'Video':
                    st.video(upload['file_data'])
                else:
                    st.info(f"Content placeholder for {upload['upload_type']}: {upload['file_name']}.")
                    st.download_button(f"Download {upload['file_name']}", upload['file_data'], upload['file_name'])
                # Use the reusable function to display content
                display_uploaded_content(upload)

                # Interaction section remains the same
with st.expander("View AI Summary & All Feedback"):
st.write("**AI-Generated Summary**")
st.code(generate_ai_summary(upload['id']), language='text')
                    
                    with get_db_connection() as conn:
                         interactions_df = pd.read_sql_query(f"SELECT * FROM interactions WHERE upload_id={upload['id']}", conn)
                    if not interactions_df.empty:
                        st.write("**Full Feedback Log:**")
                        st.dataframe(interactions_df[['user_name', 'interaction_type', 'content', 'timestamp']], use_container_width=True)

                # ... [rest of the interaction UI: reactions, votes, comments] ...
cols = st.columns(2)
with cols[0]: 
st.write("**React**")
@@ -202,14 +195,12 @@ def page_user_upload_interaction():
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
@@ -220,48 +211,53 @@ def page_user_upload_interaction():
# == Page 3: Host Review & Voting ==
def page_host_review():
st.title("Host Review Session")
    st.write("As the host, select an upload to review with the team in real-time.")
    
pod_id = st.session_state.selected_pod_id
    
with get_db_connection() as conn:
        uploads = pd.read_sql_query(f"SELECT * FROM uploads WHERE pod_id = {pod_id} ORDER BY timestamp", conn)
        # Check if a session is live for this pod
        live_upload_id = pd.read_sql_query(f"SELECT live_upload_id FROM pods WHERE id = {pod_id}", conn).iloc[0]['live_upload_id']

    if uploads.empty:
        st.warning(f"No uploads found for this pod.")
    else:
        upload_titles = uploads['file_name'].tolist()
        selected_upload_title = st.selectbox("Select an Upload to Present", upload_titles)
        
        upload = uploads[uploads['file_name'] == selected_upload_title].iloc[0]
    if live_upload_id:
        # --- ATTENDEE VIEW ---
        st.success("🟢 A retro session is LIVE! Join in and give your feedback.")
        with get_db_connection() as conn:
            live_upload_data = pd.read_sql_query(f"SELECT * FROM uploads WHERE id = {live_upload_id}", conn).iloc[0]

        st.header(f"Presenting: {upload['file_name']} by {upload['user_name']}")
        st.header(f"Presenting: {live_upload_data['file_name']} by {live_upload_data['user_name']}")
        display_uploaded_content(live_upload_data)

        if upload['upload_type'] == 'Video':
            st.video(upload['file_data'])
        else:
            st.info(f"Host presents content for {upload['upload_type']}: {upload['file_name']}. Feedback appears below.")

        # Live feedback dashboard for attendees
st.subheader("Live Feedback Dashboard")
        # ... [feedback dashboard code, same as host view] ...
with get_db_connection() as conn:
            interactions = pd.read_sql_query(f"SELECT * FROM interactions WHERE upload_id = {upload['id']}", conn)

        if interactions.empty:
            st.info("No feedback yet.")
        else:
            interactions = pd.read_sql_query(f"SELECT * FROM interactions WHERE upload_id = {live_upload_id}", conn)
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
            
            st.write("**Comments Log**")
            comments = interactions[interactions['interaction_type'] == 'comment'][['user_name', 'content', 'timestamp']]
            st.dataframe(comments, use_container_width=True)
    else:
        # --- HOST VIEW (when no session is live) ---
        st.write("As the host, select an upload to present to the team.")
        with get_db_connection() as conn:
            uploads = pd.read_sql_query(f"SELECT * FROM uploads WHERE pod_id = {pod_id}", conn)

        if uploads.empty:
            st.warning("No uploads found for this pod to present.")
            return

        upload_options = uploads.set_index('id')['file_name'].to_dict()
        selected_upload_id = st.selectbox("Select an Upload to Present", options=list(upload_options.keys()), format_func=lambda x: upload_options[x])
        
        if st.button("🚀 Go Live with this Upload"):
            with get_db_connection() as conn:
                conn.execute(f"UPDATE pods SET live_upload_id = {selected_upload_id} WHERE id = {pod_id}")
            st.rerun()

# == Page 4: Retro Summary ==
def page_retro_summary():
@@ -271,19 +267,16 @@ def page_retro_summary():
pod_id = st.session_state.selected_pod_id
with get_db_connection() as conn:
pod_name = pd.read_sql_query(f"SELECT name FROM pods WHERE id = {pod_id}", conn).iloc[0]['name']
    st.header(f"Summaries for {pod_name}")

    with get_db_connection() as conn:
uploads = pd.read_sql_query(f"SELECT * FROM uploads WHERE pod_id = {pod_id}", conn)

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

@@ -297,7 +290,6 @@ def page_retro_summary():


# --- Main App Router ---
# This block checks if the user is logged in and routes them to the correct page.
if not st.session_state.logged_in:
page_login()
else:
@@ -311,14 +303,16 @@ def page_retro_summary():
if st.sidebar.button("Current Pod Channel"):
st.session_state.page = 'user_upload_interaction'
st.rerun()
    if st.sidebar.button("Host Review Session"):
    if st.sidebar.button("Host/Live Review Session"):
st.session_state.page = 'host_review'
st.rerun()
if st.sidebar.button("Retro Summary Library"):
st.session_state.page = 'retro_summary'
st.rerun()
if st.sidebar.button("Logout"):
        # Reset all session state variables on logout
        # Reset pod's live session on logout if user is host
        with get_db_connection() as conn:
            conn.execute(f"UPDATE pods SET live_upload_id = NULL WHERE id = {st.session_state.selected_pod_id}")
for key in st.session_state.keys():
del st.session_state[key]
st.rerun()
@@ -331,4 +325,4 @@ def page_retro_summary():
elif st.session_state.page == 'retro_summary':
page_retro_summary()
else:
        page_user_upload_interaction() # Default to the main channel page
        page_user_upload_interaction()
