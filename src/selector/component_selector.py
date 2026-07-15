from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent.parent

CSV_PATH = BASE_DIR / "data" / "csv" / "components.csv"


def load_components():
    return pd.read_csv(CSV_PATH)


def select_components(topology, vin, vout, current):

    df = load_components()

    result = df[
        (df["Topology"] == topology)
        &
        (df["VinMin"] <= vin)
        &
        (df["VinMax"] >= vin)
        &
        (df["VoutMin"] <= vout)
        &
        (df["VoutMax"] >= vout)
        &
        (df["Current"] >= current)
    ]

    return result.sort_values(
        by="Efficiency",
        ascending=False
    )


if __name__ == "__main__":

    topology = input("Topology: ")

    vin = float(input("Input Voltage: "))

    vout = float(input("Output Voltage: "))

    current = float(input("Output Current: "))

    result = select_components(
        topology,
        vin,
        vout,
        current
    )

    print()

    print(result)