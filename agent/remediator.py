import anthropic
import pandas as pd
import json

# Load data sources
def load_data():
    sap = pd.read_csv("data/sample_sap_floc.csv")
    aveva = pd.read_csv("data/sample_aveva.csv")
    drawings = pd.read_csv("data/sample_drawings.csv")
    return sap, aveva, drawings

# Compare sources and find discrepancies
def find_discrepancies(sap, aveva, drawings):
    discrepancies = []
    
    # Merge on equipment tag
    merged = sap.merge(aveva, on="tag", suffixes=("_sap", "_aveva"), how="outer")
    merged = merged.merge(drawings, on="tag", suffixes=("", "_drawing"), how="outer")
    
    for _, row in merged.iterrows():
        issues = []
        if row.get("description_sap") != row.get("description_aveva"):
            issues.append({
                "field": "description",
                "sap_value": row.get("description_sap"),
                "aveva_value": row.get("description_aveva")
            })
        if issues:
            discrepancies.append({
                "tag": row["tag"],
                "issues": issues
            })
    
    return discrepancies

# Use Claude to suggest fixes
def suggest_fixes(discrepancies):
    client = anthropic.Anthropic()
    suggestions = []
    
    for item in discrepancies:
        print(f"  Calling API for tag: {item['tag']}")
        
        prompt = f"""
        You are a master data specialist for a mining and energy company.
        
        The following equipment tag has inconsistent data across systems:
        Tag: {item['tag']}
        Issues: {json.dumps(item['issues'], indent=2)}
        
        For each discrepancy, suggest the most likely correct value and explain why.
        You must respond with ONLY a JSON object, no other text, no markdown, no explanation.
        The JSON must look exactly like this:
        {{
            "tag": "tag name",
            "suggested_fixes": [
                {{
                    "field": "field name",
                    "suggested_value": "your suggestion",
                    "reasoning": "why this is correct"
                }}
            ]
        }}
        """
        
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}]
        )
        
        raw = message.content[0].text.strip()
        print(f"  Raw response: {raw[:100]}")
        
        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()
        
        try:
            suggestion = json.loads(raw)
            suggestions.append(suggestion)
            print(f"  Successfully parsed suggestion for {item['tag']}")
        except json.JSONDecodeError as e:
            print(f"  Warning: could not parse response for tag {item['tag']}: {e}")
            print(f"  Full raw response: {raw}")
            continue
    
    return suggestions

# Output report for human approval
def generate_approval_report(discrepancies, suggestions):
    report = []
    for disc, sugg in zip(discrepancies, suggestions):
        report.append({
            "tag": disc["tag"],
            "discrepancies_found": disc["issues"],
            "suggested_fixes": sugg["suggested_fixes"],
            "status": "PENDING APPROVAL"
        })
    
    with open("outputs/remediation_report.json", "w") as f:
        json.dump(report, f, indent=2)
    
    print(f"\nReport generated: {len(report)} items require approval")
    print("Review outputs/remediation_report.json before applying fixes")

# Run the agent
if __name__ == "__main__":
    print("Loading data sources...")
    sap, aveva, drawings = load_data()
    print(f"SAP rows: {len(sap)}, AVEVA rows: {len(aveva)}, Drawing rows: {len(drawings)}")
    
    print("Comparing sources...")
    discrepancies = find_discrepancies(sap, aveva, drawings)
    print(f"Found {len(discrepancies)} discrepancies")
    print(f"Discrepancies: {json.dumps(discrepancies, indent=2)}")
    
    print("\nGenerating fix suggestions...")
    suggestions = suggest_fixes(discrepancies)
    print(f"\nGot {len(suggestions)} suggestions")
    
    if len(suggestions) == 0:
        print("WARNING: No suggestions were generated - check API key and model name")
    else:
        print("\nGenerating approval report...")
        generate_approval_report(discrepancies, suggestions)