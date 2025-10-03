import json
from modules import (chat_resources, memory_resources)

def analyze(events, prompt_file="analyze_memories.txt"):
    """
    Ask the model to analyze recent events.
    Expected to return JSON, e.g. {"mood": "calm", "decision": "reply"}
    """
    if not events:
        print("Not events")
        return {}
    
    lines = []
    for e in events[-1:]:
        role = e.get("role", "user")
        text = (e.get("text") or "").strip()
        if text:
            lines.append(f"{role}: {text}")

    if not lines:
        print("Not lines")
        return {}
    
    input_text = "\n".join(lines)
    response, _ = chat_resources.run_chat_completion(
        new_input=input_text,
        history=[],
        prompt=prompt_file,
        personality_file="",
        user_file="",
        mood="",
        update_history=False
    )
    text = response[0].lower()
    block = memory_resources._extract_json_block(text)
    try:
        return json.loads(block)
    except json.JSONDecodeError:
        return {"raw": response}
    