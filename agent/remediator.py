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
        prompt = f"""
        You are a master data specialist for a mining and energy company.
        
        The following equipment tag has inconsistent data across systems:
        Tag: {item['tag']}
        Issues: {json.dumps(item['issues'], indent=2)}
        
        For each discrepancy, suggest the most likely correct value and explain why.
        Respond in JSON format like this:
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
            model="claude-opus-4-5",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}]
        )
        
        suggestion = json.loads(message.content[0].text)
        suggestions.append(suggestion)
    
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
    
    print(f"Report generated: {len(report)} items require approval")
    print("Review outputs/remediation_report.json before applying fixes")

# Run the agent
if __name__ == "__main__":
    print("Loading data sources...")
    sap, aveva, drawings = load_data()
    
    print("Comparing sources...")
    discrepancies = find_discrepancies(sap, aveva, drawings)
    print(f"Found {len(discrepancies)} discrepancies")
    
    print("Generating fix suggestions...")
    suggestions = suggest_fixes(discrepancies)
    
    print("Generating approval report...")
    generate_approval_report(discrepancies, suggestions)