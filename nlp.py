import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

def clean_text(text):
    text = text.lower()
    text = re.sub(r'[^a-zA-Z0-9\s]', ' ', text)  # remove symbols
    text = re.sub(r'\s+', ' ', text)  # remove extra spaces
    return text.strip()


def calculate_score(jd_text, resume_text):

    if not jd_text.strip() or not resume_text.strip():
        return 0, ["Missing job description or resume"]

    # ✅ CLEAN BOTH TEXTS
    jd_text = clean_text(jd_text)
    resume_text = clean_text(resume_text)

    # ✅ BETTER VECTORIZER
    vectorizer = TfidfVectorizer(
        stop_words='english',
        ngram_range=(1, 2),  # important upgrade
        max_features=5000
    )

    vectors = vectorizer.fit_transform([jd_text, resume_text])

    similarity = cosine_similarity(vectors[0:1], vectors[1:2])[0][0]

    score = round(similarity * 100, 2)

    # clamp
    score = max(0, min(score, 100))

    # suggestions
    suggestions = []
    if score < 50:
        suggestions.append("Add more relevant skills from job description")
        suggestions.append("Improve keyword matching with JD")
    elif score < 75:
        suggestions.append("Improve alignment with job description")
        suggestions.append("Add more measurable achievements")
    else:
        suggestions.append("Strong match, refine formatting")

    return score, suggestions