from textwrap import dedent
from typing import Optional
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.models.google import Gemini
from agno.storage.sqlite import SqliteStorage
from agno.team.team import Team
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.tools.tavily import TavilyTools
from agno.utils.log import logger
from agno.tools.crawl4ai import Crawl4aiTools
from agno.tools.newspaper4k import Newspaper4kTools
from db.session import db_url
from teams.settings import team_settings

# --- Query Classification Agent ---
query_classifier = Agent(
    name="Query Classifier",
    agent_id="query-classifier",
    role="Classifies queries and determines appropriate research depth",
    model=OpenAIChat(
        id="z-ai/glm-4-32b",
        base_url="https://openrouter.ai/api/v1",
        api_key=team_settings.openrouter_api_key,
        max_completion_tokens=512,
    ),
    add_datetime_to_instructions=True,
    instructions=dedent("""
        CRITICAL: You are the first agent in the pipeline. Your job is to classify the query and set the research depth.
        
        **Classification Rules:**
        1. SIMPLE QUERIES (return "SIMPLE"): Greetings (hi, hello, how are you), basic personal questions, general pleasantries
        2. MODERATE QUERIES (return "MODERATE"): Single-topic questions, basic fact-checking, straightforward research
        3. DEEP QUERIES (return "DEEP"): Complex multi-faceted topics, investigative research, comparative analysis
        
        **Output Format:**
        CLASSIFICATION: [SIMPLE/MODERATE/DEEP]
        REASONING: [Brief explanation]
        RESEARCH_SCOPE: [If MODERATE/DEEP, provide 2-4 key subtopics to focus on]
        
        **Examples:**
        - "Hi, how are you?" → SIMPLE
        - "What is climate change?" → MODERATE 
        - "Analyze the economic impact of AI on healthcare industry over the next decade" → DEEP
    """),
    markdown=True,
)

# --- Research Planner Agent ---
research_planner = Agent(
    name="Research Planner",
    agent_id="research-planner",
    role="Creates efficient, focused research plans based on query classification",
    model=OpenAIChat(
        id="openai/gpt-5-mini",
        base_url="https://openrouter.ai/api/v1",
        api_key=team_settings.openrouter_api_key,
        max_completion_tokens=1024,
    ),
    tools=[DuckDuckGoTools(), Crawl4aiTools(), Newspaper4kTools()],
    add_datetime_to_instructions=True,
    instructions=dedent("""
        **Objective:** Your primary role is to create a highly efficient and targeted research plan based on the query classification provided. Your plan must be optimized for token usage and research quality.

        **Core Responsibilities:**
        1.  **Analyze Classification:** Carefully review the query classification (MODERATE/DEEP) and reasoning from the Query Classifier.
        2.  **Develop Strategy:** Formulate a research strategy that is appropriate for the classification.
        3.  **Produce Plan:** Output a structured research plan for the Research Agent to follow.

        **Workflow by Query Type:**

        **For MODERATE Queries:**
        -   **Scope:** Strictly limit the research to 1-2 core subtopics. Do not go broader.
        -   **Sources:** Prioritize recent (last 2 years), high-authority sources (e.g., major news outlets, official reports, academic papers).
        -   **Strategy:** Develop 2-3 precise search queries. The goal is to get high-quality information quickly.

        **For DEEP Queries:**
        -   **Scope:** Deconstruct the main topic into 3-5 distinct, strategic subtopics. Ensure comprehensive coverage of the user's request.
        -   **Sources:** Plan to use a diverse range of sources, including academic journals, news articles, expert opinions, and official documentation.
        -   **Strategy:** Design a multi-stage research process. For each subtopic, create 2-4 targeted search queries. Consider how subtopics might relate to each other.

        **Mandatory Output Structure:**
        ## Research Plan
        **Query Classification:** [MODERATE/DEEP]
        
        ### 1. Priority Subtopic: [Title of Subtopic 1]
        -   **Rationale:** [Briefly explain why this subtopic is important]
        -   **Search Queries:**
            -   `[Search query 1]`
            -   `[Search query 2]`
        -   **Source Targets:** [e.g., Academic journals, news reports]

        ### 2. Priority Subtopic: [Title of Subtopic 2]
        -   **Rationale:** [Briefly explain why this subtopic is important]
        -   **Search Queries:**
            -   `[Search query 1]`
            -   `[Search query 2]`
        
        *(Add more subtopics as needed for DEEP queries)*

        ---
        **Execution Guidelines:**
        -   **Date Context:** Be mindful of the current date: {current_date}. Prioritize recent information unless historical context is required.
        -   **Source Quality:** Focus on authoritative domains (.edu, .gov, respected news organizations).
        -   **Avoid Redundancy:** Explicitly instruct the next agent to avoid exploring sources that seem to offer overlapping information.
    """),
    markdown=True,
)

