import json
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent.parent
KNOWLEDGE_DIR = BASE_DIR / "src" / "knowledge"


def load_topology():

    with open(KNOWLEDGE_DIR / "topology.json",
              "r",
              encoding="utf-8") as f:

        return json.load(f)


topology = load_topology()


def select_topology(vin, vout):

    if vin > vout:
        return "Buck"

    elif vin < vout:
        return "Boost"

    else:
        return "Unknown"


if __name__ == "__main__":

    vin = float(input("Input Voltage(V): "))

    vout = float(input("Output Voltage(V): "))

    result = select_topology(vin, vout)

    print()

    print("Recommended Topology:", result)

    print()

    print(topology[result]["description"]
          if result in topology
          else "No Topology")