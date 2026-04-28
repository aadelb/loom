import json
import re
import sys

def main():
    with open('audit_final.txt', 'r') as f:
        text = f.read()
    
    # We will parse audit_final.txt and build a clean list.
    lines = text.split('\n')
    
    ideas = []
    not_implemented = []
    
    current_not_implemented_name = None
    current_not_implemented_desc = []
    
    mode = "ideas"
    for line in lines:
        if line.startswith("--- NOT_IMPLEMENTED IDEAS ---"):
            mode = "desc"
            continue
        
        if mode == "ideas":
            if line.startswith("IDEA: "):
                ideas.append(line)
        elif mode == "desc":
            if line.startswith("--- ") and line.endswith(" ---"):
                if current_not_implemented_name:
                    not_implemented.append((current_not_implemented_name, "\n".join(current_not_implemented_desc).strip()))
                current_not_implemented_name = line[4:-4]
                current_not_implemented_desc = []
            else:
                if current_not_implemented_name:
                    current_not_implemented_desc.append(line)

    if current_not_implemented_name:
        not_implemented.append((current_not_implemented_name, "\n".join(current_not_implemented_desc).strip()))

    # Filter rules for noise reduction:
    def is_valid_tool(name, desc):
        # Exclude very short descriptions (probably utility)
        if len(desc) < 15: return False
        # Exclude typical utility names
        bad_words = ['_fetch_', '_get_', '_check_', '_parse_', '_extract_', '_read_', '_write_', '_request_', '_initialize_', '_cleanup_', '_run_', '_make_', '_test_', '_save_', '_process_', 'research_description', 'research_implementation', 'research_key_features', 'research_advanced_features', 'research_all_10_', 'research_free_data', 'research_full_async', 'research_compedgeai']
        for bad in bad_words:
            if bad in name: return False
        
        # Exclude generic utility functions
        if name in ['research_analyze', 'research_correlate', 'research_discover', 'research_enumerate', 'research_gather', 'research_aggregate', 'research_fetch', 'research_map_assets', 'research_setup', 'research_cleanup', 'research_run']:
            return False
            
        return True

    filtered_not_implemented = [x for x in not_implemented if is_valid_tool(x[0], x[1])]
    valid_names = {x[0] for x in filtered_not_implemented}
    
    # Get IMPLEMENTED from the ideas section
    valid_ideas = []
    for idea in ideas:
        match = re.match(r'IDEA:\s*(.*?)\s*\|', idea)
        if match:
            name = match.group(1)
            if "STATUS: IMPLEMENTED" in idea:
                valid_ideas.append(idea)
            elif name in valid_names:
                valid_ideas.append(idea)

    with open('filtered_output.txt', 'w') as out:
        for idea in valid_ideas:
            out.write(idea + '\n')
            
        out.write('\n\n--- NOT_IMPLEMENTED IDEAS ---\n')
        for name, desc in filtered_not_implemented:
            # truncate very long descriptions to max 3 sentences or 400 chars
            sentences = [s.strip() for s in desc.split('.') if s.strip()]
            short_desc = '. '.join(sentences[:3]) + ('.' if sentences[:3] else '')
            if len(short_desc) > 500:
                short_desc = short_desc[:497] + '...'
            out.write(f'--- {name} ---\n{short_desc}\n\n')

if __name__ == "__main__":
    main()
