import argparse
import json
from pathlib import Path


def build_demo_output(case):
    evidence = case.get("available_evidence", {})
    evidence_used = [key for key in ["ehr_summary", "imaging_summary", "laboratory_summary"] if key in evidence]

    return {
        "case_id": case["case_id"],
        "task": case.get("task", "Surgical planning"),
        "evidence_used": evidence_used,
        "recommendation": {
            "diagnostic_focus": "Displaced femoral neck fracture in an older adult with osteoporosis risk.",
            "management_plan": "Confirm imaging, assess perioperative risk, optimize comorbidities, discuss arthroplasty-based surgical management, and plan early postoperative mobilization.",
            "safety_checks": [
                "Verify patient identity and imaging laterality.",
                "Screen for anticoagulant use and correct reversible bleeding risk.",
                "Document that this is a synthetic demo output and not clinical advice.",
            ],
        },
        "mode": "deterministic_demo",
    }


def main():
    parser = argparse.ArgumentParser(description="Run the deterministic OrthoPilot synthetic demo.")
    parser.add_argument("--input", required=True, help="Path to a synthetic case JSON file.")
    parser.add_argument("--output", required=True, help="Path for the generated output JSON file.")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)

    case = json.loads(input_path.read_text())
    result = build_demo_output(case)
    output_path.write_text(json.dumps(result, indent=2) + "\n")
    print(f"Wrote deterministic demo output to {output_path}")


if __name__ == "__main__":
    main()
