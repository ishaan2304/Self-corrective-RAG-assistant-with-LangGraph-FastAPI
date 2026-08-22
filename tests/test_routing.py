"""Tests the retry/routing logic in isolation, without calling any LLM or
vector store — this is the core evaluation criterion (state schema + retry
tracking + conditional edges), so it should be verifiable with zero API keys.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.graph import route_after_grading


def test_routes_to_generate_when_relevant_docs_found():
    state = {"graded_documents": [{"content": "x"}], "retry_count": 0, "max_retries": 2}
    assert route_after_grading(state) == "generate"


def test_routes_to_rewrite_when_no_docs_and_retries_left():
    state = {"graded_documents": [], "retry_count": 1, "max_retries": 2}
    assert route_after_grading(state) == "rewrite"


def test_routes_to_fallback_when_retries_exhausted():
    state = {"graded_documents": [], "retry_count": 3, "max_retries": 2}
    assert route_after_grading(state) == "fallback"


def test_grade_documents_increments_retry_only_on_zero_relevant():
    from src import nodes

    state = {
        "question": "q",
        "documents": [{"content": "c", "source": "s", "score": 0.1, "relevant": None}],
        "retry_count": 0,
    }
    # monkeypatch the LLM call so this test needs no API key
    class FakeLLM:
        def invoke(self, _msgs):
            class R:
                content = "irrelevant"
            return R()

    nodes.get_llm.cache_clear()
    original = nodes.get_llm
    nodes.get_llm = lambda: FakeLLM()
    try:
        update = nodes.grade_documents(state)
    finally:
        nodes.get_llm = original

    assert update["graded_documents"] == []
    assert update["retry_count"] == 1


if __name__ == "__main__":
    test_routes_to_generate_when_relevant_docs_found()
    test_routes_to_rewrite_when_no_docs_and_retries_left()
    test_routes_to_fallback_when_retries_exhausted()
    test_grade_documents_increments_retry_only_on_zero_relevant()
    print("All routing tests passed.")
