#!/usr/bin/env python3
"""
medical_trajectory_generator.py — 生成包含搜索工具调用和响应的医疗诊断轨迹

功能:
  - 基于Fathom-DeepResearch的ReCall框架
  - 限制搜索工具调用次数(最多5次)
  - 生成包含搜索证据的完整轨迹
  - 输出格式与the OrthoPilot trajectory JSON schema兼容

使用:
  python medical_trajectory_generator.py \
    --question "患者入院,请基于检查结果给出入院诊断与依据" \
    --model-url http://YOUR_HOST:YOUR_PORT \
    --executors http://YOUR_HOST:YOUR_PORT \
    --tokenizer FractalAIResearch/Fathom-Search-4B \
    --output-path ./output/trajectory.json \
    --max-searches 5
"""

import argparse
import json
import os
import sys
from typing import Any, Dict, List

# Import the medical ReCall agent
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'agents', 'inference'))
from re_call_medical import ReCallMedical

# Optional: HF tokenizer
try:
    from transformers import AutoTokenizer
except Exception:
    AutoTokenizer = None


# Medical domain tool schemas
MEDICAL_ENV = "from ehr_api import get_patient, get_lab_results, search_guidelines"

MEDICAL_SCHEMAS: List[Dict[str, Any]] = [
    # {
    #     "name": "get_patient",
    #     "description": "获取患者基本信息(姓名、性别、年龄、入院时间、入院诊断等)",
    #     "parameters": {
    #         "type": "object",
    #         "properties": {},
    #         "required": [],
    #     },
    # },
    {
        "name": "search_guidelines",
        "description": "搜索相关诊疗指南和文献证据(此为搜索工具,受次数限制)",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "搜索关键词"},
                "domain": {"type": "string", "description": "专业领域,如'骨科'等"}
            },
            "required": ["query"],
        },
    },
    {
        "name": "search_differential_diagnosis",
        "description": "搜索鉴别诊断相关信息(此为搜索工具,受次数限制)",
        "parameters": {
            "type": "object",
            "properties": {
                "symptoms": {"type": "array", "items": {"type": "string"}, "description": "症状列表"},
                "age": {"type": "integer", "description": "患者年龄"},
                "specialty": {"type": "string", "description": "专科,如'骨科'"}
            },
            "required": ["symptoms"],
        },
    },
    {
        "name": "kg_search",
        "description": "通用医学知识图谱查询工具。用于检索与医学实体相关的结构化信息，包括疾病的症状、检查、治疗方式、病因、并发症、流行病学特征、预后等内容。模型在需要进行医学事实查证、补全疾病画像、推断关联医学概念时，应优先调用本工具，以保证医学内容的准确性与一致性。",
        "parameters": {
            "type": "object",
            "properties": {
            "entity": {
                "type": "string",
                "description": "要查询的医学实体名称，通常是疾病、症状、药物、检查项目、手术操作、解剖结构等的标准中文名称或常用别名。"
            },
            "relation": {
                "type": "string",
                "description": "可选的关系类型过滤。此字段必须从以下固定的关系类型中选择其一（不需要写函数名前缀）：\n\n【治疗相关】\n- \"药物治疗\"\n- \"辅助治疗\"\n- \"手术治疗\"\n- \"放射治疗\"\n- \"化疗\"\n- \"预防\"\n\n【检查相关】\n- \"实验室检查\"\n- \"影像学检查\"\n- \"辅助检查\"\n- \"内窥镜检查\"\n- \"组织学检查\"\n- \"筛查\"\n\n【症状诊断相关】\n- \"临床表现\"\n- \"病因\"\n- \"病理分型\"\n- \"并发症\"\n- \"鉴别诊断\"\n- \"高危因素\"\n\n【流行病学相关】\n- \"发病率\"\n- \"发病部位\"\n- \"多发群体\"\n- \"发病年龄\"\n- \"性别倾向\"\n- \"多发地区\"\n- \"多发季节\"\n- \"死亡率\"\n\n【预后相关】\n- \"预后状况\"\n- \"生存率\"\n- \"治疗后症状\"\n\n【其他关系】\n- \"同义词\"\n- \"风险评估因素\"\n- \"相关导致\"\n- \"相关转化\"\n- \"相关症状\"\n- \"就诊科室\"\n- \"转移部位\"\n- \"外侵部位\"\n- \"遗传因素\"\n- \"传播途径\"\n- \"发病机制\"\n- \"病理生理\"\n- \"病史\"\n- \"阶段\"\n- \"合并症\"\n- \"侵及周围组织症状\"\n\n若不填写 relation，则默认返回该实体的多类关系结果。"
            },
            },
            "required": ["entity"]
        }
        },
    {
        "name": "kg_get_relations",
        "description": "获取实体的所有关系类型和统计信息,了解实体的全部关系",
        "parameters": {
            "type": "object",
            "properties": {
                "entity": {"type": "string", "description": "医学实体名称"},
                "limit_per_relation": {"type": "integer", "description": "每种关系返回的最大数量"},
            },
            "required": ["entity"],
        },
    },
    # {
    #     "name": "kg_get_entity_type",
    #     "description": "查询指定实体的类型",
    #     "parameters": {
    #         "type": "object",
    #         "properties": {
    #             "entity": {"type": "string", "description": "医学实体名称"},
    #         },
    #         "required": ["entity"],
    #     },
    # },
    {
        "name": "kg_fuzzy_search",
        "description": "在医学知识图谱中执行模糊搜索，用于根据给定关键词查找可能匹配的医学实体列表。该接口支持大小写差异、同义词、缩写、轻微拼写错误等相似匹配，并按相似度得分排序返回结果。常用于用户输入不够规范或不确定准确写法时，将自然语言、口语化表述或不完整的实体名映射到知识图谱中的标准医学实体。",
        "parameters": {
            "type": "object",
            "properties": {
            "keyword": {
                "type": "string",
                "description": "用于检索的关键词，可以是不完整的实体名、口语化描述或可能含有轻微拼写错误的医学名词。"
            },
            "threshold": {
                "type": "number",
                "description": "相似度阈值，取值范围 0-1。仅返回相似度不低于该阈值的候选实体，数值越高，匹配越严格，数量通常越少。"
            },
            "limit": {
                "type": "integer",
                "description": "最多返回的候选实体数量上限，用于控制结果列表长度并避免信息过载。"
            }
            },
            "required": ["entity"]
  }
},

    {
        "name": "medibook_search",
        "description": "在本地或预先索引好的医学书籍与教材知识库中进行检索，包括教科书、指南、综述性资料等权威文献。适用于需要从系统医学知识中查找定义、诊疗流程、分型标准、并发症描述等场景。通过语义相似度找到最相关的章节或段落，实现比简单关键词匹配更鲁棒的语义搜索。",
        "parameters": {
            "type": "object",
            "properties": {
            "search_mode": {
                "type": "string",
                "description": "检索模式，例如 \"embedding\" 表示使用向量相似性进行语义检索（推荐默认使用），也可以根据系统实现约定支持其它模式（如关键字匹配）。"
            },
            "query": {
                "type": "string",
                "description": "检索请求内容，可以是一个问题、一段描述或若干关键术语，用于在医学书籍知识库中查找最相关的条目或上下文内容。"
            }
            },
            "required": ["query"]
  }
},

    {
        "name": "semanticscholar_search",
        "description": "基于 Semantic Scholar 等学术搜索引擎进行在线学术论文检索。适合用于查找最新或代表性的研究文献、系统综述、临床试验、方法论文等。调用该工具时，模型应构造清晰、具体的包含医学领域关键词的 query，以便返回与主题高度相关的论文元数据（如标题、作者、年份、期刊、摘要等），而不负责下载或解析全文。",
        "parameters": {
            "type": "object",
            "properties": {
            "query": {
                "type": "string",
                "description": "学术检索查询语句，可包含疾病名称、研究对象、方法关键词、时间范围等，用于精确描述想要查找的研究主题。"
            },
            "limit": {
                "type": "integer",
                "description": "返回的文献数量上限，用于控制结果规模（例如 5、10 等），通常按相关度或综合评分排序。"
            }
            },
            "required": ["query"]
        }
},
    {
    "name": "wikipedia_search",
    "description": "在 Wikipedia 语料中检索与问题相关的片段，用于快速获取通用背景知识与概念解释。适用于术语释义、疾病概览、解剖结构、常见症状/机制等的初步证据检索。",
    "parameters": {
      "type": "object",
      "properties": {
        "question": {
          "type": "string",
          "description": "要检索的问题或查询语句（建议为一句完整问题或包含关键医学实体/现象的短句）。"
        }
      },
      "required": ["question"]
    }
  },
  {
    "name": "pubmed_search",
    "description": "在 PubMed 摘要语料中检索与问题相关的片段，用于寻找研究证据、实验结果、临床结论、流行病学与机制讨论等。适用于需要文献证据支撑或更偏研究的检索场景。",
    "parameters": {
      "type": "object",
      "properties": {
        "question": {
          "type": "string",
          "description": "要检索的问题或查询语句（建议包含疾病/干预/结局等核心关键词）。"
        }
      },
      "required": ["question"]
    }
  },
  {
    "name": "textbooks_search",
    "description": "在医学教材语料中检索与问题相关的片段，用于获取较为系统、结构化的医学知识（诊断要点、鉴别诊断、治疗原则、并发症等）。适用于临床知识查证与规则性总结。",
    "parameters": {
      "type": "object",
      "properties": {
        "question": {
          "type": "string",
          "description": "要检索的问题或查询语句（建议以临床问题表述，包含关键症状/体征/检查/诊断点）。"
        }
      },
      "required": ["question"]
    }
  },
  {
    "name": "statpearls_search",
    "description": "在 StatPearls 临床知识库语料中检索与问题相关的片段，用于获取偏临床决策支持的信息（诊疗流程、分层管理、用药注意事项、随访与预后等）。适用于更贴近临床路径与实践建议的检索场景。",
    "parameters": {
      "type": "object",
      "properties": {
        "question": {
          "type": "string",
          "description": "要检索的问题或查询语句（建议包含临床场景与想确认的诊疗要点）。"
        }
      },
      "required": ["question"]
    }
  }


]


