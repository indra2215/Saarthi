# api/email_draft.py — Draft email generator with STATED vs INFERRED wording
# Uses Gemini/Groq LLM if configured, else pure template.

import yaml
import urllib.parse
from pathlib import Path


def _load_config():
    with open(Path(__file__).parent.parent / "config.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _template_stated(faculty_name: str, student_name: str, student_email: str,
                     topic: str, passage: str, slots: list[str]) -> tuple[str, str]:
    slots_str = "\n".join(f"  • {s}" for s in slots) if slots else "  • (Please suggest a convenient time)"
    subject = f"Research Inquiry — {topic}"
    body = f"""Dear {faculty_name},

I am {student_name}, a student at Keshav Memorial Engineering College (KMEC). I am interested in pursuing research on {topic}, and your stated expertise in this area caught my attention.

I came across the following from your profile:
"{passage[:300]}..."

I would appreciate the opportunity to meet with you and discuss potential research collaboration or guidance.

Proposed meeting slots:
{slots_str}

Thank you for your time and consideration.

Warm regards,
{student_name}
{student_email}
"""
    return subject, body


def _template_inferred(faculty_name: str, student_name: str, student_email: str,
                       topic: str, paper_title: str, slots: list[str]) -> tuple[str, str]:
    slots_str = "\n".join(f"  • {s}" for s in slots) if slots else "  • (Please suggest a convenient time)"
    subject = f"Query Regarding Your Research on {topic}"
    body = f"""Dear {faculty_name},

I am {student_name}, a student at Keshav Memorial Engineering College (KMEC). I recently read your research work titled "{paper_title}" and found it highly relevant to my interest in {topic}.

I would like to discuss related research directions and explore possibilities for guidance or collaboration.

Proposed meeting slots:
{slots_str}

Thank you for your time.

Warm regards,
{student_name}
{student_email}

Note: This message is based on your published research work.
"""
    return subject, body


def _llm_enhance(subject: str, body: str, provider: str, keys: dict, models: dict) -> tuple[str, str]:
    """Try to polish the email with an LLM. Fall back to template on failure."""
    prompt = f"Polish this academic email draft, keeping it professional and concise (max 200 words). Do not change the facts or add claims not present:\n\nSubject: {subject}\n\n{body}"
    
    import os
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except Exception:
        pass

    gemini_keys = [k for k in keys.get("gemini", []) if k]
    if os.environ.get("GEMINI_API_KEY"):
        gemini_keys.insert(0, os.environ["GEMINI_API_KEY"])
    groq_keys = [k for k in keys.get("groq", []) if k]
    if os.environ.get("GROQ_API_KEY"):
        groq_keys.insert(0, os.environ["GROQ_API_KEY"])

    try:
        if provider == "gemini":
            import google.generativeai as genai
            for key in gemini_keys:
                try:
                    genai.configure(api_key=key)
                    model = genai.GenerativeModel(models["gemini_model"])
                    resp = model.generate_content(prompt)
                    enhanced = resp.text.strip()
                    if enhanced:
                        return subject, enhanced
                except Exception:
                    continue

        if provider == "groq" or True:  # Always try groq as fallback
            from groq import Groq
            for key in groq_keys:
                try:
                    client = Groq(api_key=key)
                    resp = client.chat.completions.create(
                        model=models["groq_model"],
                        messages=[{"role": "user", "content": prompt}],
                        max_tokens=300,
                    )
                    enhanced = resp.choices[0].message.content.strip()
                    if enhanced:
                        return subject, enhanced
                except Exception:
                    continue
    except Exception:
        pass

    return subject, body


def draft_email(
    faculty_name: str,
    student_name: str,
    student_email: str,
    topic: str,
    expertise_basis: str,
    stated_evidence: list,
    inferred_evidence: list,
    slots: list[str],
    faculty_email: str | None = None,
) -> dict:
    cfg = _load_config()
    llm_cfg = cfg["llm"]

    # Pick passage to cite
    if expertise_basis in ("STATED", "BOTH") and stated_evidence:
        passage = stated_evidence[0].get("passage", "")
        subject, body = _template_stated(faculty_name, student_name, student_email, topic, passage, slots)
    else:
        paper_title = inferred_evidence[0].get("source_title", "your published work") if inferred_evidence else "your published work"
        subject, body = _template_inferred(faculty_name, student_name, student_email, topic, paper_title, slots)

    # Optionally enhance with LLM
    if llm_cfg.get("provider") != "template":
        subject, body = _llm_enhance(
            subject, body,
            llm_cfg.get("provider", "gemini"),
            cfg["api_keys"],
            cfg["models"]
        )

    # Build mailto link
    to = faculty_email or ""
    mailto = (
        f"mailto:{urllib.parse.quote(to)}"
        f"?subject={urllib.parse.quote(subject)}"
        f"&body={urllib.parse.quote(body)}"
    )

    return {"subject": subject, "body": body, "mailto": mailto}
