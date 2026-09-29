import os
import time

from dotenv import load_dotenv
from fastapi import FastAPI
from google import genai
from hindsight_client import Hindsight
from pydantic import BaseModel


# ============================================================
# LOAD ENVIRONMENT VARIABLES
# ============================================================

load_dotenv()


# ============================================================
# GEMINI CLIENT
# ============================================================

api_key = os.getenv("GEMINI_API_KEY")

client = genai.Client(
    api_key=api_key
)


# ============================================================
# HINDSIGHT CLIENT
# ============================================================

hindsight_api_key = os.getenv("HINDSIGHT_API_KEY")

memory = Hindsight(
    base_url="https://api.hindsight.vectorize.io",
    api_key=hindsight_api_key
)

MEMORY_BANK_ID = "opsmemory"


# ============================================================
# FASTAPI APPLICATION
# ============================================================

app = FastAPI(
    title="OpsMemory AI",
    description="AI-powered incident response agent with persistent operational memory",
    version="2.0.0"
)


# ============================================================
# INCIDENT MODEL
# ============================================================

class Incident(BaseModel):

    incident_id: str
    service: str
    severity: str
    error: str
    metrics: str
    deployment: str
    logs: str
    status: str


# ============================================================
# RESOLUTION MODEL
# ============================================================

class Resolution(BaseModel):

    root_cause: str
    action_taken: str
    outcome: str
    recovery_time: str
    engineer_feedback: str


# ============================================================
# TEMPORARY INCIDENT STORAGE
# ============================================================

incidents = []


# ============================================================
# RESOLUTION STORAGE
# ============================================================

resolutions = {}


# ============================================================
# HINDSIGHT MEMORY RECALL
# ============================================================

def recall_similar_incidents(incident: Incident):

    query = f"""
Find previous production incidents similar to this incident.

IMPORTANT:
The current incident is {incident.incident_id}.

Do NOT return memories that belong to the current incident.
Only return experiences from PREVIOUS incidents.

Current incident:

Incident ID: {incident.incident_id}
Service: {incident.service}
Error: {incident.error}
Metrics: {incident.metrics}
Deployment: {incident.deployment}
Logs: {incident.logs}

Focus on:

- similar services
- similar errors
- database or infrastructure problems
- previous root causes
- previous resolutions
- engineer feedback
- what worked
- what did not work

The purpose is to help the engineer learn from previous
operational experience.
"""

    try:

        print()
        print("==============================================")
        print("SEARCHING HINDSIGHT MEMORY")
        print("==============================================")

        result = memory.recall(
            bank_id=MEMORY_BANK_ID,
            query=query
        )

        memories = []

        for item in result.results:

            text = item.text

            # ------------------------------------------------
            # Prevent the current incident from being treated
            # as historical experience.
            # ------------------------------------------------

            if incident.incident_id in text:
                continue

            memories.append(text)

        print(
            f"HISTORICAL MEMORIES FOUND: {len(memories)}"
        )

        return memories

    except Exception as e:

        print(
            "HINDSIGHT RECALL ERROR:",
            repr(e)
        )

        return []


# ============================================================
# GEMINI INVESTIGATION
# ============================================================

