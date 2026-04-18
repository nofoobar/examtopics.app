"""
AI generation pipeline for exams, tests and questions.
All functions return plain Python dicts/lists — no DB interaction here.

Langfuse tracing is handled automatically by the langfuse.openai drop-in in
openrouter.py — no manual trace/span management needed here.
"""
import json
import re
import time
from utils.openrouter import openrouter_client


# helpers

def _parse_json(text: str) -> dict | list:
    """Strip markdown fences then parse JSON."""
    cleaned = re.sub(r"```(?:json)?", "", text).strip().rstrip("```").strip()
    return json.loads(cleaned)


def _parse_correct_answers(raw: str | int | list) -> list[int]:
    """Normalise 'correct_options' — LLM may return string, int, or list."""
    if isinstance(raw, list):
        return [int(x) for x in raw]
    if isinstance(raw, int):
        return [raw]
    parts = [p.strip() for p in str(raw).split(",") if p.strip()]
    return [int(p) for p in parts if p.isdigit()]


def _with_retry(fn, retries: int = 3, delay: float = 5.0):
    """
    Call fn(), retrying up to `retries` times on any exception.
    Waits `delay` seconds between attempts (doubles each retry).
    Raises the last exception if all attempts fail.
    """
    last_exc = None
    wait = delay
    for attempt in range(1, retries + 1):
        try:
            return fn()
        except Exception as e:
            last_exc = e
            if attempt < retries:
                time.sleep(wait)
                wait *= 2
    raise last_exc


# exam metadata

def generate_exam_metadata(exam_name: str, exam_code: str, model_key: str) -> dict:
    prompt = f"""You are an IT certification expert.
      Generate metadata for this certification exam: "{exam_name}" (code: {exam_code or 'N/A'}).

      Respond ONLY with a JSON object, no markdown, no extra text:
      {{
        "short_description": "one sentence, max 120 chars, what the exam covers",
        "description": "2-3 sentence paragraph about the exam, who it is for, and why it matters"
      }}"""

    def _call():
        raw = openrouter_client.completion(
            model_key=model_key,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
            generation_name="exam_metadata",
            metadata={"exam_name": exam_name, "exam_code": exam_code},
        )
        return _parse_json(raw)

    return _with_retry(_call, retries=3, delay=5.0)


# questions (AI-only, one per LLM call for richer output)

def generate_single_question(
    exam_name: str,
    exam_code: str,
    test_number: int,
    question_index: int,
    total_questions: int,
    model_key: str,
    enable_web_search: bool = False,
    web_search_context_size: str = "low",
) -> dict:
    """Generate a single exam question.

    When enable_web_search=True the model will ground its response with live
    web data — useful for keeping questions accurate against the latest exam
    objectives and AWS/Azure/GCP service changes.
    """
    web_search_note = (
        "\n- Use your web search capability to look up the LATEST official exam guide, "
        "blueprint, and any recent service or feature changes before writing the question."
        if enable_web_search else ""
    )

    prompt = f"""You are an expert creator of IT certification exam questions.

        Create question {question_index} of {total_questions} for:
        Exam: "{exam_name}" {f"({exam_code})" if exam_code else ""}
        Practice Test: {test_number}

        Rules:
        - Choose EITHER multiple-choice (exactly 1 correct answer) OR multi-select (2-3 correct answers)
        - Vary question style: scenario-based, concept check, "which TWO", elimination, etc.
        - Options dict uses string keys "1" through "4" (or up to "5" for multi-select)
        - correct_options is a list of integers matching the correct option keys
        - overall_explanation: 2-4 sentences — explain WHY the correct answer(s) are right
          AND briefly note why the top distractor(s) are wrong
        - domain is a short topic label (e.g. "Compute", "Networking", "Security", "Storage")
        - Difficulty: exam-level, not trivial — a prepared candidate should find it challenging{web_search_note}

        Respond ONLY with a single JSON object, no markdown, no extra text:
        {{
          "question": "...",
          "question_type": "multiple-choice",
          "options": {{"1": "...", "2": "...", "3": "...", "4": "..."}},
          "correct_options": [2],
          "overall_explanation": "...",
          "domain": "..."
        }}"""

    raw = openrouter_client.completion(
        model_key=model_key,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.8,
        generation_name=f"ai_q_t{test_number}_q{question_index}",
        metadata={
            "exam_name": exam_name,
            "exam_code": exam_code,
            "test_number": test_number,
            "question_index": question_index,
            "total_questions": total_questions,
            "web_search": enable_web_search,
        },
        enable_web_search=enable_web_search,
        web_search_context_size=web_search_context_size,
    )
    return _parse_json(raw)


