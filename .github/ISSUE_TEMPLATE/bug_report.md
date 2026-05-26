name: Bug Report
description: Report a bug to help us improve DASC-Core
title: "[BUG]: "
labels: ["bug", "triage"]
body:
  - type: markdown
    attributes:
      value: |
        Thanks for taking the time to fill out this bug report!
  - type: textarea
    id: what-happened
    attributes:
      label: What happened?
      description: Also tell us what you expected to happen.
      placeholder: Tell us what you see!
    validations:
      required: true
  - type: dropdown
    id: environment
    attributes:
      label: Environment
      options:
        - Node.js (dasc-node)
        - Python (dasc-core)
        - Dashboard (Next.js)
    validations:
      required: true
  - type: textarea
    id: reproduction
    attributes:
      label: Reproduction Steps
      description: How can we reproduce this?
      placeholder: |
        1. cd dasc-node
        2. npm start
        3. ...
    validations:
      required: true
