# Gatekeeper

**Check what your AI agent reads before it acts.**
Gatekeeper sits in front of the tool your agent uses to read web pages, and blocks hidden instructions
(prompt injection) before the model sees them. It also ships with **Learn Mode**, a local page that
teaches how each attack works.

## Install
    pip install git+https://github.com/<you>/gatekeeper.git

## Protect your agent (one line)
Find the function that reads web pages. Make it return the page's raw HTML and add `@protect`:

```python
from gatekeeper import protect

@protect
def read_page(url):
    return requests.get(url, timeout=10).text     # raw HTML in, clean text (or a BLOCKED message) out
```
Works with normal and `async` functions, and with any agent or framework that calls your Python functions.
Try it offline: `python examples/protect_example.py`.

Other ways to use it:
```python
from gatekeeper import safe_fetch, scan_html
page = safe_fetch("https://example.com")           # fetch + check
if not page.blocked: text = page.clean_text
result = scan_html(html_you_already_have)          # check HTML from anywhere
```

## Learn Mode (opens in your browser)
    gatekeeper

Pick an attack, scan it, and see what a person sees, what a naive agent reads, and why Gatekeeper blocks it.
Runs on your computer; nothing is hosted. Check a page from the terminal with `gatekeeper scan page.html`.

## How it works
1. **Rules**: hidden comments, CSS-hidden text, invisible characters, encoded text, commands aimed at the AI
2. **Score**: signals add up. 0-2 pass, 3-6 unsure, 7+ block
3. **AI check (hosted, on by default)**: only unsure pages are sent to a small hosted service for a second opinion.
   The text leaves your computer, and Gemini's free tier may use inputs to improve Google's products.
   Turn it off: `GATEKEEPER_LAYER3=off`. If the service is down, layers 1, 2 and 4 keep working.
4. **Canary** (`gatekeeper.canary`): plant a fake secret in your agent's prompt and check its output for it.

## Limits
One layer of defense, not a cure-all. It catches common patterns and cannot guarantee safety.
It only protects tools you can wrap as Python functions (not a closed, built-in browser tool).

## Develop
    pip install -e . pytest && pytest
Layer 3 server: see `docs/DEPLOY_LAYER3.md`.

</br>

>[!Note]
>This project was made for a hackathon and is mostly **AI Slop**
