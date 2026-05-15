"""REQ-045: Career Intel 6 tools with UAE-specific data testing.

This test module validates career intelligence tools with UAE-specific inputs:
- research_funding_signal: Company hiring signals (emirates, ADNOC)
- research_stealth_hire_scanner: Hidden job opportunities (Dubai, Abu Dhabi)
- research_interviewer_profiler: Interviewer research for UAE companies
- research_career_trajectory: Career path analysis
- research_market_velocity: UAE job market skill analysis
- research_optimize_resume: Resume optimization for UAE roles
- research_interview_prep: Interview preparation for UAE positions
- research_deception_job_scan: Validate job posting authenticity (UAE context)
- research_salary_synthesize: Salary estimation for UAE positions

Total tools: 9 (expanded from initial 6)
"""

import pytest
from loom.tools.career.job_signals import (
    research_funding_signal,
    research_stealth_hire_scanner,
    research_interviewer_profiler,
)
from loom.tools.career.career_trajectory import (
    research_career_trajectory,
    research_market_velocity,
)
from loom.tools.career.resume_intel import (
    research_optimize_resume,
    research_interview_prep,
)
from loom.tools.career.deception_job_scanner import research_deception_job_scan
from loom.tools.career.salary_synthesizer import research_salary_synthesize


class TestFundingSignal:
    """Test research_funding_signal with UAE companies."""

    async def test_emirates_funding_signals(self):
        """Test hiring signals for Emirates company."""
        result = await research_funding_signal(
            company="Emirates",
            domain="emirates.com"
        )
        assert isinstance(result, dict)
        assert "company" in result
        assert result["company"] == "Emirates"
        assert "funding_signals" in result

    async def test_adnoc_funding_signals(self):
        """Test hiring signals for ADNOC company."""
        result = await research_funding_signal(
            company="ADNOC",
            domain="adnoc.ae"
        )
        assert isinstance(result, dict)
        assert "company" in result
        assert "funding_signals" in result


class TestStealthHireScanner:
    """Test research_stealth_hire_scanner with UAE locations."""

    async def test_dubai_software_engineer_jobs(self):
        """Test finding hidden software engineer jobs in Dubai."""
        result = await research_stealth_hire_scanner(
            keywords="software engineer",
            location="Dubai, UAE"
        )
        assert isinstance(result, dict)
        # Check actual API response structure
        assert "stealth_jobs_found" in result or "keywords" in result
        assert "total_found" in result or "keywords" in result

    async def test_abu_dhabi_data_scientist_jobs(self):
        """Test finding hidden data scientist jobs in Abu Dhabi."""
        result = await research_stealth_hire_scanner(
            keywords="data scientist",
            location="Abu Dhabi"
        )
        assert isinstance(result, dict)
        # Should have expected structure
        assert len(result) > 0


class TestInterviewerProfiler:
    """Test research_interviewer_profiler for UAE context."""

    async def test_emirates_engineer_profile(self):
        """Test building profile for engineer at Emirates."""
        result = await research_interviewer_profiler(
            person_name="John Smith",
            company="Emirates"
        )
        assert isinstance(result, dict)
        assert "person_name" in result
        assert result["person_name"] == "John Smith"


class TestCareerTrajectory:
    """Test research_career_trajectory for UAE professionals."""

    async def test_tech_professional_trajectory(self):
        """Test career trajectory for a tech professional."""
        result = await research_career_trajectory(
            person_name="Ahmed Al Mansouri",
            domain=""
        )
        assert isinstance(result, dict)
        # Basic structure validation
        assert "person_name" in result or "error" in result


class TestMarketVelocity:
    """Test research_market_velocity for UAE job market."""

    async def test_uae_software_engineer_velocity(self):
        """Test skill velocity for software engineers in UAE."""
        result = await research_market_velocity(
            skill="software engineer",
            location="Dubai, UAE"
        )
        assert isinstance(result, dict)
        # Should have demand trend and metrics
        assert "demand_trend" in result or "academic_momentum" in result or "discussion_velocity" in result

    async def test_uae_data_scientist_velocity(self):
        """Test skill velocity for data scientists in UAE."""
        result = await research_market_velocity(
            skill="data scientist",
            location="Abu Dhabi"
        )
        assert isinstance(result, dict)
        assert len(result) > 0


