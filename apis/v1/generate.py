import os
import csv
import re
from typing import Optional

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, Request, Form, HTTPException
from fastapi.responses import RedirectResponse
from sqlmodel import Session, select, func

from apis.deps import get_db
from db.database import engine
from db.models.exam import Vendor, Exam, Test, Question, QuestionType
from db.models.generation_job import GenerationJob, JobStatus
from utils.templates import templates
from utils.ai_pipeline import (
    generate_exam_metadata,
    generate_single_question,
    generate_question_from_examtopics,
)
from core.config import settings


router = APIRouter(tags=["generate"])


# ── helpers ───────────────────────────────────────────────────────────────────

def _slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text.strip("-")


def _et_answer_to_int(letter: str) -> int:
    return {"A": 1, "B": 2, "C": 3, "D": 4, "E": 5}.get(letter.upper().strip(), 1)


# ── background task ───────────────────────────────────────────────────────────

def _run_generation(job_id: int) -> None:
    """
    Runs entirely in a background thread — has its own DB session.
    Reads the full config from the GenerationJob record and does all the work.
    Writes progress updates back to the job row after each question.
    """
    with Session(engine) as session:
        job = session.get(GenerationJob, job_id)
        if not job:
            return

        cfg = job.config

        def _fail(msg: str) -> None:
            job.status = JobStatus.failed
            job.error  = msg
            session.add(job)
            session.commit()

        def _tick() -> None:
            """Increment completed_steps and persist immediately."""
            job.completed_steps += 1
            session.add(job)
            session.commit()

        # Mark running
        job.status = JobStatus.running
        session.add(job)
        session.commit()

        # ── ADD-TO-EXAM mode ─────────────────────────────────────────────────
        mode = cfg.get("mode", "new_exam")
        if mode == "add_to_exam":
            target_exam_id       = cfg["target_exam_id"]
            create_new_test      = cfg.get("create_new_test", True)
            target_test_id       = cfg.get("target_test_id")
            new_test_name        = cfg.get("new_test_name") or "Practice Test"
            questions_per_test   = cfg["questions_per_test"]
            llm_model_aq         = cfg.get("llm_model", "gemini-cheap")
            question_source_aq   = cfg.get("question_source", "ai")
            examtopics_exam_id_aq = cfg.get("examtopics_exam_id")
            ai_percentage_aq     = cfg.get("ai_percentage", 50)
            enable_web_search_aq = cfg.get("enable_web_search", False)
            wsc_aq               = cfg.get("web_search_context_size", "low")

            exam_aq = session.get(Exam, target_exam_id)
            if not exam_aq:
                return _fail("Target exam not found.")

            if create_new_test:
                existing_count = session.exec(
                    select(func.count(Test.id)).where(Test.exam_id == exam_aq.id)
                ).one()
                slug_cand = f"{exam_aq.slug}-pt{existing_count + 1}"
                attempt = 1
                while session.exec(select(Test).where(Test.slug == slug_cand)).first():
                    attempt += 1
                    slug_cand = f"{exam_aq.slug}-pt{existing_count + attempt}"
                test_aq = Test(
                    exam_id=exam_aq.id,
                    name=new_test_name,
                    slug=slug_cand,
                    is_active=True,
                )
                session.add(test_aq)
                session.flush()
            else:
                if not target_test_id:
                    return _fail("No existing test selected.")
                test_aq = session.get(Test, target_test_id)
                if not test_aq or test_aq.exam_id != exam_aq.id:
                    return _fail("Target test not found.")

            # Question split
            if question_source_aq == "ai":
                n_ai_aq, n_et_aq = questions_per_test, 0
            elif question_source_aq == "examtopics":
                n_ai_aq, n_et_aq = 0, questions_per_test
            else:
                n_ai_aq = round(questions_per_test * ai_percentage_aq / 100)
                n_et_aq = questions_per_test - n_ai_aq

            for q_idx in range(1, n_ai_aq + 1):
                try:
                    q = generate_single_question(
                        exam_name=exam_aq.name,
                        exam_code=exam_aq.exam_code or "",
                        test_number=1,
                        question_index=q_idx,
                        total_questions=n_ai_aq,
                        model_key=llm_model_aq,
                        enable_web_search=enable_web_search_aq,
                        web_search_context_size=wsc_aq,
                    )
                except Exception as e:
                    session.rollback()
                    return _fail(f"AI question {q_idx}/{n_ai_aq} failed: {e}")
                raw_type_aq = q.get("question_type", "multiple-choice")
                session.add(Question(
                    test_id=test_aq.id,
                    question=q.get("question", ""),
                    question_type=QuestionType.multi_select if raw_type_aq == "multi-select" else QuestionType.multiple_choice,
                    options=q.get("options", {}),
                    correct_options=q.get("correct_options", [1]),
                    explanations={},
                    overall_explanation=q.get("overall_explanation"),
                    domain=q.get("domain"),
                    llm_model=f"{llm_model_aq}+websearch" if enable_web_search_aq else llm_model_aq,
                    is_active=True,
                ))
                session.commit()
                _tick()

            if n_et_aq > 0:
                base_url_aq = settings.BACKEND_ALGOHOLIC_URL
                for i in range(n_et_aq):
                    et_url_aq = (
                        f"{base_url_aq}/api/v1/examtopics/"
                        f"get-a-random-question-from-examtopics-exam/{examtopics_exam_id_aq}"
                    )
                    try:
                        with httpx.Client(timeout=10.0) as client:
                            resp_aq = client.get(et_url_aq)
                            resp_aq.raise_for_status()
                            raw_et_aq = resp_aq.json()
                    except Exception:
                        session.rollback()
                        return _fail(
                            f"Could not reach ExamTopics API. "
                            f"Check BACKEND_ALGOHOLIC_URL and exam ID {examtopics_exam_id_aq}."
                        )
                    try:
                        enhanced_aq = generate_question_from_examtopics(
                            raw_et_aq, llm_model_aq, question_index=i
                        )
                    except Exception:
                        disc_aq = raw_et_aq.get("top_3_discussions", [])
                        enhanced_aq = {
                            "question": raw_et_aq.get("question", ""),
                            "question_type": "multiple-choice",
                            "options": {
                                str(j + 1): c["choice_text"]
                                for j, c in enumerate(raw_et_aq.get("choices", []))
                            },
                            "correct_options": [_et_answer_to_int(raw_et_aq.get("answer", "A"))],
                            "overall_explanation": (
                                disc_aq[0]["content"] if disc_aq
                                else raw_et_aq.get("answer_description", "")
                            ),
                            "domain": None,
                        }
                    raw_type_aq = enhanced_aq.get("question_type", "multiple-choice")
                    session.add(Question(
                        test_id=test_aq.id,
                        question=enhanced_aq.get("question", ""),
                        question_type=QuestionType.multi_select if raw_type_aq == "multi-select" else QuestionType.multiple_choice,
                        options=enhanced_aq.get("options", {}),
                        correct_options=enhanced_aq.get("correct_options", [1]),
                        explanations={},
                        overall_explanation=enhanced_aq.get("overall_explanation"),
                        domain=enhanced_aq.get("domain"),
                        llm_model=f"et+{llm_model_aq}",
                        is_active=True,
                    ))
                    session.commit()
                    _tick()
            job.status = JobStatus.done
            job.result_exam_id = exam_aq.id
            session.add(job)
            session.commit()
            return
        # ─────────────────────────────────────────────────────────────────────

        # NEW-EXAM mode — extract config fields
        exam_name          = cfg["exam_name"]
        exam_code          = cfg.get("exam_code", "")
        vendor_id          = cfg["vendor_id"]
        num_tests          = cfg["num_tests"]
        questions_per_test = cfg["questions_per_test"]
        llm_model          = cfg.get("llm_model", "gemini-cheap")
        question_source    = cfg.get("question_source", "ai")
        examtopics_exam_id = cfg.get("examtopics_exam_id")
        ai_percentage      = cfg.get("ai_percentage", 50)
        enable_web_search  = cfg.get("enable_web_search", False)
        web_search_context_size = cfg.get("web_search_context_size", "low")

        # Question split per test
        if question_source == "ai":
            n_ai_qs, n_et_qs = questions_per_test, 0
        elif question_source == "examtopics":
            n_ai_qs, n_et_qs = 0, questions_per_test
        else:
            n_ai_qs = round(questions_per_test * ai_percentage / 100)
            n_et_qs = questions_per_test - n_ai_qs

        # Slug collision check
        slug_base = _slugify(exam_code if exam_code else exam_name)
        if session.exec(select(Exam).where(Exam.slug == slug_base)).first():
            return _fail(
                f"An exam with slug '{slug_base}' already exists. "
                "Change the exam name or code and try again."
            )

        # Step 1 — exam metadata
        try:
            meta = generate_exam_metadata(exam_name, exam_code, llm_model)
        except Exception as e:
            return _fail(f"Failed to generate exam metadata: {e}")

        exam = Exam(
            vendor_id=vendor_id,
            name=exam_name,
            exam_code=exam_code or None,
            slug=slug_base,
            short_description=meta.get("short_description"),
            description=meta.get("description"),
            is_active=True,
        )
        session.add(exam)
        session.flush()

        # Step 2 — tests + questions
        for t_idx in range(1, num_tests + 1):
            test_slug = f"{slug_base}-pt{t_idx}"
            test = Test(
                exam_id=exam.id,
                name=f"Practice Test {t_idx}",
                slug=test_slug,
                is_active=True,
            )
            session.add(test)
            session.flush()

            # AI questions - committed immediately so they appear in the frontend as they are generated
            for q_idx in range(1, n_ai_qs + 1):
                try:
                    q = generate_single_question(
                        exam_name=exam_name,
                        exam_code=exam_code,
                        test_number=t_idx,
                        question_index=q_idx,
                        total_questions=n_ai_qs,
                        model_key=llm_model,
                        enable_web_search=enable_web_search,
                        web_search_context_size=web_search_context_size,
                    )
                except Exception as e:
                    session.rollback()
                    return _fail(f"AI question {q_idx}/{n_ai_qs} test {t_idx} failed: {e}")
                raw_type = q.get("question_type", "multiple-choice")
                session.add(Question(
                    test_id=test.id,
                    question=q.get("question", ""),
                    question_type=QuestionType.multi_select if raw_type == "multi-select" else QuestionType.multiple_choice,
                    options=q.get("options", {}),
                    correct_options=q.get("correct_options", [1]),
                    explanations={},
                    overall_explanation=q.get("overall_explanation"),
                    domain=q.get("domain"),
                    llm_model=f"{llm_model}+websearch" if enable_web_search else llm_model,
                    is_active=True,
                ))
                session.commit()
                _tick()

            # ExamTopics questions - committed immediately so they appear in the frontend as they are generated
            if n_et_qs > 0:
                base_url = settings.BACKEND_ALGOHOLIC_URL
                for i in range(n_et_qs):
                    et_url = (
                        f"{base_url}/api/v1/examtopics/"
                        f"get-a-random-question-from-examtopics-exam/{examtopics_exam_id}"
                    )
                    try:
                        with httpx.Client(timeout=10.0) as client:
                            resp = client.get(et_url)
                            resp.raise_for_status()
                            raw_et = resp.json()
                    except Exception:
                        session.rollback()
                        return _fail(
                            f"Could not reach ExamTopics API for test {t_idx}. "
                            f"Check BACKEND_ALGOHOLIC_URL and exam ID {examtopics_exam_id}."
                        )
                    try:
                        enhanced = generate_question_from_examtopics(
                            raw_et,
                            llm_model,
                            question_index=(t_idx - 1) * n_et_qs + i,
                        )
                    except Exception:
                        discussions = raw_et.get("top_3_discussions", [])
                        enhanced = {
                            "question": raw_et.get("question", ""),
                            "question_type": "multiple-choice",
                            "options": {
                                str(j + 1): c["choice_text"]
                                for j, c in enumerate(raw_et.get("choices", []))
                            },
                            "correct_options": [_et_answer_to_int(raw_et.get("answer", "A"))],
                            "overall_explanation": (
                                discussions[0]["content"] if discussions
                                else raw_et.get("answer_description", "")
                            ),
                            "domain": None,
                        }
                    raw_type = enhanced.get("question_type", "multiple-choice")
                    session.add(Question(
                        test_id=test.id,
                        question=enhanced.get("question", ""),
                        question_type=QuestionType.multi_select if raw_type == "multi-select" else QuestionType.multiple_choice,
                        options=enhanced.get("options", {}),
                        correct_options=enhanced.get("correct_options", [1]),
                        explanations={},
                        overall_explanation=enhanced.get("overall_explanation"),
                        domain=enhanced.get("domain"),
                        llm_model=f"et+{llm_model}",
                        is_active=True,
                    ))
                    session.commit()
                    _tick()

        # Mark done
        job.status = JobStatus.done
        job.result_exam_id = exam.id
        session.add(job)
        session.commit()


