from transformers import pipeline

# Three-class sentiment model
sentiment_pipeline = pipeline(
    "text-classification",
    model="cardiffnlp/twitter-roberta-base-sentiment-latest"
)
sentiment_tokenizer = sentiment_pipeline.tokenizer
max_input_tokens = (
    sentiment_pipeline.model.config.max_position_embeddings
    - sentiment_tokenizer.num_special_tokens_to_add(pair=False)
)
chunk_overlap = 64

def analyze_sentiment(text):
    token_ids = sentiment_tokenizer.encode(text, add_special_tokens=False)

    if len(token_ids) <= max_input_tokens:
        return sentiment_pipeline(text)

    token_step = max_input_tokens - chunk_overlap
    scores_by_label = {}
    total_weight = 0
    covered_tokens = 0

    for start in range(0, len(token_ids), token_step):
        end = min(start + max_input_tokens, len(token_ids))
        chunk = sentiment_tokenizer.decode(
            token_ids[start:end],
            skip_special_tokens=True,
            clean_up_tokenization_spaces=True,
        )
        chunk_scores = sentiment_pipeline(chunk, top_k=None)

        weight = end - max(start, covered_tokens)
        covered_tokens = max(covered_tokens, end)
        total_weight += weight

        for item in chunk_scores:
            label = item["label"]
            scores_by_label[label] = (
                scores_by_label.get(label, 0) + item["score"] * weight
            )

    return [{
        "label": label,
        "score": score / total_weight,
    } for label, score in sorted(
        scores_by_label.items(),
        key=lambda item: item[1],
        reverse=True,
    )[:1]]