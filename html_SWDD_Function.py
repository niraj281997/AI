import os
import re
import zlib
import base64
import requests
import time
from google import genai
from google.genai import types
from google.genai import errors

# --- CONFIGURATION ---
client = genai.Client()
# Updated to use the lite model as requested
MODEL_ID = "gemini-2.0-flash-lite" 

def plantuml_encode(puml_text):
    """Encodes PlantUML text using deflate + custom base64."""
    # Standard PlantUML encoding process
    zlib_ordered_data = zlib.compress(puml_text.encode('utf-8'))[2:-4]
    standard_b64 = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
    plantuml_b64 = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz-_"
    encoded = base64.b64encode(zlib_ordered_data).decode('utf-8')
    translation_table = str.maketrans(standard_b64, plantuml_b64)
    return encoded.translate(translation_table)

def extract_functions(file_path):
    """Extracts C functions from the source file."""
    with open(file_path, "r") as f:
        content = f.read()
    # Matches common C function patterns
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

def generate_content_with_retry(prompt, system_instruction, max_retries=5):
    """Helper to handle 429 Resource Exhausted errors with exponential backoff."""
    # Force string type to prevent Pydantic validation errors
    model_name = str(MODEL_ID).strip()
    
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model=model_name,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.2 
                ),
                contents=prompt
            )
            return response.text
        except errors.ClientError as e:
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                # Lite models have tighter quotas, so we wait longer
                wait_time = (2 ** attempt) + 15 
                print(f"   ⚠️ Rate limit hit (Lite Model). Waiting {wait_time}s to retry...")
                time.sleep(wait_time)
            else:
                print(f"   ❌ API Error: {e}")
                raise e
    raise Exception("Max retries exceeded for Gemini API.")

def generate_swdd(source_path):
    abs_path = os.path.abspath(source_path)
    directory = os.path.dirname(abs_path)
    base_name = os.path.splitext(os.path.basename(abs_path))[0]
    html_output = os.path.join(directory, f"{base_name}_SWDD.html")

    if not os.path.exists(abs_path):
        print(f"❌ Source file not found: {abs_path}")
        return

    functions = extract_functions(abs_path)
    if not functions:
        print("❌ No functions found in the source file.")
        return

    print(f"🚀 Processing {len(functions)} functions using {MODEL_ID}...")

    html_body = f"""
    <html>
    <head>
        <meta charset="UTF-8">
        <title>SWDD: {base_name}.c</title>
        <style>
            body {{ font-family: -apple-system, system-ui, sans-serif; line-height: 1.6; padding: 50px; color: #24292f; max-width: 1100px; margin: auto; background-color: #fcfcfc; }}
            h1 {{ border-bottom: 2px solid #eaecef; padding-bottom: 10px; color: #0969da; }}
            .function-block {{ margin-bottom: 60px; background: white; border: 1px solid #d0d7de; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }}
            .func-header {{ background: #f6f8fa; padding: 15px; border-bottom: 1px solid #d0d7de; }}
            .func-name {{ color: #cf222e; font-family: 'SFMono-Regular', Consolas, monospace; font-size: 1.2em; font-weight: bold; }}
            .summary {{ padding: 20px; border-bottom: 1px dashed #eee; font-style: italic; color: #57606a; }}
            .diagram-container {{ text-align: center; padding: 30px; background: white; }}
            svg {{ max-width: 100%; height: auto; }}
            .footer {{ font-size: 0.8em; color: #888; text-align: center; margin-top: 50px; }}
        </style>
    </head>
    <body>
        <h1>Software Design Document (SWDD)</h1>
        <p><strong>Generated for:</strong> <code>{abs_path}</code></p>
        <hr>
    """

    sys_instr = """
    You are a Linux Kernel Architect. Analyze the provided C function.
    Output format:
    [SUMMARY] Write a 2-sentence summary of what this function does.
    [PLANTUML] Provide ONLY the @startuml to @enduml block.
    """

    for i, func_code in enumerate(functions):
        try:
            func_name = func_code.split('(')[0].strip().split()[-1].replace('*', '')
        except:
            func_name = f"Function_{i+1}"
        
        print(f"   [{i+1}/{len(functions)}] Analyzing: {func_name}")

        ai_text = generate_content_with_retry(
            prompt=f"Analyze this function:\n\n{func_code}",
            system_instruction=sys_instr
        )
        
        summary_match = re.search(r"\[SUMMARY\](.*?)(\[|$)", ai_text, re.DOTALL)
        puml_match = re.search(r"(@startuml.*?@enduml)", ai_text, re.DOTALL)
        
        summary = summary_match.group(1).strip() if summary_match else "Technical summary unavailable."
        
        diagram_html = ""
        if puml_match:
            puml_text = puml_match.group(1).strip()
            encoded = plantuml_encode(puml_text)
            puml_url = f"http://www.plantuml.com/plantuml/svg/{encoded}"
            try:
                svg_response = requests.get(puml_url, timeout=10)
                if svg_response.status_code == 200:
                    diagram_html = f'<div class="diagram-container">{svg_response.text}</div>'
                else:
                    diagram_html = "<p style='padding:20px;'>⚠️ PlantUML Server returned error.</p>"
            except Exception as e:
                diagram_html = f"<p style='padding:20px;'>⚠️ Render error: {str(e)}</p>"

        html_body += f"""
        <div class="function-block">
            <div class="func-header">
                <span class="func-name">{func_name}()</span>
            </div>
            <div class="summary">{summary}</div>
            {diagram_html}
        </div>
        """

    html_body += f"""
        <div class="footer">Generated on {time.ctime()} via {MODEL_ID}</div>
    </body>
    </html>
    """

    with open(html_output, "w", encoding='utf-8') as f:
        f.write(html_body)
    
    print(f"\n✨ DONE! Your local SWDD is ready at: {html_output}")

if __name__ == "__main__":
    target_file = "/Users/nirajgohel/Learning/character_device_driver/simple_char_driver.c"
    generate_swdd(target_file)
