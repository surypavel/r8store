import json
import requests
from typing import Dict, List

# Define the fstring schema
fstring = {
    "oneOf": [
        {
            "type": "string",
        },
        {
            "type": "object",
            "properties": {
                "__fstring": {
                    "type": "string",
                },
            },
        },
    ],
}

def rossum_hook_request_handler(payload:dict):
    variant = payload["variant"]
    configure = payload["configure"]
    settings = payload["settings"]
    form = payload["form"]
    secrets = payload["secrets"]
    hook_interface = payload["hook_interface"]
    
    def aggregate_data(dataset: str, aggregate: List[Dict]) -> Dict:
        """Aggregate data from the API"""
        response = requests.post(
            f"{url}/v1/data/aggregate",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {secrets['token']}",
            },
            json={
                "aggregate": aggregate,
                "collation": {},
                "let": {},
                "options": {},
                "dataset": dataset,
            }
        )
        return response.json()
    
    def find_data(dataset: str, filters: List[Dict]) -> Dict:
        """Find data from the API"""
        find_query = {}
        for filter_item in filters:
            find_query[filter_item["match_key"]] = {
                "$regex": filter_item["value"],
                "$options": "i",
            }
        
        response = requests.post(
            f"{url}/v1/data/find",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {secrets['token']}",
            },
            json={
                "find": find_query,
                "projection": {},
                "skip": 0,
                "limit": 500,
                "sort": {},
                "dataset": dataset,
            }
        )
        return response.json()
    
    def find_datasets() -> Dict:
        """Find available datasets"""
        response = requests.get(
            f"{url}/v2/dataset/",
            headers={
                "Authorization": f"Bearer {secrets['token']}",
            }
        )
        print(response.json())
        return response.json()
    
    # Set default URL
    url = settings.get("url", "https://elis.master.r8.lol/svc/master-data-hub/api")
    
    if variant == "command_show_master_data":
        if form and form.get("dataset"):
            data = find_data(form["dataset"], [])
            results = []
            for result in data["results"]:
                result_copy = result.copy()
                result_copy["id"] = result["_id"]
                results.append(result_copy)
            
            return {
                "intent": {
                    "form": {
                        "width": 600,
                        "defaultValue": {
                            "results": results,
                        },
                        "uiSchema": {
                            "type": "Group",
                            "elements": [
                                {
                                    "type": "Table",
                                    "scope": "#/properties/results",
                                },
                            ],
                        },
                    },
                },
            }
        
        datasets = find_datasets()
        return {
            "intent": {
                "form": {
                    "hook_interface": hook_interface,
                    "schema": {
                        "type": "object",
                        "properties": {
                            "dataset": {
                                "type": "string",
                                "enum": [d["dataset_name"] for d in datasets["datasets"]],
                            },
                        },
                    },
                },
            },
        }
    
    elif variant == "queue_lookup":
        if configure:
            datasets = find_datasets()
            columns = []
            
            if form and form.get("dataset"):
                data = find_data(form["dataset"], [])
                if data["results"]:
                    columns = list(data["results"][0].keys())
            
            return {
                "intent": {
                    "form": {
                        "width": 600,
                        "uiSchema": {
                            "type": "VerticalLayout",
                            "elements": [
                                {
                                    "type": "Control",
                                    "scope": "#/properties/dataset",
                                },
                                {
                                    "type": "Control",
                                    "scope": "#/properties/value_key",
                                },
                                {
                                    "type": "Control",
                                    "scope": "#/properties/label_key",
                                },
                                {
                                    "type": "Control",
                                    "scope": "#/properties/filters",
                                    "options": {
                                        "detail": {
                                            "type": "VerticalLayout",
                                            "elements": [
                                                {
                                                    "type": "Control",
                                                    "scope": "#/properties/match_key",
                                                },
                                                {
                                                    "type": "FString",
                                                    "scope": "#/properties/value",
                                                },
                                            ],
                                        },
                                    },
                                },
                            ],
                        },
                        "schema": {
                            "definitions": {
                                "fstring": fstring,
                            },
                            "type": "object",
                            "properties": {
                                "dataset": {
                                    "type": "string",
                                    "enum": [d["dataset_name"] for d in datasets["datasets"]],
                                },
                                "value_key": {
                                    "type": "string",
                                    "enum": columns,
                                },
                                "label_key": {
                                    "type": "string",
                                    "enum": columns,
                                },
                                "filters": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "match_key": {
                                                "type": "string",
                                                "enum": columns,
                                            },
                                            "value": {
                                                "$ref": "#/definitions/fstring",
                                            },
                                        },
                                    },
                                },
                            },
                        },
                    },
                },
            }
        else:
            data = find_data(payload["dataset"], payload.get("filters", []))
            options = []
            for result in data["results"]:
                options.append({
                    "value": result[payload["value_key"]],
                    "label": result[payload["label_key"]],
                })
            
            return {
                "options": options,
                "value": data["results"][0][payload["value_key"]] if data["results"] else None,
            }
    
    elif variant == "queue_lookup_aggregate":
        if configure:
            datasets = find_datasets()
            return {
                "intent": {
                    "form": {
                        "width": 600,
                        "uiSchema": {
                            "type": "VerticalLayout",
                            "elements": [
                                {
                                    "type": "Control",
                                    "scope": "#/properties/dataset",
                                },
                                {
                                    "type": "Control",
                                    "scope": "#/properties/aggregate",
                                    "options": {
                                        "multi": True,
                                    },
                                },
                            ],
                        },
                        "schema": {
                            "type": "object",
                            "properties": {
                                "dataset": {
                                    "type": "string",
                                    "enum": [d["dataset_name"] for d in datasets["datasets"]],
                                },
                                "aggregate": {
                                    "type": "string",
                                    "description": 'You can use a mongo query aggregation here. You have to finish the pipeline by mapping your desired fields to value/label. Example: [{"$project":{"label":"$country","value":"$country"}}].',
                                },
                            },
                        },
                    },
                },
            }
        else:
            data = aggregate_data(
                payload["dataset"],
                json.loads(payload["aggregate"])
            )
            return {
                "options": data["results"],
                "value": data["results"][0]["value"] if data["results"] else None,
            }