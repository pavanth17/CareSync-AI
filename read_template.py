#!/usr/bin/env python3
"""Read template file directly from disk"""

with open('templates/discharged_dashboard.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

print(f"Total lines: {len(lines)}")

# Find lines with key patterns
for i, line in enumerate(lines, 1):
    if 'function initializeButtonHandlers' in line:
        print(f"Line {i}: {line.strip()}")
    if "window.addEventListener('load'" in line and 'function()' in line:
        print(f"Line {i}: {line.strip()}")

# Print lines 494-502 for inspection
print("\nLines 494-502:")
for i in range(493, min(502, len(lines))):
    print(f"{i+1}: {lines[i].rstrip()}")
