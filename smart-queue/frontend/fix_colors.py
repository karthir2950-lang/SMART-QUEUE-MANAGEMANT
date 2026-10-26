import os
import re

directory = r"c:\SMART QUEUE\smart-queue\frontend\src"

def process_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Remove excessive gradients completely where they involve indigo/purple
    # E.g., 'bg-gradient-to-r from-indigo-600 to-purple-600' -> 'bg-teal-700'
    content = re.sub(r'bg-gradient-to-[a-z]+\s+from-indigo-\d+\s+to-purple-\d+', 'bg-teal-700', content)
    
    # Text gradients
    content = re.sub(r'bg-clip-text\s+text-transparent\s+bg-gradient-to-[a-z]+\s+from-indigo-\d+\s+to-purple-\d+', 'text-teal-800', content)

    # 2. Replace indigo and purple with teal
    content = re.sub(r'indigo-(\d+)', r'teal-\1', content)
    content = re.sub(r'purple-(\d+)', r'teal-\1', content)

    # 3. Ensure rounded corners are consistent (using rounded-2xl or rounded-xl for soft borders)
    # This might be harder to safely regex without breaking things, so we'll stick to colors first.

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

for root, _, files in os.walk(directory):
    for file in files:
        if file.endswith('.jsx') or file.endswith('.js'):
            process_file(os.path.join(root, file))

print("Color replacements complete.")
