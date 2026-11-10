---
tags: [research, design, accessibility]
date: 2026-11-10
status: partly unverified
---

# Interface design for case work and AI review

Research agent report, 2026-11-10. Read in full: NN/g response times, WCAG target size and use of colour, web.dev vitals, GOV.UK tag and error summary, htmx. Snippet only: PAIR, the automation-bias papers, the "AI look" critiques. Not researched: Carbon, Atlassian, Bloomberg, GOV.UK task list and summary list. Related: [[02-ai-threats-and-controls]], [[05-ankura-solution-sets]].

## Design-system rules

- GOV.UK tags: status as adjectives, fewest statuses needed, sentence case, never colour alone. https://design-system.service.gov.uk/components/tag/
- GOV.UK error summary: at the top of the main content, links to each field, wording matches inline messages. https://design-system.service.gov.uk/components/error-summary/

## Showing AI output a human must check

- Google PAIR: aim for calibrated trust; whether and how to show confidence is a design decision. https://pair.withgoogle.com/chapter/explainability-trust/
- A 2025 review of 35 studies found that explanations and transparency often fail to reduce automation bias (snippet only). https://www.iris.unict.it/retrieve/d096f7ef-6ba2-4684-a598-85fb55228c10/2025_AI%26amp%3bSociety.pdf
- A 2026 paper found explanations raised trust and increased over-reliance (snippet only). https://wiwi.uni-paderborn.de/fileadmin-wiwi/dep3ls7/1-s2.0-S0167923626001107-main.pdf
- Implication: citations alone do not prevent rubber-stamping. The interface needs deliberate friction.

## Accessibility

- Pointer targets at least 24 by 24 CSS px. https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html
- Colour must not be the only means of conveying information. https://www.w3.org/WAI/WCAG22/Understanding/use-of-color.html

## Speed

- 0.1 s feels instant, 1 s keeps thought uninterrupted, 10 s is the attention limit. https://www.nngroup.com/articles/response-times-3-important-limits/
- Core Web Vitals "good": LCP at most 2.5 s, INP at most 200 ms, CLS at most 0.1. https://web.dev/articles/vitals
- htmx: server-returned HTML with declarative attributes. https://htmx.org/essays/hypermedia-driven-applications/

## Proposed rules (the agent's own design, not sourced)

1. Each AI claim is confirmed individually before Approve unlocks.
2. The source passage sits beside the claim, not in a pop-up.
3. No bare confidence percentage. Weak matches get a "check this" flag.
4. Reject requires a reason.
5. Fully keyboard operable, with visible focus.
6. Every status colour is paired with text.
7. Server-rendered fragments, target under 100 ms.
8. Every action is logged with a timestamp.

## Design history

- 2026-11-10: first mockup rejected by the project owner as poor design. A redesign was commissioned from Codex.

See also: [[automation-bias]], [[cognitive-forcing]], [[colour-not-alone]], [[response-time-limits]], [[check-this-flag]], [[accessibility-baseline]], [[server-rendered-fragments]]
