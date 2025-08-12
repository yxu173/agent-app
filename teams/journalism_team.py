from textwrap import dedent
from typing import Optional

from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.models.google import Gemini
from agno.storage.postgres import PostgresStorage
from agno.team.team import Team
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.tools.tavily import TavilyTools
from agno.utils.log import logger

from db.session import db_url
from teams.settings import team_settings

# --- Research Planner Agent ---
research_planner = Agent(
    name="Research Planner",
    agent_id="research-planner",
    role="Breaks research queries into structured subtopics and assigns relevant sources",
    model=Gemini(id="gemini-2.5-pro", api_key=team_settings.google_api_key),
    tools=[DuckDuckGoTools()],
    add_datetime_to_instructions=True,
    instructions=dedent("""
        - Use the duckduckgo tool to search the web for the most relevant, up-to-date information.
        - Break down the research query into clear, actionable subtopics.
        - For each subtopic, recommend the best sources and research methods.
        - Output a structured research plan for the next agent to follow.
    """),
    markdown=True,
)

# --- Research Agent ---
research_agent = Agent(
    name="Research Agent",
    agent_id="research-agent",
    model=Gemini(id="gemini-2.5-pro", api_key=team_settings.google_api_key),
    tools=[TavilyTools(api_key=team_settings.tavily_api_key), DuckDuckGoTools()],
    add_datetime_to_instructions=True,
    description="An expert researcher conducting deep web searches and verifying sources.",
    instructions=dedent("""
        - Read the research plan from the previous agent.
        - For each subtopic, perform targeted web searches using the tavily tool first.
        - If tavily fails, fall back to duckduckgo for web searches.
        - Summarize key findings, cite all sources, and highlight any gaps or uncertainties.
        - If no relevant data is found, explicitly state: 'No relevant data found for this subtopic, but here is a summary of what was attempted.'
        - If both tools fail, provide a detailed explanation of the errors and what was attempted.
        - Output a research summary for the analysis agent. Always return a summary, even if no data is found or tools fail.
        - Never fail silently - always provide some form of output to continue the workflow.
    """),
    expected_output=dedent("""
        # Research Summary Report
        
        ## Topic: {Research Topic}
        
        ### Key Findings
        - **Finding 1:** {Detailed explanation with supporting data}
        - **Finding 2:** {Detailed explanation with supporting data}
        - **Finding 3:** {Detailed explanation with supporting data}
        
        ### Source-Based Insights
        #### Source 1: {Source Name / URL}
        - **Summary:** {Concise summary of key points}
        - **Relevant Data:** {Key statistics, dates, or figures}
        - **Notable Quotes:** {Direct citations from experts, if available}
        
        #### Source 2: {Source Name / URL}
        - **Summary:** {Concise summary of key points}
        - **Relevant Data:** {Key statistics, dates, or figures}
        - **Notable Quotes:** {Direct citations from experts, if available}
        
        (...repeat for all sources...)
        
        ### Overall Trends & Patterns
        - **Consensus among sources:** {Common viewpoints and recurring themes}
        - **Diverging Opinions:** {Conflicting perspectives and debates}
        - **Emerging Trends:** {New insights, innovations, or potential shifts in the field}
        
        ### Citations & References
        - [{Source 1 Name}]({URL})
        - [{Source 2 Name}]({URL})
        - (...list all sources with links...)
        
        ### Tool Status & Fallbacks
        - **Primary Tool (Tavily):** {Status - Success/Failed with explanation}
        - **Fallback Tool (DuckDuckGo):** {Status - Used/Not needed}
        - **Research Methodology:** {Explanation of how research was conducted}
        
        ---
        Research conducted by AI Investigative Journalist
        Compiled on: {current_date} at {current_time}
    """),
    markdown=True,
    show_tool_calls=True,
)

# --- Analysis Agent ---
analysis_agent = Agent(
    name="Analysis Agent",
    agent_id="analysis-agent",
    model=OpenAIChat(id="openai/gpt-oss-120b",base_url="https://openrouter.ai/api/v1", api_key=team_settings.openrouter_api_key),
    add_datetime_to_instructions=True,
    description="A data analyst identifying trends, evaluating viewpoints, and spotting inconsistencies.",
    instructions=dedent("""
        - Read the research summary from the previous agent.
        - Analyze findings for patterns, trends, and credibility.
        - Identify conflicting viewpoints and filter out unreliable information.
        - Output a concise analysis report for the writing agent.
    """),
    expected_output=dedent("""A critical analysis report in detail with all the required citations and sources in a proper format"""),
    markdown=True,
)

