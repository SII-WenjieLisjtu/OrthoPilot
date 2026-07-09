# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

import re
from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential
import uuid


def _generate_message_id() -> str:
    """Generate random message ID using common LLM format"""
    # Use 8-character random hex string, similar to OpenAI API format, avoid cross-conversation cache hits
    return f"msg_{uuid.uuid4().hex[:8]}"


@retry(
    wait=wait_exponential(multiplier=15),
    stop=stop_after_attempt(5),
    retry_error_callback=lambda retry_state: print(
        f"Retry attempt {retry_state.attempt_number} for extract_hints"
    ),
)
async def extract_hints(
    question: str,
    api_key: str,
    chinese_context: bool,
    add_message_id: bool,
    base_url: str = "https://api.openai.com/v1",
) -> str:
    """Use LLM to extract task hints"""
    client = AsyncOpenAI(api_key=api_key, timeout=600, base_url=base_url)

    instruction = """Carefully analyze the given task description (question) without attempting to solve it directly. Your role is to identify potential challenges and areas that require special attention during the solving process, and provide practical guidance for someone who will solve this task by actively gathering and analyzing information from the web.

Identify and concisely list key points in the question that could potentially impact subsequent information collection or the accuracy and completeness of the problem solution, especially those likely to cause mistakes, carelessness, or confusion during problem-solving.

The question author does not intend to set traps or intentionally create confusion. Interpret the question in the most common, reasonable, and straightforward manner, without speculating about hidden meanings or unlikely scenarios. However, be aware that mistakes, imprecise wording, or inconsistencies may exist due to carelessness or limited subject expertise, rather than intentional ambiguity.

Additionally, when considering potential answers or interpretations, note that question authors typically favor more common and familiar expressions over overly technical, formal, or obscure terminology. They generally prefer straightforward and common-sense interpretations rather than being excessively cautious or academically rigorous in their wording choices.

Also, consider additional flagging issues such as:
- Potential mistakes or oversights introduced unintentionally by the question author due to his misunderstanding, carelessness, or lack of attention to detail.
- Terms or instructions that might have multiple valid interpretations due to ambiguity, imprecision, outdated terminology, or subtle wording nuances.
- Numeric precision, rounding requirements, formatting, or units that might be unclear, erroneous, or inconsistent with standard practices or provided examples.
- Contradictions or inconsistencies between explicit textual instructions and examples or contextual clues provided within the question itself.

Do NOT attempt to guess or infer correct answers, as complete factual information is not yet available. Your responsibility is purely analytical, proactively flagging points that deserve special attention or clarification during subsequent information collection and task solving. Avoid overanalyzing or listing trivial details that would not materially affect the task outcome.

Here is the question:

"""

    # Add multilingual-context instructions if enabled.
    if chinese_context:
        instruction += """

## Multilingual context notes

If the task contains non-English names, units, or quoted phrases, preserve their meaning and formatting when they matter for the final answer. Flag possible translation-sensitive terms, abbreviations, and formatting requirements.

"""

    # Add message ID for O3 messages (if configured)
    content = instruction + question
    if add_message_id:
        message_id = _generate_message_id()
        content = f"[{message_id}] {content}"

    response = await client.chat.completions.create(
        model="Gemini-2.5-pro",
        messages=[{"role": "user", "content": content}],
        reasoning_effort="high",
    )

    result = response.choices[0].message.content

    # Check if result is empty, raise exception to trigger retry if empty
    if not result or not result.strip():
        raise ValueError("Hint extraction returned empty result")

    return result


