from transformers import pipeline

# Three-class sentiment model
sentiment_pipeline = pipeline(
    "text-classification",
    model="cardiffnlp/twitter-roberta-base-sentiment-latest"
)

def analyze_sentiment(text):
    return sentiment_pipeline(text)