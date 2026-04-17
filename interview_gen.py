import re

# Question bank organized by category
QUESTION_BANK = {
    'general': [
        "Tell me about yourself and your professional background.",
        "Why are you interested in this position?",
        "Where do you see yourself in 5 years?",
        "What is your greatest professional achievement?",
        "How do you handle pressure and tight deadlines?",
        "Describe a situation where you showed leadership.",
        "What motivates you in your work?",
        "How do you prioritize tasks when managing multiple projects?",
    ],
    'technical_ml': [
        "Explain the difference between supervised and unsupervised learning.",
        "What is overfitting and how do you prevent it?",
        "Explain TF-IDF and its applications.",
        "What is cosine similarity and when would you use it?",
        "Describe the bias-variance tradeoff.",
        "What cross-validation techniques have you used?",
        "Explain how a Random Forest works.",
        "What is the difference between precision and recall?",
    ],
    'technical_python': [
        "What are Python decorators and how do you use them?",
        "Explain list comprehensions with an example.",
        "What is the difference between a list and a tuple?",
        "How does Python's GIL affect multithreading?",
        "Explain OOP concepts in Python.",
        "What are generators and when would you use them?",
    ],
    'technical_web': [
        "Explain the difference between REST and GraphQL APIs.",
        "What is the difference between GET and POST requests?",
        "How does session management work in web applications?",
        "Explain CORS and why it matters.",
        "What are the key principles of responsive design?",
    ],
    'behavioral': [
        "Describe a time you disagreed with a team member. How did you resolve it?",
        "Tell me about a project that failed. What did you learn?",
        "Give an example of when you went above and beyond for a project.",
        "How do you handle constructive criticism?",
        "Describe your experience working in a team environment.",
    ],
    'company_specific': [
        "What do you know about our company and our products?",
        "How do your skills align with our company's mission?",
        "What unique value would you bring to our team?",
        "Have you used any of our services before? What was your experience?",
        "How would you contribute to our company culture?",
    ]
}

SKILL_KEYWORDS = {
    'machine learning': 'technical_ml',
    'data science': 'technical_ml',
    'python': 'technical_python',
    'flask': 'technical_web',
    'django': 'technical_web',
    'web': 'technical_web',
    'api': 'technical_web',
    'nlp': 'technical_ml',
    'deep learning': 'technical_ml',
}

def generate_interview_questions(job_description: str, resume_text: str, company_name: str = "") -> list:
    jd_lower = job_description.lower()
    resume_lower = resume_text.lower()

    selected_categories = {'general', 'behavioral', 'company_specific'}

    for keyword, category in SKILL_KEYWORDS.items():
        if keyword in jd_lower or keyword in resume_lower:
            selected_categories.add(category)

    questions = []

    # Always include general + behavioral
    for cat in ['general', 'behavioral']:
        for q in QUESTION_BANK[cat][:3]:
            questions.append({'category': cat.replace('_', ' ').title(), 'question': q})

    # Add technical questions based on detected skills
    for cat in selected_categories - {'general', 'behavioral', 'company_specific'}:
        for q in QUESTION_BANK[cat][:4]:
            questions.append({'category': cat.replace('_', ' ').title(), 'question': q})

    # Company-specific questions
    for q in QUESTION_BANK['company_specific'][:2]:
        personalized = q.replace("our company", company_name if company_name else "our company")
        questions.append({'category': 'Company Specific', 'question': personalized})

    # Extract skills from JD and add targeted questions
    skills = re.findall(r'\b(python|java|sql|aws|docker|kubernetes|react|node|tensorflow|pytorch)\b', jd_lower)
    for skill in set(skills[:3]):
        questions.append({
            'category': 'Skill-Based',
            'question': f"Can you walk me through a project where you used {skill.upper()} extensively?"
        })

    return questions