def investigate_with_gemini(
    incident: Incident,
    historical_memories: list
):

    # --------------------------------------------------------
    # Convert memories into readable text
    # --------------------------------------------------------

    memory_text = "\n\n".join(
        f"Historical Memory {index + 1}:\n{memory}"
        for index, memory in enumerate(historical_memories)
    )

    if not memory_text:

        memory_text = (
            "No relevant historical incidents were found "
            "in persistent operational memory."
        )


    # --------------------------------------------------------
    # Gemini prompt
    # --------------------------------------------------------

    prompt = f"""
You are OpsMemory AI.

You are an AI incident-response assistant for a production
engineering team.

Your most important capability is persistent operational
memory.

You must investigate the current incident using:

1. Current incident evidence
2. Previous operational experiences retrieved from Hindsight


============================================================
CURRENT INCIDENT
============================================================

Incident ID:
{incident.incident_id}

Service:
{incident.service}

Severity:
{incident.severity}

Error:
{incident.error}

Metrics:
{incident.metrics}

Deployment:
{incident.deployment}

Logs:
{incident.logs}

Status:
{incident.status}


============================================================
PREVIOUS OPERATIONAL EXPERIENCE
============================================================

{memory_text}


============================================================
RESPONSE FORMAT
============================================================

HYPOTHESIS

Explain the most likely cause based on the current evidence.

HISTORICAL EXPERIENCE

Explain whether previous incidents provide useful context.

If previous incidents exist, describe:

- previous root cause
- action taken
- outcome
- recovery time
- engineer feedback

CURRENT EVIDENCE

List the strongest evidence from the current incident.

HISTORICAL SIGNAL

Explain how previous experience supports or conflicts with
the current evidence.

RECOMMENDED INVESTIGATION

Give exactly 3 concrete steps the engineer should perform next.


============================================================
RULES
============================================================

- Never invent facts.
- Do not claim certainty.
- Current evidence is more important than historical memory.
- Historical incidents are supporting evidence, not proof.
- Clearly distinguish current evidence from historical experience.
- The engineer makes the final decision.
- If previous experience conflicts with the current evidence,
  explicitly say so.
"""


    # --------------------------------------------------------
    # Gemini retry logic
    # --------------------------------------------------------

    max_attempts = 3

    for attempt in range(1, max_attempts + 1):

        try:

            print()
            print("==============================================")
            print(
                f"GEMINI ATTEMPT {attempt}/{max_attempts}"
            )
            print("==============================================")


            chat = client.chats.create(
                model="gemini-3.8-flash"
            )


            response = chat.send_message(
                message=prompt
            )


            print("GEMINI SUCCESS")

            return response.text


        except Exception as e:

            print(
                f"GEMINI ERROR ON ATTEMPT {attempt}:",
                repr(e)
            )

            if attempt < max_attempts:

                wait_seconds = attempt * 2

                print(
                    f"Retrying Gemini in "
                    f"{wait_seconds} seconds..."
                )

                time.sleep(wait_seconds)

            else:

                return (
                    "Gemini is temporarily unavailable.\n\n"
                    "Hindsight memory retrieval succeeded.\n\n"
                    f"Historical memories found: "
                    f"{len(historical_memories)}\n\n"
                    +
                    "\n\n".join(
                        f"Historical Memory {index + 1}:\n{memory}"
                        for index, memory
                        in enumerate(historical_memories)
                    )
                )


# ============================================================
# RETAIN INCIDENT EXPERIENCE IN HINDSIGHT
# ============================================================

def retain_incident_experience(
    incident: Incident,
    resolution: Resolution
):

    experience = f"""
PRODUCTION INCIDENT EXPERIENCE

Incident ID:
{incident.incident_id}

Service:
{incident.service}

Severity:
{incident.severity}

Error:
{incident.error}

Metrics:
{incident.metrics}

Deployment:
{incident.deployment}

Logs:
{incident.logs}


ROOT CAUSE:
{resolution.root_cause}


ACTION TAKEN:
{resolution.action_taken}


OUTCOME:
{resolution.outcome}


RECOVERY TIME:
{resolution.recovery_time}


ENGINEER FEEDBACK:
{resolution.engineer_feedback}


OPERATIONAL LESSON:

This incident should be remembered as operational experience.

When a future incident has similar symptoms, use this
experience as supporting evidence.

Do not assume the same root cause automatically.

Compare the current evidence with this historical experience
before recommending an action.
"""

    try:

        print()
        print("==============================================")
        print("RETAINING INCIDENT EXPERIENCE")
        print("==============================================")

        result = memory.retain(
            bank_id=MEMORY_BANK_ID,
            content=experience
        )

        print("HINDSIGHT RETAIN SUCCESS")

        return {
            "success": True,
            "message": "Incident experience stored in Hindsight",
            "memory": experience
        }

    except Exception as e:

        print(
            "HINDSIGHT RETAIN ERROR:",
            repr(e)
        )

        return {
            "success": False,
            "message": "Failed to store incident experience",
            "error": str(e)
        }


# ============================================================
# ROOT ENDPOINT
# ============================================================

@app.get("/")
def root():

    return {
        "message": "OpsMemory AI backend is running!",
        "status": "ok",
        "memory_bank": MEMORY_BANK_ID
    }


