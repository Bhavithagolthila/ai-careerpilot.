"""Rule-based resume processing. No AI: just PDF text extraction + keyword matching."""
import io
import re
from pypdf import PdfReader

# Configurable skill dictionary: canonical name -> search terms (all lowercase).
SKILLS = {
    "Python": ["python"], "Java": ["java"], "JavaScript": ["javascript", "js"],
    "TypeScript": ["typescript"], "C": ["c programming", "c language"], "C++": ["c++"], "C#": ["c#"],
    "SQL": ["sql"], "MySQL": ["mysql"], "PostgreSQL": ["postgresql", "postgres"],
    "MongoDB": ["mongodb", "mongo"], "HTML": ["html", "html5"], "CSS": ["css", "css3"],
    "React": ["react", "reactjs"], "Node.js": ["node.js", "nodejs"], "Express": ["express.js", "expressjs"],
    "FastAPI": ["fastapi"], "Django": ["django"], "Flask": ["flask"], "Spring Boot": ["spring boot"],
    "Git": ["git"], "GitHub": ["github"], "Docker": ["docker"], "Linux": ["linux"],
    "REST API": ["rest api", "rest apis", "restful"], "JWT": ["jwt"], "Postman": ["postman"],
    "Pandas": ["pandas"], "NumPy": ["numpy"], "Machine Learning": ["machine learning"],
    "Data Analysis": ["data analysis", "data analytics"], "Power BI": ["power bi", "powerbi"],
    "Excel": ["excel"], "Tableau": ["tableau"], "AWS": ["aws"], "Pytest": ["pytest"],
    "Tailwind CSS": ["tailwind"], "Bootstrap": ["bootstrap"], "Redux": ["redux"], "Axios": ["axios"],
    "DSA": ["dsa", "data structures", "algorithms"], "OOP": ["oop", "oops", "object oriented"],
    "Agile": ["agile", "scrum"], "Jupyter": ["jupyter"],
    "Angular": ["angular", "angularjs"], "Vue.js": ["vue.js", "vuejs", "vue"], "Next.js": ["next.js", "nextjs"],
    "PHP": ["php"], "Kotlin": ["kotlin"], "Redis": ["redis"], "Kubernetes": ["kubernetes", "k8s"],
    "CI/CD": ["ci/cd", "cicd"], "Selenium": ["selenium"], "TensorFlow": ["tensorflow"],
    "Scikit-learn": ["scikit-learn", "sklearn"], "Matplotlib": ["matplotlib"],
}

# Extra spellings people really use. Merged into SKILLS below (kept separate so the list above stays readable).
_MORE_ALIASES = {
    "JavaScript": ["java script", "ecmascript", "es6"], "React": ["react.js", "react js"],
    "Node.js": ["node js"], "Express": ["express js"], "MongoDB": ["mongo db"],
    "PostgreSQL": ["postgre sql", "psql"], "REST API": ["restful api", "restful apis", "rest api's", "rest services"],
    "Spring Boot": ["springboot"], "Power BI": ["power-bi"], "Tailwind CSS": ["tailwindcss"],
    "Machine Learning": ["ml models"], "OOP": ["oops concepts", "object-oriented"],
}
for _name, _extra in _MORE_ALIASES.items():
    SKILLS[_name] = SKILLS[_name] + _extra

# Words that turn an ordinary English word into a NON-skill: "excel in teamwork", "react to feedback".
_NOT_A_SKILL_IF_FOLLOWED_BY = {
    "excel": r"\s+(?:in|at|as|with|to|under|by)\b",
    "react": r"\s+(?:to|quickly|fast|well|positively)\b",
}
# The single letter "C" is only trusted inside a list of skills such as "Languages: C, C++, Python".
_C_IN_LIST = re.compile(r"(?:^|[,;|/•:])\s*c\s*(?=[,;|/•]|$)", re.M)


def _pattern(term: str):
    body = re.escape(term).replace(r"\ ", r"\s+")
    guard = _NOT_A_SKILL_IF_FOLLOWED_BY.get(term, "")
    tail = r"(?![a-z0-9+#])" + (f"(?!{guard})" if guard else "")
    return re.compile(r"(?<![a-z0-9+#.])" + body + tail)


_PATTERNS = {name: [_pattern(t) for t in terms] for name, terms in SKILLS.items()}


SKILL_NAMES = sorted(SKILLS)
_ALIAS_TO_SKILL = {t: name for name, terms in SKILLS.items() for t in terms}
_ALIAS_TO_SKILL.update({name.lower(): name for name in SKILLS})


def normalize_skill(name: str) -> str:
    """Map any known spelling ("reactjs", "Node JS", "postgres") to its canonical name ("React", ...).
    Unknown skills are returned trimmed but otherwise unchanged."""
    cleaned = " ".join((name or "").split())
    return _ALIAS_TO_SKILL.get(cleaned.lower(), cleaned)


def extract_skills(text: str) -> list[str]:
    text = text.lower()
    found = {n for n, pats in _PATTERNS.items() if any(p.search(text) for p in pats)}
    if _C_IN_LIST.search(text):
        found.add("C")
    return sorted(found)


class PDFError(Exception):
    pass


def extract_text(data: bytes) -> str:
    try:
        reader = PdfReader(io.BytesIO(data))
        if reader.is_encrypted:
            raise PDFError("This PDF is password protected.")
        text = "\n".join((page.extract_text() or "") for page in reader.pages)
    except PDFError:
        raise
    except Exception:
        raise PDFError("The PDF could not be read. It may be corrupted.")
    if not text.strip():
        raise PDFError("No text found. Scanned/image PDFs are not supported.")
    return text
