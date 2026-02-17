
import os
from typing import Optional

from pymongo import MongoClient


client: Optional[MongoClient] = None
db = None
collection = None


def get_mongo_uri():
    return os.getenv("MONGO_URI")

def get_mongo_db_name():
    return os.getenv("MONGO_DB_NAME")

def init_db():
    global client, db, collection

    mongo_uri = get_mongo_uri()
    mongo_db_name = get_mongo_db_name()

    if not mongo_uri or not mongo_db_name:
        raise ValueError("MONGO_URI and MONGO_DB_NAME must be set in environment variables")

    client = MongoClient(mongo_uri)
    db = client[mongo_db_name]

    if "incidents" not in db.list_collection_names():
        db.create_collection("incidents")

    collection = db["incidents"]

    collection.create_index([("incident_id", 1)], unique=True)
    collection.create_index([("status", 1)])
    collection.create_index([("ticket_id", 1)])
