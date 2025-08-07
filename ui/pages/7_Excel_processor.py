import asyncio
import os
import tempfile

import nest_asyncio
import streamlit as st
from agno.tools.streamlit.components import check_password
from agno.utils.log import logger
from agno.workflow import Workflow

import httpx

API_BASE = "http://host.docker.internal:8000/v1/playground/workflows"
WORKFLOW_ID = "excel-keyword-processor"

async def api_list_sessions():
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{API_BASE}/{WORKFLOW_ID}/sessions")
        resp.raise_for_status()
        return resp.json()

async def api_get_session(session_id):
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{API_BASE}/{WORKFLOW_ID}/sessions/{session_id}")
        resp.raise_for_status()
        return resp.json()

async def api_delete_session(session_id):
    async with httpx.AsyncClient() as client:
        resp = await client.delete(f"{API_BASE}/{WORKFLOW_ID}/sessions/{session_id}")
        resp.raise_for_status()
        return resp.status_code == 204

from ui.css import CUSTOM_CSS
from ui.utils import (
    about_agno,
    add_message,
    display_tool_calls,
    initialize_workflow_session_state,
)
from workflows.excel_workflow import get_excel_processor

nest_asyncio.apply()

st.set_page_config(
    page_title="Excel Processor",
    page_icon=":file_folder:",
    layout="wide",
)
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
workflow_name = "excel_processor"


async def header():
    st.markdown("<h1 class='heading'>Excel Processor</h1>", unsafe_allow_html=True)
    st.markdown(
        "<p class='subheading'>Upload an Excel file with keywords and analyze them for SEO value.</p>",
        unsafe_allow_html=True,
    )


async def get_session_list():
    """Get list of available sessions for this workflow."""
    try:
        sessions = await api_list_sessions()
        # Format for selectbox
        return [
            {"id": s["session_id"], "display_name": s.get("title") or s["session_id"]}
            for s in sessions
        ]
    except Exception as e:
        logger.error(f"Error getting session list: {e}")
        return []