@retry(
    wait=wait_exponential(multiplier=15),
    stop=stop_after_attempt(5),
    retry_error_callback=lambda retry_state: print(
        f"Retry attempt {retry_state.attempt_number} for get_gaia_answer_type"
    ),
)
async def get_gaia_answer_type(
    task_description: str, api_key: str, base_url: str = "https://api.openai.com/v1"
) -> str:
    client = AsyncOpenAI(api_key=api_key, timeout=600, base_url=base_url)

    instruction = f"""Input:
`{task_description}`

Question:
Determine the expected data type of the answer. For questions asking to "identify" something, focus on the final answer type, not the identification process. Format requirements in the question often hint at the expected data type. If the question asks you to write a specific word, return string. Choose only one of the four types below:
- number - a pure number (may include decimals or signs), e.g., price, distance, length
- date - a specific calendar date (e.g., 2025-08-05 or August 5, 2025)
- time - a specific time of day or formated time cost (e.g., 14:30 or 1:30.12)
- string - any other textual answer

Output:
Return exactly one of the [number, date, time, string], nothing else.
"""
    print(f"Answer type instruction: {instruction}")

    message_id = _generate_message_id()
    response = await client.chat.completions.create(
        model="gpt-4.1",
        messages=[{"role": "user", "content": f"[{message_id}] {instruction}"}],
    )
    answer_type = response.choices[0].message.content
    # Check if result is empty, raise exception to trigger retry if empty
    if not answer_type or not answer_type.strip():
        raise ValueError("answer type returned empty result")

    print(f"Answer type: {answer_type}")

    return answer_type.strip()