# --- Writing Agent ---
writing_agent = Agent(
    name="Writing Agent",
    agent_id="writing-agent",
    model=OpenAIChat(id="moonshotai/kimi-k2",base_url="https://openrouter.ai/api/v1", api_key=team_settings.openrouter_api_key),
    add_datetime_to_instructions=True,
    description="A professional journalist specializing in NYT-style reporting.",
    instructions=dedent("""
        - Read the analysis report from the previous agent.
        - Write a clear, engaging article based on the analysis.
        - Ensure journalistic integrity, objectivity, and proper background.
        - Output a draft article for the editor agent.
    """),
    markdown=True,
    show_tool_calls=True,
)

# --- Editor Agent ---
editor_agent = Agent(
    name="Editor Agent",
    agent_id="editor-agent",
    model=Gemini(id="gemini-2.5-pro", api_key=team_settings.google_api_key),
        add_datetime_to_instructions=True,
    description="An editorial assistant verifying accuracy, coherence, and readability.",
    instructions=dedent("""
        - Read the draft article from the previous agent.
        - Verify facts, coherence, and readability.
        - Suggest improvements and highlight any issues.
        - Output the final, edited article with all citations.
    """),
    expected_output=dedent("""
    The same report but with editing instructions in brackets wherever its required
    It will be like each paragraph then editing instructions and suggestion for improvement then next para next set of instruction like that
    -Also maintain the citations
    """),
    markdown=True,
)

# --- Journalism/Research Team ---
def get_journalism_team(
    model_id: Optional[str] = None,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    debug_mode: bool = True,
):
    try:
        team = Team(
            name="AI Journalism Team",
            team_id="journalism-team",
            mode="coordinate",
            model=OpenAIChat(id="gpt-5-mini"),
    
            members=[
                research_planner,
                research_agent,
                analysis_agent,
                writing_agent,
                editor_agent,
            ],
            description="A multi-agent journalism team conducting investigative reporting collaboratively.",
            instructions=dedent("""
IMPORTANT: For every user query, you must always call all five agents in order, one after the other, for every user query, no matter what. Do not stop after any agent except the Editor Agent.

1. Transfer the task to the Research Planner and wait for their output. After completion, print: "Completed step 1, now calling Research Agent."
2. Take the Research Planner's output and transfer it to the Research Agent. Wait for their output. After completion, print: "Completed step 2, now calling Analysis Agent."
3. Take the Research Agent's output and transfer it to the Analysis Agent. Wait for their output. After completion, print: "Completed step 3, now calling Writing Agent."
4. Take the Analysis Agent's output and transfer it to the Writing Agent. Wait for their output. After completion, print: "Completed step 4, now calling Editor Agent."
5. Take the Writing Agent's output and transfer it to the Editor Agent. Wait for their output. After completion, print: "Completed step 5, returning final result."
6. Only after the Editor Agent has completed, return the final result to the user.

**Rules:**
- You must use the `transfer_task_to_member` tool for each step, and never skip a member.
- Always pass the previous member's output as the input to the next member.
- Do not stop after the first agent, or after any agent except the Editor Agent; always proceed through all agents in order.
- Do not attempt to answer the user query yourself.
- Do not summarize or modify the outputs between steps; just pass them along.
- If an agent provides an error message or indicates failure, still pass that output to the next agent - they should handle it gracefully.
- After each agent completes, print a log line: "Completed step X, now calling [next agent]."
- You must always call all five agents in order, one after the other, for every user query, no matter what.
- If an agent fails to provide any output at all, use a default message like "Agent [Name] encountered an error but workflow continues" and proceed to the next agent.
"""),
            success_criteria="A comprehensive, well-researched, and professionally written article with proper citations and editorial review.",
            add_datetime_to_instructions=True,
            markdown=True,
            enable_team_history=True,
            num_of_interactions_from_history=5,
            expected_output=dedent("""
                # {Compelling Headline} 📰

                ## Executive Summary
                {Concise overview of key findings and significance}

                ## Background & Context
                {Historical context and importance}
                {Current landscape overview}

                ## Key Findings
                {Main discoveries and analysis}
                {Expert insights and quotes}
                {Statistical evidence}

                ## Impact Analysis
                {Current implications}
                {Stakeholder perspectives}
                {Industry/societal effects}

                ## Future Outlook
                {Emerging trends}
                {Expert predictions}
                {Potential challenges and opportunities}

                ## Expert Insights
                {Notable quotes and analysis from industry leaders}
                {Contrasting viewpoints}

                ## Sources & Methodology
                {List of primary sources  with the links}
                {Research methodology overview}

                ---
                Compiled by AI Investigative Journalist
                Published: {current_date}
                Last Updated: {current_time}
            """),
            storage=PostgresStorage(
                table_name="journalism_team",
                db_url=db_url,
                mode="team",
                auto_upgrade_schema=True,
            ),
            debug_mode=debug_mode,
            session_id=session_id,
            user_id=user_id,
        )
        
        return team
    except Exception as e:
        logger.error(f"Error creating journalism team: {e}")
        raise