async def sidebar():
    """Display sidebar with session management."""
    st.sidebar.markdown("### 📊 Session Management")

    # Session naming (display only, no direct storage update)
    if workflow_name in st.session_state and "session_id" in st.session_state[workflow_name]:
        session_id = st.session_state[workflow_name]["session_id"]
        if session_id:
            session_name = st.sidebar.text_input(
                "📝 Session Name",
                value=f"Excel Analysis - {session_id[:8]}",
                help="Give your session a descriptive name"
            )

    # Session list
    sessions = await get_session_list()
    if sessions:
        selected_session = st.sidebar.selectbox(
            "Choose Session",
            options=[s["display_name"] for s in sessions],
            help="Select a previous session to load"
        )
        selected_session_id = next(s["id"] for s in sessions if s["display_name"] == selected_session)

        if st.sidebar.button("🔄 Load Session"):
            if workflow_name not in st.session_state:
                st.session_state[workflow_name] = {}
            st.session_state[workflow_name]["session_id"] = selected_session_id
            st.session_state[workflow_name]["workflow"] = None
            st.session_state[workflow_name]["messages"] = []  
            st.rerun()

        # Add delete session button
        if st.sidebar.button("🗑️ Delete Selected Session", key="delete_selected_session"):
            try:
                await api_delete_session(selected_session_id)
                # If the deleted session is the current one, clear all related state
                if (
                    workflow_name in st.session_state and
                    st.session_state[workflow_name].get("session_id") == selected_session_id
                ):
                    st.session_state[workflow_name]["session_id"] = None
                    st.session_state[workflow_name]["workflow"] = None
                    st.session_state[workflow_name]["messages"] = []
                    st.session_state[workflow_name]["just_deleted"] = True
                st.sidebar.success("Session deleted!")
                st.rerun()
            except Exception as e:
                st.sidebar.error(f"Error deleting session: {e}")
    else:
        st.sidebar.info("No previous sessions found")

    # Clear session button (just clears UI state, not backend)
    if st.sidebar.button("🗑️ Clear Current Session"):
        if workflow_name in st.session_state:
            st.session_state[workflow_name] = {}
        st.rerun()

    # Session info
    if workflow_name in st.session_state and "session_id" in st.session_state[workflow_name]:
        session_id = st.session_state[workflow_name]["session_id"]
        if session_id:
            st.sidebar.markdown(f"**Current Session:** {session_id}")

            # Check if there are results for this session
            session_excel_file = f"tmp/session_keywords_{session_id}.xlsx"
            if os.path.exists(session_excel_file):
                file_size = os.path.getsize(session_excel_file) / 1024  # KB
                st.sidebar.markdown(f"**Results File:** {file_size:.1f} KB")

                # Download button in sidebar
                with open(session_excel_file, "rb") as file:
                    st.sidebar.download_button(
                        label="📥 Download Results",
                        data=file.read(),
                        file_name=f"processed_keywords_{session_id}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )


async def body() -> None:
    ####################################################################
    # Initialize Workflow
    ####################################################################
    workflow: Workflow
    # If just deleted, show message and do not create a new session
    if st.session_state[workflow_name].get("just_deleted"):
        st.info("Session deleted. Please select or create a new session.")
        st.session_state[workflow_name]["just_deleted"] = False
        return

    if st.session_state[workflow_name].get("session_id") is None:
        logger.info("---*--- Creating New Workflow Session ---*---")
        workflow = get_excel_processor()
        try:
            workflow.set_session_id()
            session_id = workflow.load_session()
            st.session_state[workflow_name]["workflow"] = workflow
            st.session_state[workflow_name]["session_id"] = session_id
            st.session_state[workflow_name]["messages"] = []
        except Exception:
            st.warning("Could not create Workflow session, is the database running?")
            return
    else:
        logger.info("---*--- Loading Existing Workflow Session ---*---")
        workflow = get_excel_processor()
        workflow.session_id = st.session_state[workflow_name]["session_id"]
        st.session_state[workflow_name]["workflow"] = workflow
        if hasattr(workflow, 'session_state') and "messages" in workflow.session_state:
            st.session_state[workflow_name]["messages"] = workflow.session_state["messages"]
        else:
            st.session_state[workflow_name]["messages"] = []

    ####################################################################
    # File Upload Section
    ####################################################################
    st.markdown("### 📁 Upload Excel File")

    # File upload with better UX
    uploaded_file = st.file_uploader(
        "Choose an Excel file (.xlsx, .xls)",
        type=['xlsx', 'xls'],
        help="Upload an Excel file containing keywords to analyze"
    )

    if uploaded_file is not None:
        # Show file info
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("File Name", uploaded_file.name)
        with col2:
            st.metric("File Size", f"{len(uploaded_file.getvalue()) / 1024:.1f} KB")
        with col3:
            st.metric("File Type", uploaded_file.type)

        # Show file preview (first few lines)
        try:
            import pandas as pd
            with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
                tmp_file.write(uploaded_file.getvalue())
                tmp_file_path = tmp_file.name

            try:
                df = pd.read_excel(tmp_file_path, nrows=5)
                st.markdown("#### 📋 File Preview (First 5 rows)")
                st.dataframe(df, use_container_width=True)
            except Exception as e:
                st.warning(f"Could not preview file: {e}")
            finally:
                try:
                    os.unlink(tmp_file_path)
                except:
                    pass
        except Exception as e:
            st.warning(f"Error reading file: {e}")

    ####################################################################
    # Configuration Section
    ####################################################################
    st.markdown("### ⚙️ Configuration")

    col1, col2 = st.columns(2)

    with col1:
        niche = st.text_input(
            "🎯 Niche/Topic",
            value="technology",
            help="The niche or topic for keyword analysis (e.g., 'health', 'finance', 'technology')"
        )

    with col2:
        chunk_size = st.selectbox(
            "📊 Chunk Size",
            options=["50", "100", "200", "500"],
            index=1,
            help="Number of rows to process at once"
        )

    ####################################################################
    # Process Button
    ####################################################################
    if uploaded_file is not None:
        st.markdown("### 🚀 Process File")

        # Show processing options
        with st.expander("⚙️ Processing Options", expanded=False):
            st.markdown(f"**Niche:** {niche}")
            st.markdown(f"**Chunk Size:** {chunk_size} rows")
            st.markdown(f"**File:** {uploaded_file.name}")

        if st.button("🔍 Analyze Keywords", type="primary", use_container_width=True):
            # Save uploaded file to temporary location
            with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
                tmp_file.write(uploaded_file.getvalue())
                temp_file_path = tmp_file.name

            try:
                # Add user message to chat
                await add_message(workflow_name, "user", f"Processing Excel file: {uploaded_file.name}")

                # Display the uploaded file info
                with st.chat_message("user"):
                    st.markdown(f"**Uploaded File:** {uploaded_file.name}")
                    st.markdown(f"**File Size:** {len(uploaded_file.getvalue()) / 1024:.1f} KB")
                    st.markdown(f"**Niche:** {niche}")
                    st.markdown(f"**Chunk Size:** {chunk_size}")

                # Process the file
                with st.chat_message("assistant"):
                    # Create container for tool calls
                    tool_calls_container = st.empty()
                    resp_container = st.empty()

                    with st.spinner(":thinking_face: Analyzing keywords..."):
                        response = ""
                        try:
                            # Run the workflow and stream the response
                            run_response = workflow.run_workflow(
                                file_path=temp_file_path,
                                niche=niche,
                                chunk_size=chunk_size
                            )

                            for resp_chunk in run_response:
                                # Display tool calls if available
                                if hasattr(resp_chunk, 'tools') and resp_chunk.tools and len(resp_chunk.tools) > 0:
                                    display_tool_calls(tool_calls_container, resp_chunk.tools)

                                # Display response
                                if resp_chunk.content is not None:
                                    response += resp_chunk.content
                                    resp_container.markdown(response)

                            # Add the final response to the messages
                            if workflow.run_response is not None and hasattr(workflow.run_response, 'tools'):
                                await add_message(workflow_name, "assistant", response, workflow.run_response.tools)
                            else:
                                await add_message(workflow_name, "assistant", response)

                            # Show success message
                            st.success("✅ Processing completed successfully!")

                        except Exception as e:
                            logger.error(f"Error during workflow run: {str(e)}", exc_info=True)
                            error_message = f"Sorry, I encountered an error: {str(e)}"
                            await add_message(workflow_name, "assistant", error_message)
                            st.error(error_message)
                        finally:
                            # Clean up temporary file
                            try:
                                os.unlink(temp_file_path)
                            except:
                                pass

            except Exception as e:
                logger.error(f"Error processing file: {str(e)}", exc_info=True)
                st.error(f"Error processing file: {str(e)}")

    ####################################################################
    # Display workflow messages
    ####################################################################
    st.markdown("### 💬 Chat History")

    # Show session info if available
    if workflow_name in st.session_state and "session_id" in st.session_state[workflow_name]:
        session_id = st.session_state[workflow_name]["session_id"]
        if session_id:
            st.info(f"📊 **Current Session:** {session_id}")

    # Display all messages in chat format
    messages = st.session_state[workflow_name]["messages"]
    if messages:
        for message in messages:
            if message["role"] in ["user", "assistant"]:
                _content = message["content"]
                if _content is not None:
                    with st.chat_message(message["role"]):
                        # Display tool calls if they exist in the message
                        if "tool_calls" in message and message["tool_calls"]:
                            display_tool_calls(st.empty(), message["tool_calls"])
                        st.markdown(_content)
    else:
        st.info("💬 No messages yet. Upload an Excel file and start processing to see the conversation history.")

    ####################################################################
    # Instructions Section
    ####################################################################
    with st.expander("📋 Instructions"):
        st.markdown("""
        **How to use this Excel Processor:**

        1. **Upload an Excel file** containing keywords in the first column
        2. **Set the niche/topic** for your keywords (e.g., 'health', 'finance', 'technology')
        3. **Choose chunk size** based on your file size (larger files work better with bigger chunks)
        4. **Click 'Analyze Keywords'** to start processing

        **Expected Excel Format:**
        - First column should contain keywords
        - Optional second column for categories
        - Sheet name should be "CATEGORY" (or it will use the first available sheet)

        **What the processor does:**
        - Analyzes keywords for SEO value
        - Identifies valuable keywords for content creation
        - Provides reasons for keyword selection
        - Exports results to a downloadable Excel file
        """)

    ####################################################################
    # Results Summary Section
    ####################################################################
    if workflow_name in st.session_state and "session_id" in st.session_state[workflow_name]:
        session_id = st.session_state[workflow_name]["session_id"]
        if session_id:
            session_excel_file = f"tmp/session_keywords_{session_id}.xlsx"
            if os.path.exists(session_excel_file):
                st.markdown("### 📊 Results Summary")

                try:
                    import pandas as pd
                    df = pd.read_excel(session_excel_file)

                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Total Keywords", len(df))
                    with col2:
                        st.metric("File Size", f"{os.path.getsize(session_excel_file) / 1024:.1f} KB")
                    with col3:
                        st.metric("Session ID", session_id[:8])

                    # Show sample results
                    if len(df) > 0:
                        st.markdown("#### 📋 Sample Results")
                        st.dataframe(df.head(10), use_container_width=True)

                        if len(df) > 10:
                            st.info(f"Showing first 10 of {len(df)} keywords. Download the full file to see all results.")

                except Exception as e:
                    st.warning(f"Could not read results file: {e}")

    ####################################################################
    # Download Section
    ####################################################################
    if workflow_name in st.session_state and "session_id" in st.session_state[workflow_name]:
        session_id = st.session_state[workflow_name]["session_id"]
        if session_id:
            session_excel_file = f"tmp/session_keywords_{session_id}.xlsx"
            if os.path.exists(session_excel_file):
                st.markdown("### 📥 Download Results")

                col1, col2 = st.columns(2)

                with col1:
                    with open(session_excel_file, "rb") as file:
                        st.download_button(
                            label="📊 Download Excel Results",
                            data=file.read(),
                            file_name=f"processed_keywords_{session_id}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            use_container_width=True
                        )

                with col2:
                    if st.button("🗑️ Clear Results", use_container_width=True):
                        try:
                            os.remove(session_excel_file)
                            st.success("Results cleared!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error clearing results: {e}")


async def main():
    # Only initialize if not already present
    if workflow_name not in st.session_state:
        await initialize_workflow_session_state(workflow_name)
    await sidebar()
    await header()
    await body()
    await about_agno()


if __name__ == "__main__":
    if check_password():
        asyncio.run(main())
