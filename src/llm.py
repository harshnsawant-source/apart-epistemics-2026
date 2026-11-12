"""Model calls. Groq (OpenAI-compatible) and local Ollama. Standard library only.

The Groq key comes from the GROQ_API_KEY environment variable (a repository secret in GitHub Actions, the
user environment on the laptop). It is never written to a file.
"""
import json
import os
import time
import urllib.error
import urllib.request


class DailyLimit(Exception):
    """Groq asked for a long wait: the daily quota is used up. Stop; the run is resumable."""


class Transient(Exception):
    """A transport problem worth retrying: timeout, connection failure, 5xx, or a short rate-limit.
    `wait` is how long the server asked us to wait, if it said."""

    def __init__(self, msg, wait=None):
        super().__init__(msg)
        self.wait = wait


def _groq_key():
    key = os.environ.get("GROQ_API_KEY")
    if not key and os.name == "nt":
        import winreg
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as k:
                key = winreg.QueryValueEx(k, "GROQ_API_KEY")[0]
        except OSError:
            key = None
    if not key:
        raise RuntimeError("GROQ_API_KEY not set")
    return key


def _wait_seconds(headers):
    for h in ("retry-after", "x-ratelimit-reset-tokens", "x-ratelimit-reset-requests"):
        v = headers.get(h)
        if v:
            try:
                return float(v)
            except ValueError:
                total, num = 0.0, ""
                for ch in v:                      # Groq formats like "1m26.4s" or "2.08s"
                    if ch.isdigit() or ch == ".":
                        num += ch
                    elif ch in "hms" and num:
                        total += float(num) * {"h": 3600, "m": 60, "s": 1}[ch]
                        num = ""
                return total
    return 30.0


def groq(model, messages, temperature, seed, max_tokens, **extra):
    body = json.dumps(dict({"model": model, "messages": messages, "temperature": temperature, "seed": seed,
                            "max_completion_tokens": max_tokens}, **extra)).encode()
    # One attempt only. Retrying is done by run.attempt, so every attempt can be logged.
    req = urllib.request.Request("https://api.groq.com/openai/v1/chat/completions", data=body,
                                 headers={"Content-Type": "application/json", "User-Agent": "audit-study/1.0",
                                          "Authorization": f"Bearer {_groq_key()}"})
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            d = json.load(r)
    except urllib.error.HTTPError as e:
        if e.code == 429:
            wait = _wait_seconds(e.headers)
            if wait > 900:
                raise DailyLimit(f"Groq asks to wait {wait:.0f}s")
            raise Transient("HTTP 429", wait=wait + 1)
        if e.code >= 500:
            raise Transient(f"HTTP {e.code}")
        raise
    except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as e:
        raise Transient(type(e).__name__)
    m = d["choices"][0]["message"]
    return {"text": m.get("content") or "", "reasoning_chars": len(m.get("reasoning") or ""),
            "usage": d.get("usage") or {}, "model_used": d.get("model"),
            "finish": d["choices"][0].get("finish_reason")}


def ollama(model, messages, temperature, seed, max_tokens, **extra):
    body = json.dumps({"model": model, "messages": messages, "stream": False,
                       "options": {"temperature": temperature, "seed": seed, "num_predict": max_tokens}}).encode()
    req = urllib.request.Request("http://localhost:11434/api/chat", data=body,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=900) as r:
            d = json.load(r)
    except urllib.error.HTTPError as e:
        if e.code >= 500:
            raise Transient(f"HTTP {e.code}")
        raise
    except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as e:
        raise Transient(type(e).__name__)
    return {"text": d["message"]["content"], "reasoning_chars": 0,
            "usage": {"prompt_tokens": d.get("prompt_eval_count"), "completion_tokens": d.get("eval_count")},
            "model_used": d.get("model"), "finish": d.get("done_reason")}


BACKENDS = {"groq": groq, "ollama": ollama}
