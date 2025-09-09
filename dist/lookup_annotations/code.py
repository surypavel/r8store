import requests
from typing import Dict

def rossum_hook_request_handler(payload:dict):
    configure = payload["configure"]
    rossum_authorization_token = payload["rossum_authorization_token"]
    base_url = payload["base_url"]

    if configure:
        return {
            "intent": {
                "component": {
                    "name": "simple_annotation_lookup",
                    "props": {}
                }
            }
        }
    
    def find_data() -> Dict:
        """Find data from the API"""
                        
        response = requests.post(
            f"{base_url}/api/v1/annotations/search?page_size=100&sideload=documents",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {rossum_authorization_token}",
            },
            json={
                "query": {
                    "$and": [
                        {
                            "status": {
                                "$in": [
                                    "to_review",
                                    "reviewing",
                                    "importing",
                                    "failed_import"
                                ]
                            }
                        },
                        {
                            "status": {
                                "$nin": [
                                    "purged",
                                    "created",
                                    "split"
                                ]
                            }
                        }
                    ]
                }
            }
        )
        return response.json()
        
    data = find_data()
    options = []

    for result in data["results"]:
        result["document_ref"] = [doc for doc in data["documents"] if doc['url'] == result["document"]][0]
        result["document__original_file_name"] = result["document_ref"]["original_file_name"]
        options.append({
            "value": str(result[payload["payload"]["value_key"]]),
            "label": str(result[payload["payload"]["label_key"]]),
        })
    
    return {
        "options": options,
        "value": str(data["results"][0][payload["payload"]["value_key"]]) if data["results"] else None,
    }