from wordcloud import WordCloud
import matplotlib.pyplot as plt
import os
import io
import csv
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from datetime import datetime
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    make_response,
)

from models.sentiment_model import analyze_sentiment
from database.mongo import reviews

app = Flask(__name__)


# ==========================
# HOME PAGE
# ==========================
@app.route("/", methods=["GET", "POST"])
def home():

    sentiment = None
    confidence = None

    if request.method == "POST":

        review = request.form["review"]

        result = analyze_sentiment(review)

        sentiment = result[0]["label"]
        confidence = round(result[0]["score"] * 100, 2)

        reviews.insert_one({
            "review": review,
            "sentiment": sentiment,
            "confidence": confidence,
            "created_at": datetime.now()
        })

    return render_template(
        "index.html",
        sentiment=sentiment,
        confidence=confidence
    )


# ==========================
# HISTORY PAGE
# ==========================
@app.route("/history")
def history():

    search = request.args.get("search", "")
    sentiment = request.args.get("sentiment", "All")

    query = {}

    if search:
        query["review"] = {
            "$regex": search,
            "$options": "i"
        }

    if sentiment != "All":
        query["sentiment"] = sentiment

    all_reviews = list(reviews.find(query))

    return render_template(
        "history.html",
        reviews=all_reviews,
        search=search,
        sentiment=sentiment
    )


# ==========================
# DASHBOARD
# ==========================
@app.route("/dashboard")
def dashboard():

    total = reviews.count_documents({})

    positive = reviews.count_documents({"sentiment": "positive"})
    negative = reviews.count_documents({"sentiment": "negative"})
    neutral = reviews.count_documents({"sentiment": "neutral"})

    # ==========================
    # WORD CLOUD
    # ==========================
    all_reviews = list(reviews.find())

    text = " ".join(
        review["review"]
        for review in all_reviews
        if review.get("review")
    )

    if text.strip():

        os.makedirs("static/images", exist_ok=True)

        wordcloud = WordCloud(
            width=1000,
            height=500,
            background_color="white"
        ).generate(text)

        wordcloud.to_file("static/images/wordcloud.png")

    # ==========================
    # PIE CHART
    # ==========================
    pie = px.pie(
        names=["Positive", "Negative", "Neutral"],
        values=[positive, negative, neutral],
        title="Sentiment Distribution",
        hole=0.4
    )

    graph = pie.to_html(full_html=False)

    # ==========================
    # BAR CHART
    # ==========================
    bar = go.Figure()

    bar.add_trace(
        go.Bar(
            x=["Positive", "Negative", "Neutral"],
            y=[positive, negative, neutral],
            text=[positive, negative, neutral],
            textposition="outside"
        )
    )

    bar.update_layout(
        title="Sentiment Comparison",
        xaxis_title="Sentiment",
        yaxis_title="Reviews",
        template="plotly_white"
    )

    bar_graph = bar.to_html(full_html=False)

    # ==========================
    # RECENT REVIEWS
    # ==========================
    recent_reviews = list(
        reviews.find()
        .sort("created_at", -1)
        .limit(5)
    )

    return render_template(
        "dashboard.html",
        total=total,
        positive=positive,
        negative=negative,
        neutral=neutral,
        graph=graph,
        bar_graph=bar_graph,
        recent_reviews=recent_reviews
    )

# ==========================
# CSV UPLOAD
# ==========================
@app.route("/upload", methods=["GET", "POST"])
def upload():

    if request.method == "POST":

        file = request.files["file"]

        if file:

            df = pd.read_csv(file)

            # Change "review" if your CSV uses another column name
            for _, row in df.iterrows():

                review = str(row["review"])

                result = analyze_sentiment(review)

                reviews.insert_one({
                    "review": review,
                    "sentiment": result[0]["label"],
                    "confidence": round(result[0]["score"] * 100, 2),
                    "created_at": datetime.now()
                })

            return redirect(url_for("dashboard"))

    return render_template("upload.html")


# ==========================
# DOWNLOAD CSV REPORT
# ==========================
@app.route("/download")
def download():

    all_reviews = list(reviews.find())

    output = io.StringIO()

    writer = csv.writer(output)

    writer.writerow([
        "Review",
        "Sentiment",
        "Confidence"
    ])

    for review in all_reviews:

        writer.writerow([
            review["review"],
            review["sentiment"],
            review["confidence"]
        ])

    response = make_response(output.getvalue())

    response.headers["Content-Disposition"] = (
        "attachment; filename=sentiment_report.csv"
    )

    response.headers["Content-Type"] = "text/csv"

    return response


# ==========================
# RUN APP
# ==========================
if __name__ == "__main__":
    app.run(debug=True)