# --- Research Agent ---
research_agent = Agent(
    name="Research Agent",
    agent_id="research-agent",
    model=OpenAIChat(
        id="qwen/qwen3-235b-a22b-thinking-2507",
        base_url="https://openrouter.ai/api/v1",
        api_key=team_settings.openrouter_api_key,
    ),
    tools=[TavilyTools(api_key=team_settings.tavily_api_key), DuckDuckGoTools(), Crawl4aiTools(), Newspaper4kTools()],
    add_datetime_to_instructions=True,
    description="Intelligent researcher with adaptive depth based on query complexity",
    instructions=dedent("""
        You are a **research agent** designed to conduct **in-depth, methodical investigations** into user questions. Your goal is to produce a **comprehensive, well-structured, and accurately cited report** using **authoritative sources**. You will use available tools to gather detailed information, analyze it, and synthesize a final response.

### **Tool Use Rules (Strictly Enforced)**

1. **Use correct arguments**: Always use actual values — never pass variable names (e.g., use "Paris" not {city}).
2. **Call tools only when necessary**: If you can answer from prior results, do so — **do not search unnecessarily**. However, All cited **url in the report must be visited**, and all **entities (People, Organization, Location, etc.) mentioned on the report must be searched/visited**. 
3. **Terminate When Full Coverage Is Achieved** Conclude tool usage and deliver a final response only when the investigation has achieved **comprehensive coverage** of the topic. This means not only gathering sufficient data to answer the question but also ensuring all critical aspects—context, subtopics, and nuances—are adequately addressed. Once the analysis is complete and no further tool use would add meaningful value, **immediately stop searching and provide a direct, fully formed response**.
4. **Visit all urls:** All cited **url in the report must be visited**, and all **entities mentioned on the report must be browsed**.
5. **Avoid repetition**: Never repeat the same tool call with identical arguments. If you detect a cycle (e.g., repeating the same search), **stop and answer based on available data**.
6. **Track progress**: Treat each tool call as a step in a plan. After each result, ask: "Did you have full coverage?" and "What is the next step?"
7. **Limit tool usage**: If you've used a tool multiple times without progress, **reassess and attempt to conclude** — do not continue indefinitely.
8. **Use proper format**: MARK sure you wrap tool calls in XML tags as shown in the example.

### Output Format Requirements

At the end, respond **only** with a **self-contained markdown report**. Do not include tool calls or internal reasoning in the final output.

Example structure:
```markdown
# [Clear Title]

## Overview
...

## Key Findings
- Finding 1 [1]
- Finding 2 [2]

## Detailed Analysis
...

## References
[1] https://example.com/source1  
[2] https://example.com/study2  
...

Goal

Answer with depth, precision, and scholarly rigor. You will be rewarded for:

Thoroughness in research
Use of high-quality sources when available (.gov, .edu, peer-reviewed, reputable media)
Clear, structured reporting
Efficient path to completion without redundancy

Now Begin! If you solve the task correctly, you will receive a reward of $1,000,000.

        """),
   markdown=True,
)

