import React from "react";

/**
 * Coach Claude's logo: a robot with a whistle in its mouth.
 *
 * Drawn like a lucide icon (24x24, 2px round strokes in currentColor) so it drops in
 * wherever an icon goes, but the whistle is filled in the brand's gravel tone so it
 * stays readable against both the green header and the white nav.
 */
function CoachLogo({ size = 24, className, ...rest }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden="true"
      {...rest}
    >
      {/* antenna */}
      <path d="M12 6V3" />
      <circle cx="12" cy="2.4" r=".6" />
      {/* head, ear bolts, eyes */}
      <rect x="2" y="6" width="20" height="16" rx="3.5" />
      <path d="M0.5 14H2" />
      <path d="M22 14h1.5" />
      <path d="M7.5 9.6v2.2" />
      <path d="M16.5 9.6v2.2" />
      {/* whistle: slim mouthpiece stepping up into a round chamber with its pea hole */}
      <g transform="translate(5.6 18.2)" fill="var(--color-gravel-light, #d4b088)" stroke="none">
        <path d="M0 0.5L1 -0.6H4.6L6 2.1H0Z" />
        <path
          fillRule="evenodd"
          d="M5.8 -1.4a3.5 3.5 0 1 1 7 0a3.5 3.5 0 1 1 -7 0Z M11.2 -1.1a1 1 0 1 0 -2 0a1 1 0 1 0 2 0Z"
        />
      </g>
    </svg>
  );
}

export default CoachLogo;
