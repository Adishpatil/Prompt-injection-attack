"""LangGraph pipeline:

  guard_in -> load_context -> sanitize_context -> worker -> guard_out -> notifier

BASELINE: guard_in, sanitize_context and guard_out are pass-through hooks.
The mitigation step plugs real Guard logic into the same hooks, so the
before/after comparison runs the identical graph.
"""
from typing import TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph

from agents import NOTIFIER_PROMPT, WORKER_PROMPT, build_agents, format_memories
from kb import retrieve
from memory_store import load_memories


class State(TypedDict, total=False):
    user_input: str
    retrieved_ids: list      # chunk ids BEFORE any defence (for the poison_in_context check)
    memory_ids: list         # memory ids BEFORE any defence
    chunks: list             # what the Worker actually sees (after sanitize hook)
    memories: list
    worker_reply: str
    worker_raw: str          # Worker output before the output guard changed it
    quarantined: list        # chunks/memories dropped by the sanitize hook
    final: str
    blocked: bool
    block_reason: str


def _passthrough(state):
    return {}


def build_pipeline(col, store, llm=None, guard_in=None, sanitize=None, guard_out=None):
    guard_in = guard_in or _passthrough
    sanitize = sanitize or _passthrough
    guard_out = guard_out or _passthrough
    worker_agent, notifier_agent = build_agents(llm)

    def load_context(state):
        chunks = retrieve(col, state["user_input"])
        memories = load_memories(store)
        return {
            "chunks": chunks,
            "memories": memories,
            "retrieved_ids": [c["id"] for c in chunks],
            "memory_ids": [m["id"] for m in memories],
        }

    def worker(state):
        system = (WORKER_PROMPT
                  + "\nSaved memories about this customer:\n"
                  + format_memories(state["memories"]) + "\n")
        ctx = "\n".join(f"- {c['text']}" for c in state["chunks"]) or "- (none)"
        human = (f"Knowledge-base excerpts:\n{ctx}\n\n"
                 f"Customer question: {state['user_input']}")
        out = worker_agent.invoke({"messages": [SystemMessage(system), HumanMessage(human)]})
        return {"worker_reply": str(out["messages"][-1].content)}

    def notifier(state):
        system = (NOTIFIER_PROMPT
                  + "\nSaved memories about this customer:\n"
                  + format_memories(state["memories"]) + "\n")
        human = f"Support agent's answer:\n{state['worker_reply']}"
        out = notifier_agent.invoke({"messages": [SystemMessage(system), HumanMessage(human)]})
        return {"final": str(out["messages"][-1].content)}

    route = lambda s: "blocked" if s.get("blocked") else "ok"

    g = StateGraph(State)
    g.add_node("guard_in", guard_in)
    g.add_node("load_context", load_context)
    g.add_node("sanitize_context", sanitize)
    g.add_node("worker", worker)
    g.add_node("guard_out", guard_out)
    g.add_node("notifier", notifier)

    g.add_edge(START, "guard_in")
    g.add_conditional_edges("guard_in", route, {"blocked": END, "ok": "load_context"})
    g.add_edge("load_context", "sanitize_context")
    g.add_edge("sanitize_context", "worker")
    g.add_edge("worker", "guard_out")
    g.add_conditional_edges("guard_out", route, {"blocked": END, "ok": "notifier"})
    g.add_edge("notifier", END)
    return g.compile()
