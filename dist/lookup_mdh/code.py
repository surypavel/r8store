# flake8: noqa
import json
import re
from typing import Any

import requests


def get_computed_field_suggestion_prompt(
    field_schema_id: str,
    hint: str,
    schema_content: list[dict],
    available_datasets: list[dict],
) -> str:
    fields = ""
    from_scratch = True
    current_field = {}  # Initialize current_field to avoid a potential NameError

    for field in schema_content:
        if field["category"] == "section":
            continue

        field_kind = (
            "header field"
            if field.get("is_header_field", False)
            else "line item"
            if field.get("is_line_item", False)
            else "multivalue"
        )
        is_required = field.get("constraints", {}).get("required", True)
        if field["id"] == field_schema_id:
            current_field = {
                "id": field["id"],
                "label": field["label"],
                "kind": field_kind,
                "datatype": field.get("type"),
                "matching": field.get("matching"),
                "required": is_required,
            }
            from_scratch = not current_field["matching"].get("configuration", {}).get("queries")

        if field_kind != "line item":
            fields += "\n---------"
        fields += f"\nLabel: {field['label']}, ID: {field['id']}, Kind: {field_kind}, Datatype: {field.get('type')}, Required: {is_required} {'(current field)' if field['id'] == field_schema_id else ''}"
        if field_kind == "multivalue":
            fields += "\n*********"

    # Check if current_field was found and has dataset information
    if current_field and not from_scratch:
        existing_aggregate_query = json.dumps(current_field["matching"]["configuration"].get("queries"))
        existing_query_prompt = f"""
        You are to refine the following existing MongoDB aggregation query.
        
        **Existing Query:**
        ```json
        {existing_aggregate_query}
        ```
        
        **Modification Hint:**
        The user wants to modify the query based on this hint: "{hint}".
        """
    else:
        existing_query_prompt = """
        You are to create a new MongoDB aggregation query from scratch.
        """

    prompt = f"""
    Objective:
    Generate a JSON object containing a **Lookup Field** configuration for Rossum AI. This field will perform data lookups from external datasets based on the user query and available fields in the schema. 

    ### Key Instructions:

    1. **Lookup Field Overview**:
        - Uses MongoDB aggregation pipeline for complex data processing
        - Suitable for calculations, grouping, statistical operations, and data lookups

    2. **Field Reference Pattern**:
        - Use TxScript patterns wrapped in `"__formula"` format
        - **Required fields**: `{{"__formula": "field.field_name"}}`
        - **Non-required fields**: `{{"__formula": "default_to(field.field_name, default_value)"}}`
        - **Line item fields**: `{{"__formula": "field.item_field_name.all_values[0]"}}`
        - **Static values**: `{{"__formula": "\\"static_string\\""}}`
        - **Case-insensitive**: `{{"__formula": "default_to(field.field_name, \\"\\").lower()"}}`
        - **Placeholders**: Each placeholder is a TxScript expression stored in `__formula`. Reference in pipelines as `"$$placeholder_name"`
        
        Available fields:
        {fields}

    3. **Dataset Selection**:
        Preselected dataset: {current_field["matching"].get("configuration", {}).get("dataset")}
        Available datasets: {available_datasets}
        
        Choose the most appropriate dataset based on user query and metadata.description.

    4. **Configuration Structure**:
        ```json
        "matching": {{
          "configuration": {{
            "dataset": "Dataset Name",
            "queries": "JSON string of query array, each with '//' comment and 'aggregate' pipeline",
            "placeholders": {{
              "placeholder_name": {{"__formula": "field.field_name"}}
            }}
          }}
        }}
        ```

    5. **MongoDB Aggregation Guidelines**:
        
        **Core Operators**: `$match`, `$group`, `$sum`, `$avg`, `$count`, `$sort`, `$limit`, `$addFields`, `$project`
        
        **Type Casting** (use dataset metadata to determine types):
        - Numbers: `$toDouble` or `$toInt`
        - Dates: `$toDate`
        - Cast columns BEFORE using in aggregations ($sum, $avg, $group, etc.)
        - Example: `{{\\"$addFields\\": {{\\"price_num\\": {{\\"$toDouble\\": \\"$price\\"}}}}}}`
        
        **String Operations**:
        - Pre-compute complex expressions in `$addFields` before using in `$concat` or `$match`
        - WRONG: `{{\\"$concat\\": [\\".*\\", {{\\"$toLower\\": \\"$VAT_ID\\"}}, \\"$$\\"]}}`
        - CORRECT: `{{\\"$addFields\\": {{\\"vat_lower\\": {{\\"$toLower\\": \\"$VAT_ID\\"}}}}}}` first
        - **CRITICAL**: `$replaceAll` find argument MUST be plain string, NOT `$regexFind` result
        - Example (remove spaces): `{{\\"$replaceAll\\": {{\\"input\\": \\"$field\\", \\"find\\": \\" \\", \\"replacement\\": \\"\\"}}}}` ✅
        - Example (remove spaces and dashes - nested):
          ```
          {{\\"$replaceAll\\": {{
            \\"input\\": {{\\"$replaceAll\\": {{\\"input\\": \\"$PO_NUM\\", \\"find\\": \\" \\", \\"replacement\\": \\"\\"}}}},
            \\"find\\": \\"-\\",
            \\"replacement\\": \\"\\"
          }}}}
          ```
        - NEVER: `{{\\"$replaceAll\\": {{..., \\"find\\": {{\\"$regexFind\\": ...}}}}}}` ❌ (returns object, not string)
        
        **Regex Dollar Signs**:
        - Use `$$` (double dollar) for regex end anchor in `$concat`
        - MongoDB interprets `$` as field reference
        - Example: `{{\\"$concat\\": [\\"^\\", \\"DE\\", \\".*\\", \\"$$\\"]}}`
        
        **Placeholder vs Field Reference**:
        - `$$placeholder` = incoming placeholder value (defined in placeholders object)
        - `$field_name` = document field OR field created by `$addFields`
        - Once you create a field via `$addFields` (even from `$$placeholder`), use single `$` to reference it
        - Example:
          ```
          {{\\"$addFields\\": {{\\"sender_vat\\": {{...: \\"$$sender_vat_id\\"}}}}}}
          {{\\"$match\\": {{\\"$expr\\": {{\\"$eq\\": [\\"$vat_id\\", \\"$sender_vat\\"]}}}}}}  // Both single $
          ```

        **Mandatory Final Projection**:
        - Every pipeline MUST end with a `$project` stage.
        - Format: `{{"$project": {{"value": "$value_field", "label": "$label_field"}}}}`
        - `value`: The field used as the identifier/value (required).
        - `label`: The field shown to the user (required).
        - Additional fields: If the user explicitly asks for extra fields to be included in results, add them to the projection (e.g., `{{"$project": {{"value": "$id", "label": "$name", "address": "$address", "phone": "$phone"}}}}`).
        - By default, only include `value` and `label` - do not add extra fields unless specifically requested.
        - If user doesn't specify value/label, choose the most logical fields from the dataset.

    6. **Text Search and Matching Strategy**:
        
        **$search MUST be first stage** - NO `$addFields`, `$match`, or other stages before it
        
        **CRITICAL: Combining Exact Filters with Fuzzy Search**:
        If you need to:
        - Match VAT ID exactly AND fuzzy search on name
        - Filter by status AND fuzzy search
        - Any exact match + fuzzy search combination
        
        You CANNOT do this:
        ❌ `[{{"$match": {{"vat_id": "$$vat"}}}}, {{"$search": {{...}}}}]` ← INVALID! $match before $search
        
        You MUST use compound $search with filter clause:
        ✅ `[{{"$search": {{"compound": {{"must": [{{text fuzzy search}}], "filter": [{{equals: vat_id}}]}}}}}}]`
        
        See Example 2 in section 7 for the exact pattern.
        
        **Decision Tree**:
        
        STEP 1 - Identify field type:
        - **Structured Identifiers**: VAT ID, Tax ID, SKU, account number, order ID, invoice number
        - **Natural Language**: company name, person name, address, product description
        - **Hybrid**: email, phone (structured but can have typos)
        
        STEP 2 - Choose strategy:
        
        **For Structured Identifiers**:
        - ✅ Use exact `$match` with normalization (case-insensitive, trimmed)
        - ❌ AVOID fuzzy `$search` - creates false positives
        - ✅ Fallbacks: Alternative ID fields or format variations
        
        **For Natural Language Text**:
        - ✅ Use fuzzy `$search` with `maxEdits: 1-2`
        - ✅ Reason: Names/addresses have typos, abbreviations, variations
        
        **Critical Heuristics**:
        - **Names**: STRONGLY PREFER fuzzy `$search` over exact match
        - **IDs**: STRONGLY AVOID fuzzy search - a "similar" ID is a DIFFERENT entity
        
        **$search Best Practices**:
        - Always follow with: `{{\\"$addFields\\": {{\\"score\\": {{\\"$meta\\": \\"searchScore\\"}}}}}}`
        - Add score threshold for fuzzy: `{{\\"$match\\": {{\\"score\\": {{\\"$gte\\": 2}}}}}}`
        - Sort by score: `{{\\"$sort\\": {{\\"score\\": -1}}}}`
        - Use non-empty placeholder defaults: `{{"__formula": "default_to(field.name, \\"UNKNOWN\\")"}}`
        - Address matching: Include all address fields in path array, use `maxEdits: 1-2`

    7. **Multiple Queries as Fallbacks (REQUIRED APPROACH)**:
        
        **ALWAYS use multiple simpler queries over single complex pipeline**
        
        Each query object MUST have:
        - `"//"` field: Descriptive comment explaining matching strategy
        - `"aggregate"` field: Array of pipeline stages
        
        **Fallback Strategy by Field Type**:
        
        **Structured Identifiers (VAT ID, SKU, etc.)**:
        ✅ Alternative ID fields: VAT ID → Tax Number → Registration Number
        ✅ Format variations: With country code → without country code
        ❌ NO fuzzy search on same ID field
        
        **Natural Language (Names, Addresses)**:
        ✅ Exact match → Fuzzy (maxEdits:1) → Fuzzy multi-field (maxEdits:2)
        ✅ Single field → Multiple related fields
        
        **Examples**:
        
        ```json
        // Example 1: VAT ID Lookup (exact match only, no $search)
        "queries": "[
          {{\"//\": \"Exact normalized match on VAT ID\", \"aggregate\": [{{\"$addFields\": {{\"vat_norm\": {{\"$toLower\": {{\"$trim\": {{\"input\": \"$VAT_ID\"}}}}}}, \"search_norm\": {{\"$toLower\": {{\"$trim\": {{\"input\": \"$$sender_vat\"}}}}}}}}}}, {{\"$match\": {{\"$expr\": {{\"$eq\": [\"$vat_norm\", \"$search_norm\"]}}}}}}, {{\"$limit\": 5}}, {{\"$project\": {{\"value\": \"$VAT_ID\", \"label\": \"$entity_name\"}}}}]}},
          {{\"//\": \"Exact match on Tax Number\", \"aggregate\": [{{\"$match\": {{\"tax_number\": \"$$sender_tax\"}}}}, {{\"$limit\": 5}}, {{\"$project\": {{\"value\": \"$tax_number\", \"label\": \"$entity_name\"}}}}]}}
        ]"
        ```
        
        ```json
        // Example 2: Exact VAT ID + Fuzzy Name (CORRECT: use compound $search with filter)
        "queries": "[
          {{\"//\": \"Exact VAT match with exact name\", \"aggregate\": [{{\"$match\": {{\"vat_id\": \"$$vat\", \"entity_name\": \"$$name\", \"status\": \"Active\"}}}}, {{\"$limit\": 5}}, {{\"$project\": {{\"value\": \"$vat_id\", \"label\": \"$entity_name\"}}}}]}},
          {{\"//\": \"Fuzzy name with VAT and status filters in compound search\", \"aggregate\": [
            {{\"$search\": {{\"compound\": {{\"must\": [{{\"text\": {{\"path\": \"entity_name\", \"query\": \"$$name\", \"fuzzy\": {{\"maxEdits\": 1}}}}}}], \"filter\": [{{\"equals\": {{\"path\": \"vat_id\", \"value\": \"$$vat\"}}}}, {{\"equals\": {{\"path\": \"status\", \"value\": \"Active\"}}}}]}}}}}},
            {{\"$addFields\": {{\"score\": {{\"$meta\": \"searchScore\"}}}}}},
            {{\"$sort\": {{\"score\": -1}}}},
            {{\"$limit\": 5}},
            {{\"$project\": {{\"value\": \"$vat_id\", \"label\": \"$entity_name\"}}}}
          ]}}
        ]"
        ```
        
        ```json
        // Company Name Lookup
        "queries": "[
          {{\"//\": \"Exact match on company name\", \"aggregate\": [{{\"$match\": {{\"company_name\": \"$$company_name\"}}}}, {{\"$limit\": 5}}, {{\"$project\": {{\"value\": \"$company_name\", \"label\": \"$company_name\"}}}}]}},
          {{\"//\": \"Fuzzy match on company name\", \"aggregate\": [{{\"$search\": {{\"text\": {{\"path\": \"company_name\", \"query\": \"$$company_name\", \"fuzzy\": {{\"maxEdits\": 1}}}}}}}}, {{\"$addFields\": {{\"score\": {{\"$meta\": \"searchScore\"}}}}}}, {{\"$match\": {{\"score\": {{\"$gte\": 2}}}}}}, {{\"$sort\": {{\"score\": -1}}}}, {{\"$limit\": 5}}, {{\"$project\": {{\"value\": \"$company_name\", \"label\": \"$company_name\"}}}}]}},
          {{\"//\": \"Fuzzy match across name fields\", \"aggregate\": [{{\"$search\": {{\"text\": {{\"path\": [\"company_name\", \"legal_name\"], \"query\": \"$$company_name\", \"fuzzy\": {{\"maxEdits\": 2}}}}}}}}, {{\"$addFields\": {{\"score\": {{\"$meta\": \"searchScore\"}}}}}}, {{\"$match\": {{\"score\": {{\"$gte\": 1.5}}}}}}, {{\"$sort\": {{\"score\": -1}}}}, {{\"$limit\": 10}}, {{\"$project\": {{\"value\": \"$company_name\", \"label\": \"$legal_name\"}}}}]}}
        ]"
        ```
        
        **Guidelines**:
        - Order by confidence: Most reliable matches first
        - Keep each query simple: ONE clear strategy per query
        - Appropriate limits: Exact (1-5), fuzzy (5-10)
        - When NOT to use multiple queries: Aggregations needing all data (sum, average, group by)
        - Ensure final projection includes `value` and `label` (plus any additional fields if user requested them).

    8. **Summary with HTML Formatting**:
        - Use `<span class="field">Field Name</span>` for field references
        - Use `<span class="value">Dataset Name</span>` for dataset names
        - Use `<span class="operation">Operation</span>` for operations

    ### Lookup Field Information:
    You are configuring: Label="{current_field["label"]}", Type={current_field["datatype"]}, Kind={current_field["kind"]}.

    ### User Query:
    "{hint}"
    
    {existing_query_prompt}

    ### PRE-GENERATION CHECKLIST (Review BEFORE generating):
    
    Does the user want:
    - "Exact [field] match AND fuzzy search on [other field]"?
    - "VAT ID match with name search"?
    - "Filter by status AND search by name"?
    
    If YES to any above → You need compound $search with filter clause (see Example 2)
    DO NOT put $addFields/$match before $search - this will fail!
    
    ### Output Format:
    ```json
    {{
      "name": "Descriptive name of the lookup operation",
      "summary": "Brief summary using HTML formatting",
      "matching": {{
        "configuration": {{
          "dataset": "Selected Dataset Name",
          "queries": "[{{\"//\": \"Comment\", \"aggregate\": [...]}}]",
          "placeholders": {{
            "name": {{"__formula": "default_to(field.name, \\"\\")"}}
          }}
        }}
      }},
      "valid": true
    }}
    ```

    ### MANDATORY PRE-SUBMISSION VALIDATION:
    Before outputting, CHECK EVERY PIPELINE:
    1. **$search position**: For EACH aggregate array, if it contains $search anywhere, verify $search is at position [0]. If you see ANY stage before $search (like $addFields, $match, $project), the pipeline is INVALID and will fail in MongoDB.
    2. **Exact filter + fuzzy search**: If user wants "exact VAT match AND fuzzy name", you MUST use compound $search with filter clause OR separate query objects. You CANNOT put $match before $search.
    3. **$replaceAll find parameter**: Check that EVERY `$replaceAll` has a plain string in the `find` field. If you see `$regexFind` or any operator inside `find`, it's INVALID.
    4. **Query comments**: Each query has `"//"` field with descriptive comment
    5. **Placeholder defaults**: Non-empty values for $search placeholders (not "")
    6. **Field vs Variable**: `$$placeholder` for incoming values, `$field` for document/created fields
    7. **Type casting**: Columns cast to correct types before aggregations
    8. **Final Projection**: EVERY pipeline MUST end with `{{\"$project\": {{\"value\": \"...\", \"label\": \"...\"}}}}`
    9. **No fuzzy on IDs**: ID fields use exact match or alternative ID fallbacks, NOT fuzzy search
    10. **Field name accuracy**: Match dataset schema exactly (case-sensitive, spaces)
    
    **Common Violations**:
    - WRONG: Trying to filter exact VAT ID then fuzzy search name:
      `[{{"$match": {{"vat_id": "$$vat"}}}}, {{"$search": {{...}}}}]` ← $match before $search = INVALID
    - CORRECT: Use compound $search (see Example 2):
      `[{{"$search": {{"compound": {{"must": [...], "filter": [{{"equals": {{"path": "vat_id", "value": "$$vat"}}}}]}}}}}}]`
    - WRONG: `[{{\"$addFields\": ...}}, {{\"$search\": ...}}]`
    - CORRECT: `[{{\"$search\": ...}}, {{\"$addFields\": ...}}]`
    - WRONG: Missing `"//"` comment
    - WRONG: `$regexFind` in `$replaceAll` find:
      `{{\\"$replaceAll\\": {{\\"input\\": \\"$field\\", \\"find\\": {{\\"$regexFind\\": {{...}}}}, \\"replacement\\": \\"\\"}}}}` ← Returns object!
    - CORRECT: Plain string in find:
      `{{\\"$replaceAll\\": {{\\"input\\": \\"$field\\", \\"find\\": \\" \\", \\"replacement\\": \\"\\"}}}}` ← String literal
    - WRONG: Fuzzy search on ID: `{{\"$search\": {{\"text\": {{\"path\": \"vat_id\", \"fuzzy\": {{\"maxEdits\": 2}}}}}}}}`
    - CORRECT: Alternative ID fallback instead
    - WRONG: Empty default in $search: `{{"__formula": "default_to(field.name, \\"\\")"}}` 
    - CORRECT: `{{"__formula": "default_to(field.name, \\"UNKNOWN\\")"}}`
    - WRONG: Missing final projection or wrong keys.
    - CORRECT: `[..., {{"$project": {{\"value\": \"$id\", \"label\": \"$name\"}}}}]`
    
    If ANY checks fail, revise before outputting.
    
    **Provide only the JSON.**
    """

    return prompt


