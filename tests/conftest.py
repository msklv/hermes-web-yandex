"""Test harness for the Hermes plugin outside the Hermes runtime.

provider.py does ``from agent.web_search_provider import ...`` at import time — that
package only exists inside a running Hermes install. We inject minimal stand-ins and
load ``provider.py`` by file path so the plugin's ``__init__.py`` (which does a
relative import and is not a real package here) is never touched.
"""
import importlib.util
import os
import sys
import types
from pathlib import Path

# --- minimal stand-ins for the Hermes runtime -------------------------------
ws_prov = types.ModuleType("agent.web_search_provider")


class WebSearchProvider:
    name = "base"


def get_provider_env(name: str) -> str:
    return os.getenv(name, "")


ws_prov.WebSearchProvider = WebSearchProvider
ws_prov.get_provider_env = get_provider_env

agent = types.ModuleType("agent")
agent.web_search_provider = ws_prov
sys.modules["agent"] = agent
sys.modules["agent.web_search_provider"] = ws_prov

# --- load provider.py directly (bypasses the non-package __init__.py) -----
PROVIDER_PATH = Path(__file__).resolve().parent.parent / "provider.py"
_spec = importlib.util.spec_from_file_location("provider", PROVIDER_PATH)
_provider = importlib.util.module_from_spec(_spec)
sys.modules["provider"] = _provider
assert _spec.loader is not None
_spec.loader.exec_module(_provider)