# ExamTopics → LLM-enhanced question (single)

def _build_examtopics_prompt(et_data: dict) -> str:
    exam_name = et_data.get("exam_name", "IT Certification")
    question_text = et_data.get("question", "")

    choices_raw = et_data.get("choices", [])
    if choices_raw:
        choices_lines = "\n".join(
            f"  {c['choice_key']}: {c['choice_text']}"
            for c in sorted(choices_raw, key=lambda c: c.get("choice_key", ""))
        )
        choices_section = f"Question Choices:\n{choices_lines}"
    else:
        choices_section = "Question Choices: (not provided — infer from question context)"

    answer = et_data.get("answer", "")
    answer_community = et_data.get("answer_community", "")
    if answer and answer.replace(",", "").isalpha() and len(answer) <= 6:
        answer_hint = f"Answer maybe: {answer}"
    else:
        answer_hint = "Answer: please decide"
    if answer_community:
        answer_hint += f"\nCommunity Answer: {answer_community}"

    answer_desc = et_data.get("answer_description", "")
    explanation_section = f"Overall Explanation: {answer_desc}" if answer_desc else ""

    discussions = et_data.get("top_3_discussions", [])
    if discussions:
        disc_lines = "\n".join(
            f"  - {d.get('content', '')} (👍 {d.get('upvote_count', 0)})"
            for d in discussions
        )
        discussion_section = (
            "Expert Community Discussions (use these to confirm the correct answer):\n"
            + disc_lines
        )
    else:
        discussion_section = ""

    return f"""You are an expert IT certification exam question writer.

Given the following raw ExamTopics question data, produce a clean, well-structured practice question for the "{exam_name}" exam.

--- RAW DATA ---
Question: {question_text}
{answer_hint}
{explanation_section}
{choices_section}
{discussion_section}
--- END RAW DATA ---

Instructions:
- Preserve the question concept but you may lightly change it for making it unique.
- Map the lettered choices (A, B, C...) to numbered options (1, 2, 3...) in order.
- Use the answer hint AND community discussions to determine the correct option number(s).
- question_type must be "multiple-choice" (1 correct) or "multi-select" (2+ correct).
- overall_explanation should be 2-4 sentences explaining WHY the correct answer(s) are right.
- domain is a short topic label relevant to the exam (e.g. "Compute", "Networking", "Security").

Respond ONLY with a single JSON object, no markdown, no extra text:
{{
  "question": "...",
  "question_type": "multiple-choice",
  "options": {{"1": "...", "2": "...", "3": "...", "4": "..."}},
  "correct_options": [2],
  "overall_explanation": "...",
  "domain": "..."
}}"""


def generate_question_from_examtopics(
    et_data: dict,
    model_key: str,
    question_index: int | None = None,
) -> dict:
    prompt = _build_examtopics_prompt(et_data)
    name = f"et_question_{question_index}" if question_index is not None else "et_question"

    def _call():
        raw = openrouter_client.completion(
            model_key=model_key,
            messages=[
                {"role": "system", "content": "Return only valid JSON, no markdown, no extra text."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            generation_name=name,
            metadata={
                "exam_name": et_data.get("exam_name"),
                "source": "examtopics",
                "question_index": question_index,
            },
        )
        data = _parse_json(raw)
        if "correct_options" in data:
            data["correct_options"] = _parse_correct_answers(data["correct_options"])
        if "options" in data:
            data["options"] = {str(k): v for k, v in data["options"].items()}
        return data

    return _with_retry(_call, retries=3, delay=5.0)