@retry(
    wait=wait_exponential(multiplier=15),
    stop=stop_after_attempt(5),
    retry_error_callback=lambda retry_state: print(
        f"Retry attempt {retry_state.attempt_number} for extract_gaia_final_answer"
    ),
)
async def extract_gaia_final_answer(
    task_description_detail: str,
    summary: str,
    api_key: str,
    chinese_context: bool,
    base_url: str = "https://api.openai.com/v1",
) -> str:
    """Use LLM to extract final answer from summary"""
    answer_type = await get_gaia_answer_type(task_description_detail, api_key, base_url)

    client = AsyncOpenAI(api_key=api_key, timeout=600, base_url=base_url)

    # Add multilingual-context instructions and output format if enabled.
    chinese_supplement = ""
    output_format_section = """
# Output Format

Return your analysis in this exact format:

**Step-by-step Analysis:**
[Your detailed reasoning process]

**Final Answer:** \\boxed{...}

**Confidence:** [0-100 integer]

**Supporting Evidence:** [Brief summary of evidence that supports this answer]

**Potential Weaknesses:** [Any limitations, uncertainties, or factors that might make this answer incorrect - be objective and thorough]
"""

    if chinese_context:
        chinese_supplement = """

## Multilingual answer notes

Preserve names, units, abbreviations, and quoted phrases from the original task when they affect correctness. Translate only when the requested answer format clearly requires it.

---

"""
        output_format_section = """
# Output Format

Return your analysis in this exact format:

**Step-by-step Analysis:**
[Your detailed reasoning process]

**Final Answer:** \boxed{...}

**Confidence:** [0-100 integer]

**Supporting Evidence:** [Brief summary of evidence that supports this answer]

**Potential Weaknesses:** [Any limitations, uncertainties, or formatting risks]
"""

    # Common confidence assessment section (unified for all languages)
    common_confidence_section = (
        """
# Confidence Assessment

Provide a confidence score (0-100) based on objective criteria for how likely this answer is to be judged correct by an automated verifier:

**Calibration Guidelines (use these as objective anchors):**
- **85-100**: Direct factual evidence found, no contradictions, formatting requirements clearly satisfied
- **70-84**: Strong supporting evidence with minor gaps or slight formatting uncertainty
- **55-69**: Moderate evidence but requires interpretation, or some conflicting information exists
- **40-54**: Limited evidence, significant uncertainty, multiple plausible answers possible
- **25-39**: Weak evidence, mostly reasoning-based, likely incomplete information
- **0-24**: No supporting evidence found, pure speculation, or contradicts known facts

**Objective Calibration Checks:**
1. **Evidence Verifiability**: Can the key facts be directly verified from the agent summary?
2. **Contradiction Test**: Does anything in the summary contradict this answer?
3. **Completeness Test**: Does the summary contain sufficient information to answer confidently?
4. **Formatting Clarity**: Are the format requirements unambiguous and correctly followed?

Rate conservatively - if unsure between two ranges, choose the lower one.

---
"""
        + chinese_supplement
        + output_format_section
    )

    full_prompts = {
        "time": f"""# Inputs

* **Original Question**: `{task_description_detail}`
* **Agent Summary**: `{summary}`

---

# Task

1. **Independently derive** the best possible answer, step by step, based solely on evidence and reasoning from the Agent Summary. **Ignore the summary's "Final Answer" field** at this stage.
2. **Compare** your derived answer to the final answer provided in the Agent Summary (ignoring formatting and phrasing requirements at this stage).
- If both are well supported by the summary's evidence, choose the one with stronger or clearer support.
- If only one is well supported, use that one.
3. **Revise** your chosen answer to fully satisfy all formatting and phrasing requirements listed below (**Formatting rules**, **Additional constraints**, **Common pitfalls to avoid**, and **Quick reference examples**). These requirements override those in the original question if there is any conflict.

If no answer is clearly supported by the evidence, provide a well-justified educated guess. **Always wrap your final answer in a non-empty \\boxed{{...}}.**

---

# Output Guidelines

1. **Box the answer**
Wrap the answer in `\\boxed{{}}`.

2. **Answer type**
The boxed content must be a time.

3. **Formatting rules**
* Follow every formatting instruction in the original question (units, rounding, decimal places, etc.).
* Do **not** add any units (e.g., "s", "second", "seconds"), unless required.
* Ensure the correct unit (e.g., hours versus thousand hours); if the question specifies "thousand hours" or "1000 hours", treat it as the required unit - output a number like 13 (thousand hours) instead of 13000 (hours).
* If the question's written instructions for precision or rounding differ from the examples, treat the examples as authoritative - match their number of decimal places and rounding style.

4. **Additional constraints**
* If the **Agent Summary** is incomplete or unclear, provide the best possible answer (educated guess).

5. **Common pitfalls to avoid**
* Minor mismatches in the required format.
* Unit-conversion errors, especially with uncommon units.
* Incorrect precision, rounding or scale (e.g., 0.01 vs 0.001), **double-check the required level**.
* Conflicts between textual instructions and example formatting, just follow the example: if the question says to "retain the percentile" but the example shows 0.001, use 0.001 rather than 0.01.

---

# Quick reference examples

* If the question says to "rounding the seconds to the nearest hundredth", but the example shows "0.001", 1:23.4567 -> 1:23.457
* If the question says to "rounding the seconds to the nearest hundredth", but the example shows "0.001", 10:08.47445 -> 10:08.474
* If the question says to "round to one decimal place", but the example shows "0.01", 2:17.456 -> 2:17.46
* If the question says to "round to the nearest minute", but the example keeps seconds ("0:45"), 3:44.8 -> 3:45
* If the question says "keep three decimal places", but the example shows "0.1", 1:03.987 -> 1:03.1
* If the question asks for "thousand hours", 13000 -> 13

---
"""
        + common_confidence_section,
        "number": f"""# Inputs

* **Original Question**: `{task_description_detail}`
* **Agent Summary**: `{summary}`

---

# Task

1. **Independently derive** the best possible answer, step by step, based solely on evidence and reasoning from the Agent Summary. **Ignore the summary's "Final Answer" field** at this stage.
2. **Compare** your derived answer to the final answer provided in the Agent Summary (ignoring formatting and phrasing requirements at this stage).
- If both are well supported by the summary's evidence, choose the one with stronger or clearer support.
- If only one is well supported, use that one.
- For questions involving calculations, if your answer and the Agent Summary's final answer are numerically similar, prefer the summary's answer.
3. **Revise** your chosen answer to fully satisfy all formatting and phrasing requirements listed below (**Formatting rules**, **Additional constraints**, **Common pitfalls to avoid**, and **Quick reference examples**). These requirements override those in the original question if there is any conflict.

If no answer is clearly supported by the evidence, provide a well-justified educated guess. **Always wrap your final answer in a non-empty \\boxed{{...}}.**

---

# Output Guidelines

1. **Box the answer**
Wrap the answer in `\\boxed{{}}`.

2. **Answer type**
The boxed content must be a single number.

3. **Formatting rules**
* Follow every formatting instruction in the original question (units, rounding, decimal places, etc.).
* Use digits only; do **not** use words, commas or symbols (e.g., "$", "!", "?", "/").
* Do **not** add any units (e.g., "%", "$", "USD", "Angstrom", "m", "m^2", "m^3"), unless required.
* Ensure the correct unit (e.g., grams versus kilograms, meters versus kilometers, hours versus thousand hours); if the question specifies "thousand hours" or "1000 hours", treat it as the required unit - output a number like 13 (thousand hours) instead of 13000 (hours).

4. **Additional constraints**
* If the **Agent Summary** is incomplete or unclear, provide the best possible answer (educated guess).

5. **Common pitfalls to avoid**
* Minor mismatches in the required format.
* Unit-conversion errors, especially with uncommon units.
* Incorrect precision, rounding or scale (e.g., 0.01 vs 0.001), **double-check the required level**.
* Conflicts between textual instructions and example formatting, just follow the example: if the question says to "retain the percentile" but the example shows 0.001, use 0.001 rather than 0.01.
* Do not partially convert -based numbers-ensure full and accurate conversion (e.g., "one hundred million" -> 100000000, not 100).

---

# Quick reference examples

* $100 -> 100
* 100 USD -> 100
* EUR50 -> 50
* GBP75 -> 75
* JPY1,000 -> 1000
* 1,234 m -> 1234
* 3,456,789 kg -> 3456789
* 70% -> 70
* 12.5% -> 12.5
* 0.045 m^3 -> 0.045
* 0.045 m^3 -> 0.045
* -40  degrees C -> -40
* 100 km/h -> 100
* 5000 m^2 -> 5000
* 2.54 cm -> 2.54
* 50 kg -> 50
* 4.0 L -> 4
* 13 thousand hours -> 13
* Page 123/456 -> 123/456
* 100 million -> 100000000
* 200 ohm -> 200
* 200 Angstrom -> 200
* 9.81 m/s^2 -> 9.81
* 0 dB -> 0

---
"""
        + common_confidence_section,
        "string": f"""# Inputs

* **Original Question**: `{task_description_detail}`
* **Agent Summary**: `{summary}`

---

# Task

1. **Independently derive** the best possible answer, step by step, based solely on evidence and reasoning from the Agent Summary. **Ignore the summary's "Final Answer" field** at this stage.
2. **Compare** your derived answer to the final answer provided in the Agent Summary (ignoring formatting and phrasing requirements at this stage).
- If both are well supported by the summary's evidence, choose the one with stronger or clearer support.
- If only one is well supported, use that one.
3. **Revise** your chosen answer to fully satisfy all formatting and phrasing requirements listed below (**Formatting rules**, **Additional constraints**, **Common pitfalls to avoid**, and **Quick reference examples**). These requirements override those in the original question if there is any conflict.

If no answer is clearly supported by the evidence, provide a well-justified educated guess. **Always wrap your final answer in a non-empty \\boxed{{...}}.**

---

# Output Guidelines

1. **Box the answer**
Wrap the final answer in \\boxed{{...}}.

2. **Answer type**
The boxed content must be **one** of:
* a single short phrase (fewest words possible)
* a comma-separated list of numbers and/or strings

3. **Formatting rules**
* Follow every formatting instruction in the original question (alphabetization, sequencing, units, rounding, decimal places, etc.).
* Omit articles and abbreviations unless explicitly present in the expected answer.
* If a string contains numeric information, spell out the numbers **unless** the question itself shows them as digits.
* Do **not** end the answer with ".", "!", "?", or any other punctuation.
* Use only standard ASCII quotation marks ("" and ''), **not** stylized or curly quotation marks (such as " " ' ').
* Remove invisible or non-printable characters.
* If the output is lists, apply the rules item-by-item.
* Avoid unnecessary elaboration - keep the answer as short as possible
 - Do **not** add "count", "number", "count of", "total", or similar quantifying words when the noun itself already refers to the quantity (e.g., use the bare noun form only).
 - No geographical modifiers (e.g., "Western", "Southern"),
 - Use the simplest, most commonly accepted term for a substance or object (e.g., "diamond" instead of "crystalline diamond", "silicon" instead of "silicon crystals")
* For mathematical symbols, match the symbol style in the question; never substitute LaTeX commands (e.g., use <=, not \\leq, use the plain symbol when requested, use <->, not \\leftrightarrow).
* For birthplaces, give the name as it was at the time of birth, not the current name.

4. **Additional constraints**
* If the Agent Summary is incomplete or unclear, provide the best possible answer (educated guess).
* Keep the answer as short and direct as possible-no explanations or parenthetical notes.

5. **Common pitfalls to avoid**
* Minor mismatches between required and produced formats.
* Conflicts between textual instructions and example formatting-follow the example.
* **Names**: give only the commonly used first + last name (no middle name unless requested).
* **Countries**: use the common name (e.g., "China", "Brunei")
* **Locations**: output only the requested location name, without including time, modifiers (e.g., "The Castle", "The Hotel")
* When the question provides examples of expected format (e.g., "ripe strawberries" not "strawberries"), follow the exact wording style shown in the examples, preserving all descriptive terms and adjectives as demonstrated.
* Answer with historically location names when the Agent Summary provides. Never override a historically location name. For example, a birthplace should be referred to by the name it had at the time of birth (i.e., answer the original name).
* For questions asking to "identify" something, focus on the final answer, not the identification process.

---

# Quick reference examples

* INT. THE CASTLE - DAY 1 -> The Castle
* INT. THE HOTEL - NIGHT -> The Hotel
* INT. THE SPACESHIP - DAWN -> The Spaceship
* INT. THE LIBRARY - EVENING -> The Library
* INT. CLASSROOM #3 - MORNING -> Classroom #3
* People's Republic of China -> China
* citation count -> citations
* Brunei Darussalam -> Brunei
* United States of America -> United States
* Republic of Korea -> South Korea
* New York City, USA -> New York City
* Sao Paulo (Brazil) -> Sao Paulo
* John Michael Doe -> John Doe
* Mary Anne O'Neil -> Mary O'Neil
* Dr. Richard Feynman -> Richard Feynman
* INT. ZONE 42 - LEVEL B2 -> Zone 42 - Level B2
* INT. THE UNDERWATER BASE - MIDNIGHT -> The Underwater Base
* Sam's Home -> Sam's Home
* Mike's phone -> Mike's phone

---
"""
        + common_confidence_section,
    }

    full_prompt = full_prompts.get(
        answer_type if answer_type in ["number", "time"] else "string"
    )

    print("Extract Final Answer Prompt:")
    print(full_prompt)

    message_id = _generate_message_id()
    response = await client.chat.completions.create(
        model="o3",
        messages=[{"role": "user", "content": f"[{message_id}] {full_prompt}"}],
    )
    result = response.choices[0].message.content

    # Check if result is empty, raise exception to trigger retry if empty
    if not result or not result.strip():
        raise ValueError("Final answer extraction returned empty result")

    # Verify boxed answer exists
    boxed_match = re.search(r"\\boxed{([^}]*)}", result)
    if not boxed_match:
        raise ValueError("Final answer extraction returned empty answer")

    print("response:", result)

    # Return the full response directly for downstream LLM processing
    # This contains all structured information: analysis, boxed answer, confidence, evidence, and weaknesses
    return result


