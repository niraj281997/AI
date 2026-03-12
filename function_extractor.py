import re
import sys
import os

def extract_and_print_functions(file_path):
    """
    Parses a C source file to extract function blocks using a 
    bracket-counting algorithm and prints them to the terminal.
    """
    if not os.path.exists(file_path):
        print(f"Error: File '{file_path}' not found.")
        return

    with open(file_path, "r") as f:
        content = f.read()

    # Regex to find potential function starts (return type + name + parameters + opening brace)
    # This handles standard C functions, static functions, and pointer return types.
    pattern = r"((?:static\s+|inline\s+)?[\w\d\*\_]+\s+[\w\d\_]+\s*\([^)]*\)\s*\{)"
    
    # Split the content by the function signature matches
    parts = re.split(pattern, content)
    
    found_functions = 0
    print(f"\n{'='*80}")
    print(f" EXTRACTING FUNCTIONS FROM: {os.path.basename(file_path)}")
    print(f"{'='*80}\n")

    # The re.split with a capturing group returns: [text_before, signature, body_and_rest, signature, body_and_rest, ...]
    for i in range(1, len(parts), 2):
        signature = parts[i]
        rest_of_code = parts[i+1]
        
        # Extract the function name for the label
        try:
            func_name = signature.split('(')[0].strip().split()[-1].replace('*', '')
        except:
            func_name = "Unknown"

        # Bracket counting to find the end of the function body
        brace_count = 1
        body = ""
        for char in rest_of_code:
            body += char
            if char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
            
            if brace_count == 0:
                break
        
        found_functions += 1
        
        # Print the extracted function to the terminal
        print(f"--- [Function {found_functions}: {func_name}] ---")
        print(signature + body)
        print("-" * (len(func_name) + 20) + "\n")

    print(f"{'='*80}")
    print(f" Total functions found: {found_functions}")
    print(f"{'='*80}\n")

if __name__ == "__main__":
    # You can change this path to your local C file
    default_path = "/Users/nirajgohel/Learning/character_device_driver/simple_char_driver.c"
    
    # Allow command line argument for the file path
    path = sys.argv[1] if len(sys.argv) > 1 else default_path
    
    extract_and_print_functions(path)
