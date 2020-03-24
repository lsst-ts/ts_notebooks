import re
import sys

try:
    target_str = sys.argv[1]
except IndexError:
    print("Need to pass a target string.")
    
values = target_str.split()

values[0] = values[0].replace('.', '')
match = re.search(r'\W{1}', values[2])
if match is not None:
    offset = 0
else:
    offset = 1

match = re.search(r'\d+', values[2 + offset])
if match is not None:
    values[2 + offset] = values[2 + offset][match.start():]
else:
    del values[2 + offset]

target = ''.join(values[0:2 + offset])
ra = ' '.join(values[2 + offset:5 + offset])
dec = ' '.join(values[5 + offset:8 + offset])
params = f"ra=\"{ra}\", dec=\"{dec}\", target_name=\"{target}\""
params2 = f"ra=\"{ra}\", dec=\"{dec}\", rot_pa=-138.-75., target_name=\"{target}\""
print(target)
print(params)
print(params2)