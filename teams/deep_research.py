from typing import Optional
from textwrap import dedent

from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.storage.postgres import PostgresStorage
from agno.team.team import Team
from agno.tools.duckduckgo import DuckDuckGoTools
# from agno.tools.crawl4ai import Crawl4aiTools  # Uncomment if available
# from agno.tools.youtube import YouTubeTools   # Uncomment if available
# from agno.tools.resend import ResendTools     # Uncomment if available
# from agno.tools.github import GithubTools     # Uncomment if available
# from agno.tools.hackernews import HackerNewsTools  # Uncomment if available

from db.session import db_url
from teams.settings import team_settings

# --- Specialized Agents ---

search_agent = Agent(
    name="InternetSearcher",
    agent_id="internet-searcher",
    model=OpenAIChat(
        id=team_settings.gpt_4,
        max_completion_tokens=team_settings.default_max_completion_tokens,
        temperature=team_settings.default_temperature,
    ),
    tools=[DuckDuckGoTools(search=True, news=False)],
    add_history_to_messages=True,
    num_history_responses=3,
    description="Expert at finding information online.",
    instructions=[
        "Use duckduckgo_search for web queries.",
        "Cite sources with URLs.",
        "Focus on recent, reliable information."
    ],
    add_datetime_to_instructions=True,
    markdown=True,
    exponential_backoff=True
)

# Uncomment and implement these agents if the tools are available in your agno.tools package
# crawler_agent = Agent(
#     name="WebCrawler",
#     agent_id="web-crawler",
#     model=OpenAIChat(
#         id=team_settings.gpt_4,
#         max_completion_tokens=team_settings.default_max_completion_tokens,
#         temperature=team_settings.default_temperature,
#     ),
#     tools=[Crawl4aiTools(max_length=None)],
#     add_history_to_messages=True,
#     num_history_responses=3,
#     description="Extracts content from specific websites.",
#     instructions=[
#         "Use web_crawler to extract content from provided URLs.",
#         "Summarize key points and include the URL."
#     ],
#     markdown=True,
#     exponential_backoff=True
# )

# youtube_agent = Agent(
#     name="YouTubeAnalyst",
#     agent_id="youtube-analyst",
#     model=OpenAIChat(
#         id=team_settings.gpt_4,
#         max_completion_tokens=team_settings.default_max_completion_tokens,
#         temperature=team_settings.default_temperature,
#     ),
#     tools=[YouTubeTools()],
#     add_history_to_messages=True,
#     num_history_responses=3,
#     description="Analyzes YouTube videos.",
#     instructions=[
#         "Extract captions and metadata for YouTube URLs.",
#         "Summarize key points and include the video URL."
#     ],
#     markdown=True,
#     exponential_backoff=True
# )

# email_agent = Agent(
#     name="EmailAssistant",
#     agent_id="email-assistant",
#     model=OpenAIChat(
#         id=team_settings.gpt_4,
#         max_completion_tokens=team_settings.default_max_completion_tokens,
#         temperature=team_settings.default_temperature,
#     ),
#     tools=[ResendTools(from_email="noreply@example.com")],
#     add_history_to_messages=True,
#     num_history_responses=3,
#     description="Sends emails professionally.",
#     instructions=[
#         "Send professional emails based on context or user request.",
#         "Default recipient is user@example.com, but use recipient specified in the query if provided.",
#         "Include URLs and links clearly.",
#         "Ensure the tone is professional and courteous."
#     ],
#     markdown=True,
#     exponential_backoff=True
# )

# github_agent = Agent(
#     name="GitHubResearcher",
#     agent_id="github-researcher",
#     model=OpenAIChat(
#         id=team_settings.gpt_4,
#         max_completion_tokens=team_settings.default_max_completion_tokens,
#         temperature=team_settings.default_temperature,
#     ),
#     tools=[GithubTools()],
#     add_history_to_messages=True,
#     num_history_responses=3,
#     description="Explores GitHub repositories.",
#     instructions=[
#         "Search repositories or list pull requests based on user query.",
#         "Include repository URLs and summarize findings concisely."
#     ],
#     markdown=True,
#     exponential_backoff=True,
#     add_datetime_to_instructions=True
# )

# hackernews_agent = Agent(
#     name="HackerNewsMonitor",
#     agent_id="hackernews-monitor",
#     model=OpenAIChat(
#         id=team_settings.gpt_4,
#         max_completion_tokens=team_settings.default_max_completion_tokens,
#         temperature=team_settings.default_temperature,
#     ),
#     tools=[HackerNewsTools()],
#     add_history_to_messages=True,
#     num_history_responses=3,
#     description="Tracks Hacker News trends.",
#     instructions=[
#         "Fetch top stories using get_top_hackernews_stories.",
#         "Summarize discussions and include story URLs."
#     ],
#     markdown=True,
#     exponential_backoff=True,
#     add_datetime_to_instructions=True
# )

general_agent = Agent(
    name="GeneralAssistant",
    agent_id="general-assistant",
    model=OpenAIChat(
        id=team_settings.gpt_4,
        max_completion_tokens=team_settings.default_max_completion_tokens,
        temperature=team_settings.default_temperature,
    ),
    add_history_to_messages=True,
    num_history_responses=5,
    description="Handles general queries and synthesizes information from specialists.",
    instructions=[
        "Answer general questions or combine specialist inputs.",
        "If specialists provide information, synthesize it clearly.",
        "If a query doesn't fit other specialists, attempt to answer directly.",
        "Maintain a professional tone."
    ],
    markdown=True,
    exponential_backoff=True
)


def get_deep_research_team(
    model_id: Optional[str] = None,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    debug_mode: bool = True,
):
    model_id = model_id or team_settings.gpt_4

    return Team(
        name="Deep Research Team",
        team_id="deep-research-team",
        mode="coordinate",
        model=OpenAIChat(
            id=model_id,
            max_completion_tokens=team_settings.default_max_completion_tokens,
            temperature=team_settings.default_temperature if model_id != "o3-mini" else None,
        ),
        members=[
            search_agent,
            # crawler_agent,
            # youtube_agent,
            # email_agent,
            # github_agent,
            # hackernews_agent,
            general_agent,
        ],
        description="Coordinates specialists to handle research tasks.",
        instructions=[
            "Analyze the query and assign tasks to specialists.",
            "Delegate based on task type:",
            "- Web searches: InternetSearcher",
            "- URL content: WebCrawler",
            "- YouTube videos: YouTubeAnalyst",
            "- Emails: EmailAssistant",
            "- GitHub queries: GitHubResearcher",
            "- Hacker News: HackerNewsMonitor",
            "- General or synthesis: GeneralAssistant",
            "Synthesize responses into a cohesive answer.",
            "Cite sources and maintain clarity.",
            "Always check previous conversations in memory before responding.",
            "When asked about previous information or to recall something mentioned before, refer to your memory of past interactions.",
            "Use all relevant information from memory when answering follow-up questions."
        ],
        success_criteria="The user's query has been thoroughly answered with information from all relevant specialists.",
        enable_agentic_context=True,
        share_member_interactions=True,
        show_members_responses=False,
        markdown=True,
        show_tool_calls=False,
        enable_team_history=True,
        num_of_interactions_from_history=5,
        session_id=session_id,
        user_id=user_id,
        storage=PostgresStorage(
            table_name="deep_research_team",
            db_url=db_url,
            mode="team",
            auto_upgrade_schema=True,
        ),
        debug_mode=debug_mode,
    )
