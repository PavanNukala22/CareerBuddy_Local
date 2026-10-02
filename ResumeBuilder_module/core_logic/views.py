from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST, require_GET
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.conf import settings
from .models import Resume, JobDescription, ResumeInterviewSession, ResumeQuestion, ResumeAnswer, ScoreRecord
from .resume_utils import (
    extract_text_from_pdf,
    extract_text_from_docx,
    analyze_resume_with_sarvam,
    generate_interview_questions,
    evaluate_answer
)
import logging

logger = logging.getLogger(__name__)

@login_required
def resume_builder_home(request):
    """Renders the resume upload and analysis home page."""
    return render(request, "resume_builder.html")

@login_required
def resume_job_match(request):
    """Handles resume + JD upload and runs AI analysis."""
    if request.method == "POST":
        resume_file = request.FILES.get("file")
        jd_text = request.POST.get("text", "").strip()

        if not resume_file:
            return render(request, "resume_builder.html", {"error": "Please upload a resume."})
        
        db_jd_text = jd_text if jd_text else "General Resume Analysis"
        resume = Resume.objects.create(user=request.user)
        resume.file.save(resume_file.name, resume_file)
        file_path = resume.file.path

        if resume_file.name.lower().endswith(".pdf"):
            extracted_text = extract_text_from_pdf(file_path)
        elif resume_file.name.lower().endswith(".docx"):
            extracted_text = extract_text_from_docx(file_path)
        else:
            extracted_text = resume_file.read().decode("utf-8", errors="ignore")

        clean_text = (extracted_text or "").strip()
        if not clean_text or clean_text.lower().startswith("error reading"):
            resume.delete()
            return render(request, "resume_builder.html", {"error": "Could not read text from your resume."})

        resume.extracted_text = clean_text
        resume.save()
        jd = JobDescription.objects.create(user=request.user, text=db_jd_text)
        analysis = analyze_resume_with_sarvam(clean_text, jd_text)

        if isinstance(analysis, dict) and "error" in analysis:
            return render(request, "resume_builder.html", {"error": "AI analysis failed."})

        request.session["rb_resume_id"] = resume.id
        request.session["rb_jd_id"] = jd.id
        request.session["rb_analysis"] = analysis
        request.session["rb_interview_current_idx"] = 0
        request.session["rb_interview_session_id"] = None
        request.session.modified = True
        
        from career_app.resume_utils import validate_resume_fields
        is_valid, matched_count, matched_fields, missing_fields = validate_resume_fields(clean_text)
        
        validation_msg = ""
        if not is_valid:
            validation_msg = f"Invalid resume. We could only find {matched_count} out of 10 standard resume sections. Please ensure your resume contains at least 3 of: Name & Contact Info, Summary, Technical Skills, Work Experience, Projects, Education, Certifications, Achievements, Languages, or Additional Info."

        return render(request, "resume_match_result.html", {
            "analysis": analysis,
            "resume": resume,
            "jd": jd,
            "is_ats_only": not jd_text,
            "resume_valid": is_valid,
            "validation_msg": validation_msg,
        })

    analysis = request.session.get("rb_analysis")
    if analysis:
        res_id = request.session.get("rb_resume_id")
        resume_valid = True
        validation_msg = ""
        if res_id:
            try:
                res_obj = Resume.objects.get(id=res_id)
                from career_app.resume_utils import validate_resume_fields
                is_valid, matched_count, _, _ = validate_resume_fields(res_obj.extracted_text)
                resume_valid = is_valid
                if not is_valid:
                    validation_msg = f"Invalid resume. We could only find {matched_count} out of 10 standard resume sections. Please ensure your resume contains at least 3 of: Name & Contact Info, Summary, Technical Skills, Work Experience, Projects, Education, Certifications, Achievements, Languages, or Additional Info."
            except Resume.DoesNotExist:
                pass
        return render(request, "resume_match_result.html", {
            "analysis": analysis, 
            "is_ats_only": True,
            "resume_valid": resume_valid,
            "validation_msg": validation_msg,
        })
    return redirect("resume_builder_home")

