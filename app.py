from wordcloud import WordCloud
from flask import send_file
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph
from io import BytesIO
import matplotlib.pyplot 
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

    all_reviews = list(
    reviews.find(query).sort("created_at", -1)
)

    return render_template(
        "history.html",
        reviews=all_reviews,
        search=search,
        sentiment=sentiment,
        total_reviews=len(all_reviews),
    )

# ==========================
# DELETE REVIEW
# ==========================
@app.route("/delete/<id>")
def delete_review(id):

    from bson.objectid import ObjectId

    reviews.delete_one(
        {"_id": ObjectId(id)}
    )

    return redirect(url_for("history"))

# ==========================
# CLEAR ALL REVIEWS
# ==========================
@app.route("/clear")
def clear_reviews():

    reviews.delete_many({})

    return redirect(url_for("history"))

# ==========================
# DASHBOARD
# ==========================
@app.route("/dashboard")
def dashboard():

    # --------------------------
    # Counts
    # --------------------------
    total = reviews.count_documents({})
    positive = reviews.count_documents({"sentiment": "positive"})
    negative = reviews.count_documents({"sentiment": "negative"})
    neutral = reviews.count_documents({"sentiment": "neutral"})

    # --------------------------
    # Fetch All Reviews
    # --------------------------
    all_reviews = list(reviews.find())

    # --------------------------
    # Average Confidence
    # --------------------------
    if total > 0:
        average_confidence = round(
            sum(review.get("confidence", 0) for review in all_reviews) / total,
            2
        )
    else:
        average_confidence = 0

    # --------------------------
    # Word Cloud
    # --------------------------
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

    # --------------------------
    # Pie Chart
    # --------------------------
    pie = px.pie(
        names=["Positive", "Negative", "Neutral"],
        values=[positive, negative, neutral],
        title="Sentiment Distribution",
        hole=0.4
    )

    graph = pie.to_html(full_html=False)

    # --------------------------
    # Bar Chart
    # --------------------------
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

    # --------------------------
    # AI Insight
    # --------------------------
    if total == 0:
        insight = "No reviews available."

    elif positive >= negative and positive >= neutral:
        insight = "😊 Most customer reviews are positive. Overall customer satisfaction is high."

    elif negative >= positive and negative >= neutral:
        insight = "⚠️ Negative reviews are dominating. Consider investigating customer complaints."

    else:
        insight = "😐 Most reviews are neutral. Customers may need more engaging experiences."

    # --------------------------
    # Sentiment Percentages
    # --------------------------
    if total > 0:
        positive_percent = round((positive / total) * 100, 1)
        negative_percent = round((negative / total) * 100, 1)
        neutral_percent = round((neutral / total) * 100, 1)
    else:
        positive_percent = 0
        negative_percent = 0
        neutral_percent = 0

    # --------------------------
    # Best Reviews
    # --------------------------
    positive_reviews = [
        review for review in all_reviews
        if review.get("sentiment") == "positive"
    ]

    negative_reviews = [
        review for review in all_reviews
        if review.get("sentiment") == "negative"
    ]

    top_positive = (
        max(positive_reviews, key=lambda x: x.get("confidence", 0))
        if positive_reviews else None
    )

    top_negative = (
        max(negative_reviews, key=lambda x: x.get("confidence", 0))
        if negative_reviews else None
    )

    # --------------------------
    # Recent Reviews
    # --------------------------
    recent_reviews = list(
        reviews.find().sort("created_at", -1).limit(5)
    )

    # --------------------------
    # Confidence Distribution Chart
    # --------------------------
    confidence_chart = None

    if all_reviews:
        confidence_df = pd.DataFrame(all_reviews)

        confidence_fig = px.histogram(
            confidence_df,
            x="confidence",
            nbins=10,
            title="Confidence Score Distribution",
            labels={"confidence": "Confidence (%)"},
        )

        confidence_fig.update_layout(
            template="plotly_white",
            xaxis_title="Confidence (%)",
            yaxis_title="Number of Reviews"
        )

        confidence_chart = confidence_fig.to_html(full_html=False)

    # --------------------------
    # Trend Chart
    # --------------------------
    trend_data = list(
        reviews.find(
            {"created_at": {"$exists": True}},
            {"_id": 0, "created_at": 1, "sentiment": 1}
        )
    )

    trend_graph = None

    if trend_data:
        trend_df = pd.DataFrame(trend_data)
        trend_df["created_at"] = pd.to_datetime(trend_df["created_at"])
        trend_df["Date"] = trend_df["created_at"].dt.date

        trend_summary = (
            trend_df.groupby(["Date", "sentiment"])
            .size()
            .reset_index(name="Count")
        )

        trend_chart = px.line(
            trend_summary,
            x="Date",
            y="Count",
            color="sentiment",
            markers=True,
            title="Sentiment Trend Over Time"
        )
        trend_graph = trend_chart.to_html(full_html=False)

    # --------------------------
    # Render Dashboard
    # --------------------------
    return render_template(
        "dashboard.html",
        total=total,
        positive=positive,
        negative=negative,
        neutral=neutral,
        graph=graph,
        bar_graph=bar_graph,
        trend_graph=trend_graph,
        recent_reviews=recent_reviews,
        insight=insight,
        positive_percent=positive_percent,
        negative_percent=negative_percent,
        neutral_percent=neutral_percent,
        average_confidence=average_confidence,
        confidence_chart=confidence_chart,
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

@app.route("/download")
def download_report():

    total = reviews.count_documents({})
    positive = reviews.count_documents({"sentiment": "positive"})
    negative = reviews.count_documents({"sentiment": "negative"})
    neutral = reviews.count_documents({"sentiment": "neutral"})

    if total == 0:
        insight = "No reviews available."
    elif positive >= negative and positive >= neutral:
        insight = "Most customer reviews are positive. Overall customer satisfaction is high."
    elif negative >= positive and negative >= neutral:
        insight = "Negative reviews are dominating. Consider investigating customer complaints."
    else:
        insight = "Most reviews are neutral. Customers may need more engaging experiences."

    buffer = BytesIO()

    doc = SimpleDocTemplate(buffer)

    styles = getSampleStyleSheet()

    story = []

    story.append(
        Paragraph(
            "<b>AI Sentiment Analytics Report</b>",
            styles["Title"]
        )
    )

    story.append(
        Paragraph(
            f"Total Reviews: {total}",
            styles["BodyText"]
        )
    )

    story.append(
        Paragraph(
            f"Positive Reviews: {positive}",
            styles["BodyText"]
        )
    )

    story.append(
        Paragraph(
            f"Negative Reviews: {negative}",
            styles["BodyText"]
        )
    )

    story.append(
        Paragraph(
            f"Neutral Reviews: {neutral}",
            styles["BodyText"]
        )
    )

    story.append(
        Paragraph(
            insight,
            styles["BodyText"]
        )
    )

    doc.build(story)

    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name="AI_Sentiment_Report.pdf",
        mimetype="application/pdf"
    )
# ==========================
# RUN APP
# ==========================
if __name__ == "__main__":
    app.run(debug=True)