from pathlib import Path
from typing import List, Optional

import pandas as pd
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel


class SuggestedFix(BaseModel):
    field: str
    sap_value: Optional[str]
    aveva_value: Optional[str]
    drawing_value: Optional[str]
    suggested_value: str
    reasoning: str


class TagRemediation(BaseModel):
    tag: str
    fixes: List[SuggestedFix]
    status: str = "PENDING APPROVAL"


class RemediationReport(BaseModel):
    items: List[TagRemediation]


def load_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    sap = pd.read_csv("data/sample_sap_floc.csv")
    aveva = pd.read_csv("data/sample_aveva.csv")
    drawings = pd.read_csv("data/sample_drawings.csv")
    return sap, aveva, drawings


def find_discrepancies(
    sap: pd.DataFrame,
    aveva: pd.DataFrame,
    drawings: pd.DataFrame,
) -> List[dict]:
    merged = sap.merge(aveva, on="tag", suffixes=("_sap", "_aveva"), how="outer")
    merged = merged.merge(drawings, on="tag", suffixes=("", "_drawing"), how="outer")

    discrepancies = []
    for _, row in merged.iterrows():
        issues = []
        for field in ["description"]:
            sap_val = row.get(f"{field}_sap")
            aveva_val = row.get(f"{field}_aveva")
            drawing_val = row.get(field)
            values = {v for v in [sap_val, aveva_val, drawing_val] if pd.notna(v)}
            if len(values) > 1:
                issues.append({
                    "field": field,
                    "sap_value": sap_val if pd.notna(sap_val) else None,
                    "aveva_value": aveva_val if pd.notna(aveva_val) else None,
                    "drawing_value": drawing_val if pd.notna(drawing_val) else None,
                })
        if issues:
            discrepancies.append({"tag": row["tag"], "issues": issues})

    return discrepancies


PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        "You are a master data specialist for a mining and energy company. "
        "For each discrepancy, suggest the most likely correct value and explain your reasoning. "
        "Prefer values that follow standard engineering naming conventions.",
    ),
    (
        "human",
        "Tag: {tag}\n\nDiscrepancies:\n{issues}",
    ),
])


def suggest_fixes(discrepancies: List[dict]) -> RemediationReport:
    llm = ChatAnthropic(model="claude-sonnet-4-6", max_tokens=4096)
    structured_llm = llm.with_structured_output(RemediationReport)

    all_items = []
    for item in discrepancies:
        issues_text = "\n".join(
            f"- {i['field']}: SAP={i['sap_value']}, AVEVA={i['aveva_value']}, Drawing={i['drawing_value']}"
            for i in item["issues"]
        )
        result: RemediationReport = structured_llm.invoke(
            PROMPT.format_messages(tag=item["tag"], issues=issues_text)
        )
        all_items.extend(result.items)

    return RemediationReport(items=all_items)


def export_to_excel(report: RemediationReport, output_path: str):
    rows = []
    for item in report.items:
        for fix in item.fixes:
            rows.append({
                "tag": item.tag,
                "field": fix.field,
                "sap_value": fix.sap_value,
                "aveva_value": fix.aveva_value,
                "drawing_value": fix.drawing_value,
                "suggested_value": fix.suggested_value,
                "reasoning": fix.reasoning,
                "status": item.status,
            })

    df = pd.DataFrame(rows)
    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Remediation Report", index=False)


def main():
    print("Loading data sources...")
    sap, aveva, drawings = load_data()
    print(f"SAP rows: {len(sap)}, AVEVA rows: {len(aveva)}, Drawing rows: {len(drawings)}")

    print("Comparing sources...")
    discrepancies = find_discrepancies(sap, aveva, drawings)
    print(f"Found {len(discrepancies)} discrepancies")

    print("Generating fix suggestions...")
    report = suggest_fixes(discrepancies)

    Path("outputs").mkdir(exist_ok=True)
    output_path = "outputs/remediation_report.xlsx"
    export_to_excel(report, output_path)
    print(f"\nReport written to {output_path}")
    print(f"{len(report.items)} items pending approval")


if __name__ == "__main__":
    main()