def get_computed_field_summary_prompt(
    field_schema_id: str,
    schema_content: list[dict],
) -> str:
    fields = ""
    for field in schema_content:
        if field["category"] == "section":
            continue

        field_kind = (
            "header field"
            if field.get("is_header_field", False)
            else "line item"
            if field.get("is_line_item", False)
            else "multivalue"
        )
        is_required = field.get("constraints", {}).get("required", True)
        if field["id"] == field_schema_id:
            current_field = {
                "id": field["id"],
                "label": field["label"],
                "kind": field_kind,
                "datatype": field.get("type"),
                "matching": field.get("matching"),
                "required": is_required,
            }

        if field_kind != "line item":
            fields += "\n---------"
        fields += f"\nLabel: {field['label']}, ID: {field['id']}, Kind: {field_kind}, Datatype: {field.get('type')}, Required: {is_required} {'(current field)' if field['id'] == field_schema_id else ''}"
        if field_kind == "multivalue":
            fields += "\n*********"

    prompt = f"""
Analyze MongoDB aggregation pipelines and create concise, business-friendly summaries.

**Input:** JSON array of query objects with `"aggregate"` key containing aggregation stages.

**Output:** JSON object with `summary` key - a list of lists. Each inner list describes one query's business operations.

**WRITING RULES:**

1. **Start with action verbs:**
   - **Search** - fuzzy/Atlas search
   - **Filter** - exact matching
   - **Calculate** - aggregations
   - **Merge** - combining datasets
   - **Transform** - data reshaping

2. **Keep it simple:**
   - Use "typo-tolerant" not "fuzzy"
   - Focus on what, not how
   - Example: "Search vendors matching VAT ID with typo-tolerance, top 5 results"

**GROUPING RULES:**

1. **Minimum 2 summaries per query** - Only use 1 summary for extremely simple cases
2. Split when business purpose changes (exact vs. fuzzy, search vs. filter)
3. Group technical steps (scoring, sorting, limiting) with their main action

**COMMON PATTERNS:**

- Fuzzy search: "Search [entity] matching [fields] with typo-tolerance, top N results"
- Exact match: "Filter [entity] where [field] matches [value]"
- Priority filter: "Filter top N results, prioritizing [condition]"
- Aggregation: "Calculate [metric] per [group]"
- Merge: "Merge with [collection]"
- Add ", ensuring unique entries" for deduplication

**OUTPUT:**

1. **lines:** [start, end] line numbers (1-indexed from first `[`)
2. **summary:** Short action-verb description
3. **HTML tags:**
   - `<span class="field">Field</span>` for field names
   - `<span class="value">Value</span>` for values
   - `<span class="operation">Op</span>` for operations

**Return ONLY valid JSON.**

---
Here is the JSON schema to follow:

{{
  "summary": [
    [
      {{
        "lines": [
          "integer",
          "integer"
        ],
        "summary": "string"
      }},
      ...
    ],
    [
      {{
        "lines": [
          "integer",
          "integer"
        ],
        "summary": "string"
      }},
      ...
    ]
  ]
}}

---
**Example:**

Input: Query matching status + calculating totals per product
Output:
```json
{{
  "summary": [
    [
      {{
        "lines": [4, 9],
        "summary": "Filter records where <span class=\"field\">Status</span> is <span class=\"value\">completed</span>"
      }},
      {{
        "lines": [10, 25],
        "summary": "Calculate total quantity per <span class=\"field\">Product</span>, highest first"
      }}
    ]
  ]
}}
```

**Quick Tips:**

✅ Good: "Search vendors matching <span class=\"field\">Name</span> with typo-tolerance, top 5 results"
✅ Good: "Filter entities where VAT ID matches sender's VAT ID"
✅ Good: "Merge with <span class=\"value\">production vendors</span>, ensuring unique entries"

❌ Avoid: "Look for entities..." (wrong verb), technical jargon, unnecessary details

---
Now, analyze the following MongoDB aggregation query and provide the summary in the specified format.

Dataset: {str(current_field["matching"]["configuration"].get("dataset", "None"))}

MongoDB aggregation query:

{str(current_field["matching"]["configuration"].get("queries", ""))}
"""

    return prompt


