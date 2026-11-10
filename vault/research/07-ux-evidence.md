---
tags: [research, design, evidence]
date: 2026-11-10
status: partly unverified
---

# Evidence for the interface choices

Research agent report, 2026-11-10. This note ties each interface choice to a source, and says where the evidence is against us or missing. Quotes came through a page-extraction tool, so re-check the wording at the URL before quoting in the deck or the technical sheet. Related: [[06-interface-design]], [[02-ai-threats-and-controls]].

"Read" means the page was read in full. Anything else is UNVERIFIED and must not be stated as fact.

## Choices the evidence supports

| Choice | Evidence | Source | Read |
|---|---|---|---|
| Dashboard figures readable at a glance | Dashboards should be "consumed fast, with a minimum of interaction or cognitive processing" | https://www.nngroup.com/articles/dashboards-preattentive/ | yes |
| Bars, not pies or gauges | People "are quite adept at estimating how lengths compare"; pie and donut charts "should be avoided most of the time" | same | yes |
| Left-side navigation | Vertical navigation "supports more efficient scanning than horizontal navigation" and suits navigation "likely to grow" | https://www.nngroup.com/articles/vertical-nav/ | yes |
| Remove what is not needed | "Removing nonessential elements can be equally or even more effective at making important information visually salient." | https://www.nngroup.com/articles/complex-application-design/ | yes |
| Status never by colour alone | WCAG 1.4.1: "Color is not used as the only visual means of conveying information" | https://www.w3.org/WAI/WCAG22/Understanding/use-of-color.html | yes |
| Text contrast | WCAG 1.4.3: "at least 4.5:1", large text "at least 3:1" | https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html | yes |
| Speed target under 100 ms | 0.1 s is "about the limit for having the user feel that the system is reacting instantaneously" | https://www.nngroup.com/articles/response-times-3-important-limits/ | yes |
| Sortable tables with aids for keeping your place | Row aids help users "keep their place as they move their eyes across the table" | https://www.nngroup.com/articles/data-tables/ | yes |
| No "Are you sure?" on routine actions | "if you warn people too much, they stop paying attention"; reflexive confirmation "provides no protection at all" | https://www.nngroup.com/articles/confirmation-dialog/ | yes |
| Easy correction of AI output | Guidelines for Human-AI Interaction, G9: "Support efficient correction." | https://www.microsoft.com/en-us/research/articles/guidelines-for-human-ai-interaction/ | summary page |

## Choices where the evidence is mixed or against us

**Left navigation has a cost.** The same NN/g article says it has a "lower content-to-chrome ratio than horizontal navigation". We accept the cost because the product has seven sections and the Case view can collapse the navigation.

**The heatmap encodes magnitude in colour.** NN/g says "color should not be used to communicate information about quantitative values or magnitude". The owner's reference design uses a heatmap. Decision: keep one heatmap for the weekday-by-hour arrival pattern, where the shape matters and not exact values, print the count in each cell or on hover and focus, and use bars wherever a value must be read accurately.

**Citations and explanations do not prevent rubber-stamping.** Bansal et al. found "explanations increased the chance that humans will accept the AI's recommendation, regardless of its correctness" (https://arxiv.org/abs/2006.14779, abstract only). So showing the source beside each claim is not enough on its own.

**Per-claim confirmation is supported only by inference.** Buçinca, Malaya and Gajos found "cognitive forcing significantly reduced overreliance compared to the simple explainable AI approaches" (https://arxiv.org/abs/2102.09692, abstract only). Their experiment did not test per-claim confirmation, so our control is an application of the principle, not a tested design. Known costs: "people assigned the least favorable subjective ratings to the designs that reduced the overreliance the most", and the benefit was smaller for some people. A further risk, by analogy with the confirmation-dialog finding above, is that confirming becomes a reflex. This is stated as a limitation, and measuring it with real handlers is the first thing a pilot would do.

**A good-looking interface can hide problems.** NN/g's account of the aesthetic-usability effect (Kurosu and Kashimura 1995) warns that a positive response to looks "masked its usability issues and made them harder to identify" (https://www.nngroup.com/articles/aesthetic-usability-effect/). The polished style is therefore not evidence that the tool is usable. Usability is checked separately by the browser tests and the keyboard-only walk-through.

**Expandable rows clutter.** NN/g notes "users don't tend to clean up after themselves". At most one row is open at a time.

## What works and what does not, in one list

Works: few headline figures read at a glance; bars for comparison; left navigation for a growing set of sections; colour paired with text; instant response; undo and logged reasons in place of warnings; deliberate friction at the point of AI review.

Does not work: pie, donut, gauge and 3D charts; colour as the only signal or for exact magnitude; routine confirmation dialogs; trusting explanations alone to stop over-reliance; judging usability by appearance.

## Not verified, so not to be stated as fact

- Stephen Few's dashboard pitfalls, Tufte's data-ink, Shneiderman's "overview first, zoom and filter, then details-on-demand" (IEEE Visual Languages 1996, from memory), Cleveland and McGill 1984 full text, and the Doherty threshold's original paper.
- Any evidence on sparklines, comparison with a previous period, cards, whitespace, or low density hurting expert users.
- Evidence on confidence percentages, on citations specifically, and on requiring a reason for rejection. These three are our own design reasoning.
- Colour-blindness prevalence (about 1 in 12 men, 1 in 200 women) comes from a charity site, not a peer-reviewed source.
