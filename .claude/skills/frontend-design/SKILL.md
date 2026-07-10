---
name: spendly-ui-designer
description: Generates modern, production-ready UI components and pages for Spendly, a personal expense tracker app. Use this skill whenever the user asks to design, build, create, redesign, or improve any page or component for Spendly — for example "design the transactions page," "create UI for the budget summary card," "build a component for adding an expense," or "redesign the dashboard." Also trigger for general Spendly frontend work even if the user doesn't say "design" explicitly, such as "Spendly needs a settings screen" or "make the expense list look better." Produces clean fintech-style React/HTML components with consistent spacing, icons, and a card-based SaaS look matching the rest of the Spendly product.
---

# Spendly UI Designer

Spendly is a personal expense tracker. This skill produces new UI for it — pages, components, or redesigns of existing screens — that looks like it was built by the same designer who built the rest of the product, not bolted on from a generic template.

## Before writing any code

1. **Look for the existing Spendly design.** Check the conversation and any uploaded files or artifacts for prior Spendly screens, a design system, color tokens, or component code. If you find them, match their color palette, spacing, border radius, and component patterns exactly — consistency with what already exists always wins over your own aesthetic preferences.
2. **If nothing exists yet, or you're unsure what "existing" looks like, ask.** A quick clarifying question (or a request for a screenshot) is much cheaper than building something and finding out it clashes with the rest of the app. If the user has no existing UI at all (e.g. this is the first screen), say so and proceed using the design rules below as the foundation for a new system.
3. **Load the frontend-design skill** (`/mnt/skills/public/frontend-design/SKILL.md`) before writing code — it has the underlying design-token and styling guidance this skill builds on top of.

## Design rules

Spendly's visual identity is minimal, clean, fintech-style — think a tool for managing money, not a toy. Apply these consistently:

- **Layout**: card-based. Group related information into cards with soft shadows and rounded corners (aim for consistent radius across the page, e.g. all cards at the same rounding — don't mix sharp and rounded elements).
- **Spacing**: build on an 8px grid. Padding, gaps, and margins should be multiples of 8px (8, 16, 24, 32...) so the layout feels intentional rather than eyeballed.
- **Color**: subtle and restrained. A neutral base (whites/soft grays) with one or two accent colors used sparingly for actions, positive/negative amounts (e.g. income vs. expense), and key data points. Avoid loud, saturated palettes — this is a finance app, it should feel trustworthy.
- **Typography**: clear hierarchy — one strong heading style, a consistent body size, and a smaller size for secondary/meta info (dates, categories). Numbers (amounts, balances) deserve visual weight since they're the thing users came to see.
- **Icons**: use Lucide or Heroicons for anything representing an action or category (add expense, filter, categories like food/transport/etc). Don't invent custom icon styles — pull from one consistent icon set per build.
- **Density**: avoid clutter. If a section feels crowded, group items into a card or collapse them rather than shrinking spacing to fit.

Avoid: generic/dated admin-dashboard UI, unstructured walls of inline styles, inconsistent corner radii or spacing that doesn't map to the 8px grid, and mixing icon sets.

## What to produce

For every request, deliver:

1. **A brief UI structure note** — the layout and key sections you chose, and any non-obvious UX decision (e.g. "put the add-expense button as a floating action button since this is used constantly" or "grouped budgets by category since that's how users think about spending"). Keep this to a few sentences, not a spec document — the code is the real deliverable.
2. **The component code** — clean, modular, minimal boilerplate. Match whatever stack the existing Spendly code uses (React is the default assumption for this app unless the user's existing code says otherwise). Split into logical components rather than one giant file if the page has multiple distinct sections.
3. Follow the file-creation and artifact guidance already in your instructions for whether this becomes an artifact vs. inline code — Spendly UI work almost always qualifies as artifact-worthy (it's a reusable, standalone component).

## Example

**Input:** "design the transactions page"

**Output shape:**
- Short note: "Table-style list grouped by date, with a search/filter bar pinned above it, and each row showing category icon, merchant, date, and amount (red for expenses, green for income). Added a summary card at the top for total spent this month since that's the first thing users want to know."
- A single React component (or a couple of small subcomponents: `TransactionList`, `TransactionRow`) styled per the design rules above, using Lucide icons for categories.

## Iterating

If the user pushes back on a design ("too much whitespace," "doesn't match my other screens," "needs a dark mode"), treat this the same as any design revision: keep the parts that worked, and don't rebuild from scratch unless asked to.