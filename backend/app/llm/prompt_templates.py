"""Prompt templates for LLM interactions."""


RESUME_SCORING_PROMPT = """You are an expert recruiter analyzing resumes.

Your task is to evaluate how well a candidate's resume matches a job description.

**Job Description:**
{job_description}

**Resume:**
{resume_text}

Analyze the resume and provide a structured evaluation with:
1. match_score: An integer from 0-100 indicating overall match quality
2. matching_skills: List of skills from the job description that the candidate has
3. missing_skills: List of required skills from the job description that the candidate lacks
4. experience_match: Boolean indicating if years of experience matches requirements
5. summary: A brief 2-3 sentence summary of the candidate's fit for the role

Be objective and thorough in your analysis."""


RANKING_PROMPT = """You are an expert recruiter ranking candidates for a position.

**Job Description:**
{job_description}

**Candidate: {candidate_name}**

**Resume:**
{resume_text}

Evaluate this candidate and provide:
1. match_score: Integer from 0-100 for overall fit
2. matching_skills: List of relevant skills the candidate possesses
3. missing_skills: List of skills the candidate is missing
4. summary: A concise 2-3 sentence evaluation

Focus on technical skills, experience level, and role fit."""


CHAT_ROUTING_PROMPT = """You are an AI assistant for a resume screening system.

The user has asked: "{user_message}"

Determine the intent and respond appropriately. You can:
1. Search for candidates matching criteria
2. Score a resume against a job description
3. Rank multiple candidates
4. Answer general questions about the system

Categorize the intent as one of:
- "search": User wants to find candidates
- "score": User wants to score a specific resume
- "rank": User wants to rank candidates
- "info": User wants information about the system

Provide a helpful response based on the intent."""


CANDIDATE_SEARCH_PROMPT = """You are helping extract search criteria from a natural language query.

User query: "{query}"

Extract and structure the search criteria:
- required_skills: List of must-have skills
- preferred_skills: List of nice-to-have skills  
- min_years_experience: Minimum years of experience (if mentioned)
- keywords: Other important keywords or requirements

Be precise and extract only what's explicitly mentioned or clearly implied."""


RESUME_SUMMARY_PROMPT = """Analyze this resume and extract key information:

**Resume Text:**
{resume_text}

Provide a structured summary with:
1. candidate_name: Full name of the candidate (if found)
2. skills: List of technical and professional skills mentioned
3. years_experience: Estimated years of professional experience
4. key_qualifications: Top 3-5 qualifications or achievements
5. summary: 2-3 sentence professional summary

Be accurate and extract only information explicitly stated in the resume."""


RESUME_EXTRACTION_PROMPT = """You are an expert resume parser. Extract structured information from the following resume text.

**Resume Text:**
{resume_text}

Extract and return the following information:
1. skills: A comprehensive list of all technical skills, tools, frameworks, programming languages, and professional competencies mentioned in the resume. Include skills from any section (Skills, Technical Skills, Competencies, Technologies, etc.). Return as a list of strings.
2. years_experience: The total years of professional work experience. Calculate from work history, experience section, or any mention of years of experience. If specific dates are given, calculate the difference. If a range is mentioned (e.g., "5+ years"), use the lower bound. Return as an integer. If not determinable, return null.

Be thorough and extract ALL skills mentioned, regardless of which section they appear in. Handle different formats like:
- Bullet lists
- Comma-separated values  
- Paragraph descriptions
- Years mentioned as "2018-2023" or "5 years" or "5+ years experience"

Return only the structured data, nothing else."""
