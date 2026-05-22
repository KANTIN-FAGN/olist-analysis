import os
from dotenv import load_dotenv

import numpy as np
import pandas as pd
from sqlalchemy import create_engine, text

load_dotenv()


def get_database_url() -> str:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL est manquante dans le .env")
    return database_url


def haversine(lat1, lon1, lat2, lon2):
    """
    Calcule la distance haversine en kilomètres entre deux points.
    Retourne NaN si une coordonnée est manquante.
    """
    lat1 = pd.to_numeric(lat1, errors="coerce")
    lon1 = pd.to_numeric(lon1, errors="coerce")
    lat2 = pd.to_numeric(lat2, errors="coerce")
    lon2 = pd.to_numeric(lon2, errors="coerce")

    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
    c = 2 * np.arcsin(np.sqrt(a))

    r = 6371  # rayon terrestre en km
    return r * c


def main():
    engine = create_engine(get_database_url())

    with engine.begin() as conn:
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS analytics;"))

    orders = pd.read_sql("SELECT * FROM raw.orders", engine)
    customers = pd.read_sql("SELECT * FROM raw.customers", engine)
    order_items = pd.read_sql("SELECT * FROM raw.order_items", engine)
    order_payments = pd.read_sql("SELECT * FROM raw.order_payments", engine)
    order_reviews = pd.read_sql("SELECT * FROM raw.order_reviews", engine)
    sellers = pd.read_sql("SELECT * FROM raw.sellers", engine)
    geolocation = pd.read_sql("SELECT * FROM raw.geolocation", engine)

    date_cols = [
        "order_purchase_timestamp",
        "order_approved_at",
        "order_delivered_carrier_date",
        "order_delivered_customer_date",
        "order_estimated_delivery_date",
    ]
    for col in date_cols:
        if col in orders.columns:
            orders[col] = pd.to_datetime(orders[col], errors="coerce")

    if "review_creation_date" in order_reviews.columns:
        order_reviews["review_creation_date"] = pd.to_datetime(
            order_reviews["review_creation_date"], errors="coerce"
        )

    if "review_answer_timestamp" in order_reviews.columns:
        order_reviews["review_answer_timestamp"] = pd.to_datetime(
            order_reviews["review_answer_timestamp"], errors="coerce"
        )

    items_agg = (
        order_items.groupby("order_id")
        .agg(
            nb_items=("order_item_id", "count"),
            nb_sellers=("seller_id", "nunique"),
            price_total=("price", "sum"),
            freight_total=("freight_value", "sum"),
        )
        .reset_index()
    )

    payments_agg = (
        order_payments.groupby("order_id")
        .agg(
            payment_value=("payment_value", "sum"),
            payment_installments=("payment_installments", "max"),
        )
        .reset_index()
    )

    reviews_agg = (
        order_reviews.groupby("order_id")
        .agg(
            review_score=("review_score", "first"),
        )
        .reset_index()
    )

    # Premier vendeur par commande pour une distance approximative
    first_seller_per_order = (
        order_items.sort_values(["order_id", "order_item_id"])
        .groupby("order_id", as_index=False)
        .agg(first_seller_id=("seller_id", "first"))
    )

    # Géolocalisation moyenne par zip code prefix
    geo_avg = (
        geolocation.groupby("geolocation_zip_code_prefix", as_index=False)
        .agg(
            lat=("geolocation_lat", "mean"),
            lon=("geolocation_lng", "mean"),
        )
    )

    # Géolocalisation client
    customer_geo = geo_avg.rename(
        columns={
            "geolocation_zip_code_prefix": "customer_zip_code_prefix",
            "lat": "customer_lat",
            "lon": "customer_lon",
        }
    )

    # Géolocalisation vendeur
    seller_geo = sellers.merge(
        geo_avg,
        left_on="seller_zip_code_prefix",
        right_on="geolocation_zip_code_prefix",
        how="left",
    ).rename(
        columns={
            "lat": "seller_lat",
            "lon": "seller_lon",
        }
    )[
        [
            "seller_id",
            "seller_city",
            "seller_state",
            "seller_lat",
            "seller_lon",
        ]
    ]

    fact_orders = (
        orders.merge(customers, on="customer_id", how="left")
        .merge(items_agg, on="order_id", how="left")
        .merge(payments_agg, on="order_id", how="left")
        .merge(reviews_agg, on="order_id", how="left")
        .merge(first_seller_per_order, on="order_id", how="left")
        .merge(customer_geo, on="customer_zip_code_prefix", how="left")
        .merge(seller_geo, left_on="first_seller_id", right_on="seller_id", how="left")
    )

    fact_orders["delivery_time_days"] = (
        fact_orders["order_delivered_customer_date"] - fact_orders["order_purchase_timestamp"]
    ).dt.days

    fact_orders["estimated_delivery_time_days"] = (
        fact_orders["order_estimated_delivery_date"] - fact_orders["order_purchase_timestamp"]
    ).dt.days

    fact_orders["delay_days"] = (
        fact_orders["order_delivered_customer_date"] - fact_orders["order_estimated_delivery_date"]
    ).dt.days

    fact_orders["is_late"] = fact_orders["delay_days"].fillna(0).gt(0).astype(int)
    fact_orders["has_review"] = fact_orders["review_score"].notna().astype(int)
    fact_orders["has_delivery_date"] = fact_orders["order_delivered_customer_date"].notna().astype(int)

    fact_orders["distance_km"] = haversine(
        fact_orders["customer_lat"],
        fact_orders["customer_lon"],
        fact_orders["seller_lat"],
        fact_orders["seller_lon"],
    )

    # Colonnes temporelles utiles pour Superset
    fact_orders["purchase_year"] = fact_orders["order_purchase_timestamp"].dt.year
    fact_orders["purchase_month"] = fact_orders["order_purchase_timestamp"].dt.month
    fact_orders["purchase_year_month"] = fact_orders["order_purchase_timestamp"].dt.to_period("M").astype(str)

    fact_orders.to_sql(
        "fact_orders",
        engine,
        schema="analytics",
        if_exists="replace",
        index=False,
        method="multi",
        chunksize=5000,
    )

    print("Table créée : analytics.fact_orders")
    print(f"Nombre de lignes : {len(fact_orders):,}".replace(",", " "))
    print("Colonnes :")
    for col in fact_orders.columns:
        print(f" - {col}")


if __name__ == "__main__":
    main()