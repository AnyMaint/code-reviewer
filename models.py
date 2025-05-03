from typing import List
import json

class CodeReview:
    """Represents a single code review for a file."""
    def __init__(self, file: str, line: int, comments: List[str]):
        self.file = file
        self.line = line
        self.comments = comments

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "file": self.file,
            "line": self.line,
            "comments": self.comments
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
        return cls(file=file, line=line, comments=comments)

    def __str__(self) -> str:
        return f"Review for {self.file} at line {self.line}: {self.comments}"


class LLMReviewResult:
    """Represents the LLM's review output as a collection of CodeReview objects."""
    def __init__(self, reviews: List[CodeReview]):
        self.reviews = reviews

    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps([review.to_dict() for review in self.reviews], indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> 'LLMReviewResult':
        """Create from JSON string, validating structure."""
        try:
            data = json.loads(json_str)
            if not isinstance(data, list):
                raise ValueError("LLM response must be a JSON array")
            reviews = [CodeReview.from_dict(item) for item in data]
            return cls(reviews=reviews)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON response: {str(e)}")

    def __str__(self) -> str:
        return f"LLM Review Result with {len(self.reviews)} reviews"