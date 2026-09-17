import pandas as pd

df = pd.read_csv("data/raw/food_db.csv")
print(df.shape)
print(list(df.columns))
print(df.head(3).to_string())