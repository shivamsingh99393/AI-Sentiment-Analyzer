from database.mongo import reviews

sample_review = {
    "review": "This phone is amazing!",
    "sentiment": "Positive",
    "confidence": 99.99
}

reviews.insert_one(sample_review)

print("Data inserted successfully!")