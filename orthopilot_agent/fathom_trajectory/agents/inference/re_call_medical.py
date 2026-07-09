import re
import json
import requests
import time
from typing import List, Tuple, Dict, Any
from functools import wraps
from datetime import datetime


def retry(max: int = 10, sleep: int = 1, fallback=None):
    """
    Retry `max` times and, if still failing, return `fallback`
    instead of raising.  This keeps outer loops alive.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for i in range(max):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    print(f"[retry] attempt {i+1}/{max} failed: {e}")
                    if i == max - 1:                 # last try exhausted
                        print(f"[retry] giving up – returning {fallback!r}")
                        return fallback              # ← swallow the error
                    if sleep:
                        time.sleep(sleep)
        return wrapper
    return decorator


class ReCallMedical():
    """
    Medical domain version of ReCall with search limit (max 5 searches).
    Generates trajectory with search tool calls and responses for medical diagnosis.
    """

    sys_prompt = """
    你是骨科住院医生助手。你的任务是根据患者信息进行诊断分析。
    在此环境中,你可以使用一系列工具来辅助诊断。

    你可以进行多轮函数调用。在每一轮中,你可以调用一个或多个函数。

    遵循以下原则:

    1. 基于证据的诊断: 通过调用工具收集证据,探索关键要点,直至具备充分依据。
    2. 反复验证: 在给出最终诊断前,进行交叉检查与核实。
    3. 关注细节: 确保来源可信、信息相关且时效正确。

    可用函数的JSONSchema格式如下:\n```json\n{func_schemas}\n```

    在调用医学知识图谱相关工具时，请遵循以下流程：
    1. 必须首先使用 kg_get_relations工具确认医学实体在图谱中是否存在，并获取其可用关系类型；
    2. 若实体不存在或不确定，请调用 kg_fuzzy_search工具获取相似医学实体，并基于返回结果选择合适的标准实体名称；
    3. 仅对已经在图谱中确认存在的实体及其可用关系，调用 kg_search(entity, relation) 或 kg_search(entity) 获取对应的知识内容，避免直接对原始用户输入进行盲目检索。
    4. 若使用知识图谱，必须使用kg_search工具。
    
    在你的回答中,先在<think></think>中进行推理; 如需信息,在<tool_call></tool_call>中给出函数与参数;
    函数执行结果会返回,你可继续调用,直到获得最终答案; 若已具备答案,请仅将结果置于<answer></answer>中。

    例如: <think> 根据函数调用的响应,我获得了诊断依据。 </think> <answer>入院诊断:老年性髋关节病。</answer>

    对每个函数调用,在<tool_call></tool_call>标签内返回一个JSON对象:
    <tool_call>
    {{"name": <function-name>, "arguments": <args-json-object>}}
    </tool_call>
    """


    def __init__(self, executor_url, max_searches: int = 5, sys_prompt: str | None = None, teacher_hint: str | None = None, suppress_logs: bool = True):
        self.executor_url = executor_url
        self.max_searches = max_searches
        self.search_count = 0
        # 可覆盖system提示; 可追加教师提示
        base = sys_prompt if sys_prompt is not None else self.sys_prompt
        if teacher_hint:
            base = base + "\n\n[TEACHER_HINT] " + teacher_hint
        self.sys_prompt = base
        self.suppress_logs = suppress_logs


    def init_prompt(self, func_schemas, question):
        system_prompt = f"<|im_start|>system\n{self.sys_prompt.format(func_schemas=func_schemas)}<|im_end|>"
        user_prompt = f"<|im_start|>user\n{question}<|im_end|>"
        assistant_prefix = f"<|im_start|>assistant\n<think>"
        return system_prompt + "\n" + user_prompt + "\n" + assistant_prefix


    def _strip_old_tool_responses(self, prompt: str) -> str:
        TOOL_RESPONSE_RE = re.compile(r"<tool_response>.*?</tool_response>\s*", re.DOTALL)
        """Remove every existing <tool_response> … </tool_response> block."""
        return TOOL_RESPONSE_RE.sub("", prompt)

    def cat_assistant_response(self, curr_prompt, assistant_response):
        return curr_prompt + assistant_response + "<|im_end|>"

    def cat_tool_results(self, curr_prompt, tool_calls, results):
        tool_response_str = ""
        for tool_call, result in zip(tool_calls, results):
            tool_response_str += f"<tool_response>{tool_call}\n{result}\n</tool_response>\n"
        tool_response_str = f"<|im_start|>user\n{tool_response_str}<|im_end|>"
        assistant_prefix = f"<|im_start|>assistant\n<think>"
        return curr_prompt + "\n" + tool_response_str + "\n" + assistant_prefix

    def format_tool_call(self, tool_call_str: str):
        """Convert JSON function call description to Python executable code string."""
        try:
            call_json = json.loads(tool_call_str)
            func_name = call_json['name']
            arguments = call_json.get('arguments', {})

            args_str = ', '.join(f"{k}={repr(v)}" for k, v in arguments.items())
            return f"{func_name}({args_str})"
        except Exception as e:
            return f"Parse tool call failed: {e}"

    def is_search_call(self, call_str: str) -> bool:
        """Check if a tool call is a search operation."""
        search_keywords = ['search', 'query', 'retrieve', 'find']
        call_lower = call_str.lower()
        return any(keyword in call_lower for keyword in search_keywords)

    def execute_tool_calls(self, env: str, tool_calls: List[str]) -> List[str]:
        def exe_tool_call(env, call):
            url = self.executor_url + '/execute'

            call_str = self.format_tool_call(call)

            # Check search limit
            if self.is_search_call(call_str):
                self.search_count += 1
                if self.search_count > self.max_searches:
                    return f"error: 已达到最大搜索次数限制({self.max_searches}次),无法执行更多搜索操作"
                print(f"[Search {self.search_count}/{self.max_searches}] Executing: {call_str}")

            if call_str.startswith("error: parse tool call failed"):
                return call_str

            try:
                data = {
                    'env': env,
                    'call': call_str
                }
                response = requests.post(url, json=data, timeout=60000)
                if response.status_code != 200:
                    return f"error: {response.status_code}"
                response = response.json()
                ret_str = ''
                if response['result']:
                    ret_str += f'result: \n{response["result"]}\n'
                if response['output']:
                    ret_str += f'output: \n{response["output"]}\n'
                if response['error']:
                    ret_str += f'error: \n{response["error"]}\n'
                return ret_str.strip()
            except requests.exceptions.Timeout:
                return "error: execution timed out"
            except Exception as e:
                return str(e)

        results = []
        for tool_call in tool_calls:
            result = exe_tool_call(env, tool_call)
            results.append(result)
        return results

    def validate_tool_calls(self, output_str):
        start_tags = re.findall(r'<tool_call>', output_str)
        end_tags = re.findall(r'</tool_call>', output_str)

        if len(start_tags) != len(end_tags):
            return False

        start_positions = [m.start() for m in re.finditer(r'<tool_call>', output_str)]
        end_positions = [m.start() for m in re.finditer(r'</tool_call>', output_str)]

        for start, end in zip(start_positions, end_positions):
            if start >= end:
                return False

        return True

    def extract_tool_calls(self, output_str):
        if not self.validate_tool_calls(output_str):
            return []

        try:
            pattern = r'<tool_call>((?:(?!</tool_call>).)*)</tool_call>'
            matches = re.finditer(pattern, output_str, re.DOTALL)

            return [match.group(1).strip() for match in matches]
        except Exception as e:
            return []

    def extract_answer(self, output_str):
        """Extract final answer from <answer> tags."""
        pattern = r'<answer>(.*?)</answer>'
        match = re.search(pattern, output_str, re.DOTALL)
        if match:
            return match.group(1).strip()
        return None

    @retry(max=5, sleep=1, fallback={"transcript": "", "tool_calls": [], "trajectory": []})
    def run(
        self,
        env: str,
        func_schemas: str,
        question: str,
        tokenizer,
        model_url="http://YOUR_HOST:YOUR_PORT",
        temperature: float = 0.0,
        max_new_tokens: int = 40960,
        ) -> Tuple[str, List[str], List[Dict[str, Any]]]:
        """
        Run the agent and return (transcript, all_tool_calls, trajectory).

        Returns:
            - transcript: Full conversation transcript
            - all_tool_calls: List of all tool calls made
            - trajectory: List of trajectory steps with role, content, and tool info
        """
        curr_prompt = self.init_prompt(func_schemas, question)
        all_tool_calls = []
        trajectory = []

        # Add system message to trajectory
        trajectory.append({
            "role": "system",
            "content": "你是骨科住院医生,遵循\"问题→登记工具(不立取)→(下一条user)返回工具结果→回答本问\"的节律。工具只为【上一条用户问题】服务;若检索不到精确检查/检验,环境会返回已实际完成的最相近项目与结果并说明差异。检验/检查工具均支持两种入参:time_range 或 items。回答尽量基于证据;证据不足时明确指出所需检查。"
        })

        # Add initial user question to trajectory
        trajectory.append({
            "role": "user",
            "content": question
        })

        for i in range(64):
            prompt_tokens = tokenizer(curr_prompt, return_tensors=None, add_special_tokens=False)["input_ids"]
            max_tokens_left = max_new_tokens - len(prompt_tokens) - 100

            response = requests.post(
                f'{model_url}/generate',
                json={
                    "text": curr_prompt,
                    "sampling_params": {
                        "temperature": temperature,
                        "max_new_tokens": max_tokens_left,
                        "repetition_penalty": 1.05
                    },

                }
            ).json()
            if not self.suppress_logs:
                print("="*100)
                print(f"Thinking .... (Iteration {i+1})")
                print("<think>"+response['text'])
                print("="*100)

            if "error" in response.keys():
                print("resp",response)
            curr_prompt = self.cat_assistant_response(curr_prompt, response['text'])

            tool_calls: List[str] = self.extract_tool_calls(response['text'])
            final_answer = self.extract_answer(response['text'])

            # Add GPT response to trajectory
            gpt_content = response['text']
            trajectory.append({
                "role": "gpt",
                "content": gpt_content
            })

            # 若已给出<answer>，立即停止后续搜索
            if final_answer:
                break

            if len(tool_calls) == 0:
                break
            else:
                all_tool_calls += tool_calls
                results: List[str] = self.execute_tool_calls(env, tool_calls)

                # Add tool responses to trajectory
                tool_response_content = ""
                for tool_call, result in zip(tool_calls, results):
                    tool_response_content += f"<tool_response>{{\"tool\":\"{tool_call}\",\"data\":{result}}}</tool_response>\n"

                trajectory.append({
                    "role": "user",
                    "content": tool_response_content.strip()
                })

                curr_prompt = self.cat_tool_results(curr_prompt, tool_calls, results)

                # Check if we've hit search limit
                if self.search_count >= self.max_searches:
                    break

        return curr_prompt, all_tool_calls, trajectory
