name: Policy Proposal
description: Propose a new deterministic safety policy for DASC
title: "[POLICY]: "
labels: ["policy-design", "discussion"]
body:
  - type: markdown
    attributes:
      value: |
        DASC thrives on deterministic safety. Please describe the logic for your proposed policy.
  - type: input
    id: industry
    attributes:
      label: Industry / Vertical
      placeholder: e.g. Healthcare, Defense, Finance
    validations:
      required: true
  - type: textarea
    id: logic
    attributes:
      label: Deterministic Logic
      description: Describe the conditional checks (IF/THEN) this policy should enforce.
      placeholder: "IF intent contains 'rm' AND risk_tier < 3 THEN REJECT"
    validations:
      required: true
  - type: textarea
    id: sample-intent
    attributes:
      label: Sample Intent
      description: Provide a JSON example of an intent that should be REJECTED by this policy.
