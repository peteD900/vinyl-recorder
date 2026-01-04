# LLM client connection
from openai import OpenAI
from vinyl_recorder.config import Config, get_logger

logger = get_logger()


# Setup class incase later want to try switching betweem LLMs
class LLMClient:
    def __init__(self, api_key: str, model: str):
        logger.info("Starting LLMClient")
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def parse_completion(self, messages, response_format):
        """
        For stuctured respones with pydantic use completions.parse
        """
        try:
            completion = self.client.beta.chat.completions.parse(
                model=self.model, messages=messages, response_format=response_format
            )

        except Exception as e:
            logger.error(f"LLM parse failed: {e}")
            raise

        results = completion.choices[0].message.parsed

        return results

    def create_completion(self, messages):
        """
        For non-structured chat responses if required
        """
        completion = self.client.chat.completions.create(
            model=self.model, messages=messages
        )

        return completion


def get_llm_client(llm="openai", model=Config.OPENAI_MODEL):
    """
    Probably wont need a different llm but put this here in case.
    """
    if llm == "openai":
        client = LLMClient(api_key=Config.OPENAI_API_KEY, model=model)

    return client


if __name__ == "__main__":
    model = "gpt-4o"
    llm = get_llm_client(model=model)

    messages = [
        {"role": "system", "content": "You're a helpful assistant."},
        {
            "role": "user",
            "content": "Give me 5 albums I might like similar to Beatles White Album?",
        },
    ]

    response = llm.create_completion(messages=messages)
    print(response.choices[0].message.content)
