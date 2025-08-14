import asyncio
import os
import tempfile

import nest_asyncio
import streamlit as st
from agno.tools.streamlit.components import check_password
from agno.utils.log import logger
from agno.workflow import Workflow

from ui.css import CUSTOM_CSS
from ui.utils import (
    about_agno,
    add_message,
    display_tool_calls,
    initialize_workflow_session_state,
    selected_model,
    session_selector_workflow,
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


async def sidebar(workflow: Workflow):
    """Display sidebar with session management using the new session_selector_workflow."""
    st.sidebar.markdown("### 📊 Session Management")

    # Model selector
    model_id = await selected_model()

    # Session selector
    if workflow is not None and hasattr(workflow, 'storage') and workflow.storage is not None:
        await session_selector_workflow(workflow_name, workflow, get_excel_processor, "default_user", model_id)

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

    # Clear session button (just clears UI state, not backend)
    if st.sidebar.button("🗑️ Clear Current Session"):
        if workflow_name in st.session_state:
            st.session_state[workflow_name] = {}
        st.rerun()


async def body() -> None:
    ####################################################################
    # Initialize Workflow
    ####################################################################
    workflow: Workflow
    if (
        workflow_name not in st.session_state
        or st.session_state[workflow_name]["workflow"] is None
    ):
        logger.info("---*--- Creating New Workflow Session ---*---")
        try:
            workflow = get_excel_processor()
            # Set session_id before loading session
            workflow.set_session_id()
            st.session_state[workflow_name]["workflow"] = workflow
            logger.info(f"Workflow created with session_id: {workflow.session_id}")
        except Exception as e:
            logger.error(f"Error creating workflow: {e}")
            st.error(f"Error creating workflow: {e}")
            return
    else:
        workflow = st.session_state[workflow_name]["workflow"]

    ####################################################################
    # Load Workflow Session from the database
    ####################################################################
    try:
        st.session_state[workflow_name]["session_id"] = workflow.load_session()
        logger.info(f"Session loaded with ID: {st.session_state[workflow_name]['session_id']}")
    except Exception as e:
        logger.error(f"Error loading session: {e}")
        st.warning("Could not create Workflow session, is the database running?")
        return

    ####################################################################
    # Initialize messages if not present
    ####################################################################
    if "messages" not in st.session_state[workflow_name]:
        st.session_state[workflow_name]["messages"] = []


    ####################################################################
    # Call sidebar with the initialized workflow
    ####################################################################
    if workflow is not None:
        await sidebar(workflow)
    else:
        st.error("Workflow initialization failed")
        return

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

        # File info displayed above

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
                    # Create container for real-time response
                    response_container = st.empty()
                    response = ""
                    
                    # Show initial loading message
                    response_container.markdown("🤖 **AI is analyzing your keywords...**")
                    
                    try:
                        # Run the workflow and stream the response
                        run_response = workflow.run_workflow(
                            file_path=temp_file_path,
                            niche=niche,
                            chunk_size=chunk_size
                        )

                        for resp_chunk in run_response:
                            # Display response in real-time
                            if resp_chunk.content is not None:
                                response += resp_chunk.content
                                response_container.markdown(response)

                        # Add the final response to the messages (but don't display again)
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

    # Display all messages in chat format (except the most recent assistant message which is shown in real-time)
    messages = st.session_state[workflow_name]["messages"]
    if messages:
        # Skip the last assistant message if it's the most recent one (to avoid duplication with real-time display)
        messages_to_display = messages[:-1] if messages and messages[-1]["role"] == "assistant" else messages
        
        for message in messages_to_display:
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
    await header()
    await body()
    await about_agno()


if __name__ == "__main__":
    if check_password():
        asyncio.run(main())