# ============================================================
# CREATE INCIDENT
# ============================================================

@app.post("/incidents")
def create_incident(
    incident: Incident
):

    incidents.append(
        incident
    )

    print()
    print(
        f"INCIDENT CREATED: {incident.incident_id}"
    )

    return {
        "message": "Incident received and stored",
        "incident": incident
    }


# ============================================================
# GET ALL INCIDENTS
# ============================================================

@app.get("/incidents")
def get_incidents():

    return {
        "count": len(incidents),
        "incidents": incidents
    }


# ============================================================
# GET SINGLE INCIDENT
# ============================================================

@app.get("/incidents/{incident_id}")
def get_incident(
    incident_id: str
):

    for incident in incidents:

        if incident.incident_id == incident_id:

            return {
                "incident": incident
            }

    return {
        "error": "Incident not found"
    }


# ============================================================
# INVESTIGATE INCIDENT
# ============================================================

@app.post("/incidents/{incident_id}/investigate")
def investigate(
    incident_id: str
):

    print()
    print("==============================================")
    print(
        f"STARTING INVESTIGATION: {incident_id}"
    )
    print("==============================================")


    # --------------------------------------------------------
    # Find incident
    # --------------------------------------------------------

    for incident in incidents:

        if incident.incident_id == incident_id:

            # ------------------------------------------------
            # Recall previous experience
            # ------------------------------------------------

            historical_memories = (
                recall_similar_incidents(
                    incident
                )
            )


            # ------------------------------------------------
            # Gemini investigation
            # ------------------------------------------------

            investigation = (
                investigate_with_gemini(
                    incident,
                    historical_memories
                )
            )


            # ------------------------------------------------
            # Return investigation
            # ------------------------------------------------

            return {

                "incident_id": incident_id,

                "historical_memories_found": (
                    len(historical_memories)
                ),

                "historical_memories": (
                    historical_memories
                ),

                "investigation": (
                    investigation
                )
            }


    return {
        "error": "Incident not found"
    }


# ============================================================
# RESOLVE INCIDENT
# ============================================================

@app.post("/incidents/{incident_id}/resolve")
def resolve_incident(
    incident_id: str,
    resolution: Resolution
):

    print()
    print("==============================================")
    print(
        f"RESOLVING INCIDENT: {incident_id}"
    )
    print("==============================================")


    # --------------------------------------------------------
    # Find incident
    # --------------------------------------------------------

    incident = None

    for item in incidents:

        if item.incident_id == incident_id:

            incident = item
            break


    if incident is None:

        return {
            "error": "Incident not found"
        }


    # --------------------------------------------------------
    # Update incident status
    # --------------------------------------------------------

    incident.status = "resolved"


    # --------------------------------------------------------
    # Store resolution locally
    # --------------------------------------------------------

    resolutions[incident_id] = resolution


    # --------------------------------------------------------
    # Store experience in Hindsight
    # --------------------------------------------------------

    memory_result = retain_incident_experience(
        incident,
        resolution
    )


    # --------------------------------------------------------
    # Return result
    # --------------------------------------------------------

    return {

        "message": "Incident resolved",

        "incident_id": incident_id,

        "status": incident.status,

        "resolution": resolution,

        "hindsight": memory_result
    }


# ============================================================
# GET INCIDENT RESOLUTION
# ============================================================

@app.get("/incidents/{incident_id}/resolution")
def get_resolution(
    incident_id: str
):

    if incident_id not in resolutions:

        return {
            "error": "No resolution found"
        }

    return {

        "incident_id": incident_id,

        "resolution": resolutions[
            incident_id
        ]
    }


# ============================================================
# HINDSIGHT MEMORY TEST
# ============================================================

@app.get("/memory-test/{incident_id}")
def memory_test(
    incident_id: str
):

    print()
    print(
        f"Testing Hindsight memory for: {incident_id}"
    )


    # --------------------------------------------------------
    # Find incident
    # --------------------------------------------------------

    for incident in incidents:

        if incident.incident_id == incident_id:

            result = (
                recall_similar_incidents(
                    incident
                )
            )


            return {

                "incident_id": incident_id,

                "memory_count": len(result),

                "memory_result": result
            }


    return {
        "error": "Incident not found"
    }