# ── routes ────────────────────────────────────────────────────────────────────

@router.get("/generate-an-exam-hxh")
def generate_form(request: Request, session: Session = Depends(get_db)):
    vendors = session.exec(select(Vendor).where(Vendor.is_active == True)).all()
    return templates.TemplateResponse(request, "generate/form.html", {
        "vendors": vendors,
        "form": {},
        "error": None,
    })


@router.post("/generate")
async def generate_exam(
    request: Request,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_db),
    exam_name: str = Form(...),
    exam_code: str = Form(""),
    vendor_id: int = Form(...),
    num_tests: int = Form(...),
    questions_per_test: int = Form(...),
    llm_model: str = Form("gemini-cheap"),
    question_source: str = Form("ai"),
    examtopics_exam_id: Optional[int] = Form(None),
    ai_percentage: int = Form(50),
    enable_web_search: bool = Form(False),
    web_search_context_size: str = Form("low"),
):
    vendors = session.exec(select(Vendor).where(Vendor.is_active == True)).all()

    def render_error(msg: str):
        return templates.TemplateResponse(request, "generate/form.html", {
            "vendors": vendors,
            "form": {
                "exam_name": exam_name,
                "exam_code": exam_code,
                "vendor_id": str(vendor_id),
                "num_tests": num_tests,
                "questions_per_test": questions_per_test,
                "llm_model": llm_model,
                "question_source": question_source,
                "examtopics_exam_id": examtopics_exam_id,
                "ai_percentage": ai_percentage,
                "enable_web_search": enable_web_search,
                "web_search_context_size": web_search_context_size,
            },
            "error": msg,
        })

    # Fast validation before enqueuing
    vendor = session.get(Vendor, vendor_id)
    if not vendor:
        return render_error("Selected vendor not found.")

    num_tests = max(1, min(10, num_tests))
    questions_per_test = max(2, min(300, questions_per_test))
    ai_percentage = max(0, min(100, ai_percentage))

    if question_source not in ("ai", "examtopics", "mix"):
        question_source = "ai"
    if web_search_context_size not in ("low", "medium", "high"):
        web_search_context_size = "low"
    if question_source in ("examtopics", "mix") and not examtopics_exam_id:
        return render_error("ExamTopics Exam ID is required when using ExamTopics or Mix source.")

    # Slug collision check (quick, before we even create a job)
    slug_base = _slugify(exam_code if exam_code else exam_name)
    if session.exec(select(Exam).where(Exam.slug == slug_base)).first():
        return render_error(
            f"An exam with slug '{slug_base}' already exists. "
            "Change the exam name or code and try again."
        )

    # Total steps = number of questions we'll generate (for progress bar)
    if question_source == "ai":
        total_steps = num_tests * questions_per_test
    elif question_source == "examtopics":
        total_steps = num_tests * questions_per_test
    else:
        n_ai = round(questions_per_test * ai_percentage / 100)
        n_et = questions_per_test - n_ai
        total_steps = num_tests * (n_ai + n_et)

    # Create job record
    job = GenerationJob(
        exam_name=exam_name,
        status=JobStatus.pending,
        total_steps=total_steps,
        completed_steps=0,
        config={
            "exam_name": exam_name,
            "exam_code": exam_code,
            "vendor_id": vendor_id,
            "num_tests": num_tests,
            "questions_per_test": questions_per_test,
            "llm_model": llm_model,
            "question_source": question_source,
            "examtopics_exam_id": examtopics_exam_id,
            "ai_percentage": ai_percentage,
            "enable_web_search": enable_web_search,
            "web_search_context_size": web_search_context_size,
        },
    )
    session.add(job)
    session.commit()
    session.refresh(job)

    # Fire background task and return immediately
    background_tasks.add_task(_run_generation, job.id)

    return RedirectResponse(url=f"/generate/jobs/{job.id}", status_code=303)





