"""Unit 3 - Memory channel: a LangGraph Store that can contain one poisoned entry."""
from langgraph.store.memory import InMemoryStore

from config import USER_ID

NS = ("memories", USER_ID)


def build_store(poison=None):
    store = InMemoryStore()
    store.put(NS, "name", {"text": "The customer's name is Riya."})
    store.put(NS, "lang", {"text": "The customer prefers replies in English."})
    if poison:
        store.put(NS, "poisoned", {"text": poison})
    return store


def load_memories(store):
    return [{"id": it.key, "text": it.value["text"]} for it in store.search(NS)]
