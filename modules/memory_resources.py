import os
import sys
import json
import time
import re
from modules import chat_resources

MEM_FILE = "memories.jsonl"
INDEX_FILE = "memories_index.json"

def base_path():
    if getattr(sys, "frozen", False):
        return sys._MEIPASS
    else:
        return os.path.abspath(".")
    
def load_events(n = 10, mem_dir = ""):
    path = os.path.join(mem_dir, "events.jsonl")
    if not os.path.exists(path):
        print("[MEMORY] Error loading events")
    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()[-n:]
    events = []
    for ln in lines:
        events.append(json.loads(ln))
    return events
    
def load_history(n = 50, mem_dir = ""):
    events = load_events(n=n, mem_dir=mem_dir)
    history = []
    for e in events:
        role = e.get("role")
        if role not in ("user", "assistant"):
            continue
        history.append({"role": role, "content": e.get("text", "")})
    return history

def save_event(role, event, mem_dir):
    path = os.path.join(mem_dir, "events.jsonl")
    record = {
        "time-stamp": time.time(),
        "role": role,
        "text": event,
    }
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")
    return


### //////// REDO ALL CODE BELOW THIS LINE //////// ###

def _mem_path(mem_dir):
    mem_path = os.path.join(mem_dir, MEM_FILE)
    return mem_path

def _index_path(mem_dir):
    index_path = os.path.join(mem_dir, INDEX_FILE)
    return index_path

def _normalize(text):
    # Simple normalization key of upsert (phase 1):
    # lowercased, strip punctuation-like characters, collapse spaces
    t = text.lower()
    t = re.sub(r"[^\w\s]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t

def _load_index(mem_dir):
    path = _index_path(mem_dir)
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            index = json.load(f)
            return index
    except Exception:
        return {}
    
def _save_index(index, mem_dir):
    with open(_index_path(mem_dir), "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2, ensure_ascii=False)

def _append_memory(record, mem_dir):
    with open(_mem_path(mem_dir), "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

def _read_all(mem_dir):
    path = _mem_path(mem_dir)
    if not os.path.exists(path):
        return []
    out = []
    with open(path, "r", encoding="utf-8") as f:
        for ln in f:
            ln = ln.strip()
            if not ln:
                continue
            try:
                out.append(json.loads(ln))
            except json.JSONDecodeError:
                continue
    return out

def _extract_json_block(text):
    """
    Return the first JSON object/array found in s (tolerates prose).
    Handles ```json ... ``` fences, or inline JSON.
    """
    memory = re.search(r"```(?:json)?\s*(\{[\s\S]*?\}|\[[\s\S]*?\])\s*```", text, re.IGNORECASE)
    if memory:
        return memory.group(1).strip()
    for open_ch, close_ch in (("{", "}"), ("[", "]")):
        start = text.find(open_ch)
        while start != -1:
            depth = 0
            for i in range(start, len(text)):
                ch = text[i]
                if ch == open_ch:
                    depth += 1
                elif ch == close_ch:
                    depth -= 1
                    if depth == 0:
                        candidate = text[start:i+1]
                        try:
                            json.loads(candidate)
                            return candidate
                        except Exception:
                            break
            start = text.find(open_ch, start + 1)
    return None

def load_recent_memories(n = 10):
    """Return last n memory records (append-only order)."""
    allm = _read_all()
    return allm[-n:]

def find_exact(text):
    """Return the stored memory that matches this text's normalized key, if any."""
    key = _normalize(text)
    idx = _load_index()
    mem_id = idx.get(key)
    if not mem_id:
        return None
    # Scan backwards for the latest record with this id
    for record in reversed(_read_all()):
        if record.get("id") == mem_id:
            return record
    return None

def create_memories_from_history(
        history,
        prompt_file = "extract_memories.txt",
        window = 2
    ):
    """
    Use the LLM to extract concise memories from the recent chat history
    and save them into the memory store. Returns a list of saved records.
    """
    if not history:
        return []
    
    recent = history[-window:]
    transcript = chat_resources.format_conversation_history(recent)

    response_text, _ = chat_resources.run_chat_completion(
        new_input=transcript,
        prompt=prompt_file,
        history=[],
        personality_file="",
        core_memory_file="",
        mood="",
        update_history=False,
    )
    block = _extract_json_block(response_text[0])
    if not block:
        print("[memory] no JSON found; skipping")
        return []

    # Expected:
    # {"memories":[{"text":"...", "tags":["..."], "importance":0.2}, ...]}
    # or just a list: [{"text":"..."}}, ...]
    try:
        parsed = json.loads(block)
    except json.JSONDecodeError:
        print("[memory] LLM did not return JSON; skipping")
        return []
    
    if isinstance(parsed, dict) and "memories" in parsed:
        items = parsed["memories"]
    elif isinstance(parsed, list):
        items = parsed
    else:
        print("[memory] JSON shape not recognized; expected dict.memories or list")
        return []
    
    saved = []
    for item in items:
        text = (item.get("text") or "").strip()
        if not text:
            continue
        tags = item.get("tags") or []
        importance = float(item.get("importance", 0.2) or 0.2)
        record = save_memory(text, tags=tags, importance=importance, source="conversation")
        saved.append(record)
    if saved:
        print(f"[memory] saved {len(saved)} memory items(s)")
    return saved

def save_memory(
        text,
        *,
        tags = None,
        importance = 0.0,
        source = "conversation"
    ):
    """
    UPSERT by normalized text, First time we see the text -> create new memory.
    Next times -> bump times_seen, update updated_at, merge tags, max importance.
    Returns the stored record (latest).
    """
    ts = time.time() # timestamp
    key =  _normalize(text)
    idx = _load_index()
    mem_id = idx.get(key)

    if mem_id is None:
        # Create new record
        mem_id = f"m_{int(ts*1000)}"
        record = {
            "id": mem_id,
            "text": text,
            "norm_key": key,
            "tags": list(tags or []),
            "importance": float(importance or 0.0),
            "times_seen": 1,
            "source": source,
            "created_at": ts,
            "updated_at": ts,
        }
        _append_memory(record)
        idx[key] = mem_id
        _save_index(idx)
        return record
    else:
        # Update existing: create a new version line (append-only with updated fields)
        prev = None
        for r in reversed(_read_all()):
            if r.get("id") == mem_id:
                prev = r
                break
        if prev is None:
            # Index pointed to missing; treat as new
            return save_memory(text, tags=tags, importance=importance, source=source)
        
        merged_tags = sorted(set((prev.get("tags") or []) + (tags or [])))
        record = {
            **prev,
            "text": text,
            "tags": merged_tags,
            "importance": max(float(prev.get("importance", 0.0)), float(importance or 0.0)),
            "times_seen": int(prev.get("times_seen", 1)) + 1,
            "source": source,
            "updated_at": ts,
        }
        _append_memory(record)
        # index unchanged; mem_id stays the same
        return record
