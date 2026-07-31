"""
Month 1 GitHub issues for Western Union app — Phase 1 Stabilize (first month).
Based on WU_App_6Month_Roadmap.pdf
"""
from __future__ import annotations

ISSUES = [
    {
        "title": "[M1][Trust & Onboarding] Improve KYC document-scanning UX",
        "labels": ["phase-1", "month-1", "trust-onboarding", "priority-p0"],
        "body": """## Need
Users lose trust when identity verification stalls. Improve document-scanning UX so KYC submissions succeed on the first try.

## Scope (Month 1)
- Audit current document capture / crop / glare / blur rejection paths
- Add clear in-camera guidance (frame alignment, lighting, document type)
- Reduce false rejects; surface actionable error copy when a scan fails
- Instrument scan success / retry / abandon rates

## Why
Roadmap Phase 1: KYC delays are the #1 complaint across Play Store / Trustpilot; weeks-long delays were reported.

## Acceptance criteria
- [ ] Document scan guidance shown before capture
- [ ] Top rejection reasons have specific user-facing remediation
- [ ] Scan attempt metrics available in analytics baseline
- [ ] QA checklist covering AU/EU common document types

## Roadmap ref
Phase 1 — Stabilize · Trust & onboarding
""",
    },
    {
        "title": "[M1][Trust & Onboarding] Build visible KYC verification status tracker",
        "labels": ["phase-1", "month-1", "trust-onboarding", "priority-p0"],
        "body": """## Need
Users cannot tell where their verification stands. Add a visible in-app verification status tracker.

## Scope (Month 1)
- Define status model: submitted → in review → action required → approved / rejected
- Surface status on home / send flow when KYC is blocking
- Notify user when status changes or documents are re-requested
- Deep-link from status screen to fix actions (re-upload, contact support)

## Why
Roadmap Phase 1: cut KYC turnaround perception by making progress visible; #1 complaint theme.

## Acceptance criteria
- [ ] Status tracker visible whenever KYC is pending or blocked
- [ ] Each status has plain-language explanation + next step
- [ ] Push/in-app notification on status change (where permitted)
- [ ] Support can see the same status states in tooling notes

## Roadmap ref
Phase 1 — Stabilize · Trust & onboarding
""",
    },
    {
        "title": "[M1][Support] Restore/expand in-app live chat for stuck transfers",
        "labels": ["phase-1", "month-1", "support", "priority-p0"],
        "body": """## Need
Restore or expand in-app live chat for users stuck mid-transfer.

## Scope (Month 1)
- Map entry points: transfer detail, delay banner, failed payout, KYC blocked
- Restore live chat coverage for stuck-transfer intents (hours / corridors TBD with ops)
- Pass transfer context (ID, corridor, status) into the chat session
- Fallback to callback / ticket when agents unavailable

## Why
Roadmap Phase 1: reviews repeatedly cite loss of human agents as a top frustration.

## Acceptance criteria
- [ ] Live chat reachable from stuck-transfer states without leaving the app
- [ ] Agent receives transfer context automatically
- [ ] Offline hours show clear ETA + alternate contact path
- [ ] Chat open rate / resolution metrics captured

## Roadmap ref
Phase 1 — Stabilize · Support
""",
    },
    {
        "title": "[M1][Support] Self-serve “Why is my transfer delayed?” flow",
        "labels": ["phase-1", "month-1", "support", "priority-p0"],
        "body": """## Need
Add a self-serve flow that explains transfer delays and next actions without waiting for an agent.

## Scope (Month 1)
- Detect delayed / pending transfers and offer “Why is this delayed?”
- Explain common causes (compliance hold, payout partner, receiver info, banking hours)
- Show expected next update window when known
- Route to live chat only when self-serve cannot resolve

## Why
Roadmap Phase 1: support gaps amplify KYC/transfer frustration; reduce ticket volume with clarity.

## Acceptance criteria
- [ ] Flow available from transfer status for delayed states
- [ ] Copy covers top delay categories with plain language
- [ ] One-tap escalate to live chat with context
- [ ] Deflection metric: % resolved without agent

## Roadmap ref
Phase 1 — Stabilize · Support
""",
    },
    {
        "title": "[M1][Reliability] Fix cross-border login and account-linking bugs",
        "labels": ["phase-1", "month-1", "reliability", "priority-p0", "bug"],
        "body": """## Need
Fix cross-border login and account-linking failures reported in AU/EU reviews.

## Scope (Month 1)
- Reproduce top login/account-link failures across priority corridors (AU/EU first)
- Fix session restore, MFA edge cases, and multi-country account linking
- Add defensive logging for auth failures (no PII leakage)
- Regression suite for login + link flows on Android

## Why
Roadmap Phase 1 Reliability: explicitly called out in AU/EU Play Store reviews.

## Acceptance criteria
- [ ] Top known login/link bugs from current-state report closed or mitigated
- [ ] Crash-free / success-rate targets defined for auth funnel
- [ ] Automated regression tests for AU/EU login scenarios
- [ ] Release notes document user-visible auth fixes

## Roadmap ref
Phase 1 — Stabilize · Reliability
""",
    },
    {
        "title": "[M1][Reliability] Stabilize Android crash and freeze reports",
        "labels": ["phase-1", "month-1", "reliability", "priority-p0", "bug", "android"],
        "body": """## Need
Reduce Android crash/freeze rate on critical paths (login, KYC, send money).

## Scope (Month 1)
- Triage top crash clusters from Play Vitals / crash reporting
- Fix ANR/freeze hotspots on send + KYC screens
- Add startup and critical-path stability monitoring
- Ship hotfix track for P0 crashes

## Why
Roadmap Phase 1: stabilize Android before any Phase 2 feature investment.

## Acceptance criteria
- [ ] Top N crash clusters addressed or have owners + ETA
- [ ] Play Vitals crash/ANR trend improving week-over-week
- [ ] Critical path (login → KYC → send) smoke tests green on release builds
- [ ] Stability dashboard reviewed in weekly metrics ritual

## Roadmap ref
Phase 1 — Stabilize · Reliability
""",
    },
    {
        "title": "[M1][Instrumentation] Baseline funnel analytics (onboarding, KYC, support)",
        "labels": ["phase-1", "month-1", "instrumentation", "priority-p1"],
        "body": """## Need
Instrument baseline funnel analytics required to prove Phase 1 impact.

## Scope (Month 1)
- Onboarding drop-off by step
- KYC time-to-approve (submitted → approved) + median/p90
- Support ticket volume by category (incl. stuck transfer, KYC, login)
- App-store rating trend weekly snapshot process

## Why
Roadmap Phase 1 Instrumentation: needed before Phase 2 investment; exit metric depends on KYC time -50%.

## Acceptance criteria
- [ ] Dashboard live for onboarding drop-off, KYC TTA, ticket volume by category
- [ ] Definitions documented (event names, start/stop clocks)
- [ ] Weekly review of app-store rating + KYC TTA (cross-cutting rule)
- [ ] Baseline week captured for Phase 1 exit comparison

## Roadmap ref
Phase 1 — Stabilize · Instrumentation
""",
    },
    {
        "title": "[M1][Cross-cutting] Security/compliance gate for Phase 1 releases",
        "labels": ["phase-1", "month-1", "security", "compliance", "priority-p1"],
        "body": """## Need
Every Month 1 release touching auth, KYC, support, or payments ships with SCA/PCI review.

## Scope (Month 1)
- Define lightweight release security checklist for Phase 1 changes
- Review KYC document handling, chat context, and auth logging for compliance
- Block production release if checklist incomplete
- Align with “if rating or KYC TTA regresses, supersede new feature work”

## Why
Roadmap cross-cutting: security & compliance is continuous, not a phase.

## Acceptance criteria
- [ ] Checklist attached to each Phase 1 PR/release
- [ ] KYC/support/auth changes signed off before prod
- [ ] Regression policy documented for rating / KYC TTA
- [ ] Owners named for weekly metric watch

## Roadmap ref
Cross-Cutting, All Six Months · Security & compliance + Headline metrics
""",
    },
]
