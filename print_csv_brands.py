import pandas as pd

def main():
    csv_path = "Brigade_Bangalore_10_April_26 (1)bc6219c (1).csv"
    df = pd.read_csv(csv_path)
    print("Columns:", list(df.columns))
    # Print distinct brands based on actual columns
    brand_col = [c for c in df.columns if 'brand' in c.lower()]
    if brand_col:
        print("Brands:", sorted(df[brand_col[0]].dropna().unique().tolist()))

if __name__ == "__main__":
    main()
