from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.database.component_library import (
    ComponentLibrary,
)


if __name__ == "__main__":
    library = ComponentLibrary()

    part = library.load_part(
        "TPS5430DDA"
    )

    errors = library.validate_part(part)

    assert not errors, errors

    vin_pins = library.get_pin_by_role(
        part,
        "VIN",
    )

    sw_pins = library.get_pin_by_role(
        part,
        "SW",
    )

    fb_pins = library.get_pin_by_role(
        part,
        "FB",
    )

    gnd_pins = library.get_pin_by_role(
        part,
        "GND",
    )

    assert len(vin_pins) == 1
    assert len(sw_pins) == 2
    assert len(fb_pins) == 1
    assert len(gnd_pins) == 2

    print("=" * 60)
    print("COMPONENT LIBRARY VALIDATION")
    print("=" * 60)

    print(
        "Part:",
        part["part_number"],
    )
    print(
        "Symbol:",
        part["symbol_name"],
    )
    print(
        "Footprint:",
        part["footprint_name"],
    )

    print("VIN pins:", vin_pins)
    print("SW pins:", sw_pins)
    print("FB pins:", fb_pins)
    print("GND pins:", gnd_pins)

    print(
        "Component library validation passed."
    )