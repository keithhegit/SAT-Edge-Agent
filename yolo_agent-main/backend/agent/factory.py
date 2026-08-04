from __future__ import annotations

from langchain.agents import create_agent
from langchain_openai import ChatOpenAI

from config import load_config
from backend.infrastructure.checkpoints.sqlite_checkpoint import get_sqlite_checkpointer
from backend.tools.detection_tools import TOOLS


AGENT_CHECKPOINTER = None


def create_detection_agent(streaming: bool | None = None):
    """创建检测 Agent。"""
    app_config = load_config()
    effective_streaming = app_config.agent.streaming if streaming is None else streaming

    llm = ChatOpenAI(
        model=app_config.llm.model,
        openai_api_base=app_config.llm.api_base,
        openai_api_key=app_config.llm.api_key or "dummy",
        temperature=app_config.llm.temperature,
        max_tokens=app_config.llm.max_tokens,
        request_timeout=app_config.llm.request_timeout,
        streaming=effective_streaming,
    )
    checkpointer = AGENT_CHECKPOINTER or get_sqlite_checkpointer(app_config.agent.checkpoint_db_path)

    return create_agent(
        llm,
        TOOLS,
        system_prompt=app_config.agent.system_prompt,
        checkpointer=checkpointer,
    )