def format_trajectory_for_output(trajectory: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """
    Format trajectory for JSON output compatible with the OrthoPilot trajectory format.
    Converts internal format to the expected output format.
    """
    formatted = []
    for step in trajectory:
        role = step.get("role", "")
        content = step.get("content", "")

        # Clean up content - extract key parts
        if role == "gpt":
            # For GPT responses, we want to keep think, tool_call, and answer tags
            formatted.append({
                "role": role,
                "content": content
            })
        elif role == "user":
            # For user messages, keep tool_response tags
            formatted.append({
                "role": role,
                "content": content
            })
        elif role == "system":
            # Keep system messages as is
            formatted.append({
                "role": role,
                "content": content
            })

    return formatted


def main():
    parser = argparse.ArgumentParser(
        description="生成包含搜索工具调用的医疗诊断轨迹"
    )
    parser.add_argument(
        "--question",
        required=True,
        help="诊断问题/任务描述"
    )
    parser.add_argument(
        "--model-url",
        required=True,
        help="模型服务器URL"
    )
    parser.add_argument(
        "--executors",
        required=True,
        help="工具执行器URL"
    )
    parser.add_argument(
        "--tokenizer",
        default="FractalAIResearch/Fathom-Search-4B",
        help="HuggingFace tokenizer路径"
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.6,
        help="采样温度"
    )
    parser.add_argument(
        "--max-new-tokens",
        type=int,
        default=40960,
        help="最大生成token数"
    )
    parser.add_argument(
        "--max-searches",
        type=int,
        default=5,
        help="最大搜索工具调用次数"
    )
    parser.add_argument(
        "--output-path",
        required=True,
        help="输出轨迹JSON文件路径"
    )
    parser.add_argument(
        "--patient-id",
        default="unknown",
        help="患者ID(用于文件命名)"
    )

    args = parser.parse_args()

    # Initialize tokenizer
    tok = None
    if args.tokenizer:
        if AutoTokenizer is None:
            raise RuntimeError("transformers not installed; `pip install transformers`")
        print(f"Loading tokenizer: {args.tokenizer}")
        tok = AutoTokenizer.from_pretrained(args.tokenizer, trust_remote_code=True)

    # Initialize medical agent with search limit
    print(f"Initializing medical agent with max {args.max_searches} searches...")
    agent = ReCallMedical(
        executor_url=args.executors.strip(),
        max_searches=args.max_searches
    )

    # Run the agent
    print(f"Running agent on question: {args.question}")
    print("="*80)

    transcript, tool_calls, trajectory = agent.run(
        env=MEDICAL_ENV,
        func_schemas=json.dumps(MEDICAL_SCHEMAS, ensure_ascii=False, indent=2),
        question=args.question,
        model_url=args.model_url,
        temperature=args.temperature,
        max_new_tokens=args.max_new_tokens,
        tokenizer=tok,
    )

    print("="*80)
    print(f"Agent completed. Total tool calls: {len(tool_calls)}")
    print(f"Search calls made: {agent.search_count}/{args.max_searches}")

    # Format trajectory for output
    formatted_trajectory = format_trajectory_for_output(trajectory)

    # Prepare output
    output_data = formatted_trajectory

    # Ensure output directory exists
    os.makedirs(os.path.dirname(args.output_path) if os.path.dirname(args.output_path) else ".", exist_ok=True)

    # Write trajectory to file
    with open(args.output_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    print(f"\nTrajectory saved to: {args.output_path}")
    print(f"Total steps in trajectory: {len(formatted_trajectory)}")

    # Print summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print(f"Question: {args.question}")
    print(f"Total interactions: {len(trajectory)}")
    print(f"Tool calls made: {len(tool_calls)}")
    print(f"Search calls: {agent.search_count}/{args.max_searches}")
    print(f"Output saved to: {args.output_path}")


if __name__ == "__main__":
    main()
