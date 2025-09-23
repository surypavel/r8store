import json
import requests
from typing import Dict, List

def rossum_hook_request_handler(payload:dict):
    configure = payload["configure"]
    settings = payload["settings"]
    token = payload["rossum_authorization_token"]


    if configure:
        if token == None:
            return { "intent": { "error": { "message": "Token is missing. Please set a token owner of this hook." } } }

        return {
            "intent": {
                "component": {
                    "name": "simple_data_lookup",
                    "props": {}
                }
            }
        }
    
    def find_data(dataset: str, filters: List[Dict]) -> Dict:
        """Find data from the API"""
        find_filters = []
        search_filters = []
        for filter_item in filters:
            column_name = filter_item["match_key"]
            operator = filter_item.get("operator", "$eq")
            filter_value = filter_item["value"]

            if operator == "$fuzzy_conservative":
                query = str(filter_value)
                search_filters.append(
                    {"text": {"path": column_name, "query": query, "fuzzy": {"maxEdits": 1}, "matchCriteria": "all"}}
                )
            elif operator == "$fuzzy_dynamic":
                query = str(filter_value)
                search_filters.append(
                    {"text": {"path": column_name, "query": query, "fuzzy": {"maxEdits": 2}, "matchCriteria": "all"}}
                )
            else:
                find_filters.append({column_name: {operator: filter_value}})
                
        pipeline: list[dict] = []
        if search_filters:
            pipeline.append({"$search": {"compound": {"must": search_filters}}})

        if find_filters:
            pipeline.append({"$match": {"$and": find_filters}})

        pipeline.append({"$limit": 100})
        
        response = requests.post(
            f"{url}/v1/data/aggregate",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}",
                "X-Rossum-Dev": "true",
            },
            json={
                "aggregate": pipeline,
                "dataset": dataset,
            }
        )
        return response.json()
    
    # Set default URL
    url = settings.get("url", "https://elis.master.r8.lol/svc/master-data-hub/api")

    queries = payload["payload"].get("queries", [])
    
    if len(queries) == 0:
        queries.append({ "filters": [] })

    results = []
    dataset = payload["payload"]["dataset"]
    value_key = payload["payload"]["value_key"]   
    label_key = payload["payload"]["label_key"]

    for query in queries:
        print("query")
        if len(results) == 0:
            data = find_data(dataset, query["filters"])
            results = data["results"]
        else:
            break

    options = []
    
    for result in results:
        options.append({
            "value": result[value_key],
            "label": result[label_key],
        })
    
    return {
        "options": options,
        "value": options[0]["value"] if options else None,
    }