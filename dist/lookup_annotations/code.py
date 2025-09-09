import json
import requests
from typing import Dict, List

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
    
    def find_data(dataset: str, filters: List[Dict]) -> Dict:
        """Find data from the API"""
                        
        response = requests.post(
            f"{base_url}/api/v1/annotations/search?page_size=100",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {rossum_authorization_token}",
            },
            json={{
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
            }}
        )
        return response.json()
        
    data = find_data(payload["payload"]["dataset"], payload["payload"].get("filters", []))
    options = []
    
    if "message" in data:
        raise Exception(data["message"])

    for result in data["results"]:
        options.append({
            "value": result[payload["payload"]["value_key"]],
            "label": result[payload["payload"]["label_key"]],
        })
    
    return {
        "options": options,
        "value": data["results"][0][payload["payload"]["value_key"]] if data["results"] else None,
    }