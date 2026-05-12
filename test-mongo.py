from pymongo import MongoClient
from urllib.parse import quote_plus

# URL-encode password (@ becomes %40)
password = quote_plus("Rohith@0209")
username = quote_plus("rohithamalan1974_db_user")
uri = f"mongodb+srv://{username}:{password}@cluster0.zcdzur7.mongodb.net/?appName=Cluster0"

try:
    client = MongoClient(uri)

    client.admin.command("ping")

    print("✅ MongoDB Connected Successfully!")

except Exception as e:
    print("❌ Connection Failed")
    print(e)