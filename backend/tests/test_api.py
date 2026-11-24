import uuid


def chat(client, session, message, headers=None, **extra):
    body = {"session_id": session, "message": message, **extra}
    return client.post("/chat", json=body, headers=headers or {})


def unique():
    return uuid.uuid4().hex[:8]


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "keys_configured": 2, "cache_enabled": True}


def test_live_then_cache_in_new_session(client):
    msg = f"hello {unique()}"
    first = chat(client, "a", msg).json()
    second = chat(client, "b", msg).json()
    assert first["metadata"]["resolution_source"] == "LIVE_INFERENCE"
    assert first["metadata"]["key_id"] == "key_1"
    assert second["metadata"]["resolution_source"] == "LLM_CACHE"
    assert second["metadata"]["key_id"] is None
    assert second["metadata"]["fallback_attempts"] == 0
    assert second["reply"] == first["reply"]
    assert second["metadata"]["input_tokens"] == first["metadata"]["input_tokens"]


def test_different_message_is_not_cached(client):
    chat(client, "a", f"one {unique()}")
    r = chat(client, "b", f"two {unique()}").json()
    assert r["metadata"]["resolution_source"] == "LIVE_INFERENCE"


def test_tokens_are_per_request_not_running_total(client):
    r1 = chat(client, "a", "same length 1111").json()["metadata"]
    r2 = chat(client, "b", "same length 2222").json()["metadata"]
    assert abs(r1["input_tokens"] - r2["input_tokens"]) <= 2
    r3 = chat(client, "a", "same length 3333").json()["metadata"]
    assert isinstance(r3["input_tokens"], int) and r3["input_tokens"] > 0
    assert isinstance(r3["output_tokens"], int)


def test_history_and_sessions_are_separate(client):
    chat(client, "s1", "first message")
    chat(client, "s1", "second message")
    chat(client, "s2", "other session")
    h1 = client.get("/sessions/s1/messages").json()["messages"]
    h2 = client.get("/sessions/s2/messages").json()["messages"]
    assert [m["role"] for m in h1] == ["user", "assistant", "user", "assistant"]
    assert h1[0]["content"] == "first message"
    assert "input_tokens" in h1[1]["metadata"]
    assert "metadata" not in h1[0]
    assert len(h2) == 2
    assert all(m["role"] != "system" for m in h1)


def test_unknown_session_404(client):
    r = client.get("/sessions/nope/messages")
    assert r.status_code == 404
    assert r.json() == {"detail": "session not found"}


def test_validation_422(client):
    assert client.post("/chat", json={"session_id": "a"}).status_code == 422
    assert client.post("/chat", json={"session_id": "a", "message": "   "}).status_code == 422
    assert client.post("/chat", json={"message": "hi"}).status_code == 422
    assert client.post("/chat", json={"session_id": "", "message": "hi"}).status_code == 422
    assert client.post("/chat", json={"session_id": "a", "message": "x" * 4001}).status_code == 422
    bad = client.post("/chat", content="{not json", headers={"content-type": "application/json"})
    assert bad.status_code == 422
    assert "detail" in bad.json()


def test_failover_key_1_429(client):
    r = chat(client, "f", f"fail {unique()}", {"X-Simulate-Failure": "key_1=429"})
    assert r.status_code == 200
    md = r.json()["metadata"]
    assert md["key_id"] == "key_2"
    assert md["fallback_attempts"] == 1
    assert md["resolution_source"] == "LIVE_INFERENCE"


def test_failover_works_even_if_message_is_cached(client):
    msg = f"cached then fail {unique()}"
    chat(client, "a", msg)
    r = chat(client, "b", msg, {"X-Simulate-Failure": "key_1=500"}).json()
    assert r["metadata"]["key_id"] == "key_2"


def test_all_keys_fail_503_and_nothing_saved(client):
    r = chat(client, "dead", "hi", {"X-Simulate-Failure": "*=429"})
    assert r.status_code == 503
    assert r.json() == {"detail": "all providers unavailable"}
    assert client.get("/sessions/dead/messages").status_code == 404


def test_both_keys_listed_503(client):
    r = chat(client, "dead2", "hi", {"X-Simulate-Failure": "key_1=429,key_2=500"})
    assert r.status_code == 503


def test_simulation_header_ignored_when_disabled(client_no_sim):
    r = chat(client_no_sim, "x", f"hi {unique()}", {"X-Simulate-Failure": "*=429"})
    assert r.status_code == 200
    assert r.json()["metadata"]["key_id"] == "key_1"


def test_system_prompt_is_kept_for_session(client):
    chat(client, "sp", "hello", system_prompt="Talk like a pirate")
    chat(client, "sp", "again")
    # the system prompt is never returned in history
    msgs = client.get("/sessions/sp/messages").json()["messages"]
    assert len(msgs) == 4
