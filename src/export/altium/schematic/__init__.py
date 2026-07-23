from .builder import (
    AltiumSchematicBuildError,
    AltiumSchematicBuilder,
)
from .component import (
    SchComponent,
    SchPin,
    SchPinElectricalType,
)
from .document import AltiumSchematicDocument
from .label import (
    SchNetLabel,
    SchPort,
    SchPortDirection,
    SchText,
)
from .primitives import (
    AltiumSchematicModelError,
    SchPoint,
    SchRectangle,
    SchSize,
    normalize_rotation,
)
from .sheet import SchSheet, SchSheetOrientation
from .wire import SchJunction, SchWire
from .writer import AltiumSchematicPreviewWriter
from .symbols import (
    AltiumSymbolMapper,
    NativeSymbol,
    NativeSymbolKind,
    SymbolArc,
    SymbolLine,
    SymbolRectangle,
)

__all__ = [
    "AltiumSchematicBuildError",
    "AltiumSchematicBuilder",
    "AltiumSchematicDocument",
    "AltiumSchematicModelError",
    "AltiumSchematicPreviewWriter",
    "SchComponent",
    "SchJunction",
    "SchNetLabel",
    "SchPin",
    "SchPinElectricalType",
    "SchPoint",
    "SchPort",
    "SchPortDirection",
    "SchRectangle",
    "SchSheet",
    "SchSheetOrientation",
    "SchSize",
    "SchText",
    "SchWire",
    "normalize_rotation",
    "AltiumSymbolMapper",
    "NativeSymbol",
    "NativeSymbolKind",
    "SymbolArc",
    "SymbolLine",
    "SymbolRectangle",
]
from .compound_document import (
    CompoundDocumentError,
    CompoundDocumentReader,
    CompoundDocumentWriter,
)
from .schdoc_inspector import AltiumSchDocInspector, InspectedRecord
from .schdoc_writer import AltiumSchDocWriteError, AltiumSchDocWriter

__all__ += [
    "AltiumSchDocInspector",
    "AltiumSchDocWriteError",
    "AltiumSchDocWriter",
    "CompoundDocumentError",
    "CompoundDocumentReader",
    "CompoundDocumentWriter",
    "InspectedRecord",
]
