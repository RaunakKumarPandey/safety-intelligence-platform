from pathlib import Path
import pandas as pd

# Load dataset
DATA_PATH = Path(__file__).resolve().parent / "data" / "accidents.csv"
df = pd.read_csv(DATA_PATH)

print("\n========== DATASET OVERVIEW ==========")

print("\nTotal Rows:", len(df))
print("Total Columns:", len(df.columns))

print("\n========== COLUMN NAMES ==========")
for column in df.columns:
    print(column)

print("\n========== FIRST 3 ROWS ==========")
print(df.head(3))

print("\n========== MISSING VALUES ==========")
print(df.isnull().sum())

print("\n========== POTENTIAL ACCIDENT LEVEL ==========")
if "Potential Accident Level" in df.columns:
    print(df["Potential Accident Level"].value_counts())

print("\n========== CRITICAL RISK ==========")
if "Critical Risk" in df.columns:
    print(df["Critical Risk"].value_counts())