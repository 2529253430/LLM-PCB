import json
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parent.parent.parent
KNOWLEDGE_DIR = BASE_DIR / "src" / "knowledge"


def load_json(filename: str) -> dict[str, Any]:
    """
    从知识库目录读取 JSON 文件。
    """
    file_path = KNOWLEDGE_DIR / filename

    if not file_path.exists():
        raise FileNotFoundError(
            f"Knowledge file does not exist: {file_path}"
        )

    with file_path.open("r", encoding="utf-8") as file:
        return json.load(file)


def load_topology_knowledge() -> dict[str, Any]:
    """
    读取拓扑知识。
    """
    return load_json("topology.json")


def load_placement_rules() -> dict[str, Any]:
    """
    读取布局规则。
    """
    return load_json("placement_rules.json")


def load_routing_rules() -> dict[str, Any]:
    """
    读取布线规则。
    """
    return load_json("routing_rules.json")


if __name__ == "__main__":
    topology = load_topology_knowledge()
    placement = load_placement_rules()
    routing = load_routing_rules()

    print("Supported Topologies:")
    for topology_name in topology:
        print("-", topology_name)

    print("Placement rules loaded:", len(placement))
    print("Routing rules loaded:", len(routing))