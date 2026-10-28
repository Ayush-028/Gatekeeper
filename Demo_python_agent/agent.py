
import os
import json
import time

import requests
from ddgs import DDGS
from dotenv import load_dotenv
from openai import OpenAI, RateLimitError, APIStatusError, APITimeoutError, APIConnectionError

# configure this in .env
load_dotenv()
API_KEY = os.getenv("API_KEY")
BASE_URL = os.getenv("BASE_URL")
MODEL = os.getenv("MODEL")



if not (API_KEY and BASE_URL and MODEL):
    raise RuntimeError("Missing API_KEY, BASE_URL or MODEL. Check your .env file.")

client = OpenAI(api_key=API_KEY, base_url=BASE_URL, timeout=90, max_retries=0)


# Tools 
def web_search(query: str) -> str:
    """Search the web and return titles, URLs and snippets."""
    try:
        results = DDGS().text(query, max_results=5)
    except Exception as e:
        return f"Search error: {e}"
    return json.dumps(
        [{"title": r["title"], "url": r["href"], "snippet": r["body"]} for r in results]
    )


def read_page(url: str) -> str:
    """Fetch a web page"""
    try:
        resp = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
    except Exception as e:
        return f"Error fetching page: {e}"
    return resp.text


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the web. Returns titles, URLs and snippets.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_page",
            "description": "Fetch a URL and return its text content.",
            "parameters": {
                "type": "object",
                "properties": {"url": {"type": "string"}},
                "required": ["url"],
            },
        },
    },
]
FUNCS = {"web_search": web_search, "read_page": read_page}

SYSTEM_PROMPT = (
    "You are a web research assistant. Use web_search to find sources and "
    "read_page to read them. Answer concisely and list the URLs you used."
)


# ---------- LLM call with simple retry on rate limits ----------
def call_llm(messages):
    for attempt in range(4):
        try:
            print("Calling model...")
            return client.chat.completions.create(
                model=MODEL, messages=messages, tools=TOOLS
            )
        except (RateLimitError, APITimeoutError, APIConnectionError) as e:
            wait = 5 * (attempt + 1)
            print(f"Temporary problem ({type(e).__name__}). Retrying in {wait}s...")
            time.sleep(wait)
        except APIStatusError as e:
            if e.status_code >= 500:  # 500, 503 etc: server-side, worth retrying
                wait = 5 * (attempt + 1)
                print(f"Server error {e.status_code}. Retrying in {wait}s...")
                time.sleep(wait)
            else:
                raise  # 400, 401, 404: retrying won't help
    raise RuntimeError("The model service is busy. Try again in a minute.")




# ---------- Agent loop ----------
def run_agent(task: str, max_steps: int = 8, on_step=None) -> str:
    """Run the agent. `on_step(text)` is called for each tool use (optional)."""
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": task},
    ]

    for _ in range(max_steps):
        msg = call_llm(messages).choices[0].message
        messages.append(msg.model_dump(exclude_none=True))

        if not msg.tool_calls:  # no tool requested -> this is the final answer
            return msg.content or ""

        for call in msg.tool_calls:
            name = call.function.name
            args = json.loads(call.function.arguments)
            step = f"{name}({args})"
            print("->", step)
            if on_step:
                on_step(step)

            if name in FUNCS:
                result = FUNCS[name](**args)
            else:
                result = f"Unknown tool: {name}"
            messages.append(
                {"role": "tool", "tool_call_id": call.id, "content": result}
            )

    return "Stopped: reached the maximum number of steps."


if __name__ == "__main__":
    while True:
        q = input("\nAsk something (or 'quit'): ").strip()
        if q.lower() in {"quit", "exit", ""}:
            break
        print("\n" + run_agent(q))
