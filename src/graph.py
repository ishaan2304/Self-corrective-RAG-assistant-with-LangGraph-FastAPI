"""Builds the self-corrective RAG StateGraph.

Flow:

    analyze_query -> retrieve -> grade_documents --relevant docs found--> generate -> END
                          ^                    |
                          |                    --no relevant docs, retries left--
                          --------------------------------------------------------
                                              |
                                              --retries exhausted--> fallback -> END
"""
from langgraph.graph import StateGraph, START, END
from src.state import RAGState
from src import nodes, config


def route_after_grading(state: RAGState) -> str:
    if state.get("graded_documents"):
        return "generate"
    max_retries = state.get("max_retries", config.MAX_RETRIES)
    if state.get("retry_count", 0) <= max_retries:
        return "rewrite"
    return "fallback"


def build_graph():
    graph = StateGraph(RAGState)

    graph.add_node("analyze_query", nodes.analyze_query)
    graph.add_node("retrieve", nodes.retrieve)
    graph.add_node("grade_documents", nodes.grade_documents)
    graph.add_node("generate", nodes.generate)
    graph.add_node("fallback", nodes.fallback)

    graph.add_edge(START, "analyze_query")
    graph.add_edge("analyze_query", "retrieve")
    graph.add_edge("retrieve", "grade_documents")
    graph.add_conditional_edges(
        "grade_documents",
        route_after_grading,
        {"generate": "generate", "rewrite": "analyze_query", "fallback": "fallback"},
    )
    graph.add_edge("generate", END)
    graph.add_edge("fallback", END)

    return graph.compile()


_compiled_graph = None


def get_graph():
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_graph()
    return _compiled_graph


def run_query(question: str) -> RAGState:
    initial_state: RAGState = {
        "question": question,
        "retry_count": 0,
        "max_retries": config.MAX_RETRIES,
    }
    return get_graph().invoke(initial_state)
