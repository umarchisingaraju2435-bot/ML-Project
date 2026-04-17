import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.svm import LinearSVC
from sklearn.pipeline import Pipeline
import numpy as np

# Built-in stopwords — no NLTK/SSL needed
STOP_WORDS = {
    'i','me','my','we','our','you','your','he','him','his','she','her','it','its',
    'they','them','their','what','which','who','this','that','these','those','am',
    'is','are','was','were','be','been','being','have','has','had','do','does','did',
    'a','an','the','and','but','if','or','as','of','at','by','for','with','about',
    'into','through','to','from','in','out','on','off','over','under','then','here',
    'there','when','where','how','all','both','each','more','most','other','some',
    'no','not','only','same','so','than','too','very','can','will','just','should',
    'now','don','won','aren','isn','wasn','weren','didn','doesn','hadn','hasn'
}

# Pre-trained on common review patterns (lightweight demo data)
TRAIN_REVIEWS = [
    ("excellent product great quality fast delivery", 1),
    ("amazing service highly recommend best purchase", 1),
    ("good value works perfectly satisfied customer", 1),
    ("love it outstanding performance exceeded expectations", 1),
    ("fantastic build quality premium feel worth every penny", 1),
    ("terrible quality broke after one day waste of money", 0),
    ("worst product ever complete disappointment do not buy", 0),
    ("poor quality cheap material not as described", 0),
    ("horrible experience bad customer service never again", 0),
    ("defective item arrived damaged very disappointed", 0),
    ("average product nothing special mediocre quality", 2),
    ("okay for the price decent but not great", 2),
    ("works fine but could be better average experience", 2),
]

def clean_text(text):
    text = re.sub(r'[^a-zA-Z\s]', '', text.lower())
    return ' '.join(w for w in text.split() if w not in STOP_WORDS)

def build_sentiment_model():
    texts = [clean_text(r[0]) for r in TRAIN_REVIEWS]
    labels = [r[1] for r in TRAIN_REVIEWS]
    model = Pipeline([
        ('tfidf', TfidfVectorizer(ngram_range=(1, 2), max_features=5000)),
        ('clf', LinearSVC(C=1.0, max_iter=1000))
    ])
    model.fit(texts, labels)
    return model

_model = build_sentiment_model()
LABEL_MAP = {1: 'Positive', 0: 'Negative', 2: 'Neutral'}

def analyze_sentiment(reviews: list) -> dict:
    cleaned = [clean_text(r) for r in reviews]
    preds = _model.predict(cleaned)
    results = [{'review': r, 'sentiment': LABEL_MAP[p]} for r, p in zip(reviews, preds)]
    counts = {v: 0 for v in LABEL_MAP.values()}
    for p in preds:
        counts[LABEL_MAP[p]] += 1
    score = round((counts['Positive'] - counts['Negative']) / max(len(reviews), 1), 2)
    return {'results': results, 'summary': counts, 'score': score}
