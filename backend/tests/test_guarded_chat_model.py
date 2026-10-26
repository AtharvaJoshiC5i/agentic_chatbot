"""GuardedChatModel must survive LangGraph tool binding."""

from unittest.mock import MagicMock

from langchain_core.messages import AIMessage, HumanMessage

from app.llm.guarded import GuardedChatModel


def test_bind_tools_wraps_binding_without_validation_error() -> None:
    fake_binding = MagicMock(name="ChatModelBinding")
    inner = MagicMock()
    inner.bind_tools.return_value = fake_binding

    guarded = GuardedChatModel(inner=inner, provider_id="test", max_rpm=60)
    bound = guarded.bind_tools([{"name": "noop"}])

    assert isinstance(bound, GuardedChatModel)
    assert bound.inner is fake_binding
    assert bound.provider_id == "test"


def test_generate_uses_invoke_on_tool_binding() -> None:
    """Groq tool bindings return tool_calls via invoke but not via _generate."""
    binding = MagicMock(name="ChatModelBinding")
    binding.invoke.return_value = AIMessage(
        content="",
        tool_calls=[
            {
                "name": "run_return_investigation",
                "args": {"return_id": "R102"},
                "id": "tc1",
                "type": "tool_call",
            }
        ],
    )
    binding._generate.return_value = MagicMock(
        generations=[MagicMock(message=AIMessage(content="", tool_calls=[]))]
    )

    guarded = GuardedChatModel(inner=binding, provider_id="test", max_rpm=60)
    result = guarded._generate([HumanMessage(content="Investigate R102")])

    binding.invoke.assert_called_once()
    invoke_messages = binding.invoke.call_args[0][0]
    assert invoke_messages[0].content == "Investigate R102"
    binding._generate.assert_not_called()
    assert result.generations[0].message.tool_calls[0]["name"] == "run_return_investigation"