def get_organization(payload: dict) -> dict:
    response = requests.get(
        f"{payload['base_url']}/api/v1/organizations",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {payload['rossum_authorization_token']}",
        },
    )

    response.raise_for_status()
    return response.json()["results"][0]


def get_master_data_hub_credentials(payload: dict) -> tuple:
    is_api_develop = payload["base_url"].startswith("https://elis.develop.r8.lol") or payload["base_url"].startswith(
        "https://api.elis.develop.r8.lol"
    )
    is_api_review = bool(re.match(r"^https://review-ac-elis-backend-\d+\.review\.r8\.lol", payload["base_url"]))

    if is_api_develop:
        return (f"https://elis.master.r8.lol/svc/master-data-hub/api", payload["rossum_authorization_token"], "true")
    elif is_api_review:
        organization = get_organization(payload)
        return (
            "https://elis.master.r8.lol/svc/master-data-hub/api",
            organization["metadata"].get("mdh_master_token"),
            "",
        )
    else:
        return (f"{payload['base_url']}/svc/master-data-hub/api", payload["rossum_authorization_token"], "")


def rossum_hook_request_handler(payload: dict) -> dict:
    variant = payload["variant"]
    configure = payload["configure"]

    url, token, is_dev = get_master_data_hub_credentials(payload)

    messages = []

    def aggregate_data(dataset: str, aggregate: list[dict]) -> dict:
        """Aggregate data from the API"""
        response = requests.post(
            f"{url}/v1/data/aggregate",
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}", "X-ROSSUM-DEV": is_dev},
            json={
                "aggregate": aggregate,
                "collation": {},
                "let": {},
                "options": {},
                "dataset": dataset,
            },
        )

        response.raise_for_status()
        return response.json()

    def filters_to_mongo_pipeline(sort: dict, limit: int, filters: list[dict]) -> list[dict]:
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

        if sort_key := sort.get("sort_key", None):
            pipeline.append({"$sort": {sort_key: -1 if sort["desc"] else 1}})

        pipeline.append({"$limit": limit})

        return pipeline

    def find_tables() -> list[dict]:
        """Find available tables"""
        response = requests.get(
            f"{url}/v2/datasets/metadata", headers={"Authorization": f"Bearer {token}", "X-ROSSUM-DEV": is_dev}
        )

        response.raise_for_status()
        return response.json()

    if variant == "queue_lookup":
        if configure:
            if token == None:
                return {"intent": {"error": {"message": "Token is missing. Please set a token owner of this hook."}}}

            return {"intent": {"component": {"name": "simple_lookup", "props": {}}}}
        else:
            queries = payload["payload"].get("queries", [])
            sort = payload["payload"].get("sort", {"sort_key": "", "desc": False})
            limit = min(int(payload["payload"].get("limit", 100)), 100)

            if len(queries) == 0:
                queries.append({"filters": []})

            results: list = []

            dataset = payload["payload"]["dataset"]
            value_key = payload["payload"]["value_key"]
            label_key = payload["payload"]["label_key"]

            for query in queries:
                if len(results) == 0:
                    pipeline = filters_to_mongo_pipeline(sort, limit, query["filters"])
                    data = aggregate_data(dataset, pipeline)
                    results = data["results"]
                else:
                    break

            options: list[dict[str, Any]] = []

            for result in results:
                options.append(
                    {
                        "value": str(result[value_key]),
                        "label": str(result[label_key]),
                    }
                )

            return {
                "options": options,
                "value": options[0]["value"] if options else None,
            }

    elif variant == "queue_lookup_aggregate":
        if configure:
            variant_payload = payload.get("payload", None)

            suggest_prompt = (
                get_computed_field_suggestion_prompt(
                    variant_payload["field_schema_id"],
                    variant_payload["hint"],
                    variant_payload["schema_content"],
                    find_tables(),
                )
                if variant_payload and ("hint" in variant_payload)
                else None
            )

            summary_prompt = (
                get_computed_field_summary_prompt(
                    variant_payload["field_schema_id"],
                    variant_payload["schema_content"],
                )
                if variant_payload
                else None
            )

            return {
                "intent": {
                    "suggest_prompt": suggest_prompt,
                    "summary_prompt": summary_prompt,
                    "component": {"name": "complex_lookup", "props": {}},
                }
            }
        else:

            def _replaces(value: Any, placeholders: dict) -> Any:
                if isinstance(value, dict):
                    return {k: _replaces(v, placeholders) for k, v in value.items()}
                if isinstance(value, list):
                    return [_replaces(v, placeholders) for v in value]

                if isinstance(value, str) and value.startswith("$$"):
                    placeholder = value[2:]
                    if placeholder in placeholders:
                        return placeholders[placeholder]

                return value

            queries = payload["payload"].get("queries", None)
            value_key = payload["payload"].get("value_key", None)
            label_key = payload["payload"].get("label_key", None)

            if not queries:
                messages.append({"type": "error", "id": "all", "content": "Aggregation queries pipeline is missing."})
                return {
                    "options": [],
                    "value": None,
                    "messages": messages,
                }

            try:
                queries = json.loads(queries)
            except Exception as e:
                messages.extend(
                    [
                        {"type": "error", "id": "all", "content": str(e)},
                        {"type": "error", "id": "all", "content": queries},
                    ]
                )
                return {
                    "options": [],
                    "value": None,
                    "messages": messages,
                }

            placeholders = payload["payload"].get("placeholders", [])

            for placeholder in placeholders:
                # Handle both string and object formats for placeholders
                if isinstance(placeholders[placeholder], dict) and "__formula" in placeholders[placeholder]:
                    placeholders[placeholder] = placeholders[placeholder]["__formula"]
                # If it's already a string, keep it as is

            for query_index, query in enumerate(queries):
                if not (aggregate := query.get("aggregate")):
                    messages.append(
                        {"type": "info", "id": "all", "content": f"Non-aggregate queries are not supported: {query}"}
                    )
                    continue

                agg = _replaces(aggregate, placeholders)

                # messages.append({"type": "info", "id": "all", "content": str(agg)})

                data = aggregate_data(payload["payload"]["dataset"], agg)

                if "message" in data:
                    messages.append({"type": "error", "id": "all", "content": data["message"]})
                    continue

                if not data.get("results"):
                    # messages.append({"type": "info", "id": "all", "content": str(data)})
                    continue

                options = []
                for result in data["results"]:
                    if "value" in result and "label" in result:
                        struct: dict[str, Any] = {
                            **{k: v for k, v in result.items() if k not in ("value", "label")},
                            "__query_index": query_index,
                        }
                        options.append(
                            {
                                "value": result["value"],
                                "label": result["label"],
                                "struct": struct,
                            }
                        )
                    elif value_key in result and label_key in result:
                        options.append(
                            {
                                "value": result[value_key],
                                "label": result[label_key],
                            }
                        )

                selected = options[0]
                if selected:
                    return {
                        "options": options,
                        "value": selected.get("value"),
                        "struct": selected.get("struct"),
                        "messages": messages,
                    }

                # messages.append(
                #     {"type": "warning", "id": "all", "content": f"No value match in the results: {data['results']}"}
                # )

            # messages.append({"type": "warning", "id": "all", "content": "No query produced any results"})

            return {
                "options": [],
                "value": None,
                "struct": {},
                "messages": messages,
            }

    raise NotImplementedError
