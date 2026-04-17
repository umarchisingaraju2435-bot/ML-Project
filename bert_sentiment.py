"""
BERT-based Sentiment Analysis for Customer Reviews.
Uses distilbert-base-uncased-finetuned-sst-2-english
— a lightweight BERT model fine-tuned on sentiment (SST-2 dataset).
Accuracy: ~91% on real review data.
"""
from transformers import pipeline
import re

# Load BERT model once at startup (cached after first download)
print("Loading BERT sentiment model...")
_bert = pipeline(
    "sentiment-analysis",
    model="distilbert-base-uncased-finetuned-sst-2-english",
    truncation=True,
    max_length=512
)
print("✅ BERT model loaded.")

LABEL_MAP = {
    'POSITIVE': 'Good Review',
    'NEGATIVE': 'Bad Review',
}

EMOJI_MAP = {
    'Good Review': '✅',
    'Bad Review':  '❌',
}

def clean_review(text: str) -> str:
    text = re.sub(r'<[^>]+>', ' ', text)          # remove HTML
    text = re.sub(r'[^\w\s.,!?]', ' ', text)      # keep punctuation
    text = re.sub(r'\s+', ' ', text).strip()
    return text[:512]                              # BERT max length

def analyze_reviews_bert(reviews: list) -> dict:
    """
    Analyze customer reviews using BERT.
    Returns detailed results with label, confidence score, and emoji.
    """
    if not reviews:
        return {'results': [], 'summary': {}, 'score': 0, 'accuracy_note': ''}

    cleaned = [clean_review(r) for r in reviews if r.strip()]
    if not cleaned:
        return {'results': [], 'summary': {}, 'score': 0, 'accuracy_note': ''}

    # Run BERT inference
    raw_preds = _bert(cleaned)

    results = []
    good_count = 0
    bad_count  = 0

    for review, pred in zip(reviews, raw_preds):
        label      = LABEL_MAP[pred['label']]
        confidence = round(pred['score'] * 100, 1)   # e.g. 97.3%

        if label == 'Good Review':
            good_count += 1
        else:
            bad_count += 1

        results.append({
            'review':     review,
            'label':      label,
            'emoji':      EMOJI_MAP[label],
            'confidence': confidence,
            'bar_width':  int(confidence),
            'color':      '#22c55e' if label == 'Good Review' else '#ef4444',
        })

    total = len(results)
    good_pct = round((good_count / total) * 100, 1)
    bad_pct  = round((bad_count  / total) * 100, 1)

    # Overall sentiment score (-1 to +1)
    score = round((good_count - bad_count) / total, 2)

    # Star rating (1–5)
    star_rating = round(1 + (score + 1) * 2, 1)   # maps -1→1, +1→5

    return {
        'results':      results,
        'summary': {
            'Good Review': good_count,
            'Bad Review':  bad_count,
            'Total':       total,
        },
        'good_pct':     good_pct,
        'bad_pct':      bad_pct,
        'score':        score,
        'star_rating':  star_rating,
        'stars_display': '⭐' * int(round(star_rating)),
        'model':        'BERT (distilbert-base-uncased-finetuned-sst-2-english)',
        'accuracy_note': '~91% accuracy on real review data (SST-2 benchmark)',
        'verdict': (
            '🟢 Mostly Positive — Customers love this product!'
            if score > 0.3 else
            '🔴 Mostly Negative — Product needs improvement.'
            if score < -0.3 else
            '🟡 Mixed Reviews — Some customers satisfied, some not.'
        )
    }
