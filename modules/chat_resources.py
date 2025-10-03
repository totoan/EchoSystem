import os
import sys
import re
import uuid
import json
import httpx


def format_conversation_history(history):
    formatted_history = ""
    for message in list(history)[-10:]:
        prefix = "User:" if message["role"] == "user" else "assistant:"
        clean = re.sub(r"\b(Assistant|User)\s*:\s*", "", message["content"], flags=re.IGNORECASE).strip()
        formatted_history += f"{prefix} {clean}\n"
    return formatted_history

def build_system_prompt(new_input, 
                        formatted_history = "", 
                        prompt_file = "default.txt", 
                        personality_file = "",
                        user_file = "",
                        mood = "",
                        ):
    prompt_dir = "modules\prompts"
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.abspath(".")
    prompt_path = os.path.join(base_path, prompt_dir, prompt_file)
    print(f"Using prompt file: {prompt_path}")
    if not os.path.exists(prompt_path):
        raise FileNotFoundError(f"Prompt file '{prompt_path}' not found.")
    with open(prompt_path, "r", encoding="utf-8") as f:
        base_prompt = f.read()
    if prompt_file == "response_prompt.txt":
        with open(personality_file, "r", encoding="utf-8") as f:
            personality = f.read()
        with open(user_file, "r", encoding="utf-8") as f:
            core_memory = f.read()
        system_prompt = base_prompt.format(
            new_input=new_input,
            personality=personality,
            user_file=user_file,
            mood=mood,
            history=formatted_history
        )
    else:
        system_prompt = base_prompt.format(
            new_input=new_input
        )
    return system_prompt

def generate_response_from_ollama(prompt):
    request_id = str(uuid.uuid4())[:8]
    print(f"[Request {request_id}] Sending prompt to Ollama...")
    payload = {
        "model": "llama3",
        "prompt": prompt,
        "stream": True
    }
    final_response = ""
    with httpx.stream("POST", "http://localhost:11434/api/generate", json=payload, timeout=60.0) as r:
        for line in r.iter_lines():
            if not line.strip():
                continue
            try:
                chunk = json.loads(line)
                final_response += chunk.get("response", "")
            except json.JSONDecodeError:
                print(f"[Ollama Stream Error] Could not parse: {line}")
    return final_response
    
def parse_model_response(output_text):
    match = re.search(r"assistant:\s*(.*)", output_text, re.DOTALL)
    assistant_section = match.group(1).strip() if match else output_text.strip()
    assistant_section = re.sub(r"Tone:\s*\w+\s*\|\s*Emotion:\s*\w+", "", assistant_section).strip()
    assistant_reply_raw = assistant_section
    tags = re.findall(r"<([^:>]+):([^>]+)>", assistant_reply_raw)
    return assistant_section, tags

def run_chat_completion(new_input, prompt, history, personality_file, user_file, mood, update_history=False):
    formatted_history = format_conversation_history(history) if update_history else ""
    system_prompt = build_system_prompt(new_input, 
                                        formatted_history=formatted_history, 
                                        prompt_file=prompt, 
                                        personality_file=personality_file,
                                        user_file=user_file,
                                        mood=mood)
    response = generate_response_from_ollama(system_prompt)
    cleaned_response = parse_model_response(response)
    if update_history:
        history.append({"role": "user", "content": new_input})
        history.append({"role": "assistant", "content": cleaned_response[0]})
    return cleaned_response, history

if __name__ == "__main__":
    while True:
        new_input = input("Say something to test: ")
        output = run_chat_completion(new_input)
        print("Echo: ", output[0])
