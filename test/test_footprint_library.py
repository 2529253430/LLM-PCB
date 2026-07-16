from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.database.footprint_library import (
    FootprintLibrary,
)


if __name__ == "__main__":
    library = FootprintLibrary()

    footprint = library.load_footprint(
        "SOIC-8-PowerPAD-DDA"
    )

    errors = library.validate_footprint(
        footprint
    )

    assert not errors, errors

    assert len(
        footprint["pads"]
    ) == 9

    pad_7 = library.get_pad(
        footprint,
        "7",
    )

    assert pad_7["x"] == 2.7
    assert pad_7["y"] == 0.635

    absolute_position = (
        library.get_absolute_pad_position(
            footprint_data=footprint,
            pad_number="7",
            component_x=50.0,
            component_y=40.0,
        )
    )

    assert absolute_position == (
        52.7,
        40.635,
    )

    print("=" * 60)
    print("FOOTPRINT LIBRARY VALIDATION")
    print("=" * 60)

    print(
        "Footprint:",
        footprint["footprint_name"],
    )
    print(
        "Body:",
        footprint["body"],
    )
    print(
        "Pad count:",
        len(footprint["pads"]),
    )
    print(
        "Pad 7:",
        pad_7,
    )
    print(
        "Pad 7 absolute position:",
        absolute_position,
    )

    print(
        "Footprint library validation passed."
    )