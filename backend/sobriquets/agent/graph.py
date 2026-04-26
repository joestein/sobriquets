import logging
from typing import Literal

from langchain_core.messages import AIMessage, SystemMessage
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode

from sobriquets.agent.prompts import SYSTEM_PROMPT
from sobriquets.agent.tools import get_tools
from sobriquets.config import Settings

logger = logging.getLogger(__name__)


def _get_llm(settings: Settings):
    """Create the LLM based on settings."""
    if settings.AGENT_LLM_PROVIDER == "anthropic":
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(
            model=settings.AGENT_LLM_MODEL,
            api_key=settings.ANTHROPIC_API_KEY,
            streaming=True,
        )
    elif settings.AGENT_LLM_PROVIDER == "openai":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=settings.AGENT_LLM_MODEL,
            api_key=settings.OPENAI_API_KEY,
            streaming=True,
        )
    else:
        raise ValueError(
            f"Unknown LLM provider: {settings.AGENT_LLM_PROVIDER}. "
            "Use 'anthropic' or 'openai'."
        )


def should_continue(state: MessagesState) -> Literal["tools", "__end__"]:
    """Determine if the agent should call tools or end."""
    messages = state["messages"]
    last_message = messages[-1]
    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        return "tools"
    return END


def create_agent_graph(settings: Settings):
    """Create and compile the LangGraph agent."""
    tools = get_tools()
    llm = _get_llm(settings)
    llm_with_tools = llm.bind_tools(tools)

    async def agent_node(state: MessagesState) -> dict:
        """Call the LLM with system prompt and conversation history."""
        messages = state["messages"]

        # Prepend system prompt if not already there
        if not messages or not isinstance(messages[0], SystemMessage):
            messages = [SystemMessage(content=SYSTEM_PROMPT)] + messages

        response = await llm_with_tools.ainvoke(messages)
        return {"messages": [response]}

    graph = StateGraph(MessagesState)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", ToolNode(tools))

    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", should_continue)
    graph.add_edge("tools", "agent")

    return graph.compile()
