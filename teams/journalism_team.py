from textwrap import dedent
from typing import Optional
import re

from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.models.google import Gemini
from agno.storage.postgres import PostgresStorage
from agno.team.team import Team
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.tools.tavily import TavilyTools
from agno.utils.log import logger
from agno.tools.crawl4ai import Crawl4aiTools
from agno.tools.newspaper4k import Newspaper4kTools
from db.session import db_url
from teams.settings import team_settings

# --- Query Classification Agent (NEW) ---
query_classifier = Agent(
    name="Query Classifier",
    agent_id="query-classifier",
    role="Classifies queries and determines appropriate research depth",
    model=Gemini(id="gemini-2.5-pro", api_key=team_settings.google_api_key),
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
        ESTIMATED_TOKEN_BUDGET: [LOW/MEDIUM/HIGH based on classification]
        
        **Token Optimization:**
        - SIMPLE: Suggest direct response without full pipeline
        - MODERATE: Recommend focused research on 1-2 subtopics
        - DEEP: Full multi-agent pipeline with comprehensive analysis
        
        **Examples:**
        - "Hi, how are you?" → SIMPLE
        - "What is climate change?" → MODERATE 
        - "Analyze the economic impact of AI on healthcare industry over the next decade" → DEEP
    """),
    markdown=True,
)

# --- Optimized Research Planner Agent ---
research_planner = Agent(
    name="Research Planner",
    agent_id="research-planner",
    role="Creates efficient, focused research plans based on query classification",
    model=OpenAIChat(id="qwen/qwen3-235b-a22b-thinking-2507", base_url="https://openrouter.ai/api/v1", api_key=team_settings.openrouter_api_key),
    tools=[DuckDuckGoTools(), Crawl4aiTools(), Newspaper4kTools()],
    add_datetime_to_instructions=True,
    instructions=dedent("""
        **EFFICIENCY FIRST:** Read the query classification and adapt your research plan accordingly.
        
        **For MODERATE queries:**
        - Focus on 1-2 core subtopics maximum
        - Prioritize recent, authoritative sources
        - Limit search scope to avoid token waste
        
        **For DEEP queries:**
        - Break into 3-5 strategic subtopics
        - Include diverse source types (academic, news, expert opinions)
        - Plan for comprehensive but focused research
        
        **Output Structure:**
        ## Research Plan
        **Query Type:** [From classifier]
        **Priority Subtopics:** [Numbered list, 1-5 max]
        **Search Strategy:** [Keyword combinations for each subtopic]
        **Source Targets:** [Types of sources to prioritize]
        **Token Budget:** [Estimated tokens needed per subtopic]
        
        **Quality Filters:**
        - Prioritize sources from last 2 years unless historical context needed
        - Focus on authoritative domains (.edu, .gov, major publications)
        - Skip redundant or low-quality sources
    """),
    markdown=True,
)

# --- Enhanced Research Agent ---
research_agent = Agent(
    name="Research Agent",
    agent_id="research-agent",
    model=Gemini(id="gemini-2.5-pro", api_key=team_settings.google_api_key),
    tools=[TavilyTools(api_key=team_settings.tavily_api_key), DuckDuckGoTools(), Crawl4aiTools(), Newspaper4kTools()],
    add_datetime_to_instructions=True,
    description="Intelligent researcher with adaptive depth based on query complexity",
    instructions=dedent("""
        **ADAPTIVE RESEARCH:** Follow the research plan and query classification strictly.
        
        **Token Optimization Rules:**
        1. For MODERATE queries: Maximum 3 targeted searches, focus on quality over quantity
        2. For DEEP queries: Up to 6-8 strategic searches across subtopics
        3. Always start with Tavily (more comprehensive), fallback to DuckDuckGo if needed
        4. Skip duplicate or low-value sources immediately
        
        **Research Methodology:**
        - Use specific, targeted search terms from the research plan
        - Extract only relevant information, ignore tangential content
        - Summarize findings concisely but comprehensively
        - Track source credibility and recency
        
        **Error Handling:**
        - If tools fail, provide clear error explanation
        - Continue research with available tools
        - Never fail silently - always return actionable output
        
        **Output Efficiency:**
        - Lead with executive summary (2-3 sentences)
        - Organize findings by subtopic from research plan
        - Include only high-impact quotes and statistics
        - Maintain source links but avoid excessive citation bloat
    """),
    expected_output=dedent("""
        # Research Summary: {Topic}
        
        **Executive Summary:** {2-3 sentence overview of key findings}
        
        ## Key Findings by Subtopic
        
        ### {Subtopic 1}
        - **Core Finding:** {Most important insight}
        - **Supporting Data:** {Key statistics or evidence}
        - **Source Quality:** {Assessment of source reliability}
        
        ### {Subtopic 2}
        - **Core Finding:** {Most important insight}
        - **Supporting Data:** {Key statistics or evidence}
        - **Source Quality:** {Assessment of source reliability}
        
        ## Source Summary
        **Primary Sources:** [{Source 1}]({URL}), [{Source 2}]({URL})
        **Research Depth:** {MODERATE/DEEP based on classification}
        **Search Success Rate:** {X/Y successful searches}
        
        ## Research Gaps
        {Any limitations or areas needing follow-up}
    """),
    markdown=True,
    show_tool_calls=True,
)

# --- Streamlined Analysis Agent ---
analysis_agent = Agent(
    name="Analysis Agent",
    agent_id="analysis-agent",
    model=OpenAIChat(id="openai/gpt-oss-120b",base_url="https://openrouter.ai/api/v1", api_key=team_settings.openrouter_api_key),
    add_datetime_to_instructions=True,
    description="Efficient analyst focusing on high-impact insights and patterns",
    instructions=dedent("""
        **FOCUSED ANALYSIS:** Provide sharp, actionable analysis without redundancy.
        
        **Analysis Framework:**
        1. **Pattern Recognition:** Identify 2-3 key trends or patterns
        2. **Credibility Assessment:** Evaluate source reliability and consensus
        3. **Gap Analysis:** Note missing information or conflicting viewpoints
        4. **Impact Assessment:** Highlight most significant implications
        
        **Token Efficiency:**
        - Lead with core insights (3-4 bullet points max)
        - Focus on novel or surprising findings
        - Avoid restating research findings verbatim
        - Synthesize rather than summarize
        
        **Quality Filters:**
        - Flag low-credibility sources
        - Identify potential biases
        - Note temporal relevance of findings
        - Highlight expert consensus vs. outlier opinions
    """),
    expected_output=dedent("""
        # Analysis Report: {Topic}
        
        ## Core Insights
        1. **Primary Pattern:** {Most significant trend or finding}
        2. **Key Implication:** {Most important consequence or meaning}
        3. **Notable Gap:** {Missing information or conflicting data}
        
        ## Credibility Assessment
        - **Strong Sources:** {Number and brief description}
        - **Weak Sources:** {Any sources to treat cautiously}
        - **Expert Consensus:** {Level of agreement among authorities}
        
        ## Strategic Implications
        {2-3 sentences on broader significance}
        
        ## Recommendation for Writing
        **Focus Areas:** {Top 2-3 points for final article}
        **Narrative Arc:** {Suggested structure for compelling story}
    """),
    markdown=True,
)

# --- Efficient Writing Agent ---
writing_agent = Agent(
    name="Writing Agent",
    agent_id="writing-agent",
    model=OpenAIChat(id="moonshotai/kimi-k2",base_url="https://openrouter.ai/api/v1", api_key=team_settings.openrouter_api_key),
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
        - MODERATE topics: 300-500 words
        - DEEP topics: 600-1000 words
        - Always prioritize clarity over length
        
        **Engagement Elements:**
        - Compelling headline
        - Strong opening paragraph
        - Smooth transitions between points
        - Concrete examples and specific data
        - Clear conclusion with implications
    """),
    markdown=True,
)

