import json
import threading
import requests
from gi.repository import GLib


class APIError(Exception):
    pass


class APIClient:
    def __init__(self, config):
        self.config = config

    def _headers(self):
        return {
            'Authorization': f'Bearer {self.config.api_key}',
            'Content-Type': 'application/json',
            'HTTP-Referer': self.config.get('site_url', ''),
            'X-Title': self.config.get('site_name', 'digest'),
        }

    def _url(self, path):
        return f"{self.config.base_url.rstrip('/')}/{path.lstrip('/')}"

    def complete(self, messages, system=None):
        if not self.config.api_key:
            raise APIError("No API key configured. Open Settings to add your OpenRouter API key.")
        payload = {'model': self.config.model, 'messages': messages}
        if system:
            payload['messages'] = [{'role': 'system', 'content': system}] + list(messages)
        try:
            resp = requests.post(
                self._url('/chat/completions'),
                headers=self._headers(),
                json=payload,
                timeout=120,
            )
            resp.raise_for_status()
            return resp.json()['choices'][0]['message']['content']
        except requests.HTTPError as e:
            try:
                detail = e.response.json().get('error', {}).get('message', str(e))
            except Exception:
                detail = str(e)
            raise APIError(f"API error: {detail}")
        except requests.RequestException as e:
            raise APIError(f"Network error: {e}")

    def complete_async(self, messages, system=None, on_done=None, on_error=None):
        def run():
            try:
                result = self.complete(messages, system=system)
                if on_done:
                    GLib.idle_add(on_done, result)
            except Exception as e:
                if on_error:
                    GLib.idle_add(on_error, str(e))
        threading.Thread(target=run, daemon=True).start()
