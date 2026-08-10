---
name: Feature request
about: Propose an implementation-ready Track Session Timer feature
title: ''
labels: NewFeature
assignees: ''
---

<!--
Use an action-oriented title, for example:
"Add a guided Launch Mode calibration wizard"

If applicable, add "Parent: #123" above the Summary. New feature work
normally belongs beneath roadmap epic #23, either directly or through a
focused parent issue.
-->

## Summary

<!--
Describe the capability, the user problem or opportunity it addresses, and
the intended outcome. Keep this understandable without implementation detail.
-->

## User experience

<!--
Describe what the driver sees and how they interact with the feature. Include
entry and exit behavior, gestures, prompts, display layout, colours, and saved
choices where relevant. Account for the 240x240 circular display.
-->

## Functional behavior

<!--
Define the required rules and state transitions precisely. Include defaults,
configuration values, persistence, reset/cancel behavior, and explicit scope
boundaries. Use subsections when the feature has distinct parts.
-->

## Hardware, safety, and compatibility

<!--
Cover relevant RP2040, LCD, touchscreen, IMU, battery, memory, and timing
constraints. State how peripheral failure or missing hardware must degrade.
Protect active track/rest sessions from accidental interruption. Describe any
configuration migration or backward-compatibility requirements.
-->

## Acceptance criteria

<!--
Replace the prompts below with observable, testable outcomes. Add or remove
items to fit the feature, while retaining applicable safety and validation
coverage.
-->

- [ ] <!-- Primary user-visible behavior works as described. -->
- [ ] <!-- Entry, exit, cancel, reset, and persistence behavior is verified. -->
- [ ] <!-- Failure and degraded-mode behavior is safe and actionable. -->
- [ ] <!-- Existing configuration and functionality remain compatible. -->
- [ ] <!-- Host-side tests cover logic, boundaries, and failure paths. -->
- [ ] <!-- The feature is exercised on supported physical hardware. -->

## Documentation

<!--
List required README, User Guide, installation, configuration, gesture, or
troubleshooting updates. Remove this section only when no user-facing or
maintainer-facing behavior changes.
-->

- [ ] Documentation is updated for the new behavior and configuration.

## Relationship

<!--
Identify the parent issue or roadmap epic, dependencies, related issues, and
features explicitly left for later. Example:

This is a focused deliverable beneath #49. Low-battery warnings and broader
power-saving behavior remain tracked by the parent issue.
-->
