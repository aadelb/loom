"""Live integration tests for 6 Career Intelligence tools (REQ-045)."""
import pytest

pytestmark = [pytest.mark.live, pytest.mark.timeout(60)]


class TestCareerIntelTools:
    @pytest.mark.asyncio
    async def test_funding_signal(self):
        from loom.tools.career.job_signals import research_funding_signal
        result = await research_funding_signal(company="Google", domain="AI")
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_stealth_hire_scanner(self):
        from loom.tools.career.job_signals import research_stealth_hire_scanner
        result = await research_stealth_hire_scanner(company="OpenAI")
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_career_trajectory(self):
        from loom.tools.career.career_trajectory import research_career_trajectory
        result = await research_career_trajectory(role="AI Engineer", location="Dubai")
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_market_velocity(self):
        from loom.tools.career.career_trajectory import research_market_velocity
        result = await research_market_velocity(field="AI", region="UAE")
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_optimize_resume(self):
        from loom.tools.career.resume_intel import research_optimize_resume
        result = await research_optimize_resume(resume_text="Software engineer with 5 years experience", target_role="AI Engineer")
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_interview_prep(self):
        from loom.tools.career.resume_intel import research_interview_prep
        result = await research_interview_prep(role="AI Engineer", company="tech startup")
        assert isinstance(result, dict)
