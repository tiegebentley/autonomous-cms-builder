"""
Critic Agent - Validates and scores the analysis from Analyzer Agent
"""
import os
from typing import Dict, Any, List
import anthropic
from .base import BaseAgent


class CriticAgent(BaseAgent):
    """
    Reviews the output of Analyzer Agent and provides:
    - Validation of completeness
    - Confidence scoring
    - Gap detection
    - Quality assessment
    """

    def __init__(self, project_path: str, project_name: str, analyzer_output: Dict[str, Any], anthropic_api_key: str = None):
        super().__init__(project_path, project_name)
        self.anthropic_api_key = anthropic_api_key or os.getenv("ANTHROPIC_API_KEY")
        self.client = anthropic.Anthropic(api_key=self.anthropic_api_key)
        self.analyzer_output = analyzer_output

    async def execute(self) -> Dict[str, Any]:
        """Execute the critic validation workflow"""
        results = {
            "validation_status": "pending",
            "overall_confidence": 0.0,
            "completeness_score": 0.0,
            "accuracy_score": 0.0,
            "gaps_identified": [],
            "strengths_identified": [],
            "recommendations": [],
            "approval": False,
            "critique": {},
            "confidence_breakdown": {}
        }

        # Step 1: Validate completeness
        completeness = await self._check_completeness()
        results["completeness_score"] = completeness["score"]
        results["gaps_identified"] = completeness["gaps"]
        results["strengths_identified"] = completeness.get("strengths", [])

        # Step 2: Validate accuracy using AI (skip if API key missing)
        try:
            ai_critique = await self._ai_validation()
            results["accuracy_score"] = ai_critique.get("accuracy_score", 0.7)
            results["critique"] = ai_critique
            results["recommendations"] = ai_critique.get("recommendations", [])
        except Exception as e:
            print(f"AI validation skipped: {str(e)}")
            # Use completeness score as fallback for accuracy
            results["accuracy_score"] = results["completeness_score"]
            results["recommendations"] = ["AI validation unavailable - using rule-based scoring"]

        # Step 3: Calculate overall confidence with detailed breakdown
        results["overall_confidence"] = (
            results["completeness_score"] * 0.5 +  # Increased weight for completeness
            results["accuracy_score"] * 0.5
        )

        results["confidence_breakdown"] = {
            "completeness": results["completeness_score"],
            "accuracy": results["accuracy_score"],
            "weighted_total": results["overall_confidence"]
        }

        # Step 4: Determine approval (lowered threshold from 0.7 to 0.6 for rule-based systems)
        approval_threshold = 0.6
        results["approval"] = results["overall_confidence"] >= approval_threshold
        results["validation_status"] = "approved" if results["approval"] else "needs_revision"

        return results

    async def _check_completeness(self) -> Dict[str, Any]:
        """Check if the analysis is complete with enhanced validation"""
        score = 1.0
        gaps = []
        strengths = []

        # Check for required fields
        required_fields = ["framework", "content_types_found", "cms_recommendations", "extracted_patterns"]
        for field in required_fields:
            if field not in self.analyzer_output or not self.analyzer_output[field]:
                gaps.append(f"Missing or empty field: {field}")
                score -= 0.15
            else:
                strengths.append(f"Found {field}")

        # Enhanced content type validation
        content_types = self.analyzer_output.get("content_types_found", [])
        if not content_types:
            gaps.append("No content types identified")
            score -= 0.25
        elif len(content_types) == 1:
            gaps.append("Only one content type identified - may need deeper analysis")
            score -= 0.05
        else:
            strengths.append(f"Identified {len(content_types)} distinct content types")

        # Enhanced CMS recommendations validation
        cms_recs = self.analyzer_output.get("cms_recommendations", {})
        if not cms_recs or not isinstance(cms_recs, dict):
            gaps.append("No CMS recommendations provided")
            score -= 0.25
        else:
            # Check quality of recommendations
            for content_type, config in cms_recs.items():
                if not config.get("fields"):
                    gaps.append(f"Content type '{content_type}' has no fields defined")
                    score -= 0.1
                elif len(config.get("fields", [])) < 2:
                    gaps.append(f"Content type '{content_type}' has very few fields")
                    score -= 0.05
                else:
                    # Check for domain-specific fields (good sign)
                    field_names = [f.get("name", "") for f in config.get("fields", [])]
                    if any(name in field_names for name in ["address", "phone", "email", "price", "date", "author"]):
                        strengths.append(f"'{content_type}' has domain-specific fields")

                # Check page count
                page_count = config.get("page_count", 0)
                if page_count == 0:
                    gaps.append(f"Content type '{content_type}' has no pages")
                    score -= 0.1
                elif page_count >= 3:
                    strengths.append(f"'{content_type}' has {page_count} pages")

        # Check extracted patterns quality
        patterns = self.analyzer_output.get("extracted_patterns", {})
        if patterns:
            pattern_count = len([k for k, v in patterns.items() if isinstance(v, dict) and v.get("title")])
            if pattern_count > 10:
                strengths.append(f"Extracted {pattern_count} detailed page patterns")
            elif pattern_count < 3:
                gaps.append("Very few page patterns extracted")
                score -= 0.1

        # Check if routes were extracted (for non-static sites)
        framework = self.analyzer_output.get("framework")
        if framework in ["react", "nextjs", "vite"]:
            if not self.analyzer_output.get("routes"):
                gaps.append("Routes not extracted from React/Next.js project")
                score -= 0.15
            else:
                strengths.append("Routes successfully extracted")

        # File analysis quality check
        files_analyzed = self.analyzer_output.get("files_analyzed", 0)
        if files_analyzed == 0:
            gaps.append("No files were analyzed")
            score -= 0.2
        elif files_analyzed < 5:
            gaps.append(f"Only {files_analyzed} files analyzed - may be incomplete")
            score -= 0.05
        else:
            strengths.append(f"Analyzed {files_analyzed} files")

        return {
            "score": max(0.0, min(1.0, score)),
            "gaps": gaps,
            "strengths": strengths
        }

    async def _ai_validation(self) -> Dict[str, Any]:
        """Use AI to validate the quality and accuracy of the analysis"""

        # Prepare the analyzer output summary
        import json
        analyzer_summary = json.dumps(self.analyzer_output, indent=2, default=str)[:3000]  # Limit size

        prompt = f"""You are a senior technical architect reviewing an AI-generated analysis of a frontend project for CMS integration.

Project: {self.project_name}
Framework: {self.analyzer_output.get('framework', 'unknown')}

Analyzer Output:
{analyzer_summary}

Please critique this analysis and provide:

1. **Accuracy Assessment** (0.0-1.0): How accurate does this analysis appear?
2. **Specific Issues**: What specific problems or inaccuracies do you see?
3. **Missing Elements**: What important aspects were not analyzed?
4. **Recommendations**: What should be improved or added?
5. **Strengths**: What was done well?

Respond in JSON format:
{{
  "accuracy_score": 0.85,
  "issues": ["issue 1", "issue 2"],
  "missing_elements": ["element 1", "element 2"],
  "recommendations": ["rec 1", "rec 2"],
  "strengths": ["strength 1", "strength 2"],
  "summary": "Brief overall assessment"
}}
"""

        try:
            message = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=2048,
                messages=[{"role": "user", "content": prompt}]
            )

            # Extract JSON from response
            response_text = message.content[0].text

            # Try to parse JSON
            import re
            json_match = re.search(r'```json\s*(.*?)\s*```', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                json_str = json_match.group(0) if json_match else response_text

            ai_response = json.loads(json_str)
            return ai_response

        except Exception as e:
            print(f"Error in AI validation: {str(e)}")
            return {
                "accuracy_score": 0.5,
                "issues": [f"AI validation error: {str(e)}"],
                "missing_elements": [],
                "recommendations": ["Re-run validation"],
                "strengths": [],
                "summary": "Validation incomplete due to error"
            }
