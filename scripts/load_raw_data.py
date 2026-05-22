import os
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

import pandas as pd
from sqlalchemy import create_engine, text

RAW_DIR = Path("data/raw")

CSV_TABLE_MAP = {
    "olist_customers_dataset.csv": "customers",
    "olist_geolocation_dataset.csv": "geolocation",
    "olist_order_items_dataset.csv": "order_items",
    "olist_order_payments_dataset.csv": "order_payments",
    "olist_order_reviews_dataset.csv": "order_reviews",
    "olist_orders_dataset.csv": "orders",
    "olist_products_dataset.csv": "products",
    "olist_sellers_dataset.csv": "sellers",
    "product_category_name_translation.csv": "product_category_translation",
}


def get_database_url() -> str:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError(
            "La variable d'environnement DATABASE_URL est manquante. "
            "Exemple attendu : postgresql://user:password@localhost:5432/dbname"
        )
    return database_url


def build_engine():
    database_url = get_database_url()
    return create_engine(database_url)


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df.columns = [
        col.strip()
        .lower()
        .replace(" ", "_")
        .replace("-", "_")
        .replace("(", "")
        .replace(")", "")
        for col in df.columns
    ]
    return df


def read_csv_file(csv_path: Path) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    df = normalize_columns(df)
    return df


def ensure_schema(engine, schema_name: str = "raw") -> None:
    with engine.begin() as conn:
        conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema_name};"))


def load_one_csv(engine, csv_path: Path, table_name: str, schema_name: str = "raw") -> None:
    print(f"Lecture : {csv_path.name}")
    df = read_csv_file(csv_path)

    print(f"  → {len(df):,} lignes | {len(df.columns)} colonnes".replace(",", " "))
    df.to_sql(
        name=table_name,
        con=engine,
        schema=schema_name,
        if_exists="replace",
        index=False,
        method="multi",
        chunksize=5000,
    )
    print(f"Chargé dans {schema_name}.{table_name}")


def main() -> None:
    if not RAW_DIR.exists():
        raise FileNotFoundError(
            f"Le dossier {RAW_DIR} est introuvable. "
            "Place tes CSV dans data/raw/"
        )

    engine = build_engine()
    ensure_schema(engine, "raw")

    loaded_tables = []

    for filename, table_name in CSV_TABLE_MAP.items():
        csv_path = RAW_DIR / filename

        if not csv_path.exists():
            print(f"Fichier absent : {filename}")
            continue

        load_one_csv(engine, csv_path, table_name, schema_name="raw")
        loaded_tables.append(f"raw.{table_name}")

    print("\nChargement terminé.")
    if loaded_tables:
        print("Tables créées :")
        for table in loaded_tables:
            print(f" - {table}")
    else:
        print("Aucune table n'a été chargée.")


if __name__ == "__main__":
    main()