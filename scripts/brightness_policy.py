"""Record an evidence-based brightness decision. Does not read or edit images."""
import argparse
import json


def decide(purpose, reference_verified=False, match_requested=False):
    if purpose == "unknown":
        return {"method": "preserve", "state": "needs_review",
                "reason": "Confirm purpose before choosing a brightness correction"}
    if reference_verified:
        return {"method": "independent_reference", "state": "ready_for_parameters",
                "reason": "Use verified independent reference, not specimen distribution",
                "quantitative_validation_required": purpose != "appearance"}
    if purpose == "phenotype":
        return {"method": "preserve", "state": "ready",
                "reason": "No verified reference; preserve biological brightness/color differences"}
    if match_requested:
        return {"method": "display_match", "state": "ready_for_parameters",
                "reason": "Appearance-only requested match; not quantitative calibration"}
    return {"method": "preserve", "state": "ready", "reason": "No brightness match requested"}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--purpose', choices=['appearance', 'phenotype', 'unknown'], required=True)
    p.add_argument('--reference-verified', action='store_true')
    p.add_argument('--match-requested', action='store_true')
    args = p.parse_args()
    print(json.dumps({"purpose": args.purpose, **decide(args.purpose, args.reference_verified,
          args.match_requested), "limitation": "Caller verifies purpose and reference; no image inspected"},
          ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
