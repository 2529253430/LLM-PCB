from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.constraint.graph_builder import GraphBuilder
from src.constraint.knowledge_enricher import KnowledgeEnricher
from src.constraint.rule_engine import RuleEngine

def build_test_design():
    """
    建立一个 24V 转 5V、3A 的 Buck 测试设计。
    """

    vin = 24
    vout = 5
    current = 3
    priority = "Efficiency"
    topology_name = "Buck"

    builder = GraphBuilder()

    graph = builder.build(
        vin=vin,
        vout=vout,
        current=current,
        priority=priority,
    )

    enricher = KnowledgeEnricher()

    graph = enricher.enrich_topology(
        graph=graph,
        topology_name=topology_name,
    )

    graph = enricher.enrich_controller_candidates(
        graph=graph,
        topology_name=topology_name,
        vin=vin,
        vout=vout,
        current=current,
        limit=3,
    )

    rule_engine = RuleEngine()

    graph = rule_engine.apply_rules(
        graph=graph,
        topology_name=topology_name,
    )

    return graph


if __name__ == "__main__":
    design_graph = build_test_design()
    design_graph.show()