# Cursor prompt: rebuild the ShopSphere frontend to a ChatGPT / Claude standard

Paste everything below the line into Cursor (agent mode, repo root open).

---

## Role and goal
You are a senior product designer and frontend engineer. Rebuild the visual layer of `frontend/` so it feels like a calm, premium, ChatGPT / Claude-class assistant used by operations staff all day. Keep all behaviour, routes, API calls and state logic (`src/api`, `src/context`, `src/lib`) unchanged unless a change is listed below. This is a redesign, not a rewrite of business logic.

## Non-negotiables
1. **Tailwind CSS v4 utilities only.** `src/index.css` may contain only `@import "tailwindcss"` and a `@theme` block (fonts, colours, radii, shadows). No custom classes, no `@apply`, no component CSS. The only allowed exception is third-party library overrides that cannot be done with utilities (docx preview), isolated in a clearly commented block.
2. **Inter** for all UI and body text (variable font, `opsz` axis, weights 400/500/600 only). `font-mono` only for code, IDs and tool arguments.
3. **One neutral palette.** Use `zinc` everywhere (remove all `slate`). One accent colour defined in `@theme` (suggest a restrained blue, `accent-600` around `#2563eb`) used only for focus rings, links, the active state and the primary send button state. Do not redefine the accent as grey.
4. **No text below 12px.** No `text-[10px]` / `text-[11px]`. No uppercase micro-labels. Minimum contrast WCAG AA: never use `zinc-400` for text on white (use `zinc-500` or darker).
5. Keep lint clean (`npm run lint`) and `npm run build` passing. Do not add UI libraries other than `lucide-react` and (optionally) `@radix-ui/react-*` primitives for menus, dialogs and tooltips.

## Why the current UI looks unprofessional (fix every item)
- Type scale collapsed to 10-13px; reads like a debug console, not a product.
- Two grey palettes (`zinc` and `slate`) mixed, accent redefined as grey, so there is no hierarchy or brand.
- Radii are inconsistent (`md`, `lg`, `2xl` mixed), and boxes sit inside boxes (tool box inside trace inside message inside thread).
- The chat is cramped: narrow column, a context panel that auto-opens and takes a third of the screen, and controls everywhere (provider toggle inside the composer, Data explorer in two places).
- Agent output is raw: tool names in backticks, JSON in tiny mono boxes, "What I did / Findings / Recommendation" boilerplate, internal jargon (F2/F3/F4, scenario slugs).
- The landing page is a generic SaaS template (hero, 3x2 icon grid, dark CTA).

## Design system (implement first, in `@theme` plus `components/ui/`)
- **Type scale:** body 15px/1.65 (chat answers 16px/1.7), UI 14px/1.4, small 13px/1.4, caption 12px. Page title 20px/600, section title 16px/600. Letter-spacing `-0.01em` on titles.
- **Colour:** background white, sidebar `zinc-50`, borders `zinc-200`, text `zinc-900/600/500`. Semantic: success `emerald`, warning `amber`, danger `red`, used only for status badges and alerts.
- **Radius:** 8px controls, 12px cards and the composer, 9999px chips and avatars. Nothing else.
- **Elevation:** borders for structure, one soft shadow for popovers and the composer. No gradients, glows or decorative blobs.
- **Spacing:** 4px base, generous vertical rhythm; separate with whitespace first, borders second.
- Build primitives: `Button` (primary, secondary, ghost, icon), `Badge`, `Chip`, `Tooltip`, `Menu`, `Dialog`, `Skeleton`, `Avatar`, `Kbd`. Everything else composes these.