# ── Add-questions form & API ─────────────────────────────────────────────────

@router.get("/api/v1/exams/{exam_id}/tests-list")
def list_tests_for_exam(exam_id: int, session: Session = Depends(get_db)):
    """Return tests (with question counts) for an exam — used by add-questions AJAX."""
    tests = session.exec(
        select(Test)
        .where(Test.exam_id == exam_id, Test.is_active == True)
        .order_by(Test.name)
    ).all()
    result = []
    for t in tests:
        count = session.exec(
            select(func.count(Question.id))
            .where(Question.test_id == t.id, Question.is_active == True)
        ).one()
        result.append({"id": t.id, "name": t.name, "slug": t.slug, "question_count": count})
    return result


@router.get("/add-questions-hxh")
def add_questions_form(request: Request, session: Session = Depends(get_db)):
    """Form: choose an existing exam/test, then generate more questions into it."""
    vendors = session.exec(select(Vendor).where(Vendor.is_active == True)).all()
    vendors_with_exams = []
    for v in vendors:
        exams = session.exec(
            select(Exam)
            .where(Exam.vendor_id == v.id, Exam.is_active == True)
            .order_by(Exam.name)
        ).all()
        if exams:
            vendors_with_exams.append({"vendor": v, "exams": exams})
    return templates.TemplateResponse(request, "generate/add_questions.html", {
        "vendors_with_exams": vendors_with_exams,
        "form": {},
        "error": None,
    })


