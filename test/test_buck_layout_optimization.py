from src.design.buck_engine import BuckDesignEngine, BuckDesignInput, BuckICParameters
from src.schematic.buck_builder import BuckSchematicBuilder
from src.schematic.layout import BuckSchematicLayoutEngine
from src.schematic.layout_quality import SchematicLayoutScorer


def _design():
    inp = BuckDesignInput(18.0, 24.0, 5.0, 3.0)
    ic = BuckICParameters("EX36S4", 0.8, 500_000.0, 5.5)
    return BuckSchematicBuilder().build(inp, ic, BuckDesignEngine().design(inp, ic))


def test_optimized_layout_has_no_component_overlap():
    report = SchematicLayoutScorer().evaluate(BuckSchematicLayoutEngine().layout(_design()))
    assert report.component_overlaps == 0


def test_bootstrap_network_is_local():
    layout = BuckSchematicLayoutEngine().layout(_design())
    length = sum(abs(w.start.x-w.end.x)+abs(w.start.y-w.end.y) for w in layout.wires_for_net("BOOT"))
    assert length < 50.0


def test_feedback_is_not_global_bus():
    layout = BuckSchematicLayoutEngine().layout(_design())
    assert max(abs(w.start.x-w.end.x) for w in layout.wires_for_net("FB")) < 120.0


def test_quality_report_is_available():
    report = SchematicLayoutScorer().evaluate(BuckSchematicLayoutEngine().layout(_design()))
    assert report.score > 80.0
