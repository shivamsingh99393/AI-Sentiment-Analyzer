from flask import Flask, render_template, request
from models.sentiment_model import analyze_sentiment

app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def home():

    result = None

    if request.method == "POST":
        review = request.form["review"]
        result = analyze_sentiment(review)

    return render_template("index.html", result=result)

if __name__ == "__main__":
    app.run(debug=True)