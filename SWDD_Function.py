
import os
import re
from google import genai
from google.genai import types

client = genai.Client()

def extract_functions(file_path):
    """Parses a C file to extract individual function blocks."""
    with open(file_path, "r") as f:
        content = f.read()
    
    # Matches common C function patterns: static/int/void name(args) { body }
    pattern = r"((?:static\s+|inline\s+)?[\w\d\*\_]+\s+[\w\d\_]+\s*\([^)]*\)\s*\{)"
    splits = re.split(pattern, content)
    
    functions = []
    for i in range(1, len(splits), 2):
        func_sig = splits[i]
        func_rest = splits[i+1]
        
        brace_count = 1
        func_body = ""
        for char in func_rest:
            func_body += char
            if char == '{': brace_count += 1
            if char == '}': brace_count -= 1
            if brace_count == 0: break
        
        functions.append(func_sig + func_body)
    return functions

def generate_functional_swdd(source_path):
    # 1. Setup Paths
    abs_source_path = os.path.abspath(source_path)
    directory = os.path.dirname(abs_source_path)
    base_name = os.path.splitext(os.path.basename(abs_source_path))[0]
    output_path = os.path.join(directory, f"{base_name}_SWDD.md")

    # 2. Extract Functions
    functions = extract_functions(abs_source_path)
    if not functions:
        print("❌ No functions detected. Check your regex or file content.")
        return

    print(f"📂 Source: {abs_source_path}")
    print(f"📝 Target: {output_path}")
    print(f"🔍 Found {len(functions)} functions. Processing...")

    sys_instr = """
    You are a Technical Architect. For the provided C function, produce:
    1. A brief summary (2 sentences max).
    2. A PlantUML Activity Diagram (flowchart) for the internal logic.
    Use clean Markdown formatting.
    """

    catalog = [f"# Software Design Document: {base_name}.c\n\n"]

    for func_code in functions:
        # Extract function name for logging
        try:
            func_name = func_code.split('(')[0].split()[-1].replace('*', '')
        except IndexError:
            func_name = "Unknown_Function"
            
        print(f"   -> Analyzing: {func_name}")

        response = client.models.generate_content(
            model="gemini-2.5-flash-lite",
            config=types.GenerateContentConfig(system_instruction=sys_instr),
            contents=f"Analyze this function:\n\n{func_code}"
        )
        catalog.append(f"## Function: {func_name}\n\n{response.text}\n\n---\n")

    # 3. Save Output
    with open(output_path, "w") as f:
        f.write("\n".join(catalog))
    
    print(f"\n✅ Success! File created at: {output_path}")

# Example Usage:
user_file = "/Users/nirajgohel/Learning/character_device_driver/simple_char_driver.c"
generate_functional_swdd(user_file)
