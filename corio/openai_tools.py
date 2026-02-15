from fmtr.tools import environment_tools
from functools import lru_cache
from openai import OpenAI

OPENAI_TOKEN_KEY = 'FMTR_OPENAI_API_KEY'


@lru_cache
def get_client():
    """

    Get an OpenAI client instance

    """
    OPENAI_KEY = environment_tools.get(OPENAI_TOKEN_KEY)
    client = OpenAI(api_key=OPENAI_KEY)
    return client


def get_text(prompt, model='gpt-4o'):
    """

    Very simple prompt-to-output

    """
    client = get_client()
    messages = [{"role": 'user', "content": prompt}]

    completion = client.chat.completions.create(
        messages=messages,
        model=model
    )
    text = completion.choices[0].message.content
    return text


if __name__ == '__main__':
    text = get_text('hi')
    text
