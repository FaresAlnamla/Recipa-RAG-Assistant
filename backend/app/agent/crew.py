from typing import Any, Dict, List, Optional
from crewai import Agent, Task, Crew

from .tools import rag_tool, memory_read_tool, memory_write_tool, log_turn_tool

PLANNER_SYSTEM = """
You are an orchestrator for RecipaAI.
You decide the best action:
- If user greets or asks vague question, reply with ONE short line prompting for a specific cookbook question.
- Otherwise, you MUST use the RAG tool output to answer (do not invent facts).
Also:
- Use long-term memory facts ONLY as user preferences/constraints, not as cookbook facts.
- Output clean Markdown.
"""

def run_agent(question: str, k: int, history: Optional[List[Dict[str, Any]]]):
    planner = Agent(
        role="Planner",
        goal="Decide whether to answer directly, ask clarification, or use RAG tool.",
        backstory="You route requests safely and efficiently.",
        verbose=False,
    )

    executor = Agent(
        role="Executor",
        goal="Use tools to get grounded answer and produce final response.",
        backstory="You never hallucinate cookbook facts; you rely on RAG tool.",
        verbose=False,
                        )

    memory_keeper = Agent(
        role="Memory Keeper",
        goal="Store stable user preferences and a short answer summary.",
        backstory="You keep long-term memory concise.",
        verbose=False,
    )

    # 1) read memory (preferences)
    mem_text = memory_read_tool()

    t1 = Task(
        description=f"""{PLANNER_SYSTEM}

Long-term memory facts (preferences):
{mem_text}

Conversation history (short-term):
{history or []}

User question:
{question}

Decide what to do and produce an instruction for the Executor.
""",
        agent=planner,
        expected_output="A short instruction to the Executor plus any clarification question if needed."
    )

    # 2) execute: call RAG tool if needed + final answer
    t2 = Task(
        description=f"""
Use this tool when needed:
- rag_tool(question, k, history)  -> grounded cookbook answer

User question: {question}
k: {k}

Produce final Markdown answer.
If greeting/vague: reply with 1 short line asking for a specific cookbook question.
""",
        agent=executor,
        expected_output="Final answer in Markdown."
    )

    # 3) store memory + log turn
    t3 = Task(
        description="""
From the final answer:
- Extract any user preferences/constraints (diet, time, budget, equipment).
- Save them as memory_write_tool("...", tag="preference") if present.
- Save a 1-line summary as memory_write_tool("...", tag="summary").
Finally log the turn using log_turn_tool(user, assistant).
""",
        agent=memory_keeper,
        expected_output="Confirmation that memory was updated."
    )

    crew = Crew(agents=[planner, executor, memory_keeper], tasks=[t1, t2, t3], verbose=False)

    # NOTE: CrewAI tasks can't automatically call python functions unless you expose tools as actual CrewAI Tools.
    # MVP approach: We'll run RAG ourselves and inject it to executor via context.
    # So instead of relying on agent to call rag_tool, we do it here:
    is_vague = question.strip().lower() in {"hi", "hello", "hey", "سلام", "مرحبا"} or len(question.strip()) < 5

    if is_vague:
        final_answer = "أهلًا! احكيلي شو بدك من كتاب The Low-Cost Cookbook بالزبط (اسم وصفة أو مكوّن/فكرة) وبساعدك فورًا."
        # memory + log
        memory_write_tool("User greeted / vague request.", tag="summary")
        log_turn_tool(question, final_answer)
        return final_answer

    grounded = rag_tool(question=question, k=k, history=history)

    # Save summary + log (مبدئيًا)
    memory_write_tool(f"Last answer summary: {grounded[:160]}...", tag="summary")
    log_turn_tool(question, grounded)

    # (النسخة الثانية بنعمل استخراج preferences بشكل ذكي)
    return grounded