@router.post("/add-questions")
async def add_questions_submit(
    request: Request,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_db),
    exam_id: int = Form(...),
    test_mode: str = Form("new"),          # "existing" | "new"
    test_id: Optional[int] = Form(None),
    new_test_name: str = Form(""),
    questions_per_test: int = Form(...),
    llm_model: str = Form("gemini-cheap"),
    question_source: str = Form("ai"),
    examtopics_exam_id: Optional[int] = Form(None),
    ai_percentage: int = Form(50),
    enable_web_search: bool = Form(False),
    web_search_context_size: str = Form("low"),
):
    vendors = session.exec(select(Vendor).where(Vendor.is_active == True)).all()
    vendors_with_exams = []
    for v in vendors:
        exams = session.exec(
            select(Exam)
            .where(Exam.vendor_id == v.id, Exam.is_active == True)
            .order_by(Exam.name)
        ).all()
        if exams:
            vendors_with_exams.append({"vendor": v, "exams": exams})

    def render_error(msg: str):
        return templates.TemplateResponse(request, "generate/add_questions.html", {
            "vendors_with_exams": vendors_with_exams,
            "form": {
                "exam_id": str(exam_id),
                "test_mode": test_mode,
                "test_id": str(test_id) if test_id else "",
                "new_test_name": new_test_name,
                "questions_per_test": questions_per_test,
                "llm_model": llm_model,
                "question_source": question_source,
                "examtopics_exam_id": examtopics_exam_id,
                "ai_percentage": ai_percentage,
                "enable_web_search": enable_web_search,
                "web_search_context_size": web_search_context_size,
            },
            "error": msg,
        })

    exam = session.get(Exam, exam_id)
    if not exam:
        return render_error("Selected exam not found.")

    create_new_test = (test_mode == "new")
    resolved_test_id = None
    if not create_new_test:
        if not test_id:
            return render_error("Please select an existing test.")
        test_obj = session.get(Test, test_id)
        if not test_obj or test_obj.exam_id != exam.id:
            return render_error("Selected test not found.")
        resolved_test_id = test_id

    questions_per_test = max(3, min(30, questions_per_test))
    ai_percentage = max(0, min(100, ai_percentage))
    if question_source not in ("ai", "examtopics", "mix"):
        question_source = "ai"
    if web_search_context_size not in ("low", "medium", "high"):
        web_search_context_size = "low"
    if question_source in ("examtopics", "mix") and not examtopics_exam_id:
        return render_error("ExamTopics Exam ID is required when using ExamTopics or Mix source.")

    if question_source == "ai":
        total_steps = questions_per_test
    elif question_source == "examtopics":
        total_steps = questions_per_test
    else:
        n_ai = round(questions_per_test * ai_percentage / 100)
        total_steps = questions_per_test  # n_ai + n_et

    job_label = (
        f"{exam.name} — "
        + (new_test_name or "New Test" if create_new_test else f"Test #{resolved_test_id}")
    )
    job = GenerationJob(
        exam_name=job_label,
        status=JobStatus.pending,
        total_steps=total_steps,
        completed_steps=0,
        config={
            "mode": "add_to_exam",
            "target_exam_id": exam_id,
            "create_new_test": create_new_test,
            "target_test_id": resolved_test_id,
            "new_test_name": new_test_name or f"Practice Test",
            "questions_per_test": questions_per_test,
            "llm_model": llm_model,
            "question_source": question_source,
            "examtopics_exam_id": examtopics_exam_id,
            "ai_percentage": ai_percentage,
            "enable_web_search": enable_web_search,
            "web_search_context_size": web_search_context_size,
        },
    )
    session.add(job)
    session.commit()
    session.refresh(job)

    background_tasks.add_task(_run_generation, job.id)
    return RedirectResponse(url=f"/generate/jobs/{job.id}", status_code=303)


