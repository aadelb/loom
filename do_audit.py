import os
import re
import glob

def audit():
    # 1. Find all research_ functions in src/loom/tools/
    tools_dir = 'src/loom/tools/'
    registrations_dir = 'src/loom/registrations/'
    
    function_pattern = re.compile(r'(?:async\s+)?def\s+(research_[a-zA-Z0-9_]+)')
    
    # functions mapping: name -> filename
    tools_functions = {}
    for root, dirs, files in os.walk(tools_dir):
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                    matches = function_pattern.findall(content)
                    for match in matches:
                        tools_functions[match] = filepath
                        
    # 2. Find all registrations in src/loom/registrations/
    # Usually it looks like:
    # mcp.tool()(research_func) or @mcp.tool(...) def research_func
    # Let's just find all occurrences of "research_[a-zA-Z0-9_]+" in registrations directory
    
    registered_names = set()
    registration_files = {}
    
    for root, dirs, files in os.walk(registrations_dir):
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # Find all mentions of research_ functions
                    mentions = re.findall(r'(research_[a-zA-Z0-9_]+)', content)
                    for mention in mentions:
                        registered_names.add(mention)
                        if mention not in registration_files:
                            registration_files[mention] = []
                        registration_files[mention].append(filepath)

    # 3. Find unregistered tools (in tools_functions but not in registered_names)
    unregistered = []
    for func, filepath in tools_functions.items():
        if func not in registered_names:
            unregistered.append(func)
            
    # 4. Find broken registrations (in registered_names but not in tools_functions)
    broken = []
    for func in registered_names:
        if func not in tools_functions:
            broken.append(func)

    # Note: Sometimes a function might be defined in registrations/ directly, we should check if they are in tools_functions or defined in registrations.
    # Let's refine broken: check if it's defined in registrations
    for root, dirs, files in os.walk(registrations_dir):
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                    matches = function_pattern.findall(content)
                    for match in matches:
                        if match in broken:
                            broken.remove(match) # It's defined in registration file itself
                            # and add to tools_functions so it counts as a function
                            tools_functions[match] = filepath
                            
    # Also we should count actual registrations, which is the number of @mcp.tool or mcp.tool()
    reg_count_pattern = re.compile(r'mcp\.tool|record_success')
    reg_count = 0
    for root, dirs, files in os.walk(registrations_dir):
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.split('\n')
                    for line in lines:
                        if reg_count_pattern.search(line):
                            reg_count += 1
                            
    func_count = len(tools_functions)
    
    print(f"FUNCTION_COUNT: {func_count}")
    print(f"REGISTERED_COUNT (approx by mcp.tool/record_success): {reg_count}")
    print(f"Functions imported/used in registrations: {len(registered_names)}")
    
    print("\n--- UNREGISTERED TOOLS ---")
    for func in sorted(unregistered):
        print(f"{func} (in {tools_functions[func]})")
        
    print("\n--- BROKEN REGISTRATIONS ---")
    for func in sorted(broken):
        print(f"{func} (mentioned in {registration_files[func]})")

if __name__ == '__main__':
    audit()
