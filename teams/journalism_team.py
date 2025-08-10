import os
from textwrap import dedent
from typing import Optional

from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.models.openrouter import OpenRouter
from agno.storage.postgres import PostgresStorage
from agno.team.team import Team
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.tools.tavily import TavilyTools
from agno.utils.log import logger
from rich.pretty import pprint
# from agno.tools.newspaper4k import Newspaper4kTools  # Uncomment if available

from db.session import db_url
from teams.settings import team_settings

def print_team_metrics(team: Team, run_title: str = "Team Run"):
    """Print aggregated team leader metrics after every response."""
    print("\n" + "="*80)
    print(f"📊 {run_title} - AGGREGATED TEAM LEADER METRICS")
    print("="*80)
    
    if hasattr(team, 'run_response') and team.run_response:
        print("\n🔍 Team Leader Run Metrics:")
        pprint(team.run_response.metrics)
        
        if hasattr(team, 'session_metrics') and team.session_metrics:
            print("\n📈 Team Leader Session Metrics:")
            pprint(team.session_metrics)
        
        if hasattr(team, 'full_team_session_metrics') and team.full_team_session_metrics:
            print("\n🌐 Full Team Session Metrics (including all members):")
            pprint(team.full_team_session_metrics)
        
        # Print individual member metrics if available
        if hasattr(team.run_response, 'member_responses') and team.run_response.member_responses:
            print("\n👥 Individual Team Member Metrics:")
            for i, member_response in enumerate(team.run_response.member_responses, 1):
                print(f"\n--- Member {i} Metrics ---")
                if hasattr(member_response, 'metrics'):
                    pprint(member_response.metrics)
                else:
                    print("No metrics available for this member")
    else:
        print("⚠️  No run response available yet. Run the team first to see metrics.")
    
    print("="*80 + "\n")

def print_current_metrics(team: Team):
    """Print current metrics for the team (can be called manually)."""
    print_team_metrics(team, "Current Team Status")

def print_detailed_metrics(team: Team):
    """Print detailed metrics breakdown including per-message and per-tool metrics."""
    print("\n" + "="*80)
    print("🔍 DETAILED METRICS BREAKDOWN")
    print("="*80)
    
    if hasattr(team, 'run_response') and team.run_response:
        # Print per-message metrics
        if hasattr(team.run_response, 'messages') and team.run_response.messages:
            print("\n📝 Per-Message Metrics:")
            for i, message in enumerate(team.run_response.messages, 1):
                if message.role == "assistant":
                    print(f"\n--- Message {i} ---")
                    if hasattr(message, 'content') and message.content:
                        print(f"Content: {message.content[:100]}...")
                    if hasattr(message, 'tool_calls') and message.tool_calls:
                        print(f"Tool calls: {len(message.tool_calls)}")
                    if hasattr(message, 'metrics') and message.metrics:
                        pprint(message.metrics)
        
        # Print per-tool execution metrics
        if hasattr(team.run_response, 'tools') and team.run_response.tools:
            print("\n🛠️  Per-Tool Execution Metrics:")
            for i, tool_exec in enumerate(team.run_response.tools, 1):
                print(f"\n--- Tool Execution {i} ---")
                if hasattr(tool_exec, 'metrics') and tool_exec.metrics:
                    pprint(tool_exec.metrics)
                else:
                    print("No metrics available for this tool execution")
    
    print("="*80 + "\n")

# --- Research Planner Agent ---
research_planner = Agent(
    name="Research Planner",
    agent_id="research-planner",
    role="Breaks research queries into structured subtopics and assigns relevant sources",
    model=OpenAIChat(id="gpt-5-mini"),
    tools=[DuckDuckGoTools()],
    add_datetime_to_instructions=True,
    instructions=dedent("""
        - Use the duckduckgo tool to search the web for the most relevant information
        - Decompose research queries into well-structured subtopics covering all key aspects.
        - Ensure logical flow and coverage of historical, current, and future perspectives.
        - Identify and recommend the most credible sources for each subtopic.
        - Prioritize primary research, expert opinions, and authoritative publications.
        - Generate a detailed research roadmap specifying:
          1. Subtopics with clear focus areas.
          2. Recommended sources (websites, papers, reports).
          3. Suggested research methodologies (quantitative, qualitative, case studies).
    """),
    markdown=True,
)

