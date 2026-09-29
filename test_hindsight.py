import os

from dotenv import load_dotenv
from hindsight_client import Hindsight


load_dotenv()

api_key = os.getenv("HINDSIGHT_API_KEY")

client = Hindsight(
    base_url="https://api.hindsight.vectorize.io",
    api_key=api_key
)

bank_id = "opsmemory"


print("Creating memory bank...")

try:
    client.create_bank(
        bank_id=bank_id,
        name="OpsMemory AI"
    )
    print("Memory bank created.")

except Exception as e:
    print("Memory bank may already exist.")
    print(e)


print("\nStoring incident memory...")

client.retain(
    bank_id=bank_id,
    content=(
        "Incident INC-001 occurred in payment-api. "
        "The incident involved HTTP 500 errors and database "
        "connection pool exhaustion. Database connection usage "
        "reached 98%. The incident occurred shortly after "
        "payment-service v3.4.1 was deployed. "
        "The investigation suspected a database connection leak "
        "or connection pool configuration issue."
    )
)

print("Memory stored successfully.")


print("\nRecalling memory...")

result = client.recall(
    bank_id=bank_id,
    query="Have we previously experienced a payment API incident involving database connection pool exhaustion?"
)

print("\nMEMORIES FOUND:")

for memory in result.results:
    print("\n---")
    print(memory.text)


client.close()

print("\nHindsight test completed successfully!")