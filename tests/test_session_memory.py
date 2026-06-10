import pytest
from app.core.session_memory import SessionMemory

def test_session_memory_operations():
    memory = SessionMemory(max_turns=2)
    
    # Empty at start
    assert len(memory.get_messages()) == 0
    
    # Add messages
    memory.add_user_message("Hello")
    memory.add_assistant_message("Hi")
    
    messages = memory.get_messages()
    assert len(messages) == 2
    assert messages[0] == {"role": "user", "content": "Hello"}
    assert messages[1] == {"role": "assistant", "content": "Hi"}

def test_session_memory_truncation():
    # max_turns = 2 means max 4 messages
    memory = SessionMemory(max_turns=2)
    
    memory.add_user_message("1")
    memory.add_assistant_message("1r")
    memory.add_user_message("2")
    memory.add_assistant_message("2r")
    
    assert len(memory.get_messages()) == 4
    
    # Adding a 5th message should truncate without starting history with assistant.
    memory.add_user_message("3")
    
    messages = memory.get_messages()
    assert len(messages) == 3
    assert messages[0] == {"role": "user", "content": "2"}
    assert messages[1] == {"role": "assistant", "content": "2r"}
    assert messages[2] == {"role": "user", "content": "3"}
    
    memory.add_assistant_message("3r")
    messages = memory.get_messages()
    assert len(messages) == 4
    assert messages[0] == {"role": "user", "content": "2"}
    assert messages[1] == {"role": "assistant", "content": "2r"}
    assert messages[2] == {"role": "user", "content": "3"}
    assert messages[3] == {"role": "assistant", "content": "3r"}

def test_session_memory_clear():
    memory = SessionMemory()
    memory.add_user_message("Hello")
    memory.clear()
    assert len(memory.get_messages()) == 0

def test_session_memory_truncation_never_starts_with_assistant_on_11th_turn():
    memory = SessionMemory(max_turns=10)

    for index in range(10):
        memory.add_user_message(f"user-{index}")
        memory.add_assistant_message(f"assistant-{index}")

    memory.add_user_message("user-10")
    messages = memory.get_messages()

    assert messages[0]["role"] == "user"
    assert messages[-1] == {"role": "user", "content": "user-10"}
    assert len(messages) == 19

    memory.add_assistant_message("assistant-10")
    messages = memory.get_messages()

    assert messages[0]["role"] == "user"
    assert messages[0]["content"] == "user-1"
    assert messages[-1] == {"role": "assistant", "content": "assistant-10"}
    assert len(messages) == 20