# --- Final Editor Agent ---
editor_agent = Agent(
    name="Editor Agent",
    agent_id="editor-agent",
    model=Gemini(id="gemini-2.5-pro", api_key=team_settings.google_api_key),
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
        - Ensure proper citation format
        - Verify coherent narrative arc
        - Confirm readability and engagement
        
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
def get_journalism_team(
    model_id: Optional[str] = None,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    debug_mode: bool = True,
):
    """
    Optimized journalism team with intelligent query handling and token efficiency.
    """
    try:
        team = Team(
            name="Smart AI Research Team",
            team_id="smart-journalism-team",
            mode="coordinate",
            model=OpenAIChat(id="z-ai/glm-4.5", base_url="https://openrouter.ai/api/v1", api_key=team_settings.openrouter_api_key),
            members=[
                query_classifier,
                research_planner,
                research_agent,
                analysis_agent,
                writing_agent,
                editor_agent,
            ],
            description="Intelligent multi-agent research team with adaptive depth and token optimization.",
            instructions=dedent("""
**SMART WORKFLOW COORDINATION:**

You are the team coordinator for an intelligent research team. Your job is to orchestrate the workflow efficiently based on query complexity.

**Step 1: Query Classification**
- Always start by transferring to Query Classifier
- Wait for classification result (SIMPLE/MODERATE/DEEP)

**Step 2: Adaptive Workflow**

**For SIMPLE queries (greetings, basic pleasantries):**
- Respond directly with a friendly, brief answer
- DO NOT proceed through the full pipeline
- Example response: "Hello! I'm an AI research assistant ready to help you with any research questions or analysis needs. What would you like to explore today?"

**For MODERATE queries:**
- Proceed with: Research Planner → Research Agent → Writing Agent → Editor Agent
- Skip Analysis Agent to save tokens on straightforward topics
- Log: "Moderate query detected, using streamlined 4-agent workflow"

**For DEEP queries:**
- Use full pipeline: Research Planner → Research Agent → Analysis Agent → Writing Agent → Editor Agent
- Log: "Deep query detected, using comprehensive 5-agent workflow"

**Coordination Rules:**
1. Always pass the complete output from each agent to the next
2. Print progress logs: "Step X completed, proceeding to [Next Agent]"
3. If any agent fails, continue workflow with error context
4. Monitor token usage and provide efficiency metrics at the end
5. Ensure each agent has clear context from previous steps

**Token Efficiency Tracking:**
- Log estimated tokens used at each step
- Provide final efficiency report
- Suggest optimizations for future similar queries

**Error Handling:**
- Never stop workflow due to single agent failure
- Pass error context to subsequent agents
- Maintain workflow continuity

**Final Output Standards:**
- SIMPLE: Direct response (50-100 words)
- MODERATE: Focused article (300-500 words)
- DEEP: Comprehensive report (600-1000 words)
"""),
            success_criteria="Deliver high-quality research output efficiently, matching depth to query complexity while optimizing token usage.",
            add_datetime_to_instructions=True,
            markdown=True,
            enable_team_history=True,
            num_of_interactions_from_history=3,  # Reduced for efficiency
            expected_output=dedent("""
                **For Simple Queries:**
                Friendly, direct response without full research pipeline.
                
                **For Moderate/Deep Queries:**
                # {Engaging Headline}
                
                ## Key Insights
                {Core findings and analysis}
                
                ## Background & Context
                {Essential context only}
                
                ## Main Findings
                {Research results organized by importance}
                
                ## Implications
                {Significance and next steps}
                
                ## Sources
                {Clean citation list with links}
                
                ---
                **Research Efficiency Report:**
                - Query Classification: {SIMPLE/MODERATE/DEEP}
                - Agents Used: {X of 6}
                - Estimated Tokens: {Approximate count}
                - Research Quality: {High/Medium}
            """),
            storage=PostgresStorage(
                table_name="smart_journalism_team",
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
        logger.error(f"Error creating smart journalism team: {e}")
        raise