---
name: Academic Excellence System
colors:
  surface: '#f8f9fa'
  surface-dim: '#d9dadb'
  surface-bright: '#f8f9fa'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f3f4f5'
  surface-container: '#edeeef'
  surface-container-high: '#e7e8e9'
  surface-container-highest: '#e1e3e4'
  on-surface: '#191c1d'
  on-surface-variant: '#43474e'
  inverse-surface: '#2e3132'
  inverse-on-surface: '#f0f1f2'
  outline: '#74777f'
  outline-variant: '#c4c6cf'
  surface-tint: '#455f87'
  primary: '#001835'
  on-primary: '#ffffff'
  primary-container: '#0f2d52'
  on-primary-container: '#7b95c0'
  inverse-primary: '#adc8f5'
  secondary: '#286864'
  on-secondary: '#ffffff'
  secondary-container: '#acebe6'
  on-secondary-container: '#2d6c68'
  tertiary: '#755b00'
  on-tertiary: '#ffffff'
  tertiary-container: '#cea72c'
  on-tertiary-container: '#4f3d00'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#d5e3ff'
  primary-fixed-dim: '#adc8f5'
  on-primary-fixed: '#001b3b'
  on-primary-fixed-variant: '#2d476e'
  secondary-fixed: '#afeee9'
  secondary-fixed-dim: '#93d2cc'
  on-secondary-fixed: '#00201e'
  on-secondary-fixed-variant: '#02504c'
  tertiary-fixed: '#ffe08e'
  tertiary-fixed-dim: '#ecc246'
  on-tertiary-fixed: '#241a00'
  on-tertiary-fixed-variant: '#584400'
  background: '#f8f9fa'
  on-background: '#191c1d'
  surface-variant: '#e1e3e4'
typography:
  display-lg:
    fontFamily: Inter
    fontSize: 48px
    fontWeight: '700'
    lineHeight: 56px
    letterSpacing: -0.02em
  display-lg-mobile:
    fontFamily: Inter
    fontSize: 32px
    fontWeight: '700'
    lineHeight: 40px
  headline-lg:
    fontFamily: Inter
    fontSize: 32px
    fontWeight: '600'
    lineHeight: 40px
  headline-md:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
  title-lg:
    fontFamily: Inter
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 28px
  title-md:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '600'
    lineHeight: 24px
  body-lg:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '400'
    lineHeight: 28px
  body-md:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  body-sm:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  label-md:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '500'
    lineHeight: 16px
    letterSpacing: 0.05em
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  base: 4px
  xs: 8px
  sm: 16px
  md: 24px
  lg: 48px
  xl: 80px
  container-max: 1280px
  gutter: 24px
  margin-mobile: 16px
---

## Brand & Style

The design system is built for the **Pakistan Institute of Science and Technology (PIST)**, reflecting a heritage of academic rigor, public service, and technical innovation. The brand personality is **authoritative, stable, and intellectually grounded**, mirroring the prestige of top-tier global research institutions.

The design style is **Corporate Modern with Institutional Weight**. It avoids ephemeral digital trends in favor of a timeless, structured aesthetic. The UI prioritizes high information density that remains legible and accessible, ensuring that students, faculty, and researchers can navigate complex data with ease. Visual interest is generated through precise alignment, generous whitespace, and the strategic use of institutional colors rather than decorative flourishes.

## Colors

The palette is anchored by **Deep Navy Blue**, signifying trust and state-sanctioned authority. **Dark Teal** provides a sophisticated secondary layer for departmental distinction, while **Gold** is reserved strictly for high-level accents such as honors, crests, and primary calls to action.

- **Primary (Navy):** Used for global navigation, headers, and primary buttons.
- **Secondary (Teal):** Used for sub-navigation, section headers, and category tags.
- **Accent (Gold):** Used for significant highlights, notifications of achievement, and "Apply Now" triggers.
- **Backgrounds:** Use pure White (#FFFFFF) for content areas and Light Gray (#F8F9FA) for subtle section differentiation and container backgrounds.

## Typography

The design system utilizes **Inter** for all roles to ensure maximum legibility across digital interfaces and technical documentation. 

- **Headlines:** Use tighter letter-spacing and bold weights to convey strength.
- **Body Text:** Use standard weights (400) with generous line-height (1.5x) to facilitate long-form reading of research papers and academic regulations.
- **Data Display:** For fee structures and administrative tables, use `body-sm` or `body-md` to maintain high density without sacrificing clarity.
- **Hierarchy:** Ensure a clear vertical rhythm by maintaining consistent margins between typographic levels.

## Layout & Spacing

This design system employs a **12-column fixed grid** for desktop, centering the content at a maximum width of 1280px to maintain professional proportions on wide monitors.

- **Desktop (1024px+):** 12 columns, 24px gutters, 48px+ side margins.
- **Tablet (768px - 1023px):** 8 columns, 24px gutters, 32px side margins.
- **Mobile (Up to 767px):** 4 columns, 16px gutters, 16px side margins.

Spacing follows an 8px base grid (incremented by 4px for tight UI elements). Use `lg` (48px) and `xl` (80px) vertical spacing to separate major content blocks like "News" and "Research Areas" to prevent the interface from feeling cluttered.

## Elevation & Depth

To maintain a conservative and institutional feel, depth is communicated through **Tonal Layering** and **Subtle Keyline Borders** rather than heavy shadows.

1.  **Level 0 (Base):** Light Gray (#F8F9FA) for the main background.
2.  **Level 1 (Cards/Surface):** Pure White (#FFFFFF) with a 1px border (#E9ECEF). No shadow.
3.  **Level 2 (Interactive):** Pure White with a very soft, diffused shadow (0px 4px 12px rgba(0, 0, 0, 0.05)) used only for hovered cards or dropdown menus.
4.  **Utility Bar:** The top utility bar (containing language, login, and search) should be "Anchored" using the Deep Navy primary color, creating a strong structural cap at the top of the viewport.

## Shapes

The shape language is **Soft and Professional**. Avoid fully rounded "pill" shapes or sharp "brutalist" corners. 

- **Small Components:** Checkboxes and small tags use 0.25rem (4px) corner radius.
- **Standard Components:** Buttons and Input fields use 0.25rem (4px).
- **Large Components:** Academic cards and content containers use 0.5rem (8px). 

This subtle rounding provides a modern touch while maintaining the serious, structured appearance required for an institutional identity.

## Components

### Buttons
- **Primary:** Deep Navy background, White text. Squared corners (4px).
- **Secondary:** Dark Teal background or Navy outline.
- **CTA:** Gold background with Navy text (used exclusively for "Apply" or "Donate").

### Academic Cards
Cards should be white-background containers with a 1px #E9ECEF border. They should feature a clear header area for the course/department name and a footer for metadata (e.g., "Credits: 3.0"). Image-based cards should use a 16:9 aspect ratio for campus photography.

### Data Tables
Tables are critical for fee structures. Use a clean "Minimalist Institutional" style:
- Header: Deep Navy background with White bold text.
- Rows: Alternating zebra stripes using Light Gray (#F8F9FA).
- Borders: Horizontal lines only to reduce visual noise.

### Navigation Utility Bar
A thin bar sitting above the main header. 
- Background: #0F2D52 (Primary).
- Content: White text, smaller scale (`label-md`). 
- Items: Quick links for Faculty, Students, Alumni, and a Search icon.

### Input Fields
- Border: 1px #CED4DA.
- Focus State: 1px border #0F2D52 with a soft blue 2px outer glow.
- Label: Always visible above the field, never hidden as placeholder text.