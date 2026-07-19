from flask import Flask, render_template, request
from models.sentiment_model import analyze_sentiment
from database.mongo import reviews

app = Flask(__name__)


@app.route("/", methods=["GET", "POST"])
def home():

    result = None

    if request.method == "POST":
        review = request.form["review"]
        result = analyze_sentiment(review)

        reviews.insert_one({
            "review": review,
            "sentiment": result[0]["label"],
            "confidence": round(result[0]["score"] * 100, 2)
        })

    return render_template("index.html", result=result)


@app.route("/history")
def history():

    all_reviews = list(reviews.find())

    return render_template(
        "history.html",
        reviews=all_reviews
    )


if __name__ == "__main__":
    app.run(debug=True)