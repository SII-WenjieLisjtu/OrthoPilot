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
            'type': item.get('type', '开放') 
        })
    
    return rt_data


if __name__ == "__main__":
    all_questions = {}
    for key in ['task1', 'task2']:
        all_questions[key] = {
            '开放': [], #ROUGE-L F1, BLEU Score, Cosine Similarity
            '选择': [0, 0], # T, F
            '判断': [0, 0, 0, 0] #TT, TF, FT, FF
        }


    task_1_data = prepare_json('/Users/wangchenrun/Work/骨科/data/task1.json')
    task_2_data = prepare_json('/Users/wangchenrun/Work/骨科/data/task2.json')

    data_pairs = {
        'task1': [task_1_data],
        'task2': [task_2_data]
    }
    

    for task, data in data_pairs.items():
        for pid, qas in data[0].items():
            for idx, qa in enumerate(qas):
                gt = qa['c'][2]['value']
                answer = qa['c'][3]['value']

                if qa['type'] == '判断':                
                    answer = answer[-1]
                    if gt == answer:
                        all_questions[task]['判断'][0] += 1
                    elif gt == '是' and answer == '否':
                        all_questions[task]['判断'][1] += 1
                    elif gt == '否' and answer == '是':
                        all_questions[task]['判断'][2] += 1
                    else:
                        all_questions[task]['判断'][3] += 1
                
                if qa['type'] == '选择':
                    gt = gt.lower()  
                    answer = answer[-1]
                    if answer not in ['a', 'b', 'c', 'd', 'A', 'B', 'C', 'D']:
                        # 提取最后20个字符中的最后一个英文字母
                        last_20 = qa['c'][3]['value'][-20:]
                        match = re.findall(r'[a-zA-Z]', last_20)
                        answer = match[-1] if match else ''
                        if not answer or answer not in ['a', 'b', 'c', 'd', 'A', 'B', 'C', 'D']:
                            break
                    answer = answer.lower()
                    if gt == answer:
                        all_questions[task]['选择'][0] += 1
                    else:
                        all_questions[task]['选择'][1] += 1
                        
                if qa['type'] == '开放':
                    rouge_l, bleu, cosine = compute_all_metrics(gt, answer)
                    all_questions[task]['开放'].append([rouge_l, bleu, cosine])
                    
            
    
    # 输出数据总结
    for task, results in all_questions.items():
        print(f"任务: {task}")
        # 开放题
        if results['开放']:
            rouge_l_scores = [x[0] for x in results['开放']]
            bleu_scores = [x[1] for x in results['开放']]
            cosine_scores = [x[2] for x in results['开放']]
            print(f"  开放题数量: {len(results['开放'])}")
            print(f"    ROUGE-L F1 平均值: {np.mean(rouge_l_scores):.4f}")
            print(f"    BLEU 平均值: {np.mean(bleu_scores):.4f}")
            print(f"    Cosine Similarity 平均值: {np.mean(cosine_scores):.4f}")
        else:
            print("  开放题: 无数据")
        # 选择题
        total_choice = sum(results['选择'])
        if total_choice > 0:
            print(f"  选择题数量: {total_choice}")
            print(f"    正确: {results['选择'][0]}, 错误: {results['选择'][1]}, 正确率: {results['选择'][0]/total_choice:.2%}")
        else:
            print("  选择题: 无数据")
        # 判断题
        total_judge = sum(results['判断'])
        if total_judge > 0:
            print(f"  判断题数量: {total_judge}")
            print(f"    TT: {results['判断'][0]}, TF: {results['判断'][1]}, FT: {results['判断'][2]}, FF: {results['判断'][3]}")
            print(f"    正确率: {(results['判断'][0]/total_judge):.2%}")
        else:
            print("  判断题: 无数据")
        print("-" * 40)
