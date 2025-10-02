# Modular AI Cognitive Architecture

This AI cognitive architecture is designed in a modular format to simulate the different parts of the brain.
Modules include but not limited to:
    Input | Chat (Response) | Thought | Memory
This system is also intended to contain multiple files that will be maintained and altered by the system to shape the AI's persona.
Current files include:
    Personality | conversation history | events | Core Memory | User Profile | System Prompts | State
The current structure will have access to a lengthy conversation history and shapes it's responses according to the personality file.
The AI will start with a small set of hardcoded facts and traits which will define the initial personality.

Current System Pipeline:
    Gathers needed files based on config (personality and user related files)
    Initializes Websocket endpoint (local LAN only)
    Receives user input from Websocket client
        Checks user input for 'exit' message to quit, otherwise continues
    Runs chat completion using the conversation history with added user input
        Instructs LLM to provide a response based on the most recent history message
        Also injects current mood into model as determined by the summarization function
    Gets new mood value based on most recent interaction and applies it to the state

TODO:
    Remake persistant memory system

    Add user file system
    
Notes:
    personality file:
        Name, Core disposition, Favorite things, Special traits and quirks, Boundaries, Core values

    user Definition file:
        Name, Role, Relationship, Boundaries

    core memory file:
        WIP

    conversation history (events.jsonl):
        The literal conversation history from the last group of turns (currently 10 exchanges)

    
