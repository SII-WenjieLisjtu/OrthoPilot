import nltk
import numpy as np
from rouge_score import rouge_scorer
from nltk.translate.bleu_score import sentence_bleu, SmoothingFunction
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# model
nltk.download('punkt')

def compute_rouge_l(reference, hypothesis):
    scorer = rouge_scorer.RougeScorer(['rougeL'], use_stemmer=True)
    scores = scorer.score(reference, hypothesis)
    return scores['rougeL'].fmeasure

def compute_bleu(reference, hypothesis):
    ref_tokens = [nltk.word_tokenize(reference)]
    hyp_tokens = nltk.word_tokenize(hypothesis)
    smoothing = SmoothingFunction().method1
    return sentence_bleu(ref_tokens, hyp_tokens, smoothing_function=smoothing)

def compute_cosine_similarity(text1, text2):
    vectorizer = TfidfVectorizer()
    vectors = vectorizer.fit_transform([text1, text2])
    cosine_sim = cosine_similarity(vectors[0:1], vectors[1:2])
    return cosine_sim[0][0]

def compute_all_metrics(reference, hypothesis):
    rouge_l = compute_rouge_l(reference, hypothesis)
    bleu = compute_bleu(reference, hypothesis)
    cosine = compute_cosine_similarity(reference, hypothesis)

    print(": ")
    print(f" ROUGE-L F1: {rouge_l:.4f}")
    print(f" BLEU Score: {bleu:.4f}")
    print(f" Cosine Similarity: {cosine:.4f}")

#
if __name__ == "__main__":
    reference = "patient,."
    hypothesis = "patient."

    compute_all_metrics(reference, hypothesis)


# pip install rouge-score nltk scikit-learn
