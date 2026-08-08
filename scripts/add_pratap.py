import json

with open('/home/pi/ProductFlow/data/relay_pipelines.json') as f:
    pipelines = json.load(f)

pratap_groups = [
    "Pratap Bhai watch mumbai (B.T)",
    "120363161841232917@g.us",
    "120363144835818481@g.us"
]

for p in pipelines:
    if p['name'] == 'Test Pipeline':
        for g in pratap_groups:
            if g not in p['source_groups']:
                p['source_groups'].append(g)
                print('Added:', g)

with open('/home/pi/ProductFlow/data/relay_pipelines.json', 'w') as f:
    json.dump(pipelines, f, indent=2, ensure_ascii=False)

print('Total source groups:', len(pipelines[0]['source_groups']))
