import asyncio
import nest_asyncio
import streamlit as st
from agno.team import Team
from agno.tools.streamlit.components import check_password
from agno.utils.log import logger
from markdown_it import MarkdownIt

from teams import get_enova_deep_research_team
from ui.css import CUSTOM_CSS
from ui.utils import (
    add_message,
    display_tool_calls,
    example_inputs,
    initialize_team_session_state,
)

# Apply nest_asyncio to handle nested event loops
nest_asyncio.apply()

st.set_page_config(
    page_title="Enova Deep Research",
    page_icon=":newspaper:",
    layout="wide",
)
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
team_name = "enova_deep_research_team"

async def header():
    st.markdown("<h1 class='heading'>Enova Deep Research Team</h1>", unsafe_allow_html=True)
    st.markdown(
        "<p class='subheading'>A multi-agent research team for deep investigation, analysis, and comprehensive reporting.</p>",
        unsafe_allow_html=True,
    )

async def body() -> None:

    ####################################################################
    # Initialize Team
    ####################################################################
    team: Team
    if team_name not in st.session_state or st.session_state[team_name]["team"] is None:
        logger.info("---*--- Creating Enova Deep Research Team ---*---")
        team = get_enova_deep_research_team()
        st.session_state[team_name] = {"team": team, "session_id": None, "messages": []}
    else:
        team = st.session_state[team_name]["team"]

    ####################################################################
    # Load Team Session from the database
    ####################################################################
    try:
        if st.session_state[team_name]["session_id"] is None:
            st.session_state[team_name]["session_id"] = team.load_session()
    except Exception as e:
        logger.error(f"Could not create Team session: {e}")
        st.warning("Could not create Team session, is the database running?")
        return

    ####################################################################
    # Get user input
    ####################################################################
    if prompt := st.chat_input("🔍 What should we research?"):
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
            # Container for agent workflow steps
            agent_steps_container = st.empty()
            # Layout: main area for final response, side area for per-agent steps
            resp_container = st.empty()
            with st.spinner(":thinking_face: Researching..."):
                md = MarkdownIt()
                # Track final response separately from agent step outputs
                final_response = ""
                # Buffer for SIMPLE flows (no activation markers seen)
                buffered_simple = ""
                # Reset per-run agent sections in session
                st.session_state[team_name]["agent_sections"] = []
                # Internal mapping for activation markers → section titles
                activation_markers = {
                    "🎯 QUERY CLASSIFIER ACTIVATED": "Query Classifier",
                    "📋 RESEARCH PLANNER ACTIVATED": "Research Planner",
                    "🔍 RESEARCH AGENT ACTIVATED": "Research Agent",
                    "🧠 ANALYSIS AGENT ACTIVATED": "Analysis Agent",
                    "✍️ WRITING AGENT ACTIVATED": "Writing Agent",
                    "📝 EDITOR AGENT ACTIVATED": "Editor Agent",
                }
                # Fallback mapping from agent_id to human-readable titles
                id_to_title = {
                    "query-classifier": "Query Classifier",
                    "research-planner": "Research Planner",
                    "research-agent": "Research Agent",
                    "analysis-agent": "Analysis Agent",
                    "writing-agent": "Writing Agent",
                    "editor-agent": "Editor Agent",
                }
                marker_order = list(activation_markers.keys())
                current_section_idx = None
                markers_seen = False

                def render_agent_steps():
                    with agent_steps_container.container():
                        st.markdown("<h4>🤖 Agent Workflow</h4>", unsafe_allow_html=True)
                        for sec in st.session_state[team_name].get("agent_sections", []):
                            if not sec.get("title") or not sec.get("content"):
                                continue

                            with st.expander(f'**{sec["title"]}**'):
                                content_html = md.render(str(sec.get("content", "")))
                                st.markdown(content_html, unsafe_allow_html=True)

                try:
                    # Run the team and stream the response
                    run_response = await team.arun(user_message, stream=True)
                    async for resp_chunk in run_response:
                        # Display tool calls if available
                        if hasattr(resp_chunk, 'tools') and resp_chunk.tools and len(resp_chunk.tools) > 0:
                            display_tool_calls(tool_calls_container, resp_chunk.tools)
                        # Stream member agent events into their respective sections
                        try:
                            # Normalize to a list of event-like items
                            event_items = []
                            if hasattr(resp_chunk, 'events') and resp_chunk.events:
                                event_items.extend(resp_chunk.events)
                            # Also treat the current chunk as an event if it has agent metadata
                            if hasattr(resp_chunk, 'agent_name') or hasattr(resp_chunk, 'agent_id'):
                                event_items.append(resp_chunk)
                            for ev in event_items:
                                agent_name = getattr(ev, 'agent_name', None)
                                agent_id = getattr(ev, 'agent_id', None)
                                event_content = getattr(ev, 'content', None)
                                # Also capture reasoning/think-aloud if present
                                reasoning_extra = ""
                                try:
                                    rc = getattr(ev, 'reasoning_content', None)
                                    th = getattr(ev, 'thinking', None)
                                    if rc:
                                        reasoning_extra += str(rc)
                                    if th:
                                        reasoning_extra += "\n" + str(th)
                                except Exception:
                                    pass
                                if not event_content and not reasoning_extra:
                                    continue
                                # Determine section title from name or id
                                sec_title = None
                                if agent_name:
                                    sec_title = agent_name
                                elif agent_id and agent_id in id_to_title:
                                    sec_title = id_to_title[agent_id]
                                if not sec_title:
                                    continue
                                # Normalize base title
                                if sec_title.endswith(" Agent"):
                                    base_title = sec_title.replace(" Agent", "")
                                else:
                                    base_title = sec_title
                                # Find or create the section index for this agent
                                target_idx = None
                                for i, sec in enumerate(st.session_state[team_name]["agent_sections"]):
                                    if sec.get("title") in {base_title, sec_title}:
                                        target_idx = i
                                        break
                                if target_idx is None:
                                    # Create a new section at the end
                                    st.session_state[team_name]["agent_sections"].append({"title": base_title, "content": ""})
                                    target_idx = len(st.session_state[team_name]["agent_sections"]) - 1
                                # Append streamed content
                                to_append = ""
                                if event_content:
                                    to_append += str(event_content)
                                if reasoning_extra:
                                    to_append += ("\n" if to_append else "") + reasoning_extra
                                st.session_state[team_name]["agent_sections"][target_idx]["content"] += to_append
                            # Re-render agent steps with latest streamed content
                            render_agent_steps()
                        except Exception:
                            pass
                        # Display response
                        if resp_chunk.content is not None:
                            chunk = resp_chunk.content
                            # Parse for one or more activation markers in the chunk
                            processed_pos = 0
                            while True:
                                # Find the next marker occurrence in the remaining text
                                next_marker_pos = None
                                next_marker_key = None
                                for m in marker_order:
                                    pos = chunk.find(m, processed_pos)
                                    if pos != -1 and (next_marker_pos is None or pos < next_marker_pos):
                                        next_marker_pos = pos
                                        next_marker_key = m

                                if next_marker_pos is None:
                                    # No more markers; append remaining text to current section or final response
                                    remaining = chunk[processed_pos:]
                                    if remaining:
                                        if current_section_idx is None:
                                            # Buffer pre-marker content; render later only if no markers ever appear (SIMPLE flow)
                                            buffered_simple += remaining
                                        else:
                                            # Ensure section exists
                                            while len(st.session_state[team_name]["agent_sections"]) <= current_section_idx:
                                                st.session_state[team_name]["agent_sections"].append({"title": "", "content": ""})
                                            st.session_state[team_name]["agent_sections"][current_section_idx]["content"] += remaining
                                            # Mirror Editor Agent output into main response area
                                            current_title = st.session_state[team_name]["agent_sections"][current_section_idx]["title"]
                                            if current_title == "Editor Agent":
                                                final_response += remaining
                                            # Re-render agent steps
                                            render_agent_steps()
                                    break

                                else:
                                    # Append text before the marker to the appropriate target
                                    before = chunk[processed_pos:next_marker_pos]
                                    if before:
                                        if current_section_idx is None:
                                            # Buffer pre-marker content; render later only if no markers ever appear (SIMPLE flow)
                                            buffered_simple += before
                                        else:
                                            while len(st.session_state[team_name]["agent_sections"]) <= current_section_idx:
                                                st.session_state[team_name]["agent_sections"].append({"title": "", "content": ""})
                                            st.session_state[team_name]["agent_sections"][current_section_idx]["content"] += before
                                            # Mirror Editor Agent output into main response area
                                            current_title = st.session_state[team_name]["agent_sections"][current_section_idx]["title"]
                                            if current_title == "Editor Agent":
                                                final_response += before
                                    # Move cursor past the marker text and switch current section
                                    processed_pos = next_marker_pos + len(next_marker_key)
                                    section_title = activation_markers[next_marker_key]
                                    # Find existing section by title; create only if absent
                                    existing_idx = None
                                    for i, sec in enumerate(st.session_state[team_name]["agent_sections"]):
                                        if sec.get("title") == section_title:
                                            existing_idx = i
                                            break
                                    if existing_idx is None:
                                        st.session_state[team_name]["agent_sections"].append({"title": section_title, "content": ""})
                                        current_section_idx = len(st.session_state[team_name]["agent_sections"]) - 1
                                    else:
                                        current_section_idx = existing_idx
                                    markers_seen = True
                                    # Render updated agent steps with the new section header
                                    render_agent_steps()

                    # Post-run enrichment: recursively backfill agent sections from member_responses
                    try:
                        if hasattr(team, "run_response") and team.run_response is not None:
                            def extract_text_from_response(resp) -> str:
                                text = ""
                                try:
                                    base = getattr(resp, "content", None)
                                    if base:
                                        text += str(base)
                                    # Also accumulate any event contents (streamed deltas + final)
                                    events = getattr(resp, "events", None)
                                    if events:
                                        for ev in events:
                                            c = getattr(ev, "content", None)
                                            # Also capture reasoning/think-aloud if present
                                            reasoning_extra = ""
                                            try:
                                                rc = getattr(ev, 'reasoning_content', None)
                                                th = getattr(ev, 'thinking', None)
                                                if rc:
                                                    reasoning_extra += str(rc)
                                                if th:
                                                    reasoning_extra += "\n" + str(th)
                                            except Exception:
                                                pass
                                            if c:
                                                text += str(c)
                                            if reasoning_extra:
                                                text += "\n" + reasoning_extra
                                except Exception:
                                    pass
                                return text

                            def collect_member_contents(responses, out_dict):
                                if not responses:
                                    return
                                for r in responses:
                                    try:
                                        # Agent-level / team-level identifiers
                                        agent_name = getattr(r, "agent_name", None)
                                        agent_id = getattr(r, "agent_id", None)
                                        team_member_name = getattr(r, "team_name", None)
                                        text = extract_text_from_response(r)
                                        if text:
                                            if agent_name:
                                                out_dict[agent_name] = text
                                            if team_member_name:
                                                out_dict[team_member_name] = text
                                            if agent_id:
                                                out_dict[agent_id] = text
                                        nested = getattr(r, "member_responses", None)
                                        if nested:
                                            collect_member_contents(nested, out_dict)
                                    except Exception:
                                        continue

                            name_to_content = {}
                            collect_member_contents(getattr(team.run_response, "member_responses", None), name_to_content)

                            # Map known section titles to collected content
                            for sec in st.session_state[team_name]["agent_sections"]:
                                title = sec.get("title")
                                if not title or sec.get("content"):
                                    continue
                                candidates = {title}
                                if title.endswith(" Agent"):
                                    candidates.add(title.replace(" Agent", ""))
                                else:
                                    candidates.add(f"{title} Agent")
                                # Also consider agent_id fallbacks mapped to this title
                                for aid, human in id_to_title.items():
                                    if human == title:
                                        candidates.add(aid)
                                # Try exact then case-insensitive matches
                                filled = False
                                for key in list(candidates):
                                    if key in name_to_content and name_to_content[key]:
                                        sec["content"] = str(name_to_content[key])
                                        filled = True
                                        break
                                if not filled:
                                    # Case-insensitive fallback
                                    lower_map = {k.lower(): v for k, v in name_to_content.items()}
                                    for key in candidates:
                                        if key.lower() in lower_map and lower_map[key.lower()]:
                                            sec["content"] = str(lower_map[key.lower()])
                                            break

                            # Re-render with backfilled content
                            render_agent_steps()
                    except Exception:
                        pass

                    # Add the response to the messages
                    # SIMPLE fallback: if no markers were ever seen, render buffered content now
                    if not markers_seen and not final_response and buffered_simple:
                        final_response = buffered_simple
                    
                    # Get final response from team object
                    if team.run_response and hasattr(team.run_response, 'content') and team.run_response.content:
                        final_response = team.run_response.content
                    
                    resp_container.markdown(final_response)

                    if team.run_response is not None and hasattr(team.run_response, 'tools'):
                        await add_message(team_name, "assistant", final_response, team.run_response.tools)
                    else:
                        await add_message(team_name, "assistant", final_response)
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