def _ensure_resume_interview_questions(session):
    if session.questions.exists(): return
    skills = session.matching_skills or []
    raw_questions = generate_interview_questions(session.resume.extracted_text, session.job_description.text, skills=skills)
    for i, q_data in enumerate(raw_questions):
        ResumeQuestion.objects.create(session=session, text=q_data.get("question", ""), topic=q_data.get("topic", "General"), order=i)

@login_required
def resume_start_interview(request):
    res_id, jd_id = request.session.get("rb_resume_id"), request.session.get("rb_jd_id")
    analysis = request.session.get("rb_analysis", {})
    if not res_id or not jd_id: return redirect("resume_job_match")
    
    resume = Resume.objects.get(id=res_id, user=request.user)
    jd = JobDescription.objects.get(id=jd_id, user=request.user)
    interview_session = ResumeInterviewSession.objects.create(resume=resume, job_description=jd, matching_skills=analysis.get("matching_skills", []))
    
    request.session["rb_interview_session_id"] = interview_session.id
    request.session["rb_interview_current_idx"] = 0
    request.session.modified = True
    return redirect("resume_interview_chat")

@login_required
def resume_interview_chat(request):
    s_id = request.session.get("rb_interview_session_id")
    if not s_id: return redirect("resume_job_match")
    session = ResumeInterviewSession.objects.get(id=s_id)
    _ensure_resume_interview_questions(session)
    return render(request, "resume_interview.html")

@login_required
@require_GET
def resume_get_next_question(request):
    s_id = request.session.get("rb_interview_session_id")
    if not s_id: return JsonResponse({"error": "No session"}, status=400)
    session = ResumeInterviewSession.objects.get(id=s_id)
    questions = list(session.questions.order_by("order"))
    curr_idx = request.session.get("rb_interview_current_idx", 0)
    
    if request.GET.get("next") == "true":
        if curr_idx < len(questions) and hasattr(questions[curr_idx], "answer"):
            curr_idx += 1
            request.session["rb_interview_current_idx"] = curr_idx
            request.session.modified = True
    
    if curr_idx >= len(questions):
        session.is_completed = True; session.save()
        return JsonResponse({"status": "completed"})
    
    q = questions[curr_idx]
    return JsonResponse({"id": q.id, "text": q.text, "topic": q.topic, "progress": f"{curr_idx+1}/{len(questions)}", "status": "active"})

@login_required
@csrf_exempt
@require_POST
def resume_submit_answer(request):
    q_id = request.POST.get("question_id")
    ans_text = request.POST.get("answer_text", "").strip()
    question = ResumeQuestion.objects.get(id=q_id)
    eval_res = evaluate_answer(question.text, ans_text)
    ResumeAnswer.objects.update_or_create(question=question, defaults={"text": ans_text, "score": eval_res.get("score", 0), "feedback": eval_res.get("feedback", "")})
    ScoreRecord.objects.create(user=request.user, module="interview", score=eval_res.get("score", 0), max_score=10, label=question.topic)
    return JsonResponse({"score": eval_res.get("score", 0), "feedback": eval_res.get("feedback", "")})

@login_required
def resume_analytics(request):
    s_id = request.session.get("rb_interview_session_id")
    session = ResumeInterviewSession.objects.filter(resume__user=request.user).order_by("-start_time").first() if not s_id else ResumeInterviewSession.objects.get(id=s_id)
    if not session: return redirect("resume_builder_home")
    results = []
    for q in session.questions.order_by("order"):
        try:
            ans = q.answer
            results.append({"topic": q.topic, "question": q.text, "answer": ans.text, "score": ans.score, "feedback": ans.feedback})
        except: pass
    return render(request, "resume_analytics.html", {"session": session, "results": results})
