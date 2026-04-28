import os
import re
import ast

def get_server_tools():
    with open('src/loom/server.py', 'r') as f:
        content = f.read()
    # Find all tools registered in the server
    # Look for @mcp.tool() or similar, or just find all async def / def
    tree = ast.parse(content)
    funcs = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if not node.name.startswith('_'):
                funcs.append(node.name)
    return funcs

def extract_ideas(directory):
    # Regex for tool-like names: snake_case starting with research_, fetch_, etc.
    idea_pattern = re.compile(r'\b(?:research|fetch|search|find|analyze|detect|run)_[a-z_]+\b')
    ideas = set()
    for root, _, files in os.walk(directory):
        for file in files:
            filepath = os.path.join(root, file)
            try:
                with open(filepath, 'r') as f:
                    content = f.read()
                    matches = idea_pattern.findall(content)
                    ideas.update(matches)
            except Exception:
                pass
    return ideas

def main():
    tools = set(get_server_tools())
    ideas = extract_ideas('docs/creative-research/')
    print("Total registered tools in server.py:", len(tools))
    print("Total unique ideas found:", len(ideas))
    print("\nIdeas NOT implemented:")
    for idea in sorted(ideas):
        if idea not in tools:
            print(f"GAP: {idea}")

if __name__ == '__main__':
    main()