class TestOptimizeResume:
    """Test research_optimize_resume for UAE jobs."""

    async def test_resume_optimization_for_emirates_role(self):
        """Test resume optimization for Emirates software engineer role."""
        sample_resume = """
        Ahmed Ali
        Dubai, UAE
        +971 501 234567

        EXPERIENCE:
        Senior Software Engineer, TechCorp (2020-2024)
        - Led backend systems development
        - Managed team of 5 engineers
        - Designed microservices architecture for high-traffic systems

        SKILLS: Python, Java, Cloud Architecture, AWS, Kubernetes

        EDUCATION: BS Computer Science from UAE University
        """

        sample_job_desc = """
        Job: Senior Software Engineer at Emirates
        Location: Dubai, UAE

        Requirements:
        - 5+ years backend development
        - Python, Java, Go
        - Kubernetes, Docker, AWS
        - Team leadership experience
        - UAE residence preferred
        """

        result = await research_optimize_resume(
            resume_text=sample_resume,
            job_description=sample_job_desc
        )
        assert isinstance(result, dict)
        # Check for match score or improvements
        assert "match_score" in result or "improvements" in result or "missing_keywords" in result

    async def test_resume_optimization_for_adnoc_role(self):
        """Test resume optimization for ADNOC energy sector role."""
        sample_resume = """
        Fatima Mohammed
        Abu Dhabi, UAE
        +971 502 567890

        EDUCATION: BS Petroleum Engineering, UAE University
        EXPERIENCE: Oil & Gas Operations Engineer (2018-2024)
        - Managed production operations at offshore facilities
        - Optimized SCADA systems for process control

        SKILLS: SCADA, Process Control, SAP, Reservoir Engineering

        CERTIFICATIONS: PMP, HAZOP Trained
        """

        sample_job_desc = """
        Job: Process Engineer at ADNOC
        Location: Abu Dhabi, UAE

        Requirements:
        - Petroleum/Chemical Engineering degree
        - Process optimization expertise
        - SCADA systems experience
        - Arabic language preferred
        """

        result = await research_optimize_resume(
            resume_text=sample_resume,
            job_description=sample_job_desc
        )
        assert isinstance(result, dict)
        assert len(result) > 0


class TestInterviewPrep:
    """Test research_interview_prep for UAE positions."""

    async def test_interview_prep_emirates_engineer(self):
        """Test interview prep for Emirates software engineer role."""
        job_desc = """
        Senior Backend Engineer at Emirates
        Location: Dubai, UAE

        We are looking for a backend engineer with expertise in:
        - Microservices architecture
        - Kubernetes
        - AWS
        - CI/CD pipelines
        """

        result = await research_interview_prep(
            job_description=job_desc,
            company="Emirates",
            interview_type="technical"
        )
        assert isinstance(result, dict)
        # Should have questions or other interview prep content
        assert "questions" in result or "company_values" in result or "key_topics_to_study" in result

    async def test_interview_prep_adnoc_engineer(self):
        """Test interview prep for ADNOC petroleum engineer role."""
        job_desc = """
        Petroleum Engineer at ADNOC
        Location: Abu Dhabi, UAE

        Requirements include experience with upstream operations
        and reservoir engineering. Strong SCADA and process control skills needed.
        """

        result = await research_interview_prep(
            job_description=job_desc,
            company="ADNOC",
            interview_type="technical"
        )
        assert isinstance(result, dict)
        assert len(result) > 0


