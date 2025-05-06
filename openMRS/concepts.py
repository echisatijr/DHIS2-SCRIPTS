import csv
import requests

# === Configuration ===
BASE_URL = "http://localhost/openmrs/ws/rest/v1/concept"
USERNAME = "admin"
PASSWORD = "Admin123"
CSV_FILE = f"concepts.csv"

# === Load CSV and Post to OpenMRS ===
with open(CSV_FILE, newline='', encoding='utf-8') as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
        name = row["Name"].strip()
        description = row["Description"].strip()
        concept_class = row.get("Class", "Symptom").strip()
        datatype = row.get("Datatype", "N/A").strip()

        payload = {
            "names": [{
                "name": name,
                "locale": "en",
                "conceptNameType": "FULLY_SPECIFIED"
            }],
            "descriptions": [{
                "description": description,
                "locale": "en"
            }],
            "datatype": datatype,
            "conceptClass": concept_class
        }

        response = requests.post(BASE_URL, json=payload, auth=(USERNAME, PASSWORD))

        if response.status_code == 201:
            print(f"✔️ Created: {name}")
            print(f"Name: {row['Name']}")
            print(f"Description: '{row.get('Description')}'")

        else:
            try:
                error_message = response.json().get('error', {}).get('message', response.text)
            except ValueError:
                error_message = response.text
            print(f"❌ Failed: {name} | status code: {response.status_code} | \n{error_message}")