@retry(
    wait=wait_exponential(multiplier=15),
    stop=stop_after_attempt(5),
    retry_error_callback=lambda retry_state: print(
        f"Retry attempt {retry_state.attempt_number} for extract_browsecomp_zh_final_answer"
    ),
)
async def extract_browsecomp_zh_final_answer(
    task_description_detail: str,
    summary: str,
    api_key: str,
    base_url: str = "https://api.openai.com/v1",
) -> str:
    """Use an LLM to extract a boxed final answer from a summary."""
    client = AsyncOpenAI(api_key=api_key, timeout=600, base_url=base_url)

    full_prompt = f"""# Input

* **Task**: `{task_description_detail}`
* **Agent summary**: `{summary}`

---

# Task

Extract the final answer from the agent summary. Preserve the answer semantics. Do not invent facts.
If the summary contains multiple candidates, choose the answer most directly supported by the evidence.

# Output

Return the following sections exactly:

**Analysis:**
Briefly explain the extraction decision.

**Answer:** \boxed{{...}}

**Confidence:** [0-100]

**Evidence:**
Quote the key evidence used to select the answer.

**Weaknesses:**
List any uncertainty or missing evidence.
"""

    print("Extract Final Answer Prompt:")
    print(full_prompt)

    message_id = _generate_message_id()
    response = await client.chat.completions.create(
        model="o3",
        messages=[{"role": "user", "content": f"[{message_id}] {full_prompt}"}],
        reasoning_effort="medium",
    )
    result = response.choices[0].message.content

    if not result or not result.strip():
        raise ValueError("Final answer extraction returned empty result")

    boxed_match = re.search(r"\\boxed{([^}]*)}", result)
    if not boxed_match:
        raise ValueError("Final answer extraction returned empty answer")

    print("response:", result)
    return result
