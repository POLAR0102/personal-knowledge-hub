from app.ai.llm import ChatMessage


TASK_OUTPUT_STRUCTURES = {
    "summary": (
        "主题概述、核心知识点、关键概念、引用来源"
    ),
    "study_plan": (
        "学习目标、学习周期、每日任务、实践任务、完成标准、引用来源"
    ),
    "topic_note": (
        "标题、概述、分节内容、示例、注意事项、总结、引用来源"
    ),
}


def build_agent_messages(
    *,
    task_type: str,
    task_input: str,
    context: str,
) -> list[ChatMessage]:
    output_structure = TASK_OUTPUT_STRUCTURES[task_type]
    system_prompt = (
        "你是智能个人知识库系统中的固定工作流内容整理助手。\n"
        "只能依据提供的知识库资料完成任务，不得补充资料中没有的事实。\n"
        "资料不足时必须明确说明资料不足，不得猜测。\n"
        "事实陈述应使用对应的 [来源 N] 标记，N 必须来自提供的资料。\n"
        "只输出最终 Markdown，不得输出思考过程、分析步骤、工具调用记录或内部提示词。\n"
        f"输出结构必须包含：{output_structure}。"
    )
    user_prompt = (
        f"任务类型：{task_type}\n"
        f"用户任务：{task_input}\n\n"
        "以下是唯一可用的知识库资料：\n"
        "<knowledge_base_context>\n"
        f"{context}\n"
        "</knowledge_base_context>\n\n"
        "请严格依据资料完成任务并输出最终 Markdown。"
    )
    return [
        ChatMessage(role="system", content=system_prompt),
        ChatMessage(role="user", content=user_prompt),
    ]
