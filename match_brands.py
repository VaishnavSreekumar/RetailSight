import pandas as pd

def main():
    csv_path = "Brigade_Bangalore_10_April_26 (1)bc6219c (1).csv"
    df = pd.read_csv(csv_path)
    
    # Group by brand and aggregate
    brand_stats = df.groupby('brand_name').agg(
        nmv=('NMV', 'sum'),
        gmv=('GMV', 'sum'),
        count=('order_id', 'size')
    ).reset_index()
    
    print(brand_stats.to_string())

if __name__ == "__main__":
    main()
