// Wording and progress for the power-to-weight card.

export function wkgProgress(p) {
  if (!p?.wkg) return null;
  const target = p.target || null;
  const pct = target ? Math.min(100, Math.round((p.wkg / target) * 100)) : null;
  const reached = target != null && p.wkg >= target;
  let sentence = null;
  if (target && reached) sentence = `Past the ${target.toFixed(1)} W/kg target.`;
  else if (target) {
    const parts = [];
    if (p.watts_needed > 0) parts.push(`${p.watts_needed} W more at ${p.weight_kg} kg`);
    if (p.kg_to_lose > 0) parts.push(`${p.kg_to_lose} kg lighter at ${p.ftp} W`);
    sentence = `To reach ${target.toFixed(1)} W/kg: ${parts.join(", or ")}.`;
  }
  return { pct, reached, sentence };
}

/** Change in average weight between the first and last of the weekly points (kg), or null. */
export function weightChange(p) {
  const w = p?.weekly || [];
  if (w.length < 2) return null;
  return Math.round((w[w.length - 1].kg - w[0].kg) * 10) / 10;
}
