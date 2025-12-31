import streamlit as st
from supabase import create_client
import json
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Prompt Manager", page_icon="📋", layout="wide")


# Auth check
if "user_email" not in st.session_state:
    st.switch_page("login.py")
    st.stop()
# Initialize Supabase
@st.cache_resource
def get_supabase_client():
    return create_client(
        st.secrets["SUPABASE_URL"],
        st.secrets["SUPABASE_ANON_KEY"]
    )

supabase = get_supabase_client()
ADMIN = st.session_state.get("user_role") == "admin"

# Header
st.title("📋 Prompt Manager")
col1, col2 = st.columns([3, 1])
with col1:
    st.caption(f"Logged in as {st.session_state.user_email}")
with col2:
    if st.button("🔄 Refresh", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# Fetch prompts with caching
@st.cache_data(ttl=60)
def fetch_prompts():
    return supabase.table("prompts").select("*").order("created_at", desc=True).execute().data

# Bulk import from JSON
with st.expander("📁 Bulk Import from JSON"):
    uploaded_file = st.file_uploader("Upload JSON file", type=['json'])
    if uploaded_file:
        try:
            data = json.load(uploaded_file)
            st.write(f"Found {len(data)} entries")
            
            if st.button("Import All Entries"):
                with st.spinner("Importing..."):
                    for entry in data:
                        supabase.table("prompts").insert({
                            "prompt": entry.get("prompt", ""),
                            "query": entry.get("query", ""),
                            "response": entry.get("response", ""),
                            "created_by": st.session_state.user_email
                        }).execute()
                st.success(f"✅ Successfully imported {len(data)} entries!")
                st.cache_data.clear()
                st.rerun()
        except json.JSONDecodeError:
            st.error("Invalid JSON file")
        except Exception as e:
            st.error(f"Error: {str(e)}")

# Export options
prompts = fetch_prompts()

if prompts:
    with st.expander("📤 Export Data"):
        col1, col2 = st.columns(2)
        
        # Prepare export data
        export_data = [{"prompt": p["prompt"], "query": p["query"], "response": p["response"]} 
                      for p in prompts]
        
        with col1:
            # JSON export
            json_str = json.dumps(export_data, indent=2)
            st.download_button(
                label="⬇️ Download JSON",
                data=json_str,
                file_name=f"prompts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json",
                use_container_width=True
            )
        
        with col2:
            # CSV export
            df = pd.DataFrame(export_data)
            csv = df.to_csv(index=False)
            st.download_button(
                label="⬇️ Download CSV",
                data=csv,
                file_name=f"prompts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                use_container_width=True
            )

# Add new prompt
with st.expander("➕ Add New Prompt", expanded=False):
    with st.form("add_prompt_form", clear_on_submit=True):
        p = st.text_input("Prompt", placeholder="Enter prompt description...")
        q = st.text_area("Query", placeholder="Enter SQL query or command...", height=150)
        r = st.text_area("Response", placeholder="Enter expected response...", height=150)
        
        if st.form_submit_button("💾 Save Prompt", use_container_width=True):
            if p and q and r:
                supabase.table("prompts").insert({
                    "prompt": p,
                    "query": q,
                    "response": r,
                    "created_by": st.session_state.user_email
                }).execute()
                st.success("✅ Prompt added successfully!")
                st.cache_data.clear()
                st.rerun()
            else:
                st.error("Please fill in all fields")

# Search and filter
col1, col2 = st.columns([3, 1])
with col1:
    search_term = st.text_input("🔍 Search prompts", placeholder="Search by prompt, query, or response...")
with col2:
    sort_order = st.selectbox("Sort by", ["Newest First", "Oldest First"])

# Filter prompts
if search_term:
    prompts = [p for p in prompts if 
               search_term.lower() in p["prompt"].lower() or
               search_term.lower() in p["query"].lower() or
               search_term.lower() in p["response"].lower()]

if sort_order == "Oldest First":
    prompts = list(reversed(prompts))

st.divider()
st.subheader(f"📚 Prompts ({len(prompts)})")

# Display prompts
if not prompts:
    st.info("No prompts found. Add your first prompt above!")
else:
    for idx, item in enumerate(prompts):
        with st.expander(f"{idx + 1}. {item['prompt']}", expanded=False):
            # Display query
            st.markdown("**Query:**")
            st.code(item['query'], language='sql')
            
            # Display response
            st.markdown("**Response:**")
            st.text_area("", value=item['response'], height=150, disabled=True, key=f"resp_{item['id']}")
            
            st.caption(f"Created by: {item.get('created_by', 'Unknown')} | Created: {item.get('created_at', 'N/A')}")
            
            # Actions
            col1, col2, col3, col4 = st.columns([1, 1, 2, 1])
            
            with col1:
                if st.button("👍", key=f"up_{item['id']}", use_container_width=True):
                    supabase.table("ratings").upsert({
                        "prompt_id": item["id"],
                        "user_email": st.session_state.user_email,
                        "rating": "up"
                    }, on_conflict="prompt_id,user_email").execute()
                    st.success("Upvoted!")
            
            with col2:
                if st.button("👎", key=f"down_{item['id']}", use_container_width=True):
                    supabase.table("ratings").upsert({
                        "prompt_id": item["id"],
                        "user_email": st.session_state.user_email,
                        "rating": "down"
                    }, on_conflict="prompt_id,user_email").execute()
                    st.warning("Downvoted!")
            
            with col4:
                if ADMIN and st.button("🗑️ Delete", key=f"del_{item['id']}", use_container_width=True):
                    supabase.table("prompts").delete().eq("id", item["id"]).execute()
                    st.cache_data.clear()
                    st.rerun()
            
            # Notes section
            with st.form(f"note_form_{item['id']}"):
                note = st.text_input("Add a note", key=f"note_input_{item['id']}")
                if st.form_submit_button("💬 Save Note"):
                    if note:
                        supabase.table("notes").insert({
                            "prompt_id": item["id"],
                            "note": note,
                            "created_by": st.session_state.user_email
                        }).execute()
                        st.success("Note added!")
                        st.rerun()
