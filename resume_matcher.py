import re
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Built-in stopwords — no NLTK needed
STOP_WORDS = {
    'i','me','my','myself','we','our','ours','ourselves','you','your','yours',
    'yourself','yourselves','he','him','his','himself','she','her','hers',
    'herself','it','its','itself','they','them','their','theirs','themselves',
    'what','which','who','whom','this','that','these','those','am','is','are',
    'was','were','be','been','being','have','has','had','having','do','does',
    'did','doing','a','an','the','and','but','if','or','because','as','until',
    'while','of','at','by','for','with','about','against','between','into',
    'through','during','before','after','above','below','to','from','up','down',
    'in','out','on','off','over','under','again','further','then','once','here',
    'there','when','where','why','how','all','both','each','few','more','most',
    'other','some','such','no','nor','not','only','own','same','so','than',
    'too','very','s','t','can','will','just','don','should','now','d','ll',
    'm','o','re','ve','y','ain','aren','couldn','didn','doesn','hadn','hasn',
    'haven','isn','ma','mightn','mustn','needn','shan','shouldn','wasn','weren',
    'won','wouldn'
}

def clean(text: str) -> str:
    text = re.sub(r'[^a-zA-Z\s]', ' ', text.lower())
    return ' '.join(w for w in text.split() if w not in STOP_WORDS)

def match_resumes(job_description: str, resumes: list) -> list:
    """
    resumes: [{'id': int, 'name': str, 'text': str, 'email': str}]
    Returns ranked list with match scores.
    """
    jd_clean = clean(job_description)
    resume_texts = [clean(r['text']) for r in resumes]

    corpus = [jd_clean] + resume_texts
    vectorizer = TfidfVectorizer(ngram_range=(1, 2), max_features=8000)
    tfidf_matrix = vectorizer.fit_transform(corpus)

    jd_vec = tfidf_matrix[0]
    resume_vecs = tfidf_matrix[1:]
    scores = cosine_similarity(jd_vec, resume_vecs)[0]

    ranked = []
    for i, r in enumerate(resumes):
        score = round(float(scores[i]) * 100, 1)
        ranked.append({
            'id': r.get('id', i + 1),
            'name': r['name'],
            'email': r.get('email', 'N/A'),
            'score': score,
            'grade': _grade(score),
            'text_preview': r['text'][:200] + '...' if len(r['text']) > 200 else r['text']
        })

    return sorted(ranked, key=lambda x: x['score'], reverse=True)

def _grade(score: float) -> str:
    if score >= 70: return 'Excellent Match'
    if score >= 50: return 'Good Match'
    if score >= 30: return 'Partial Match'
    return 'Low Match'

def suggest_resume_improvements(resume_text: str, job_description: str) -> list:
    jd_words = set(clean(job_description).split())
    resume_words = set(clean(resume_text).split())
    missing = jd_words - resume_words
    keywords = [w for w in missing if len(w) > 4][:10]
    suggestions = []
    if keywords:
        suggestions.append(f"Add these missing keywords: {', '.join(keywords)}")
    if len(resume_text.split()) < 200:
        suggestions.append("Resume is too short. Add more details about experience and skills.")
    if 'project' not in resume_text.lower():
        suggestions.append("Include a Projects section to showcase practical experience.")
    if not any(w in resume_text.lower() for w in ['github', 'linkedin', 'portfolio']):
        suggestions.append("Add links to GitHub, LinkedIn, or portfolio.")
    return suggestions if suggestions else ["Resume looks well-aligned with the job description!"]