## Workspace layout (the main product, `/workspace`)
Match the ChatGPT / Claude structure:
- **Sidebar (260px, collapsible):** brand, New chat (primary), search, conversations grouped by Today / Yesterday / Previous 7 days (hover reveals rename/delete menu), Data explorer as a nav item, and a **user menu at the bottom** (avatar with initials, name, role badge, Sign out). Move the model selector out of the sidebar.
- **Header (48px, minimal):** sidebar toggle, conversation title (editable), **model picker dropdown** (Groq / Gemini; show unavailable ones disabled with a reason), and a "Return context" toggle button that shows the pinned return ID as a chip. No other controls.
- **Thread:** centred column, `max-w-3xl`, 16px text. User messages: right-aligned soft `zinc-100` bubble, no avatar. Assistant messages: no bubble, no heavy borders, small brand avatar. Hover actions under each assistant message: copy, regenerate, thumbs up/down. Show relative timestamp on hover.
- **Composer:** one rounded-12px card, 56px min height, auto-grow to 200px, placeholder "Message the returns agent". Left: attach/pin return (popover with an input and recent return suggestions). Right: send button that becomes a **Stop** button while the agent runs. Return chip appears above the textarea inside the card. `Enter` sends, `Shift+Enter` newline, show hint in a tooltip. Footer disclaimer in 12px `zinc-500`.
- **Context panel:** closed by default; opens as a right drawer (360px) only when the user clicks the return chip. Sections as clean key-value rows with status badges and a vertical timeline.
- **Empty state:** vertically centred greeting ("Good afternoon, {first name or role}"), the composer in the middle, and below it 4 suggestion chips chosen by role (analyst: investigate / refund request; supervisor: approvals / overdue; warehouse: recovery / inspection; support: refund status). Remove the large card grid.
- **Scrolling:** auto-scroll while streaming; a "Scroll to latest" floating button when the user scrolls up.

## Agent experience (most important)
- **Progressive disclosure of work:** while running, show one live line, e.g. "Checking inspection results…", with a subtle shimmer (no spinner wall). When done, collapse into a single summary row, e.g. "Used 3 tools · 4.2s" with a chevron. Expanded view shows a clean step list: friendly step titles ("Looked up return R102", "Searched policy documents", "Checked refund ledger"), a status icon, and per-step "Details" that reveal input/output in a tidy mono block (max 12px mono, 13px labels, no uppercase). Map tool names to friendly titles in one lookup file; fall back to a humanised name.
- **Answer first:** render the markdown answer prominently (headings, lists, tables with proper styling, inline code chips, links). Do not display the "What I did" boilerplate; the collapsed trace replaces it. Keep internal jargon out of the UI copy (rename "F2 signal" etc. to plain labels in the context panel, while leaving API fields untouched).
- **Sources as chips:** documents and records the answer used appear below the answer as compact source chips (icon, filename or record ID). Clicking opens the existing preview modal. Group as "Sources (4)".
- **Actions that need approval** (refund requests, tasks) render as a clear **action card**: what, which return, amount, status badge (Pending approval / Approved / Executed), and role-aware buttons (Approve / Reject for supervisors only). Wire to the existing action endpoints.
- **States:** streaming text, stop generation, error message with Retry, rate-limit message ("The model is busy, try again in a minute or switch model"), empty/skeleton states, offline banner.

## Landing and login
- Landing: replace the template with a restrained, editorial page: concise headline, one product screenshot-style preview built from the real components, three short sections max, plain footer. Sentence-case copy, no jargon, no icon grid. Login: split layout is fine; remove the pre-filled password and demo hints behind a collapsed "Demo accounts" disclosure shown only in development (`import.meta.env.DEV`).

## Data explorer
Same design system: clean tables (sticky header, 14px rows, zebra off, hover row), status badges, filters in a toolbar, side preview for documents. Empty and loading states.

## Accessibility and quality
Visible focus rings (accent), full keyboard navigation (menus, dialogs trap focus, Esc closes), `aria-live` for streaming status, 44px minimum touch targets on mobile, responsive from 360px (sidebar and context panel become overlays with backdrops), `prefers-reduced-motion` respected. Subtle 150ms transitions only.

## Process
Work in phases and stop after each for me to review: (1) tokens and primitives, (2) workspace shell, sidebar, header and composer, (3) message rendering and the agent trace, sources and action cards, (4) context panel and empty state, (5) landing, login and data explorer, (6) polish and accessibility pass. After each phase run `npm run lint` and `npm run build` and fix errors. Take screenshots at 1440px and 390px and compare with ChatGPT / Claude for spacing, type size and density before moving on.

## Acceptance checklist
- [ ] No `slate-*` classes, no text under 12px, no custom CSS classes, only Inter plus mono for code
- [ ] One accent colour, used sparingly; all status colours semantic
- [ ] Only three radii in use
- [ ] Thread is centred, `max-w-3xl`, 16px text; composer matches ChatGPT / Claude behaviour including Stop
- [ ] Agent work is collapsed to a one-line summary with friendly step names; no raw tool names or JSON visible by default
- [ ] Sources shown as chips; approval actions shown as cards with role-aware buttons
- [ ] Model picker in the header; user menu in the sidebar; context panel closed by default
- [ ] Lint clean, build passes, works at 360px, keyboard-only usable
