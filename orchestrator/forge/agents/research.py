"""Research Agent — web search, document analysis, structured reports."""

from pydantic_ai import Agent
from pydantic_ai.common_tools.duckduckgo import duckduckgo_search_tool

from ..judges import CompletenessJudge, FactualGroundingJudge, JudgePanel, TaskAlignmentJudge
from .base import ForgeAgent

# The raw Pydantic AI agent
_research_agent = Agent(
    model="claude-sonnet-4-6",
    system_prompt="""You are a Research Agent in the Forge orchestrator system.

Your job is to conduct thorough research on topics given to you and produce structured, actionable reports.

Guidelines:
- Search the web for current information when needed
- Cite sources with URLs when possible
- Structure findings clearly with headers and bullet points
- Distinguish facts from opinions/speculation
- Note confidence levels for key claims
- If project context is provided, tailor research to that project's needs

Output format: A structured research report with:
1. Executive Summary (2-3 sentences)
2. Key Findings (bullet points)
3. Details (organized by subtopic)
4. Sources (URLs)
5. Recommended Next Steps
""",
    tools=[duckduckgo_search_tool()],
)

# Judge panel for research output
_research_panel = JudgePanel(
    judges=[TaskAlignmentJudge(), CompletenessJudge(), FactualGroundingJudge()],
)

# Wrapped with Forge task lifecycle + judges
research_agent = ForgeAgent(
    name="research",
    agent=_research_agent,
    judge_panel=_research_panel,
    task_type="research",
)
