/**
 * Short name for a goal, to print on a medal: "Complete C2C (Corvallis to Coast) - 65 miles" -> "C2C".
 * Drops a leading verb, then cuts at the first dash, bracket or colon.
 */
export function medalLabel(description, max = 26) {
  let s = (description || "").trim();
  s = s.replace(/^(complete|finish|achieve|raise|build|do|hit|reach)\s+(a\s+|an\s+|the\s+)?/i, "");
  s = s.split(/\s+[—–-]\s+|\s*\(|:/)[0].trim();
  if (!s) return "Goal";
  s = s.charAt(0).toUpperCase() + s.slice(1);
  if (s.length <= max) return s;
  // cut at a word boundary and don't leave a dangling connector ("... test to")
  let cut = s.slice(0, max - 1);
  const endsOnWord = s.charAt(cut.length) === " ";
  if (!endsOnWord && cut.includes(" ")) cut = cut.slice(0, cut.lastIndexOf(" "));
  cut = cut.replace(/\s+(to|of|the|and|for|a|an|at|in)$/i, "");
  return `${cut.trimEnd()}…`;
}
