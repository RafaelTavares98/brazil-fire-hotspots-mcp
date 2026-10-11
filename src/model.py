"""The one place that knows DeepSeek exists.

The agent takes any function of (messages, tools) that returns one
assistant message. This builds that function for DeepSeek's chat API.
"""

import os

import httpx

URL = 'https://api.deepseek.com/chat/completions'

#: Choosing a tool off a list of six and copying its number into a
#: sentence is light work, so the cheap, fast model does it.
MODEL = 'deepseek-flash'

TIMEOUT_SECONDS = 60

#: Where the key may sit in the system keychain, tried in order. The
#: earlier projects on this machine already wrote these.
KEYRING_ENTRIES = (('fire-mcp', 'deepseek'), ('payables-panel', 'deepseek'),
                   ('deepseek', 'api-key'))


class ModelFailed(Exception):
    """The model could not be asked, or answered with an error."""


def _from_keyring():
    try:
        import keyring
    except ImportError:
        return None
    for service, name in KEYRING_ENTRIES:
        found = keyring.get_password(service, name)
        if found:
            return found
    return None


def key():
    """The key from DEEPSEEK_API_KEY, else the keychain, else None."""
    return os.environ.get('DEEPSEEK_API_KEY') or _from_keyring()


def deepseek(api_key, transport=None, name=MODEL):
    """A function that sends messages and tools, and returns the reply."""
    client = httpx.Client(transport=transport, timeout=TIMEOUT_SECONDS,
                          headers={'Authorization': f'Bearer {api_key}'})

    def ask(messages, tools):
        body = {'model': name, 'messages': messages, 'temperature': 0}
        if tools:
            body['tools'] = tools
        try:
            reply = client.post(URL, json=body)
        except httpx.HTTPError as error:
            raise ModelFailed(f'DeepSeek could not be reached: {error}')
        if reply.status_code != 200:
            raise ModelFailed(f'DeepSeek answered {reply.status_code}: '
                              f'{reply.text[:200]}')
        return reply.json()['choices'][0]['message']

    return ask
