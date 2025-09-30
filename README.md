# Modular AI Cognitive Architecture - By Andrew 'Glass' Toto

This AI cognitive architecture is designed in a modular format to simulate the different parts of the brain.
Modules include but not limited to:
    Input | Chat (Response) | Thought | Memory
This system is also intended to contain multiple files that will be maintained and altered by the system to shape the AI's persona.
Current files include:
    Personality | conversation history | Long and Short Term Memory | Core Memory | Memory Bank | User Definition | System Prompts | State.json (emotional or system status)
The current structure will work based off of a dynamic learning system that the model refers to when needed and is encouraged to ask questions to gather information.
The AI will start with a small set of hardcoded facts and traits which will define the initial personality of the AI which will then grow over time.

Current System Pipeline:
    Receives user input
        Checks user input for 'exit' message to quit, otherwise continues
    Runs chat completion using the conversation history with added user input
        Instructs LLM to provide a response based on the most recent history message
        Also injects current mood into model as determined by the summarization function
    Creates a summary of the latest input output pair to determine mood shift or importance for memory
    Saves summary to short term memory with mood and importance value tags
    Gets new mood value based on most recent summary and applies it to the global mood setting

TODO:
    ReWrite README for new system!!!

    Remake persistant memory system

    Add user file system
    
Notes:
    personality file:
        Name, Core disposition, Favorite things, Special traits and quirks, Boundaries, Core values

    user Definition file:
        Name, Role, Relationship, Boundaries

    core memory file:
        Define this file as the model's reference bank and lightly restrict them to the information present in the bank.
            Should allow for the model to learn over time if the bank is dynamic
            Allows for responses that ask questions to learn more about unknown topics rather than hallucinating
            Can include:
                Core identity facts, Hardcoded facts and preferences, Stored memories, Explicit Boundaries
            * Acts similar to a library of information for the model to refer to when responding *

    conversation history:
        The literal conversation history from the last group of turns (currently 10 exchanges)

    long-term archive:
        A library of vectors that can be referenced as past memories that are not always passed to the model
            Should be able to implement this as a tool function later on
            Possibly used in memory "resting" where they are triggered by keywords
