import os
import httpx
from anthropic.types.beta import BetaTextBlock  # so loop._response_to_params() can read it


class _NebiusRawResponse:
    def __init__(self, http_response: httpx.Response, text: str):
        self.http_response = http_response
        self._text = text

    def parse(self):
        # Return an object with `.content` that includes a BetaTextBlock,
        # which loop._response_to_params() already knows how to handle.
        class _Msg:
            def __init__(self, text):
                self.content = [BetaTextBlock(type="text", text=text)]
        return _Msg(self._text)


def _extract_system_text(system):
    if isinstance(system, list) and system:
        block = system[0]
        if isinstance(block, dict):
            return block.get("text", "")
    return ""


def _extract_last_user_text(msgs):
    for m in reversed(msgs or []):
        if m.get("role") == "user":
            content = m.get("content")
            if isinstance(content, list):
                # find last text block
                for b in reversed(content):
                    if isinstance(b, dict) and b.get("type") == "text":
                        return b.get("text", "")
            elif isinstance(content, str):
                return content
    return ""


class _WithRawResponse:
    def create(self, *, model=None, messages=None, system=None,
               max_tokens=1024, **kwargs):
        api_key = os.environ.get("NEBIUS_API_KEY")
        if not api_key:
            raise ValueError("NEBIUS_API_KEY is not set in the environment.")

        base_url = os.environ.get("NEBIUS_BASE_URL", "https://api.studio.nebius.com/v1/").rstrip("/")
        model_id = model or os.environ.get("NEBIUS_MODEL") or "deepseek-ai/DeepSeek-R1-0528"

        system_text = _extract_system_text(system)
        user_text = _extract_last_user_text(messages or [])

        payload_msgs = []
        if system_text:
            payload_msgs.append({"role": "system", "content": system_text})
        if user_text:
            payload_msgs.append({"role": "user", "content": user_text})

        payload = {
            "model": model_id,
            "messages": payload_msgs,
            "max_tokens": max_tokens,
            "temperature": 0.7,
            "stream": False,
        }

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        url = f"{base_url}/chat/completions"
        resp = httpx.post(url, headers=headers, json=payload, timeout=60)
        if resp.status_code >= 400:
            raise RuntimeError(f"Nebius {resp.status_code}: {resp.text} Sent payload: {payload}")

        data = resp.json()
        try:
            text = data["choices"][0]["message"]["content"]
        except Exception:
            text = str(data)

        return _NebiusRawResponse(resp, text)


class _Messages:
    # IMPORTANT: .with_raw_response must be an OBJECT with .create (no parentheses)
    with_raw_response = _WithRawResponse()


class NebiusClient:
    def __init__(self):
        # nothing else required; we read env vars in _WithRawResponse
        self.messages = _Messages()  # so: client.beta.messages.with_raw_response.create works

    @property
    def beta(self):
        # The app calls client.beta.messages...
        return self
