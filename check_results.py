import pandas as pd

# Read the results
df = pd.read_csv('risk_scores.csv')

print("=== WALLET RISK SCORING RESULTS ===")
print(f"Total wallets processed: {len(df)}")
print(f"Columns: {df.columns.tolist()}")
print("\nFirst 10 results:")
print(df[['wallet_id', 'score']].head(10))

print("\nRisk Score Statistics:")
print(f"Mean: {df['score'].mean():.2f}")
print(f"Median: {df['score'].median():.2f}")
print(f"Min: {df['score'].min()}")
print(f"Max: {df['score'].max()}")

print("\nRisk Score Distribution:")
print(f"Low Risk (0-200): {len(df[df['score'] <= 200])} wallets")
print(f"Low-Medium Risk (201-400): {len(df[(df['score'] > 200) & (df['score'] <= 400)])} wallets")
print(f"Medium Risk (401-600): {len(df[(df['score'] > 400) & (df['score'] <= 600)])} wallets")
print(f"High Risk (601-800): {len(df[(df['score'] > 600) & (df['score'] <= 800)])} wallets")
print(f"Very High Risk (801-1000): {len(df[df['score'] > 800])} wallets")

print("\nTop 10 Highest Risk Wallets:")
top_risk = df.nlargest(10, 'score')[['wallet_id', 'score']]
print(top_risk.to_string(index=False)) 