# --- Research Agent ---
research_agent = Agent(
    name="Research Agent",
    agent_id="research-agent",
    model=OpenAIChat(id="gpt-5-mini"),
    tools=[TavilyTools(api_key="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")],
    add_datetime_to_instructions=True,
    description="An expert researcher conducting deep web searches and verifying sources.",
    instructions=dedent("""
        - Go through the research plan
        - Perform relevant web searches based on the planned topics and resources
        - Prioritize recent and authoritative sources.
        - Identify key stakeholders and perspectives
        - Use the tavily tool to search the web for the most relevant information
        - Search with the query "latest news on {topic}"
        - Search with the query "latest research on {topic}"
        - Search with the query "latest reports on {topic}"
        - Search with the query "latest articles on {topic}"
        - Search with the query "latest news on {topic}"
        - Search with the query "latest research on {topic}"
        - Search with the query "latest reports on {topic}"
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
    model=OpenAIChat(id="moonshotai/kimi-k2:free",base_url="https://openrouter.ai/api/v1", api_key="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"),
    add_datetime_to_instructions=True,
    description="A data analyst identifying trends, evaluating viewpoints, and spotting inconsistencies.",
    instructions=dedent("""
        - Analyze collected research for patterns, trends, and conflicting viewpoints.
        - Evaluate the credibility of sources and filter out misinformation.
        - Summarize findings with statistical and contextual backing.
    """),
    expected_output=dedent("""A critical analysis report in detail with all the required citations and sources in a proper format"""),
    markdown=True,
)

# --- Writing Agent ---
writing_agent = Agent(
    name="Writing Agent",
    agent_id="writing-agent",
    model=OpenAIChat(id="gpt-5-mini"),
    add_datetime_to_instructions=True,
    description="A professional journalist specializing in NYT-style reporting.",
    instructions=dedent("""
        - Write a compelling, well-structured article based on the analysis.
        - Maintain journalistic integrity, objectivity, and balance.
        - Use clear, engaging language and provide necessary background.
    """),
    markdown=True,
    show_tool_calls=True,
)

# --- Editor Agent ---
editor_agent = Agent(
    name="Editor Agent",
    agent_id="editor-agent",
model=OpenAIChat(id="moonshotai/kimi-k2:free",base_url="https://openrouter.ai/api/v1", api_key="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"),
        add_datetime_to_instructions=True,
    description="An editorial assistant verifying accuracy, coherence, and readability.",
    instructions=dedent("""
        Check the article generated
        - Verify all facts, statistics, and quotes based on the research analysis report.
        - Ensure smooth narrative flow and logical structure.
        - Check grammar, clarity, and engagement level.
        - Highlight any areas needing further verification or revision.
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
    #model_id = "gpt-5-mini"

    try:
        return Team(
            name="AI Journalism Team",
            team_id="journalism-team",
            mode="coordinate",
            model=OpenAIChat(id="moonshotai/kimi-k2:free",base_url="https://openrouter.ai/api/v1", api_key="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"),
    
            members=[
                research_planner,
                research_agent,
                analysis_agent,
                writing_agent,
                editor_agent,
            ],
            description="A multi-agent journalism team conducting investigative reporting collaboratively.",
            instructions=dedent("""
                You are responsible for executing a structured research workflow.
                
                Follow this exact sequence:
                1. **Research Planner**: First, use the research-planner to break down the query into structured subtopics and identify relevant sources.
                2. **Research Agent**: Then, use the research-agent to conduct web searches based on the research plan and gather information.
                3. **Analysis Agent**: Next, use the analysis-agent to analyze the collected research for patterns, trends, and credibility.
                4. **Writing Agent**: Then, use the writing-agent to write a compelling, well-structured article based on the analysis.
                5. **Editor Agent**: Finally, use the editor-agent to verify accuracy, coherence, and readability of the final article.
                
                - Ensure that the output from one agent flows into the next.
                - Each agent should build upon the work of the previous agent.
                - Finally, produce a well-researched, structured final report based on the output from the editor_agent with proper citations.
            """),
            success_criteria="A comprehensive, well-researched, and professionally written article with proper citations and editorial review.",
            enable_agentic_context=True,
            share_member_interactions=True,
            #show_members_responses=True,
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
        
        # Add metrics printing functionality
        original_run = team.run
        
        def run_with_metrics(*args, **kwargs):
            """Wrapper to automatically print metrics after every team run."""
            try:
                # Run the team
                result = original_run(*args, **kwargs)
                
                # Print metrics after the run
                print_team_metrics(team, "Journalism Team Run")
                
                return result
            except Exception as e:
                logger.error(f"Error in team run: {e}")
                # Still try to print metrics if available
                if hasattr(team, 'run_response') and team.run_response:
                    print_team_metrics(team, "Journalism Team Run (Error Recovery)")
                raise
        
        # Replace the run method with our metrics-enabled version
        team.run = run_with_metrics
        
        return team
    except Exception as e:
        logger.error(f"Error creating journalism team: {e}")
        raise

def get_journalism_team_with_metrics(
    model_id: Optional[str] = None,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    debug_mode: bool = True,
):
    """Get journalism team with automatic metrics printing enabled."""
    return get_journalism_team(model_id, user_id, session_id, debug_mode)
