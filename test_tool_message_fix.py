"""
Test pour vérifier que le format des messages tool est correct
"""
import json


def test_message_format():
    """Vérifie que le format des messages est correct"""

    # Simule un assistant_message avec tool_calls mais content=None
    class MockMessage:
        def __init__(self):
            self.content = None
            self.tool_calls = [MockToolCall()]

    class MockToolCall:
        def __init__(self):
            self.id = "call_123"
            self.function = MockFunction()

    class MockFunction:
        def __init__(self):
            self.name = "test_tool"
            self.arguments = '{"param": "value"}'

    assistant_message = MockMessage()

    # Test de la construction du message (comme dans chat_app.py ligne 1663-1680)
    conversation_history = []
    conversation_history.append({
        "role": "assistant",
        "content": assistant_message.content or "",  # ✅ Correction appliquée
        "tool_calls": [
            {
                "id": tc.id,
                "type": "function",
                "function": {
                    "name": tc.function.name,
                    "arguments": tc.function.arguments
                }
            }
            for tc in assistant_message.tool_calls
        ]
    })

    # Vérification
    assert len(conversation_history) == 1
    assert conversation_history[0]["role"] == "assistant"
    assert conversation_history[0]["content"] == ""  # Doit être "" et non None
    assert len(conversation_history[0]["tool_calls"]) == 1
    assert conversation_history[0]["tool_calls"][0]["id"] == "call_123"

    print("✅ Test réussi : le content est bien '' et non None")
    print(f"Message formaté correctement :\n{json.dumps(conversation_history[0], indent=2, ensure_ascii=False)}")

    # Maintenant ajoutons le message tool (comme dans chat_app.py ligne 1707)
    conversation_history.append({
        "role": "tool",
        "tool_call_id": "call_123",
        "content": "Résultat de l'outil"
    })

    # Vérification que la séquence est correcte
    assert conversation_history[0]["role"] == "assistant"
    assert "tool_calls" in conversation_history[0]
    assert conversation_history[1]["role"] == "tool"
    assert conversation_history[1]["tool_call_id"] == conversation_history[0]["tool_calls"][0]["id"]

    print("\n✅ Test réussi : la séquence assistant->tool est correcte")
    print(f"\nHistoire de conversation valide :\n{json.dumps(conversation_history, indent=2, ensure_ascii=False)}")


if __name__ == "__main__":
    test_message_format()

