import asyncio
import nest_asyncio
import streamlit as st
from agno.team import Team
from agno.tools.streamlit.components import check_password
from agno.utils.log import logger

from teams.journalism_team import get_journalism_team_with_metrics
from ui.css import CUSTOM_CSS
from ui.utils import (
    about_agno,
    add_message,
    display_tool_calls,
    example_inputs,
    initialize_team_session_state,
    selected_model,
    export_chat_history,
)
from datetime import datetime

# Apply nest_asyncio to handle nested event loops
nest_asyncio.apply()

st.set_page_config(
    page_title="Journalism Team",
    page_icon=":newspaper:",
    layout="wide",
)
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
team_name = "journalism_team"

def create_session_entry(session_id: str, session_type: str = "conversation") -> dict:
    """Create a standardized session entry with metadata."""
    return {
        "session_id": session_id,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "message_count": 0,
        "type": session_type,
        "status": "active"
    }

async def header():
    st.markdown("<h1 class='heading'>AI Journalism Team</h1>", unsafe_allow_html=True)
    st.markdown(
        "<p class='subheading'>A multi-agent journalism team for deep research, analysis, and article writing.</p>",
        unsafe_allow_html=True,
    )

async def body() -> None:

    ####################################################################
    # Initialize Team
    ####################################################################
    team: Team
    if team_name not in st.session_state or st.session_state[team_name]["team"] is None:
        logger.info("---*--- Creating Journalism Team ---*---")
        team = get_journalism_team_with_metrics()
        st.session_state[team_name] = {"team": team, "session_id": None, "messages": [], "conversation_sessions": []}
    else:
        team = st.session_state[team_name]["team"]

    ####################################################################
    # Initialize conversation sessions if not exists
    ####################################################################
    if "conversation_sessions" not in st.session_state[team_name]:
        st.session_state[team_name]["conversation_sessions"] = []
    
    # Create new session for each conversation
    current_session_id = None
    if st.session_state[team_name]["conversation_sessions"]:
        current_session_id = st.session_state[team_name]["conversation_sessions"][-1]["session_id"]
    
    ####################################################################
    # Load Team Session from the database
    ####################################################################
    try:
        if current_session_id:
            # Load existing session
            st.session_state[team_name]["session_id"] = team.load_session(session_id=current_session_id)
        else:
            # Create new session
            st.session_state[team_name]["session_id"] = team.load_session()
            # Add to conversation sessions
            st.session_state[team_name]["conversation_sessions"].append(
                create_session_entry(st.session_state[team_name]["session_id"], "initial")
            )
    except Exception as e:
        logger.error(f"Could not create Team session: {e}")
        st.warning("Could not create Team session, is the database running?")
        return

    ####################################################################
    # Add export chat history button in the sidebar
    ####################################################################
    with st.sidebar:
        st.markdown("#### 🛠️ Utilities")
        if st.button(":file_folder: Export Chat History", key="export_chat_journalism_team"):
            try:
                # Create new session specifically for export
                export_session_id = team.load_session()
                
                # Temporarily switch to the export session
                original_session_id = st.session_state[team_name]["session_id"]
                st.session_state[team_name]["session_id"] = export_session_id
                
                # Export from the new export session
                fn = f"{team_name}_export_{export_session_id}.md"
                export_data = export_chat_history(team_name)
                
                st.download_button(
                    label="Download Chat History as Markdown",
                    data=export_data,
                    file_name=fn,
                    mime="text/markdown",
                )
                
                # Add export session to conversation sessions
                st.session_state[team_name]["conversation_sessions"].append(
                    create_session_entry(export_session_id, "export")
                )
                
                # Restore the original session
                st.session_state[team_name]["session_id"] = original_session_id
                
                st.success(f"Export session created and used: {export_session_id}")
                
            except Exception as e:
                logger.error(f"Error exporting chat history: {e}")
                st.error("Failed to export chat history")
                # Try to restore original session on error
                if 'original_session_id' in locals():
                    st.session_state[team_name]["session_id"] = original_session_id
        
        # Add metrics display section
        st.markdown("#### 📊 Metrics")
        if st.button(":chart_with_upwards_trend: Show Current Metrics", key="show_metrics_journalism_team"):
            if hasattr(team, 'run_response') and team.run_response:
                st.json(team.run_response.metrics)
            else:
                st.info("No metrics available yet. Run the team first!")
        
        if st.button(":bar_chart: Show Session Metrics", key="show_session_metrics_journalism_team"):
            if hasattr(team, 'session_metrics') and team.session_metrics:
                st.json(team.session_metrics)
            else:
                st.info("No session metrics available yet.")
        
        # Add export session management section
        st.markdown("#### 📁 Export Session Management")
        st.info("💡 Export operations create dedicated sessions for clean separation")
        
        # Add session management section
        st.markdown("#### 🔄 Session Management")
        if st.button("🆕 New Conversation Session", key="new_session_journalism_team"):
            try:
                # Create new session
                new_session_id = team.load_session()
                st.session_state[team_name]["session_id"] = new_session_id
                st.session_state[team_name]["messages"] = []  # Clear messages for new session
                
                # Add to conversation sessions
                st.session_state[team_name]["conversation_sessions"].append(
                    create_session_entry(new_session_id, "conversation")
                )
                
                st.success(f"New session created: {new_session_id}")
                st.rerun()
            except Exception as e:
                logger.error(f"Error creating new session: {e}")
                st.error(f"Failed to create new session: {str(e)}")
        
        # Show current session info
        if st.session_state[team_name]["session_id"]:
            st.info(f"Current Session: {st.session_state[team_name]['session_id']}")
            st.info(f"Total Sessions: {len(st.session_state[team_name]['conversation_sessions'])}")
        
        # Display session history
        if st.session_state[team_name]["conversation_sessions"]:
            st.markdown("#### 📚 Session History")
            
            # Separate export sessions from conversation sessions
            export_sessions = [s for s in st.session_state[team_name]["conversation_sessions"] if s.get("type") == "export"]
            conversation_sessions = [s for s in st.session_state[team_name]["conversation_sessions"] if s.get("type") != "export"]
            
            # Show conversation sessions first
            if conversation_sessions:
                st.markdown("**💬 Conversation Sessions:**")
                for i, session in enumerate(conversation_sessions):
                    session_type = session.get("type", "conversation")
                    session_icon = "💬" if session_type == "message" else "🆕" if session_type == "initial" else "🔄"
                    st.text(f"{session_icon} Session {i+1}: {session['session_id'][:8]}... ({session_type})")
            
            # Show export sessions separately
            if export_sessions:
                st.markdown("**📁 Export Sessions:**")
                for i, session in enumerate(export_sessions):
                    with st.expander(f"📁 Export {i+1}: {session['session_id'][:8]}... (created: {session['created_at']})"):
                        st.text(f"Session ID: {session['session_id']}")
                        st.text(f"Created: {session['created_at']}")
                        st.text(f"Type: {session['type']}")
                        st.text(f"Status: {session['status']}")
                        
                        # Add button to re-export from this session
                        if st.button(f"🔄 Re-export from Session {i+1}", key=f"reexport_{i}"):
                            try:
                                # Switch to the export session
                                original_session_id = st.session_state[team_name]["session_id"]
                                st.session_state[team_name]["session_id"] = session['session_id']
                                
                                # Re-export
                                reexport_fn = f"{team_name}_reexport_{session['session_id']}.md"
                                reexport_data = export_chat_history(team_name)
                                
                                st.download_button(
                                    label=f"Download Re-export from Session {i+1}",
                                    data=reeexport_data,
                                    file_name=reexport_fn,
                                    mime="text/markdown",
                                )
                                
                                # Restore original session
                                st.session_state[team_name]["session_id"] = original_session_id
                                
                                st.success(f"Re-exported from session: {session['session_id'][:8]}...")
                                
                            except Exception as e:
                                logger.error(f"Error re-exporting: {e}")
                                st.error(f"Failed to re-export: {str(e)}")
                                # Try to restore original session on error
                                if 'original_session_id' in locals():
                                    st.session_state[team_name]["session_id"] = original_session_id
            
            # Add clear sessions buttons
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("🗑️ Clear All Sessions", key="clear_sessions_journalism_team"):
                    st.session_state[team_name]["conversation_sessions"] = []
                    st.session_state[team_name]["messages"] = []
                    st.success("All sessions cleared!")
                    st.rerun()
            
            with col2:
                if st.button("📁 Clear Export Sessions", key="clear_export_sessions_journalism_team"):
                    # Keep only non-export sessions
                    st.session_state[team_name]["conversation_sessions"] = [
                        s for s in st.session_state[team_name]["conversation_sessions"] 
                        if s.get("type") != "export"
                    ]
                    st.success("Export sessions cleared!")
                    st.rerun()
            
            # Add session switcher (only for conversation sessions)
            if len(conversation_sessions) > 1:
                st.markdown("#### 🔄 Switch Conversation Session")
                session_options = [f"Session {i+1}: {session['session_id'][:8]}... ({session.get('type', 'conversation')})" 
                                for i, session in enumerate(conversation_sessions)]
                selected_session = st.selectbox("Choose conversation session to load:", session_options, key="session_switcher")
                
                if st.button("📂 Load Selected Session", key="load_session_journalism_team"):
                    try:
                        selected_index = session_options.index(selected_session)
                        selected_session_data = conversation_sessions[selected_index]
                        
                        # Load the selected session
                        st.session_state[team_name]["session_id"] = team.load_session(session_id=selected_session_data["session_id"])
                        st.session_state[team_name]["messages"] = []  # Clear current messages
                        
                        st.success(f"Loaded conversation session: {selected_session_data['session_id'][:8]}...")
                        st.rerun()
                    except Exception as e:
                        logger.error(f"Error loading session: {e}")
                        st.error(f"Failed to load session: {str(e)}")
            
            # Add export session switcher
            if len(export_sessions) > 0:
                st.markdown("#### 📁 Switch Export Session")
                export_session_options = [f"Export {i+1}: {session['session_id'][:8]}... ({session['created_at']})" 
                                        for i, session in enumerate(export_sessions)]
                selected_export_session = st.selectbox("Choose export session to load:", export_session_options, key="export_session_switcher")
                
                if st.button("📂 Load Export Session", key="load_export_session_journalism_team"):
                    try:
                        selected_index = export_session_options.index(selected_export_session)
                        selected_export_session_data = export_sessions[selected_index]
                        
                        # Load the selected export session
                        st.session_state[team_name]["session_id"] = team.load_session(session_id=selected_export_session_data["session_id"])
                        st.session_state[team_name]["messages"] = []  # Clear current messages
                        
                        st.success(f"Loaded export session: {selected_export_session_data['session_id'][:8]}...")
                        st.rerun()
                    except Exception as e:
                        logger.error(f"Error loading export session: {e}")
                        st.error(f"Failed to load export session: {str(e)}")

    ####################################################################
    # Get user input
    ####################################################################
    if prompt := st.chat_input("📰 What should we investigate?"):
        # Create new session for each new message
        try:
            new_message_session_id = team.load_session()
            st.session_state[team_name]["session_id"] = new_message_session_id
            
            # Add to conversation sessions
            st.session_state[team_name]["conversation_sessions"].append(
                create_session_entry(new_message_session_id, "message")
            )
            
            logger.info(f"New message session created: {new_message_session_id}")
            
        except Exception as e:
            logger.error(f"Error creating new message session: {e}")
            st.error(f"Failed to create new session: {str(e)}")
            return
        
        await add_message(team_name, "user", prompt)

    ####################################################################
    # Show example inputs
    ####################################################################
    await example_inputs(team_name)

    ####################################################################
    # Display team messages
    ####################################################################
    for message in st.session_state[team_name]["messages"]:
        if message["role"] in ["user", "assistant"]:
            _content = message["content"]
            if _content is not None:
                with st.chat_message(message["role"]):
                    # Display tool calls if they exist in the message
                    if "tool_calls" in message and message["tool_calls"]:
                        display_tool_calls(st.empty(), message["tool_calls"])
                    st.markdown(_content)

    ####################################################################
    # Generate response for user message
    ####################################################################
    last_message = st.session_state[team_name]["messages"][-1] if st.session_state[team_name]["messages"] else None
    if last_message and last_message.get("role") == "user":
        user_message = last_message["content"]
        logger.info(f"Responding to message: {user_message}")
        with st.chat_message("assistant"):
            # Create container for tool calls
            tool_calls_container = st.empty()
            resp_container = st.empty()
            with st.spinner(":thinking_face: Investigating..."):
                response = ""
                try:
                    # Run the team and stream the response
                    run_response = await team.arun(user_message, stream=True)
                    async for resp_chunk in run_response:
                        # Display tool calls if available
                        if hasattr(resp_chunk, 'tools') and resp_chunk.tools and len(resp_chunk.tools) > 0:
                            display_tool_calls(tool_calls_container, resp_chunk.tools)
                        # Display response
                        if resp_chunk.content is not None:
                            response += resp_chunk.content
                            resp_container.markdown(response)
                    # Add the response to the messages
                    if team.run_response is not None and hasattr(team.run_response, 'tools'):
                        await add_message(team_name, "assistant", response, team.run_response.tools)
                    else:
                        await add_message(team_name, "assistant", response)
                    
                    # Update message count for current session
                    if st.session_state[team_name]["conversation_sessions"]:
                        current_session = st.session_state[team_name]["conversation_sessions"][-1]
                        current_session["message_count"] = len(st.session_state[team_name]["messages"])
                        logger.info(f"Updated session {current_session['session_id']} with {current_session['message_count']} messages")
                except Exception as e:
                    logger.error(f"Error during team run: {str(e)}", exc_info=True)
                    error_message = f"Sorry, I encountered an error: {str(e)}"
                    await add_message(team_name, "assistant", error_message)
                    st.error(error_message)

async def main():
    try:
        await initialize_team_session_state(team_name)
        await header()
        await body()
      #  await about_agno()
    except Exception as e:
        logger.error(f"Error in main: {e}", exc_info=True)
        st.error(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    if check_password():
        try:
            asyncio.run(main())
        except Exception as e:
            logger.error(f"Error running main: {e}", exc_info=True)
            st.error(f"Failed to start application: {str(e)}")
