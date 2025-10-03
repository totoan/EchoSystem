import os
import sys
import json
import asyncio
import functools
import websockets

from modules import (
    input_resources,
    chat_resources,
    memory_resources,
    thought_resources,
)

user = "Andrew" # TODO: Add user section to config and remove hardcoded user
history = []
mood = {"tag": ""}
MEM_TRIGGER = 10

def _base_path():
    if getattr(sys, "frozen", False):
        return sys._MEIPASS
    else: 
        return os.path.abspath(".")
    
def set_persona():
    base_path = _base_path()
    config_file = os.path.join(base_path, "config.json")
    with open(config_file, "r", encoding="utf-8") as f:
        config = json.load(f)
        PERSONA = config.get("ACTIVE_PERSONA", "")
    return PERSONA

def get_core_files():
    base_path = _base_path()
    def path(file_name): 
        return os.path.join(base_path, "personas", set_persona().lower(), file_name)
    personality_file = path("personality.txt")
    core_memory_file = path("core_memory.txt")
    memory_dir = path("memory")
    os.makedirs(memory_dir, exist_ok=True)
    user_file = os.path.join(base_path, "users", f"{user.lower()}.txt")
    print(f"Using core files:\nPersonality: {personality_file}\nCore memory:  {core_memory_file}\nUser: {user_file}")
    return personality_file, core_memory_file, user_file, memory_dir

def get_state():
    state_json = os.path.join(_base_path(), "state.json")
    with open(state_json, "r") as f:
        try:
            state = json.load(f)
            return state
        except FileNotFoundError:
            return {}
        
def save_state(new_state):
    state = get_state()
    state.update(new_state)
    state_json = os.path.join(_base_path(), "state.json")
    with open(state_json, "w") as f:
        json.dump(state, f)

async def primary_loop(ws, history, personality, user_file, mem_dir):
    print("client connected")
    # 0) get state
    state = get_state()

    try:
        async for user_text in ws:
            

            # 1) get input
            # user_text = input_resources.get_input()
            if user_text.lower() == "exit":
                print("Exiting...")
                sys.exit()

            memory_resources.save_event("user", user_text, mem_dir)

            # 2) chat (uses history for context)
            reply_text, history = await asyncio.to_thread(chat_resources.run_chat_completion,
                new_input=user_text,
                prompt="response_prompt.txt",
                history=history,
                personality_file=personality,
                user_file=user_file,
                mood=state.get("mood"),
                update_history=True
            )

            await ws.send(f"Assistant: {reply_text[0]}")
            print("Assistant: ", reply_text[0])

            memory_resources.save_event("assistant", reply_text[0], mem_dir)

            # 3) create memories from conversation history - Currently not in use
            # turn = state.get("turn", 0)
            # if turn == MEM_TRIGGER:
            #     memory = memory_resources.create_memories_from_history(
            #         history,
            #         prompt_file="extract_memories.txt",
            #         window=MEM_TRIGGER
            #         )
            #     if memory:
            #         print(f"[memory] created {len(memory)} fact(s): {[m['text'] for m in memory]}")
            #         save_state({"turn": 0})
            # elif turn < MEM_TRIGGER:
            #     save_state({"turn": turn+1})
            # print(f"[Turn Count]: {turn}")

            # 4) thought = analyze recent memory
            recent_events = memory_resources.load_events(n=10, mem_dir=mem_dir)
            analysis = thought_resources.analyze(recent_events, prompt_file="analyze_memories.txt")
            # expected JSON: e.g. {"mood": "calm", "decision": "reply"}
            new_mood = analysis.get("mood", "")
            if new_mood:
                save_state({"mood": new_mood})
                print(f"[mood] {new_mood}")
        
    except websockets.ConnectionClosedOK:
        print("client disconnected (OK)")
    except websockets.ConnectionClosedError as e:
        print(f"client disconnected with error: {e}")
    except Exception as e:
        print("Unhandled error in primary_loop:", repr(e))

async def main():
    personality_file, core_memory_file, user_file, mem_dir = get_core_files()
    history = memory_resources.load_history(n=20, mem_dir=mem_dir)
    print(f"[init] Loaded {len(history)} history messages from events file")

    host, port = "0.0.0.0", 5395

    handler = functools.partial(primary_loop,
                                history=history,
                                personality=personality_file,
                                user_file=user_file,
                                mem_dir=mem_dir,
                                )

    async with websockets.serve(handler, host, port):
        print(f"listening on ws://{host}:{port}")
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())

    # personality_file, core_memory_file, user_file, mem_dir = get_core_files()
    # history = memory_resources.load_history(n=20, mem_dir=mem_dir)
    # print(f"[init] Loaded {len(history)} history messages from events file")

    # while True:
    #     primary_loop(history, personality=personality_file, core_memory=core_memory_file, mem_dir=mem_dir)
