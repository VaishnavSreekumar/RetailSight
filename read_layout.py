
import pandas as pd
import os

# Define the path to the Excel file
LAYOUT_FILE_PATH = os.path.join(os.path.dirname(__file__), 'Brigade Road - Store layoutc5f5d56.xlsx')

def read_layout_file():
    """
    Reads the store layout data from the provided Excel file and prints its contents.
    """
    print(f"--- Reading Store Layout from {LAYOUT_FILE_PATH} ---")

    if not os.path.exists(LAYOUT_FILE_PATH):
        print(f"ERROR: Layout file not found at {LAYOUT_FILE_PATH}")
        return

    try:
        # Read the Excel file
        df = pd.read_excel(LAYOUT_FILE_PATH)
        
        print("\n--- Layout Data ---")
        print(df.to_string())

    except Exception as e:
        print(f"ERROR: Failed to read Excel file: {e}")

if __name__ == "__main__":
    read_layout_file()
