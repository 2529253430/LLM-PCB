COMPONENT_TABLE = """
CREATE TABLE IF NOT EXISTS component (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    part_number TEXT,

    manufacturer TEXT,

    category TEXT,

    topology TEXT,

    package TEXT,

    vin_min REAL,

    vin_max REAL,

    vout_min REAL,

    vout_max REAL,

    current REAL,

    frequency REAL,

    symbol TEXT,

    footprint TEXT,

    datasheet TEXT,

    description TEXT

)
"""