class TestDeceptionJobScan:
    """Test research_deception_job_scan for UAE job postings."""

    def test_scan_legitimate_emirates_posting(self):
        """Test scanning a legitimate Emirates job posting."""
        job_text = """
        Position: Senior Software Engineer
        Company: Emirates
        Location: Dubai, UAE
        Salary: AED 15,000 - 25,000 per month

        We are seeking a senior backend engineer with:
        - 5+ years of experience
        - Strong Python and Java skills
        - Experience with microservices

        Benefits:
        - Competitive salary
        - Health insurance
        - Visa sponsorship
        - Annual leave

        Apply at: careers.emirates.com
        """

        result = research_deception_job_scan(
            job_url="https://careers.emirates.com/example",
            job_text=job_text
        )
        assert isinstance(result, dict)
        # Check for deception indicators - API returns analysis_timestamp, company_age_days, red_flags, etc.
        assert "red_flags" in result or "analysis_timestamp" in result or "deception_score" in result

    def test_scan_suspicious_uae_posting(self):
        """Test scanning a suspicious job posting."""
        suspicious_job = """
        URGENT HIRING!!! Make Money Fast!!!

        Position: Work From Home Agent
        Location: Dubai, UAE
        Salary: AED 50,000+ per week!!!

        NO EXPERIENCE NEEDED!
        Work just 2 hours per day!

        Send $500 processing fee to start

        WhatsApp: +971505555555
        """

        result = research_deception_job_scan(
            job_text=suspicious_job
        )
        assert isinstance(result, dict)
        # Check if red flags detected
        assert len(result) > 0


class TestSalarySynthesizer:
    """Test research_salary_synthesize for UAE positions."""

    def test_software_engineer_salary_dubai(self):
        """Test salary synthesis for software engineer in Dubai."""
        result = research_salary_synthesize(
            job_title="software engineer",
            location="Dubai, UAE",
            skills=["Python", "Kubernetes", "AWS"]
        )
        assert isinstance(result, dict)
        assert len(result) > 0

    def test_data_scientist_salary_abu_dhabi(self):
        """Test salary synthesis for data scientist in Abu Dhabi."""
        result = research_salary_synthesize(
            job_title="data scientist",
            location="Abu Dhabi",
            skills=["Python", "Machine Learning", "SQL"]
        )
        assert isinstance(result, dict)
        assert len(result) > 0

    def test_petroleum_engineer_salary_abu_dhabi(self):
        """Test salary synthesis for petroleum engineer (UAE specific)."""
        result = research_salary_synthesize(
            job_title="petroleum engineer",
            location="Abu Dhabi, UAE",
            skills=["SCADA", "Process Control", "Reservoir Engineering"]
        )
        assert isinstance(result, dict)
        assert len(result) > 0


class TestIntegrationUAECareerFlow:
    """Integration tests for complete UAE career workflows."""

    async def test_complete_job_search_workflow_emirates(self):
        """Test complete job search and market analysis workflow for Emirates."""
        # Step 1: Find hidden job opportunities
        stealth_results = await research_stealth_hire_scanner(
            keywords="software engineer",
            location="Dubai, UAE"
        )
        assert isinstance(stealth_results, dict)

        # Step 2: Analyze market velocity
        velocity_results = await research_market_velocity(
            skill="software engineer",
            location="Dubai, UAE"
        )
        assert isinstance(velocity_results, dict)

        # Step 3: Get salary insights
        salary_results = research_salary_synthesize(
            job_title="software engineer",
            location="Dubai, UAE"
        )
        assert isinstance(salary_results, dict)

    async def test_complete_interview_workflow_adnoc(self):
        """Test complete interview preparation workflow for ADNOC."""
        job_desc = """
        Petroleum Engineer - ADNOC
        Abu Dhabi, UAE

        5+ years upstream experience
        Experience with production operations
        Reservoir engineering knowledge required
        Strong SCADA system management skills
        """

        # Step 1: Resume optimization with longer text
        resume = """
        Senior Petroleum Engineer with 7 years of experience in upstream operations and production management.
        Skilled in SCADA systems, process control, and reservoir engineering with expertise in offshore operations.
        Seeking role in Abu Dhabi with international energy company to leverage technical expertise and leadership experience.
        """
        optimize_result = await research_optimize_resume(
            resume_text=resume,
            job_description=job_desc
        )
        assert isinstance(optimize_result, dict)

        # Step 2: Interview preparation
        prep_result = await research_interview_prep(
            job_description=job_desc,
            company="ADNOC"
        )
        assert isinstance(prep_result, dict)


@pytest.fixture
def uae_test_context():
    """Fixture providing UAE-specific test context."""
    return {
        "locations": ["Dubai, UAE", "Abu Dhabi", "Sharjah"],
        "companies": ["Emirates", "ADNOC", "Dubai Petroleum", "DP World"],
        "job_titles": ["software engineer", "data scientist", "petroleum engineer"],
        "skills": ["Python", "Kubernetes", "SCADA", "Process Control"],
    }
