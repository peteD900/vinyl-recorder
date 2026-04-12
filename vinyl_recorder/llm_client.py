# LLM client connection
import json
import anthropic
from vinyl_recorder.config import Config, get_logger

logger = get_logger()


class LLMClient:
    def __init__(self, api_key: str, model: str):
        logger.info("Starting LLMClient")
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model

    def _extract_system(self, messages: list) -> tuple[str, list]:
        """Separate system messages from user/assistant messages.

        Anthropic requires the system prompt as a separate parameter,
        not as a message in the messages array.
        """
        system_parts = []
        other_messages = []

        for msg in messages:
            if msg["role"] == "system":
                system_parts.append(msg["content"])
            else:
                other_messages.append(msg)

        return "\n\n".join(system_parts), other_messages

    def parse_completion(self, messages: list, response_format):
        """
        Get structured response using tool_use to match a Pydantic model.
        """
        system, user_messages = self._extract_system(messages)

        # Convert pydantic model schema to an Anthropic tool definition
        tool = {
            "name": "structured_output",
            "description": "Return the structured data extracted from the request.",
            "input_schema": response_format.model_json_schema(),
        }

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=system,
                messages=user_messages,
                tools=[tool],
                tool_choice={"type": "tool", "name": "structured_output"},
            )
        except Exception as e:
            logger.error(f"LLM parse failed: {e}")
            raise

        # Extract the tool_use block from the response
        for block in response.content:
            if block.type == "tool_use":
                return response_format.model_validate(block.input)

        raise ValueError("No structured output returned from LLM")

    def create_completion(self, messages: list) -> str:
        """
        Get a plain text response from the LLM.
        """
        system, user_messages = self._extract_system(messages)

        response = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            system=system,
            messages=user_messages,
        )

        return response.content[0].text


def get_llm_client(llm="anthropic", model=None):
    """Factory function for LLM client."""
    model = model or Config.ANTHROPIC_MODEL

    if llm == "anthropic":
        client = LLMClient(api_key=Config.ANTHROPIC_API_KEY, model=model)

    return client


if __name__ == "__main__":
    llm = get_llm_client()

    messages = [
        {"role": "system", "content": "You're a helpful assistant."},
        {
            "role": "user",
            "content": "Give me 5 albums I might like similar to Beatles White Album?",
        },
    ]

    response = llm.create_completion(messages=messages)
    print(response)
