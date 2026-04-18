from app.backend.db.db import DB_ENABLED, DATABASE_URL

print("DB_ENABLED=", DB_ENABLED)
print("DB_TARGET=", DATABASE_URL.rsplit("@", 1)[-1] if DATABASE_URL else None)

