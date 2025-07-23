from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
import httpx

app = FastAPI()

# Environment variables (use python-dotenv in production)
PROFILE_API = "https://sandbox.appleazy.com/api/v1/user"
JOB_API = "https://server.appleazy.com/api/v1/job-listing"
AUTO_APPLY_THRESHOLD = 0.85  # Adjust based on testing

class SwipeRequest(BaseModel):
    user_id: str
    job_id: str
    action: str  # "like" or "pass"

class JobApplication(BaseModel):
    application_id: str
    status: str
    match_score: float

async def fetch_user_profile(user_id: str):
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{PROFILE_API}/get-profile/{user_id}")
        if response.status_code != 200:
            raise HTTPException(status_code=404, detail="User profile not found")
        return response.json()

async def fetch_job_details(job_id: str):
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{JOB_API}?id={job_id}")
        if response.status_code != 200:
            raise HTTPException(status_code=404, detail="Job not found")
        return response.json()[0]  # Assuming first match is correct

def calculate_match_score(user_skills: list[str], job_requirements: list[str]) -> float:
    """Simplified cosine similarity implementation"""
    # In production, use sentence-transformers
    user_skills_set = set(user_skills)
    job_reqs_set = set(job_requirements)
    intersection = user_skills_set.intersection(job_reqs_set)
    return len(intersection) / len(job_reqs_set) if job_reqs_set else 0
@app.post("/api/swipes", response_model=JobApplication)
async def handle_swipe(swipe: SwipeRequest):
    # Validate action
    if swipe.action not in ["like", "pass"]:
        raise HTTPException(status_code=400, detail="Invalid action")
    
    if swipe.action == "pass":
        # Store pass for ML training (pseudo-code)
        # await store_swipe_feedback(swipe.user_id, swipe.job_id, liked=False)
        return {"status": "skipped", "application_id": "", "match_score": 0}
    
    # Get user and job data
    user = await fetch_user_profile(swipe.user_id)
    job = await fetch_job_details(swipe.job_id)
    
    # Calculate match score
    match_score = calculate_match_score(
        user.get("skills", []),
        job.get("requirements", [])
    )
    
    # Auto-apply logic
    if match_score >= AUTO_APPLY_THRESHOLD:
        # Submit application (pseudo-code)
        application_id = await submit_application(
            user_id=swipe.user_id,
            job_id=swipe.job_id,
            resume=user.get("resume"),
            cover_letter=generate_cover_letter(user, job)
        )
        return {
            "application_id": application_id,
            "status": "applied",
            "match_score": match_score
        }
    else:
        # Save to favorites
        # await save_to_favorites(swipe.user_id, swipe.job_id)
        return {
            "application_id": "",
            "status": "saved_for_later",
            "match_score": match_score
        }
async def submit_application(user_id: str, job_id: str, resume: str, cover_letter: str):
    """Replace with actual ATS integration"""
    return f"app_{user_id[:4]}_{job_id[:4]}_{hash(resume[:10])}"

def generate_cover_letter(user: dict, job: dict) -> str:
    """Simplified cover letter generator"""
    return f"""
    Dear {job.get('company', 'Hiring Manager')},
    
    I'm excited to apply for {job.get('title')} at {job.get('company')}.
    My skills in {', '.join(user.get('skills', []))} align well with your needs.
    
    Sincerely,
    {user.get('name')}
    """
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    return JSONResponse(
        status_code=422,
        content={"detail": "Invalid swipe data", "errors": exc.errors()},
    )