@router.get("/generate/jobs/{job_id}")
def job_status_page(job_id: int, request: Request, session: Session = Depends(get_db)):
    """Renders the status page — JS polls the JSON endpoint below."""
    job = session.get(GenerationJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return templates.TemplateResponse(request, "generate/job_status.html", {"job": job})


@router.get("/api/v1/generate/jobs/{job_id}")
def job_status_api(job_id: int, session: Session = Depends(get_db)):
    """JSON status endpoint polled by the status page."""
    job = session.get(GenerationJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    pct = 0
    if job.total_steps > 0:
        pct = round(job.completed_steps / job.total_steps * 100)

    return {
        "id":               job.id,
        "exam_name":        job.exam_name,
        "status":           job.status,
        "completed_steps":  job.completed_steps,
        "total_steps":      job.total_steps,
        "progress_pct":     pct,
        "error":            job.error,
        "result_exam_id":   job.result_exam_id,
        "result_url":       f"/exams/{job.result_exam_id}" if job.result_exam_id else None,
    }


@router.get("/generate/examtopics-exams/")
def generate_examtopics_exams(background_tasks: BackgroundTasks):
    background_tasks.add_task(_run_csv_generation)
    return {"message": "CSV generation started in background. Watch uvicorn logs for progress."}


def _run_csv_generation() -> None:
    import logging
    log = logging.getLogger("csv_generation")
    logging.basicConfig(level=logging.INFO, force=True)

    with open("examtopics_exam_list.csv", "r") as f:
        rows = list(csv.reader(f))[1:]  # skip header

    total = len(rows)
    log.info(f"[CSV] Starting: {total} exams to process")

    done = skipped = failed = 0

    for idx, row in enumerate(rows, start=1):
        examtopics_exam_id   = int(row[0])
        examtopics_exam_name = row[1]
        vendor_slug          = row[2]

        log.info(f"[CSV] [{idx}/{total}] Starting: {examtopics_exam_name} (et_id={examtopics_exam_id}, vendor={vendor_slug})")

        result = generate_exams_from_csv_data(
            examtopics_exam_id=examtopics_exam_id,
            examtopics_exam_name=examtopics_exam_name,
            vendor_slug=vendor_slug,
        )

        status = result.get("status")
        if status == "done":
            done += 1
            partial = f" | partial_errors={len(result['errors'])}" if result.get("errors") else ""
            log.info(
                f"[CSV] [{idx}/{total}] OK: {examtopics_exam_name}"
                f" | exam_id={result.get('exam_id')}"
                f" | questions={result.get('questions_added')}"
                f"{partial}"
            )
        elif status == "skipped":
            skipped += 1
            log.info(f"[CSV] [{idx}/{total}] SKIPPED: {examtopics_exam_name} | {result.get('error')}")
        else:
            failed += 1
            log.error(f"[CSV] [{idx}/{total}] FAILED: {examtopics_exam_name} | {result.get('error')}")

    log.info(f"[CSV] Finished. done={done} skipped={skipped} failed={failed} total={total}")


def generate_exams_from_csv_data(
    examtopics_exam_id: int,
    examtopics_exam_name: str,
    vendor_slug: str,
    questions_per_test: int = 120,
    llm_model: str = "gemini-cheap",
) -> dict:
    """
    Generate a full exam (metadata + 1 test + N questions) from ExamTopics source.
    All questions are fetched from the ExamTopics API and enhanced via LLM.
    Vendor is resolved by slug; falls back to 'others' if not found.
    Returns a result dict with status, exam_id, and any error message.
    """
    with Session(engine) as session:

        # Vendor lookup with 'others' fallback
        vendor = session.exec(
            select(Vendor).where(Vendor.slug == vendor_slug)
        ).first()
        if not vendor:
            vendor = session.exec(
                select(Vendor).where(Vendor.slug == "others")
            ).first()
        if not vendor:
            return {
                "status": "failed",
                "error": f"Vendor '{vendor_slug}' not found and 'others' fallback is missing. Run seed_vendors.py first.",
            }

        # Slug collision check — skip instead of crash
        slug_base = _slugify(examtopics_exam_name)
        if session.exec(select(Exam).where(Exam.slug == slug_base)).first():
            return {"status": "skipped", "error": f"Exam with slug '{slug_base}' already exists."}

        # Exam metadata via LLM
        try:
            meta = generate_exam_metadata(examtopics_exam_name, "", llm_model)
        except Exception as e:
            return {"status": "failed", "error": f"Metadata generation failed: {e}"}

        exam = Exam(
            vendor_id=vendor.id,
            name=examtopics_exam_name,
            exam_code=None,
            slug=slug_base,
            short_description=meta.get("short_description"),
            description=meta.get("description"),
            is_active=True,
        )
        session.add(exam)
        session.flush()

        # Test record
        test = Test(
            exam_id=exam.id,
            name="Practice Test 1",
            slug=f"{slug_base}-pt1",
            is_active=True,
        )
        session.add(test)
        session.flush()

        # Fetch + enhance questions from ExamTopics
        base_url = settings.BACKEND_ALGOHOLIC_URL
        et_url = (
            f"{base_url}/api/v1/examtopics/"
            f"get-a-random-question-from-examtopics-exam/{examtopics_exam_id}"
        )

        questions_added = 0
        errors = []

        for i in range(questions_per_test):
            # Fetch raw question
            try:
                with httpx.Client(timeout=15.0) as client:
                    resp = client.get(et_url)
                    resp.raise_for_status()
                    raw_et = resp.json()
            except Exception as e:
                errors.append(f"Q{i+1} fetch failed: {e}")
                # If the very first question fails it is likely a connectivity
                # or config issue — abort early rather than hammering the API
                # N times and leaving an empty exam in the DB.
                if i == 0:
                    session.delete(test)
                    session.delete(exam)
                    session.commit()
                    return {
                        "status": "failed",
                        "error": f"Aborting — first question fetch failed: {e}. Check BACKEND_ALGOHOLIC_URL and SSL config.",
                        "errors": errors,
                    }
                continue

            # Enhance with LLM; fallback to raw data on failure
            try:
                enhanced = generate_question_from_examtopics(
                    raw_et, llm_model, question_index=i
                )
            except Exception:
                discussions = raw_et.get("top_3_discussions", [])
                enhanced = {
                    "question": raw_et.get("question", ""),
                    "question_type": "multiple-choice",
                    "options": {
                        str(j + 1): c["choice_text"]
                        for j, c in enumerate(raw_et.get("choices", []))
                    },
                    "correct_options": [_et_answer_to_int(raw_et.get("answer", "A"))],
                    "overall_explanation": (
                        discussions[0]["content"] if discussions
                        else raw_et.get("answer_description", "")
                    ),
                    "domain": None,
                }

            raw_type = enhanced.get("question_type", "multiple-choice")
            session.add(Question(
                test_id=test.id,
                question=enhanced.get("question", ""),
                question_type=(
                    QuestionType.multi_select
                    if raw_type == "multi-select"
                    else QuestionType.multiple_choice
                ),
                options=enhanced.get("options", {}),
                correct_options=enhanced.get("correct_options", [1]),
                explanations={},
                overall_explanation=enhanced.get("overall_explanation"),
                domain=enhanced.get("domain"),
                llm_model=f"et+{llm_model}",
                is_active=True,
            ))
            session.commit()
            questions_added += 1

        # If we somehow finished the loop with zero questions (partial failures)
        # clean up the empty exam so the slug is free for a retry.
        if questions_added == 0:
            session.delete(test)
            session.delete(exam)
            session.commit()
            return {
                "status": "failed",
                "error": "No questions were added. Exam record cleaned up so you can retry.",
                "errors": errors,
            }

        return {
            "status": "done",
            "exam_id": exam.id,
            "exam_slug": slug_base,
            "vendor_slug": vendor.slug,
            "questions_added": questions_added,
            "errors": errors,
        }