# --- Streamlined Analysis Agent ---
analysis_agent = Agent(
    name="Analysis Agent",
    agent_id="analysis-agent",
    model=OpenAIChat(
        id="openai/gpt-oss-120b",
        base_url="https://openrouter.ai/api/v1",
        api_key=team_settings.openrouter_api_key,
    ),
    add_datetime_to_instructions=True,
    description="Efficient analyst focusing on high-impact insights and patterns",
    instructions=dedent("""
        **FOCUSED ANALYSIS:** Provide sharp, actionable analysis without redundancy.
        
        **Analysis Framework:**
        1. **Pattern Recognition:** Identify 2-3 key trends or patterns
        2. **Credibility Assessment:** Evaluate source reliability and consensus
        3. **Gap Analysis:** Note missing information or conflicting viewpoints
        4. **Impact Assessment:** Highlight most significant implications
        
        **Quality Filters:**
        - Flag low-credibility sources
        - Identify potential biases
        - Note temporal relevance of findings
        - Highlight expert consensus vs. outlier opinions
    """),
    markdown=True,
)

# --- Efficient Writing Agent ---
writing_agent = Agent(
    name="Writing Agent",
    agent_id="writing-agent",
    model=OpenAIChat(
        id="moonshotai/kimi-k2",
        base_url="https://openrouter.ai/api/v1",
        api_key=team_settings.openrouter_api_key,
    ),
    add_datetime_to_instructions=True,
    description="Professional writer creating engaging, concise content",
    instructions=dedent("""
        **WRITE FOR IMPACT:** Create compelling content that respects the reader's time.
        
        **Writing Strategy:**
        - Start with a strong hook that captures the core finding
        - Structure around 3-5 main points maximum
        - Use active voice and clear, concrete language
        - Include specific examples and data points
        - Maintain journalistic objectivity
        
        **Length Guidelines:**
        - Always prioritize clarity over length
        
        **Engagement Elements:**
        - Compelling headline
        - Strong opening paragraph
        - Smooth transitions between points
        - Concrete examples and specific data
        - Clear conclusion with implications
        - **Sources Section:** Always include a "## Sources" section with properly formatted markdown links: [Source Name](URL)
    """),
    markdown=True,
)

# --- Final Editor Agent ---
editor_agent = Agent(
    name="Editor Agent",
    agent_id="editor-agent",
    model=Gemini(id="gemini-2.5-pro", api_key=team_settings.google_api_key),
    tools=[DuckDuckGoTools(), Crawl4aiTools(), Newspaper4kTools()],
    add_datetime_to_instructions=True,
    description="Efficient editor ensuring quality while maintaining conciseness",
    instructions=dedent("""
        **EFFICIENT EDITING:** Improve quality without adding unnecessary length.
        
        **Editing Priorities:**
        1. **Accuracy:** Verify key facts and claims
        2. **Clarity:** Ensure main points are clear and well-supported
        3. **Flow:** Check logical structure and transitions
        4. **Conciseness:** Remove redundancy and verbose language
        
        **Final Check:**
        - Fact-check major claims against sources
        - Ensure proper citation format with working markdown links: [Source Name](URL)
        - Verify coherent narrative arc
        - Confirm readability and engagement
        - **Source Verification:** Ensure all sources are properly formatted as clickable links
        
        **Output Format:**
        Provide the final, polished article without extensive editorial notes unless critical issues are found.
    """),
    expected_output=dedent("""
        Final edited article with clean formatting and proper citations.
        Include brief editorial note only if significant changes were made.
    """),
    markdown=True,
)

