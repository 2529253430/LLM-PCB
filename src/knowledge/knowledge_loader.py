import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

KNOWLEDGE_DIR = BASE_DIR / "src" / "knowledge"


def load_json(filename):
    with open(KNOWLEDGE_DIR / filename, "r", encoding="utf-8") as f:
        return json.load(f)


topology = load_json("topology.json")
placement = load_json("placement_rules.json")
routing = load_json("routing_rules.json")

print("Supported Topologies:")
for name in topology:
    print("-", name)
print("Placement Rules Loaded")
print("Routing Rules Loaded")