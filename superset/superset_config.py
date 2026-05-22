import os

# Clé secrète Flask utilisée pour signer les sessions (obligatoire)
SECRET_KEY = os.environ["SUPERSET_SECRET_KEY"]

# URI de la base de données PostgreSQL utilisée par Superset pour ses métadonnées (dashboards, utilisateurs, etc.)
SQLALCHEMY_DATABASE_URI = os.environ["SUPERSET_METADATA_DB"]

# URL du serveur Redis (utilisé pour le cache)
REDIS_URL = os.environ.get("REDIS_URL", "redis://redis:6379/0")

# Configuration du cache applicatif (résultats de requêtes, etc.)
CACHE_CONFIG = {
    "CACHE_TYPE": "RedisCache",
    "CACHE_DEFAULT_TIMEOUT": 300,
    "CACHE_KEY_PREFIX": "superset_",
    "CACHE_REDIS_URL": REDIS_URL,
}

# Utilise la même configuration pour le cache des données de charts
DATA_CACHE_CONFIG = CACHE_CONFIG

# Langue de l'interface Superset
BABEL_DEFAULT_LOCALE = "fr"

# Désactive la protection CSRF (à activer en production si l'app est exposée publiquement)
WTF_CSRF_ENABLED = False

# Timeout en secondes pour les requêtes longues dans le serveur web Superset
SUPERSET_WEBSERVER_TIMEOUT = 300