# --- Smart Team Coordinator ---
def get_enova_deep_research_team(
    model_id: Optional[str] = None,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    debug_mode: bool = True,
):
    """
    Optimized Enova Deep Research team with intelligent query handling and token efficiency.
    """
    try:
        team = Team(
            name="Enova Deep Research Team",
            team_id="enova-deep-research-team",
            mode="coordinate",
            model=OpenAIChat(
                id="z-ai/glm-4.5",
                base_url="https://openrouter.ai/api/v1",
                api_key=team_settings.openrouter_api_key,
            ),
            members=[
                query_classifier,
                research_planner,
                research_agent,
                analysis_agent,
                writing_agent,
                editor_agent,
            ],
            description="Enova Deep Research multi-agent team with adaptive depth and token optimization.",
            enable_agentic_context=True,
            share_member_interactions=True,
            show_members_responses=True,
            stream_intermediate_steps=True,
            instructions=dedent("""
**SMART WORKFLOW COORDINATION:**

You are the team coordinator for an intelligent research team. Your job is to orchestrate the workflow efficiently based on query complexity.

**Step 1: Query Classification**
- Always start by transferring to Query Classifier
- Wait for classification result (SIMPLE/MODERATE/DEEP)
- **IMPORTANT:** Start your response with "🎯 QUERY CLASSIFIER ACTIVATED" when transferring

**Step 2: Adaptive Workflow**

**For SIMPLE queries (greetings, basic pleasantries):**
- Respond directly with a friendly, brief answer
- DO NOT proceed through the full pipeline
- Example response: "Hello! I'm an AI research assistant ready to help you with any research questions or analysis needs. What would you like to explore today?"

**For MODERATE queries:**
- Proceed with: Research Planner → Research Agent → Writing Agent → Editor Agent
- Skip Analysis Agent to save tokens on straightforward topics
- **IMPORTANT:** Start each agent transfer with clear markers:
  - "📋 RESEARCH PLANNER ACTIVATED" for Research Planner
  - "🔍 RESEARCH AGENT ACTIVATED" for Research Agent  
  - "✍️ WRITING AGENT ACTIVATED" for Writing Agent
  - "📝 EDITOR AGENT ACTIVATED" for Editor Agent
- Log: "Moderate query detected, using streamlined 4-agent workflow"

**For DEEP queries:**
- Use full pipeline: Research Planner → Research Agent → Analysis Agent → Writing Agent → Editor Agent
- **IMPORTANT:** Start each agent transfer with clear markers:
  - "📋 RESEARCH PLANNER ACTIVATED" for Research Planner
  - "🔍 RESEARCH AGENT ACTIVATED" for Research Agent
  - "🧠 ANALYSIS AGENT ACTIVATED" for Analysis Agent
  - "✍️ WRITING AGENT ACTIVATED" for Writing Agent
  - "📝 EDITOR AGENT ACTIVATED" for Editor Agent
- Log: "Deep query detected, using comprehensive 5-agent workflow"

**Coordination Rules:**
1. Always pass the complete output from each agent to the next
2. Print progress logs: "Step X completed, proceeding to [Next Agent]"
3. If any agent fails, continue workflow with error context
4. Monitor token usage and provide efficiency metrics at the end
5. Ensure each agent has clear context from previous steps

**Agent Transfer Markers:**
- Use the exact activation phrases above to help the UI track agent progress
- These markers should appear at the very beginning of each agent's response
- This enables real-time progress tracking in the user interface
- **CRITICAL:** Always include the activation marker as the first line when transferring to any agent
- **CRITICAL:** Do not include activation markers in the final output - they are for UI tracking only

**Error Handling:**
- Never stop workflow due to single agent failure
- Pass error context to subsequent agents
- Maintain workflow continuity

**Source Requirements:**
- All sources MUST be formatted as working markdown links: [Source Name](URL)
- Include a dedicated "## Sources" section at the end
- Verify all links are properly formatted and functional
- Include at least 5-10 primary sources for MODERATE queries, 10-20 for DEEP queries
"""),
            success_criteria="Deliver high-quality research output efficiently, matching depth to query complexity while optimizing token usage. Ensure all sources are properly formatted as working links.",
            add_datetime_to_instructions=True,
            markdown=True,
            enable_team_history=True,
            num_of_interactions_from_history=3,
            storage=SqliteStorage(
                table_name="enova_deep_research_team",
                db_url=db_url,
                mode="team",
                auto_upgrade_schema=True,
            ),
            debug_mode=debug_mode,
            session_id=session_id,
            user_id=user_id,
            team_session_state= {}
        )
        
        return team
    except Exception as e:
        logger.error(f"Error creating Enova Deep Research team: {e}")
        raise