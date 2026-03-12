

import os
from google import genai
from google.genai import types

client = genai.Client()

def generate_swdd(file_path):
    with open(file_path, "r") as f:
        code_content = f.read()

    # Updated for PlantUML focus
    sys_instr = """
    You are a Senior Software Architect specializing in Linux Kernel development. 
    Your task is to analyze C code and produce a Software Design Document (SWDD). 
    Always include professional PlantUML diagrams (enclosed in @startuml and @enduml).
    Focus on Sequence Diagrams for function calls and State Diagrams for the driver lifecycle.
    """

    prompt = f"""
    Analyze the following Linux Character Driver code:
    ---
    {code_content}
    ---
    Generate:
    1. Module Overview.
    2. Detailed logic analysis of 'read' and 'write'.
    3. A PlantUML Activity Diagram for the 'read' function logic.
    4. A PlantUML State Diagram for the driver states (Unloaded -> Loaded -> Registered -> Open -> Closed).
    """

    response = client.models.generate_content(
        model="gemini-2.5-flash-lite",
        config=types.GenerateContentConfig(system_instruction=sys_instr),
        contents=prompt
    )
    
    return response.text

# Run it
print(generate_swdd("/Users/nirajgohel/Learning/character_device_driver/simple_char_driver.c"))
    
