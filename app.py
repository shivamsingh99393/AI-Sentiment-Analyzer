import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for

from models.sentiment_model import analyze_sentiment
from database.mongo import reviews

app = Flask(__name__)

# ==========================
# Home Page
# ==========================
@app.route("/", methods=["GET", "POST"])
def home():

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

    return render_template("index.html")


# ==========================
# History Page
# ==========================
@app.route("/history")
def history():

    search = request.args.get("search", "")

    if search:

        all_reviews = list(
            reviews.find({
                "review": {
                    "$regex": search,
                    "$options": "i"
                }
            })
        )

    else:

        all_reviews = list(reviews.find())

    return render_template(
        "history.html",
        reviews=all_reviews,
        search=search
    )


# ==========================
# Dashboard
# ==========================
@app.route("/dashboard")
def dashboard():

    total = reviews.count_documents({})

    positive = reviews.count_documents({"sentiment": "positive"})
    negative = reviews.count_documents({"sentiment": "negative"})
    neutral = reviews.count_documents({"sentiment": "neutral"})

    # Pie Chart
    pie = px.pie(
        names=["Positive", "Negative", "Neutral"],
        values=[positive, negative, neutral],
        title="Sentiment Distribution",
        hole=0.4
    )

    graph = pie.to_html(full_html=False)

    # Bar Chart
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
        yaxis_title="Number of Reviews",
        template="plotly_white"
    )

    bar_graph = bar.to_html(full_html=False)

    # Recent Reviews
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
# Upload CSV
# ==========================
@app.route("/upload", methods=["GET", "POST"])
def upload():

    if request.method == "POST":

        file = request.files["file"]

        if file:

            df = pd.read_csv(file)

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
# Run App
# ==========================
if __name__ == "__main__":
    app.run(debug=True)