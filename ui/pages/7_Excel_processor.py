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
    add_message,
    display_tool_calls,
    initialize_workflow_session_state,
    selected_model,
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


async def excel_session_selector(workflow, model_id: str):
    """Enhanced session selector for Excel workflow with database persistence."""
    try:
        # Check if we need to reset the session selector
        reset_selector = st.session_state.get("reset_session_selector", False)
        if reset_selector:
            # Clear the reset flag
            del st.session_state["reset_session_selector"]
            # Clear session data
            if workflow_name in st.session_state:
                if "session_id" in st.session_state[workflow_name]:
                    del st.session_state[workflow_name]["session_id"]
                if "session_name" in st.session_state[workflow_name]:
                    del st.session_state[workflow_name]["session_name"]
                if "session_data" in st.session_state[workflow_name]:
                    del st.session_state[workflow_name]["session_data"]
            # Clean up any old session selector keys
            if "excel_session_selector_reset" in st.session_state:
                del st.session_state["excel_session_selector_reset"]
        
        # List existing sessions
        sessions = workflow.list_sessions(user_id="default_user", limit=20)
        
        if sessions:
            st.sidebar.markdown("**📋 Existing Sessions:**")
            
            # Create session options for selectbox (only existing sessions)
            session_options = ["No session selected"] + [f"{s['session_name']} ({s['status']})" for s in sessions]
            
            # Use a dynamic key to force reset when needed
            selector_key = "excel_session_selector_reset" if reset_selector else "excel_session_selector"
            
            # Set default index to "No session selected" (index 0) when resetting
            default_index = 0 if reset_selector else None
            
            selected_session = st.sidebar.selectbox(
                "Choose a session:",
                options=session_options,
                index=default_index,
                key=selector_key
            )
            
            if selected_session and selected_session != "No session selected":
                # Extract session name from the selected option
                session_name = selected_session.split(" (")[0]
                
                # Load the selected session
                session_data = workflow.get_session_by_name(session_name)
                if session_data:
                    # Update session state
                    st.session_state[workflow_name]["session_id"] = session_data['session_id']
                    st.session_state[workflow_name]["session_name"] = session_data['session_name']
                    st.session_state[workflow_name]["session_data"] = session_data
                    
                    # Populate form fields with session data
                    st.session_state["niche_input"] = session_data['niche']
                    st.session_state["chunk_size_selector"] = str(session_data['chunk_size'])
                    
                    # Set a flag to indicate session is loaded (for file uploader)
                    st.session_state["session_loaded"] = True
                    st.session_state["session_file_path"] = session_data['file_path']
                    st.session_state["session_original_filename"] = session_data['original_filename']
                    
                    # Show session details
                    st.sidebar.markdown(f"**📊 Session Details:**")
                    st.sidebar.markdown(f"• **File:** {session_data['original_filename']}")
                    st.sidebar.markdown(f"• **Niche:** {session_data['niche']}")
                    st.sidebar.markdown(f"• **Chunk Size:** {session_data['chunk_size']}")
                    st.sidebar.markdown(f"• **Status:** {session_data['status']}")
                    st.sidebar.markdown(f"• **Keywords:** {session_data['total_keywords']}")
                    
                    # Show results file if available
                    if session_data['results_file_path'] and os.path.exists(session_data['results_file_path']):
                        file_size = os.path.getsize(session_data['results_file_path']) / 1024  # KB
                        st.sidebar.markdown(f"• **Results:** {file_size:.1f} KB")
                        
                        # Download button
                        with open(session_data['results_file_path'], "rb") as file:
                            st.sidebar.download_button(
                                label="📥 Download Results",
                                data=file.read(),
                                file_name=f"processed_keywords_{session_data['session_id']}.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                            )
        else:
            st.sidebar.markdown("**📋 No existing sessions found.**")
            st.sidebar.markdown("*Upload a file and click 'Analyze Keywords' to create your first session.*")
            
    except Exception as e:
        st.sidebar.error(f"Error loading sessions: {str(e)}")


async def header():
    st.markdown("<h1 class='heading'>Excel Processor</h1>", unsafe_allow_html=True)
    st.markdown(
        "<p class='subheading'>Upload an Excel file with keywords and analyze them for SEO value.</p>",
        unsafe_allow_html=True,
    )


async def sidebar(workflow: Workflow):
    """Display sidebar with session management and settings configuration."""
    st.sidebar.markdown("### 📊 Session Management")

    # Model selector
    model_id = await selected_model()

    # Session selector with enhanced session management
    if workflow is not None:
        # Ensure model selection applies to the current workflow instance
        try:
            if hasattr(workflow, 'set_model'):
                workflow.set_model(model_id)
        except Exception:
            pass
        
        # Enhanced session selector for Excel workflow
        await excel_session_selector(workflow, model_id)

    # Session info (simplified since details are shown in session selector)
    if workflow_name in st.session_state and "session_name" in st.session_state[workflow_name]:
        session_name = st.session_state[workflow_name]["session_name"]
        if session_name:
            st.sidebar.markdown(f"**Current Session:** {session_name}")

    # New session button
    if st.sidebar.button("✨ New Session"):
        await initialize_workflow_session_state(workflow_name)
        
        # Clear UI widget states by resetting their session state keys
        if "file_uploader" in st.session_state:
            del st.session_state["file_uploader"]
        if "niche_input" in st.session_state:
            st.session_state.niche_input = ""  # Reset to default
        if "chunk_size_selector" in st.session_state:
            st.session_state.chunk_size_selector = "75"  # Reset to default
        
        # Clear session loaded flags
        if "session_loaded" in st.session_state:
            del st.session_state["session_loaded"]
        if "session_file_path" in st.session_state:
            del st.session_state["session_file_path"]
        if "session_original_filename" in st.session_state:
            del st.session_state["session_original_filename"]
        
        # Set a flag to reset session selector on next render
        st.session_state["reset_session_selector"] = True

        st.rerun()

    # Settings Configuration Section
    st.sidebar.markdown("---")
    st.sidebar.markdown("### ⚙️ AI Instructions Settings")
    
    # Import the settings manager
    from workflows.settings_manager import WorkflowSettingsManager
    
    # Get current instructions
    current_instructions = WorkflowSettingsManager.get_setting(
        workflow_name="excel_processor",
        setting_key="agent_instructions"
    )
    
    # If no custom instructions exist, get the default
    if current_instructions is None:
        from workflows.excel_workflow import ExcelProcessor
        temp_workflow = ExcelProcessor()
        current_instructions = temp_workflow._get_default_instructions()
    
    # Instructions editor
    st.sidebar.markdown("**🤖 AI Agent Instructions**")
    st.sidebar.markdown("*Customize how the AI analyzes keywords*")
    
    # Use a text area for editing instructions
    edited_instructions = st.sidebar.text_area(
        "Instructions",
        value=current_instructions,
        height=300,
        help="Customize the AI agent instructions. Use {niche} as a placeholder for the niche/topic."
    )
    
    # Save button
    col1, col2 = st.sidebar.columns(2)
    
    with col1:
        if st.button("💾 Save Instructions", type="primary"):
            try:
                success = WorkflowSettingsManager.save_setting(
                    workflow_name="excel_processor",
                    setting_key="agent_instructions",
                    setting_value=edited_instructions,
                    description="Custom AI agent instructions for Excel keyword analysis"
                )
                if success:
                    st.sidebar.success("✅ Instructions saved successfully!")
                else:
                    st.sidebar.error("❌ Failed to save instructions")
            except Exception as e:
                st.sidebar.error(f"❌ Error saving instructions: {str(e)}")
    
    with col2:
        if st.button("🔄 Reset to Default"):
            try:
                from workflows.excel_workflow import ExcelProcessor
                temp_workflow = ExcelProcessor()
                default_instructions = temp_workflow._get_default_instructions()
                
                success = WorkflowSettingsManager.save_setting(
                    workflow_name="excel_processor",
                    setting_key="agent_instructions",
                    setting_value=default_instructions,
                    description="Default AI agent instructions for Excel keyword analysis"
                )
                if success:
                    st.sidebar.success("✅ Reset to default instructions!")
                    st.rerun()
                else:
                    st.sidebar.error("❌ Failed to reset instructions")
            except Exception as e:
                st.sidebar.error(f"❌ Error resetting instructions: {str(e)}")
    
    # Instructions info
    st.sidebar.markdown("---")
    st.sidebar.markdown("**📝 Instructions Guide:**")
    st.sidebar.markdown("""
    - Use `{niche}` as a placeholder for the niche/topic
    - Changes take effect immediately
    """)


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
            # Don't set session_id here - it will be set when creating/loading sessions
            st.session_state[workflow_name]["workflow"] = workflow
            logger.info("Workflow created successfully")
        except Exception as e:
            logger.error(f"Error creating workflow: {e}")
            st.error(f"Error creating workflow: {e}")
            return
    else:
        workflow = st.session_state[workflow_name]["workflow"]

    ####################################################################
    # Initialize session state (no need to load from old system)
    ####################################################################
    # The new session management system handles sessions differently
    # We don't need to call workflow.load_session() anymore
    if "session_id" not in st.session_state[workflow_name]:
        st.session_state[workflow_name]["session_id"] = None
    if "session_name" not in st.session_state[workflow_name]:
        st.session_state[workflow_name]["session_name"] = None
    if "session_data" not in st.session_state[workflow_name]:
        st.session_state[workflow_name]["session_data"] = None

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

    # Check if a session is loaded
    session_loaded = st.session_state.get("session_loaded", False)
    
    if session_loaded:
        # Show loaded session file info
        session_file_path = st.session_state.get("session_file_path", "")
        session_original_filename = st.session_state.get("session_original_filename", "")
        
        if session_file_path and os.path.exists(session_file_path):
            st.info(f"📋 **Session File Loaded:** {session_original_filename}")
            
            # Show file info
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("File Name", session_original_filename)
            with col2:
                file_size = os.path.getsize(session_file_path) / 1024  # KB
                st.metric("File Size", f"{file_size:.1f} KB")
            with col3:
                st.metric("File Type", "Excel File")
            
            # Allow user to upload a new file if needed
            st.markdown("*💡 You can upload a new file to replace the session file.*")
    
    # File upload with better UX
    uploaded_file = st.file_uploader(
        "Choose an Excel file (.xlsx, .xls)",
        type=['xlsx', 'xls'],
        help="Upload an Excel file containing keywords to analyze",
        key="file_uploader"
    )

    if uploaded_file is not None:
        # Show file info for newly uploaded file
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("File Name", uploaded_file.name)
        with col2:
            st.metric("File Size", f"{len(uploaded_file.getvalue()) / 1024:.1f} KB")
        with col3:
            st.metric("File Type", uploaded_file.type)

        # Clear session loaded flag when new file is uploaded
        if "session_loaded" in st.session_state:
            del st.session_state["session_loaded"]

    ####################################################################
    # Configuration Section
    ####################################################################
    st.markdown("### ⚙️ Configuration")

    col1, col2 = st.columns(2)

    with col1:
        niche = st.text_input(
            "🎯 Niche/Topic",
            help="The niche or topic for keyword analysis (e.g., 'health', 'finance', 'technology')",
            key="niche_input"
        )

    with col2:
        chunk_size = st.selectbox(
            "📊 Chunk Size",
            options=["50","75", "100", "150", "200", "500"],
            help="Number of rows to process at once",
            key="chunk_size_selector"
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
                # Generate session name
                from workflows.excel_session_manager import ExcelSessionManager
                session_manager = ExcelSessionManager()
                session_name = session_manager.generate_session_name(uploaded_file.name, niche)
                
                # Add user message to chat
                await add_message(workflow_name, "user", f"Processing Excel file: {uploaded_file.name}")

                # Display the uploaded file info
                with st.chat_message("user"):
                    st.markdown(f"**Uploaded File:** {uploaded_file.name}")
                    st.markdown(f"**File Size:** {len(uploaded_file.getvalue()) / 1024:.1f} KB")
                    st.markdown(f"**Niche:** {niche}")
                    st.markdown(f"**Chunk Size:** {chunk_size}")
                    st.markdown(f"**Session Name:** {session_name}")

                # Process the file
                with st.chat_message("assistant"):
                    # Create container for real-time response
                    response_container = st.empty()
                    response = ""
                    
                    # Show initial loading message
                    response_container.markdown("🤖 **AI is analyzing your keywords...**")
                    
                    try:
                        # Get the current model ID from session state (already selected in sidebar)
                        selected_model_key = st.session_state.get("model_selector", "openai/o4-mini")
                        # Map the selected key to the actual model ID
                        model_options = {
                            "openai/o4-mini": "openai/o4-mini",
                            "o3-mini": "o3-mini",
                            "openai/gpt-5-mini": "openai/gpt-5-mini",
                            "openai/gpt-5-nano": "openai/gpt-5-nano",
                            "z-ai/glm-4.5": "z-ai/glm-4.5",
                            "z-ai/glm-4.5-air": "z-ai/glm-4.5-air",
                            "qwen/qwen3-235b-a22b-thinking-2507": "qwen/qwen3-235b-a22b-thinking-2507",
                        }
                        current_model_id = model_options.get(selected_model_key, "openai/o4-mini")
                        
                        # Run the workflow with enhanced session management
                        run_response = workflow.run_workflow(
                            file_path=temp_file_path,
                            niche=niche,
                            chunk_size=chunk_size,
                            session_name=session_name,
                            original_filename=uploaded_file.name,
                            user_id="default_user",
                            model_id=current_model_id
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
                        
                        # Refresh session data to get updated results file path
                        try:
                            if session_name:
                                updated_session_data = workflow.get_session_by_name(session_name)
                                if updated_session_data:
                                    st.session_state[workflow_name]["session_data"] = updated_session_data
                                    logger.info("Session data refreshed with results file path")
                        except Exception as e:
                            logger.warning(f"Could not refresh session data: {e}")

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
    if workflow_name in st.session_state and "session_name" in st.session_state[workflow_name]:
        session_name = st.session_state[workflow_name]["session_name"]
        session_id = st.session_state[workflow_name].get("session_id", "")
        session_data = st.session_state[workflow_name].get("session_data", {})
        
        if session_name:
            # Check if results are available
            has_results = False
            if session_data and session_data.get("results_file_path"):
                has_results = os.path.exists(session_data["results_file_path"])
            elif session_id:
                # Check manually
                potential_results_file = f"tmp/session_keywords_{session_id}.xlsx"
                has_results = os.path.exists(potential_results_file)
            
            status_icon = "✅" if has_results else "⏳"
            status_text = "Results Ready" if has_results else "Processing"
            
            st.info(f"📊 **Current Session:** {session_name} (ID: {session_id[:8]}...) {status_icon} {status_text}")

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
    # Check for results in session data or look for files manually
    results_file_path = None
    session_data = None
    
    if workflow_name in st.session_state and "session_data" in st.session_state[workflow_name]:
        session_data = st.session_state[workflow_name]["session_data"]
        if session_data and session_data.get("results_file_path"):
            results_file_path = session_data["results_file_path"]
    
    # If no results file path in session data, try to find it manually
    if not results_file_path and session_data and session_data.get("session_id"):
        potential_results_file = f"tmp/session_keywords_{session_data['session_id']}.xlsx"
        if os.path.exists(potential_results_file):
            results_file_path = potential_results_file
            # Update session data with the found file
            if session_data:
                session_data["results_file_path"] = results_file_path
                st.session_state[workflow_name]["session_data"] = session_data
    
    if results_file_path and os.path.exists(results_file_path):
            st.markdown("### 📊 Results Summary")

            try:
                import pandas as pd
                df = pd.read_excel(session_data["results_file_path"])

                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Keywords", len(df))
                with col2:
                    st.metric("File Size", f"{os.path.getsize(session_data['results_file_path']) / 1024:.1f} KB")
                with col3:
                    st.metric("Session", session_data["session_name"][:20] + "..." if len(session_data["session_name"]) > 20 else session_data["session_name"])

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
    # Use the same results file path logic as above
    if results_file_path and os.path.exists(results_file_path):
            st.markdown("### 📥 Download Results")

            col1, col2, col3 = st.columns(3)

            with col1:
                with open(session_data["results_file_path"], "rb") as file:
                    st.download_button(
                        label="📊 Download Excel Results",
                        data=file.read(),
                        file_name=f"processed_keywords_{session_data['session_id']}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )

            with col2:
                if st.button("🔄 Refresh Session", use_container_width=True):
                    try:
                        if session_data.get("session_name"):
                            updated_session_data = workflow.get_session_by_name(session_data["session_name"])
                            if updated_session_data:
                                st.session_state[workflow_name]["session_data"] = updated_session_data
                                st.success("Session data refreshed!")
                                st.rerun()
                    except Exception as e:
                        st.error(f"Error refreshing session: {e}")

            with col3:
                if st.button("🗑️ Clear Results", use_container_width=True):
                    try:
                        os.remove(session_data["results_file_path"])
                        # Update session status
                        workflow.update_session_status("pending", results_file_path=None)
                        st.success("Results cleared!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error clearing results: {e}")


async def main():
    # Only initialize if not already present
    if workflow_name not in st.session_state:
        await initialize_workflow_session_state(workflow_name)

    # Initialize widget states if they are not already set
    if "chunk_size_selector" not in st.session_state:
        st.session_state.chunk_size_selector = "75"  # Default value
    if "niche_input" not in st.session_state:
        st.session_state.niche_input = ""  # Default value

    await header()
    await body()


if __name__ == "__main__":
    if check_password():
        asyncio.run(main())
