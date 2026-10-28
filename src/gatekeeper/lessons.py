"""Learn Mode text. One short lesson per signal, written by hand (no AI needed)."""

LESSONS = {
    "hidden_comment": {
        "title": "Hidden comment caught",
        "what": "An HTML comment contained instructions aimed at an AI.",
        "why": "You can't see comments on a page, but an agent reading the source can, and may obey them.",
        "spot": "Look for text that talks to the AI instead of the reader, especially inside <!-- -->.",
    },
    "hidden_css": {
        "title": "Invisible text caught",
        "what": "Text was hidden with CSS (display:none, tiny font, off-screen).",
        "why": "People never see it, but an agent that reads the page text does.",
        "spot": "Check the page source for styles like display:none or font-size:0 on text blocks.",
    },
    "zero_width": {
        "title": "Invisible characters caught",
        "what": "Zero-width characters were mixed into plain text.",
        "why": "They can split or disguise words so simple filters miss them, while the AI still reads the message.",
        "spot": "Copy suspicious text into a tool that shows hidden characters.",
    },
    "encoded_text": {
        "title": "Encoded message caught",
        "what": "A base64 string on the page decoded into readable text.",
        "why": "Encoding hides commands from human readers and from basic keyword filters.",
        "spot": "Long random-looking strings of letters and digits can hide a message.",
    },
    "ai_phrase": {
        "title": "Command aimed at the AI",
        "what": "The page contains phrases like 'ignore previous instructions' or 'note to the assistant'.",
        "why": "Real content is written for readers. Text addressed to the AI is a strong sign of an attack.",
        "spot": "Be suspicious of any page that gives orders to 'the assistant' or tells it to forget its rules.",
    },
    "secret_request": {
        "title": "Request for secrets or data",
        "what": "The text asks the AI to reveal or send out keys, passwords, or other private data.",
        "why": "This is how prompt injection steals information without the user noticing.",
        "spot": "A web page has no reason to ask an assistant for secrets.",
    },
    "hidden_instruction": {
        "title": "Instruction hidden on purpose",
        "what": "Instruction-like text was found inside hidden content.",
        "why": "Legitimate pages rarely hide commands. Hiding them means the author didn't want you to see them.",
        "spot": "Hidden content plus commands is the clearest sign of a prompt injection attack.",
    },
}


def explain(signals) -> list:
    """Turn detected signals into lesson cards for the UI."""
    cards = []
    for s in signals:
        lesson = LESSONS.get(s.name)
        if lesson:
            cards.append({**lesson, "evidence": s.evidence, "points": s.points})
    return cards
