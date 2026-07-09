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
 instead of raising. This keeps outer loops alive.
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
                        print(f"[retry] giving up - returning {fallback!r}")
                        return fallback              # <- swallow the error
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
 yes clinician.taskyespatient.
,.

.,.

:

 1.:,,.
 2.:,.
 3.:,.

 JSONSchema:\n```json\n{func_schemas}\n```

,:
 1. kg_get_relations returns yes or no when applicable.
 2. does not exist, kg_fuzzy_search, resultchoice;
 3., kg_search(entity, relation) kg_search(entity) content, input.
 4., textkg_search.

,<think></think>;,<tool_call></tool_call>;
 result,,answer; answer,result<answer></answer>.

: <think>,. </think> <answer>:.</answer>

,<tool_call></tool_call>JSON:
 <tool_call>
 {{"name": <function-name>, "arguments": <args-json-object>}}
 </tool_call>
 """


    def __init__(self, executor_url, max_searches: int = 5, sys_prompt: str | None = None, teacher_hint: str | None = None, suppress_logs: bool = True):
        self.executor_url = executor_url
        self.max_searches = max_searches
        self.search_count = 0
        # system;
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
        """Remove every existing <tool_response> ... </tool_response> block."""
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
                    return f"error: ({self.max_searches}),"
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
        model_url="http://localhost:8000",
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
            "content": "yes clinician,\"->()->(user)result->\".[];/,result./:time_range items.;."
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
                print(f"Thinking.... (Iteration {i+1})")
                print("<think>"+response.get('text') or response.get('content', ''))
                print("="*100)

            if "error" in response.keys():
                print("resp",response)
            curr_prompt = self.cat_assistant_response(curr_prompt, response.get('text') or response.get('content', ''))

            tool_calls: List[str] = self.extract_tool_calls(response.get('text') or response.get('content', ''))
            final_answer = self.extract_answer(response.get('text') or response.get('content', ''))

            # Add GPT response to trajectory
            gpt_content = response.get('text') or response.get('content', '')
            trajectory.append({
                "role": "gpt",
                "content": gpt_content
            })

            # <answer>,
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
