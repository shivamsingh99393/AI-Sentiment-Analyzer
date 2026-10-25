import os
from dotenv import load_dotenv
from pymongo import MongoClient

# Load .env file
load_dotenv()

# Read MongoDB URI
MONGO_URI = os.getenv("MONGO_URI")

# Connect to MongoDB
client = MongoClient(MONGO_URI)

# Create Database
db = client["sentiment_db"]

# Create Collection
reviews = db["reviews"]
print("URI:", os.getenv("MONGO_URI"))
