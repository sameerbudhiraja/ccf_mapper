import os
import time
from dotenv import load_dotenv
from pageindex import PageIndexClient
from src.external_controls.ingestion.ec_ingestion import input_file

load_dotenv()

pi_api_key = os.getenv("PAGEINDEX_API_KEY")
if not pi_api_key:
    raise ValueError("PAGEINDEX_API_KEY not found in environment variables.")

# Initialize client
pi_client = PageIndexClient(pi_api_key)

# Submit document
result = pi_client.submit_document(input_file)
doc_id = result["doc_id"]

print(f"Document submitted for indexing. Document ID: {doc_id}")

# Wait for processing
while True:
    status = pi_client.get_document(doc_id)["status"]
    print("Processing status:", status)

    if status == "completed":
        print("File processing completed")
        break

    elif status == "failed":
        raise Exception("Document processing failed")

    time.sleep(5)

# Retrieve tree structure
while True:
    tree_result = pi_client.get_tree(doc_id)

    if tree_result.get("status") == "completed":
        result = tree_result.get("result")

        print("PageIndex Tree Structure:")
        print("result written to ISO27001_2022.txt")

        # Write result to file
        with open("ISO27001_2022.txt", "w") as f:
            f.write(str(result))

        print("Result written to ISO27001_2022.txt")
        break

    print("Tree still building...")
    time.sleep(3)