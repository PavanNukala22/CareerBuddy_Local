const HP = '..';  // parent HP/ dir (run build from HP/_build)
module.exports = {
  content: [`${HP}/*.html`],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        "secondary-fixed": "#f0dbff", "tertiary-fixed": "#ffdbcd", "on-tertiary-fixed": "#360f00",
        "on-surface-variant": "#424655", "primary": "#0056c8", "shadow-dark": "#d1d9e6",
        "on-tertiary-fixed-variant": "#7e2c00", "surface-container-lowest": "#ffffff",
        "surface-container": "#eeeeee", "on-surface": "#1a1c1c", "on-secondary-fixed-variant": "#602a93",
        "on-secondary-container": "#561e89", "on-primary-container": "#fffdff", "tertiary-container": "#cb4c00",
        "on-tertiary-container": "#fffdff", "surface-variant": "#e2e2e2", "error": "#ba1a1a",
        "surface-container-low": "#f3f3f3", "surface": "#f9f9f9", "on-background": "#1a1c1c",
        "on-tertiary": "#ffffff", "tertiary-fixed-dim": "#ffb598", "on-primary-fixed": "#001945",
        "inverse-on-surface": "#f0f1f1", "error-container": "#ffdad6", "inverse-primary": "#b0c6ff",
        "on-secondary-fixed": "#2c0050", "shadow-light": "#ffffff", "surface-dim": "#dadada",
        "secondary": "#7944ad", "surface-tint": "#0058cb", "outline-variant": "#c2c6d7",
        "secondary-container": "#c890fe", "primary-container": "#146ef5", "surface-light": "#ffffff",
        "inverse-surface": "#2f3131", "surface-container-highest": "#e2e2e2", "text-main": "#000000",
        "tertiary": "#a23b00", "secondary-fixed-dim": "#ddb7ff", "on-secondary": "#ffffff",
        "background": "#f9f9f9", "surface-bright": "#f9f9f9", "on-error": "#ffffff",
        "on-error-container": "#93000a", "primary-fixed-dim": "#b0c6ff", "outline": "#727786",
        "on-primary": "#ffffff", "text-muted": "#666666", "surface-container-high": "#e8e8e8",
        "primary-fixed": "#d9e2ff", "on-primary-fixed-variant": "#00429c"
      },
      borderRadius: { "DEFAULT": "0.25rem", "lg": "0.5rem", "xl": "0.75rem", "full": "9999px" },
      spacing: { "section-h": "32px", "container-max": "1200px", "section-v": "48px", "gutter": "24px", "base": "8px" },
      fontFamily: {
        "h3": ["Domine"], "body": ["Domine"], "display-hero-mobile": ["Domine"], "h2": ["Domine"],
        "display-hero": ["Domine"], "h1": ["Domine"], "caption": ["Domine"], "label-caps": ["Work Sans"]
      },
      fontSize: {
        "h3": ["22px", { lineHeight: "28px", fontWeight: "600" }],
        "body": ["16px", { lineHeight: "24px", fontWeight: "400" }],
        "display-hero-mobile": ["40px", { lineHeight: "44px", letterSpacing: "-1px", fontWeight: "700" }],
        "h2": ["28px", { lineHeight: "35px", fontWeight: "600" }],
        "display-hero": ["56px", { lineHeight: "60px", letterSpacing: "-1.5px", fontWeight: "700" }],
        "h1": ["40px", { lineHeight: "46px", letterSpacing: "-0.5px", fontWeight: "700" }],
        "caption": ["13px", { lineHeight: "18px", fontWeight: "400" }],
        "label-caps": ["14px", { lineHeight: "20px", letterSpacing: "1.5px", fontWeight: "600" }]
      }
    }
  },
  plugins: [require('@tailwindcss/forms'), require('@tailwindcss/container-queries')],
};
