from typing import List, Dict
import json

class CodeReview:
    """Represents a single code review for a file."""
    def __init__(self, file: str, line: int, comments: List[str],
        bug_count: int, smell_count: int, optimization_count: int,
        logical_errors: int, performance_issues: int):
        self.file = file
        self.line = line
        self.comments = comments
        self.bug_count = bug_count
        self.smell_count = smell_count
        self.optimization_count = optimization_count
        self.logical_errors = logical_errors
        self.performance_issues = performance_issues

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "file": self.file,
            "line": self.line,
            "comments": self.comments,
            "bugCount": self.bug_count,
            "smellCount": self.smell_count,
            "optimizationCount": self.optimization_count,
            "logicalErrors": self.logical_errors,  
            "performanceIssues": self.performance_issues,            
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'CodeReview':
        """Create from dictionary, validating required fields."""
        if not isinstance(data, dict):
            raise ValueError("Input must be a dictionary")
        file = data.get("file", "")
        if not file:
            raise ValueError("Missing 'file' in review data")
        line = data.get("line", 1)
        if not isinstance(line, int):
            raise ValueError("'line' must be an integer")
        comments = data.get("comments", [])
        if not isinstance(comments, list):
            raise ValueError("'comments' must be a list")
        # Validate and default counts
        def get_count(key: str) -> int:
            value = data.get(key, 0)
            if not isinstance(value, int) or value < 0:
                raise ValueError(f"'{key}' must be a non-negative integer")
            return value
        bug_count = get_count("bugCount")
        smell_count = get_count("smellCount")
        optimization_count = get_count("optimizationCount")
        logical_errors = get_count("logicalErrors")
        performance_issues = get_count("performanceIssues")

        return cls(
            file=file,
            line=line,
            comments=comments,
            bug_count=bug_count,
            smell_count=smell_count,
            optimization_count=optimization_count,
            logical_errors=logical_errors,
            performance_issues=performance_issues,
        )

    def __str__(self) -> str:
        return f"Review for {self.file} at line {self.line}: {self.comments}"


class LLMReviewResult:
    """Represents the LLM's review output as a collection of CodeReview objects."""
    def __init__(self, reviews: List[CodeReview], total_tokens: int, prompt_tokens: int, completion_tokens: int):
        self.reviews = reviews
        self.totals = self.summarize_reviews(reviews, total_tokens, prompt_tokens, completion_tokens)

    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps([review.to_dict() for review in self.reviews], indent=2)
    
    def get_overall_review(
        self,
        deep: bool,
        full_context: bool,
        model: str
    ) -> str:
        """
        Return a human-readable summary of overall review metrics,
        including only those with non-zero values.
        """
        # mapping of internal keys to display labels
        labels = {
            'total_tokens': 'Total tokens',
            'prompt_tokens': 'Prompt tokens',
            'completion_tokens': 'Completion tokens',
            'bug_count': 'Bugs found',
            'smell_count': 'Code smells',
            'optimization_count': 'Optimizations suggested',
            'logical_errors': 'Logical errors',
            'performance_issues': 'Performance issues',
        }

        # build list of non-zero metrics
        parts = [f"{labels[key]}: {value}"
                 for key, value in self.totals.items()
                 if key in labels and value > 0]

        if not parts:
            return f"No issues detected by {model}."

        # join with semicolons for clarity
        metrics_summary = "; ".join(parts)
        return f"{model} review summary{' (deep)' if deep else ''}{' with full context' if full_context else ''}: {metrics_summary}."
                

    def summarize_reviews(self, reviews: List[CodeReview], total_tokens: int, 
                prompt_tokens: int, completion_tokens: int) -> Dict[str, int]:
        totals = {
            "bug_count": 0,
            "smell_count": 0,
            "optimization_count": 0,
            "logical_errors": 0,
            "performance_issues": 0,
            "total_tokens": total_tokens,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
        }
        for r in reviews:
            totals["bug_count"]          += r.bug_count
            totals["smell_count"]        += r.smell_count
            totals["optimization_count"] += r.optimization_count
            totals["logical_errors"]     += r.logical_errors
            totals["performance_issues"] += r.performance_issues
        return totals    

    @classmethod
    def from_json(cls, json_str: str, total_tokens: int,prompt_tokens:int, completion_tokens : int) -> 'LLMReviewResult':
        """Create from JSON string, validating structure."""
        try:
            data = json.loads(json_str)
            if not isinstance(data, list):
                raise ValueError("LLM response must be a JSON array")
            reviews = [CodeReview.from_dict(item) for item in data]
            return cls(reviews=reviews, total_tokens=total_tokens,
                prompt_tokens=prompt_tokens, completion_tokens=completion_tokens)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON response: {str(e)}")

    def __str__(self) -> str:
        return f"LLM Review Result with {len(self.reviews)} reviews"