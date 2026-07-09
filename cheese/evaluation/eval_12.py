import nltk
import numpy as np
from rouge_score import rouge_scorer
from nltk.translate.bleu_score import sentence_bleu, SmoothingFunction
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import json, os
import re



nltk.download('punkt_tab', download_dir='./nltk_data')
nltk.data.path.append(os.path.abspath('./nltk_data'))

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
    return rouge_l, bleu, cosine

def prepare_json(json_path):
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    rt_data = {}
    for item in data:
        if item['id'] not in rt_data:
            rt_data[item['id']] = []
        rt_data[item['id']].append({
            'c': item['conversations'],
            'type': item.get('type', 'open')
        })

    return rt_data


if __name__ == "__main__":
    all_questions = {}
    for key in ['task1', 'task2']:
        all_questions[key] = {
            'open': [], #ROUGE-L F1, BLEU Score, Cosine Similarity
            'choice': [0, 0], # T, F
            'judgement': [0, 0, 0, 0] #TT, TF, FT, FF
        }


    task_1_data = prepare_json('path/to/task1.json')
    task_2_data = prepare_json('path/to/task2.json')

    data_pairs = {
        'task1': [task_1_data],
        'task2': [task_2_data]
    }


    for task, data in data_pairs.items():
        for pid, qas in data[0].items():
            for idx, qa in enumerate(qas):
                gt = qa['c'][2]['value']
                answer = qa['c'][3]['value']

                if qa['type'] == 'judgement':
                    answer = answer[-1]
                    if gt == answer:
                        all_questions[task]['judgement'][0] += 1
                    elif gt == 'yes' and answer == 'no':
                        all_questions[task]['judgement'][1] += 1
                    elif gt == 'no' and answer == 'yes':
                        all_questions[task]['judgement'][2] += 1
                    else:
                        all_questions[task]['judgement'][3] += 1

                if qa['type'] == 'choice':
                    gt = gt.lower()
                    answer = answer[-1]
                    if answer not in ['a', 'b', 'c', 'd', 'A', 'B', 'C', 'D']:
                        # 20
                        last_20 = qa['c'][3]['value'][-20:]
                        match = re.findall(r'[a-zA-Z]', last_20)
                        answer = match[-1] if match else ''
                        if not answer or answer not in ['a', 'b', 'c', 'd', 'A', 'B', 'C', 'D']:
                            break
                    answer = answer.lower()
                    if gt == answer:
                        all_questions[task]['choice'][0] += 1
                    else:
                        all_questions[task]['choice'][1] += 1

                if qa['type'] == 'open':
                    rouge_l, bleu, cosine = compute_all_metrics(gt, answer)
                    all_questions[task]['open'].append([rouge_l, bleu, cosine])



    # output
    for task, results in all_questions.items():
        print(f"task: {task}")
        # open
        if results['open']:
            rouge_l_scores = [x[0] for x in results['open']]
            bleu_scores = [x[1] for x in results['open']]
            cosine_scores = [x[2] for x in results['open']]
            print(f" open: {len(results['open'])}")
            print(f" ROUGE-L F1: {np.mean(rouge_l_scores):.4f}")
            print(f" BLEU: {np.mean(bleu_scores):.4f}")
            print(f" Cosine Similarity: {np.mean(cosine_scores):.4f}")
        else:
            print(" open: ")
        # choice
        total_choice = sum(results['choice'])
        if total_choice > 0:
            print(f" choice: {total_choice}")
            print(f": {results['choice'][0]}, error: {results['choice'][1]},: {results['choice'][0]/total_choice:.2%}")
        else:
            print(" choice: ")
        # judgement
        total_judge = sum(results['judgement'])
        if total_judge > 0:
            print(f" judgement: {total_judge}")
            print(f" TT: {results['judgement'][0]}, TF: {results['judgement'][1]}, FT: {results['judgement'][2]}, FF: {results['judgement'][3]}")
            print(f": {(results['judgement'][0]/total_judge):.2%}")
        else:
            print(" judgement: ")
        print("-" * 40)
