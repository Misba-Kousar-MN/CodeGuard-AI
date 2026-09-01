import os
from typing import List
from core.llm import GeminiLLMProvider
from core.schemas import ReviewIssue, ReviewResult, AnalysisResult

class SecurityReviewerAgent:
    """Agent 3: Performs focused security review for secrets, injections, eval/exec, and unsafe functions."""

    def __init__(self, llm: GeminiLLMProvider):
        self.llm = llm
        prompt_path = os.path.join(os.path.dirname(__file__), "..", "prompts", "security.txt")
        with open(prompt_path, "r", encoding="utf-8") as f:
            self.prompt_template = f.read()

    def audit(self, code: str, analysis: Optional[AnalysisResult] = None, static_security_issues: Optional[List[ReviewIssue]] = None, language: str = "python") -> List[ReviewIssue]:
        static_security_issues = static_security_issues or []
        sec_static = [i for i in static_security_issues if i.category == "Security Vulnerability"]
        sec_str = "\n".join([f"- [Line {i.line}] {i.severity} {i.title}: {i.description}" for i in sec_static]) if sec_static else "None"
        analysis_summary = analysis.summary if analysis and analysis.summary else f"Security vulnerability audit for {language}."

        if not self.llm.is_available():
            return sec_static

        prompt = (
            self.prompt_template
            .replace("{code}", code)
            .replace("{language}", language)
            .replace("{analysis_summary}", analysis_summary)
            .replace("{static_security_issues}", sec_str)
        )

        result = self.llm.generate_structured(
            prompt=prompt,
            schema_class=ReviewResult,
            system_instruction="You are Agent 3 (Security Reviewer). Audit code for security vulnerabilities only."
        )

        if not result:
            return sec_static

        ai_sec_issues = [i for i in result.issues if i.category == "Security Vulnerability"]
        
        # Merge AST static security issues
        existing_keys = {(iss.line, iss.title) for iss in ai_sec_issues}
        for st_iss in sec_static:
            if (st_iss.line, st_iss.title) not in existing_keys:
                ai_sec_issues.append(st_iss)

        return ai_sec_issues
