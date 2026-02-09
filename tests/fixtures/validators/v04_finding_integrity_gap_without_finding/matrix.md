| Req ID | Normative Requirement | Source | Owner | Enforcement Type | Enforcement Point | VS Code Implementation | Data Fields | Telemetry Proof | Test | Status | Finding |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| R-1 | Validate inputs | RFC 1.0:L3 | Intake Classifier | hard gate | intake boundary | prompt file | UserRequest.context | intake.classify | Test-1 | gap | - |
| R-2 | Record outputs | RFC 1.0:L4 | Output Controller | hard gate | emission | output gate | AssistantResponse.answer | execute.respond | Test-2 | covered | - |
