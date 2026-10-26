/*
 * What each dashboard number means, written from how this app computes it.
 * `short` and `read` feed the hover card on the KPI tiles; the rest fill the metric guide page (/metrics).
 * `interpret(value)` turns today's number into a plain-language reading.
 */

const signed = (n) => `${n > 0 ? "+" : ""}${n}`;

export const METRICS = [
  {
    id: "tss",
    name: "Training Stress Score (TSS)",
    short: "How hard a single workout was, as one number. 100 TSS is one hour at your threshold power.",
    read: "A 40 TSS spin is easy, 100 is a solid day, 200+ is a big gravel day.",
    what: "TSS rolls a workout's duration and intensity into a single number so very different sessions can be added up and compared. An hour at exactly threshold power scores 100; an hour of easy spinning is about 40.",
    how: "TSS = duration (s) × normalized power × intensity factor ÷ (FTP × 3600) × 100. The numbers come from TrainingPeaks; the app never asks the AI coach to estimate them.",
    ranges: [
      ["Under 50", "Recovery or easy aerobic"],
      ["50 to 100", "A normal training day"],
      ["100 to 200", "A hard day: expect to feel it tomorrow"],
      ["200 and up", "A big day (a long gravel ride); plan recovery around it"],
    ],
    coach: "Weekly TSS drives the plan: the coach is given a TSS band for next week and has to plan inside it.",
    limits: "TSS reflects power and time, not terrain stress, heat, fuelling or how you slept. Strength and yoga score low even when they tire you.",
  },
  {
    id: "ctl",
    name: "Fitness (CTL)",
    short: "Your long-term training load: an exponentially weighted average of daily TSS over about 6 weeks.",
    read: "Higher means you have built more fitness. It rises slowly and falls slowly.",
    what: "Chronic Training Load is the app's measure of fitness. Every ride adds to it a little, and the effect fades over weeks, so it only climbs when you train consistently.",
    how: "CTL(today) = CTL(yesterday) + (TSS today − CTL(yesterday)) ÷ 42. Rebuilt from your whole history after every sync.",
    ranges: [
      ["Rising 2 to 4 per week", "Healthy build"],
      ["Flat", "Maintaining"],
      ["Falling", "Rest, illness or a recovery block; fine for a week or two"],
    ],
    coach: "The weekly target is derived from your current CTL plus a bounded ramp. The tile also shows CTL a year ago, so you can see the real trend.",
    limits: "CTL counts every TSS point equally, so it can't tell whether your fitness is aerobic or top-end. It is a trend, not a test result.",
  },
  {
    id: "atl",
    name: "Fatigue (ATL)",
    short: "Your short-term training load: the same average, but over only 7 days.",
    read: "Higher than CTL means you are carrying fatigue; lower means you are fresh.",
    what: "Acute Training Load responds fast. A big weekend pushes it up immediately, and a few easy days bring it back down.",
    how: "ATL(today) = ATL(yesterday) + (TSS today − ATL(yesterday)) ÷ 7.",
    ranges: [
      ["Well above CTL", "Fatigued: you are absorbing a hard block"],
      ["Near CTL", "Balanced"],
      ["Well below CTL", "Fresh, or detraining if it lasts"],
    ],
    coach: "Compared with CTL it gives form (TSB), which sets whether the next week should build or recover.",
    limits: "Like CTL it knows nothing about sleep, stress or illness; that is what the readiness numbers add.",
  },
  {
    id: "tsb",
    name: "Form (TSB)",
    short: "Fitness minus fatigue (CTL − ATL). Positive means fresh, negative means loaded.",
    read: "Around −10 to +5 is normal training. Below −25 means a lot of fatigue; above +15 is race-fresh.",
    what: "Training Stress Balance estimates how rested you are. Hard blocks push it negative on purpose; a taper or recovery week brings it up.",
    how: "TSB = CTL − ATL, both as of today's latest data. (The stored daily history uses the previous day's values, so a hard ride today shows up in tomorrow's form.)",
    ranges: [
      ["Above +15", "Very fresh: race or test day, or you have been resting a while"],
      ["+5 to +15", "Fresh"],
      ["−10 to +5", "Neutral, normal training"],
      ["−30 to −10", "Productive fatigue in a build block"],
      ["Below −30", "Deep fatigue: injury and illness risk rises"],
    ],
    coach: "Today's call on the dashboard uses it: lowish form (−20) suggests an easy day, very low form (−30) suggests rest.",
    interpret: (v) => {
      if (v == null) return null;
      if (v > 15) return "Very fresh";
      if (v > 5) return "Fresh";
      if (v >= -10) return "Neutral: normal training";
      if (v >= -30) return "Productive fatigue";
      return "Deep fatigue: consider rest";
    },
    limits: "The bands are rules of thumb from the Performance Manager model, and people differ. Learn your own: note how you feel at each TSB.",
  },
  {
    id: "ramp",
    name: "CTL ramp",
    short: "How fast your fitness has been rising: CTL change per week, averaged over the last 4 weeks.",
    read: "+2 to +4 a week is a sustainable build. Much more than +5 for long risks overreaching.",
    what: "Ramp rate is the slope of your fitness. It is the guard-rail against the main way training goes wrong: adding load faster than the body adapts.",
    how: "(CTL today − CTL 28 days ago) ÷ 4. Build weeks in the plan target +2 to +4; after three build weeks, a recovery week drops to 60 to 70% of the recent average.",
    ranges: [
      ["Below 0", "Fitness is falling"],
      ["0 to +2", "Maintaining"],
      ["+2 to +4", "Target build"],
      ["Above +5", "Aggressive: watch HRV, sleep and form"],
    ],
    coach: "Every weekly TSS band is solved from the ramp target; a plan that falls outside the band is sent back to be fixed.",
    interpret: (v) => {
      if (v == null) return null;
      if (v < 0) return "Fitness is easing off";
      if (v < 2) return "Maintaining";
      if (v <= 4) return "In the build range";
      return "Aggressive build";
    },
    limits: "A 4-week window smooths out single big weeks but is slow to show a change of direction.",
  },
  {
    id: "ftp",
    name: "Zwift FTP",
    short: "The threshold power Zwift is using for your workouts. Plan watts only match Zwift when this matches.",
    read: "It changes only after a Zwift ramp test or race. If it hasn't moved in 6 weeks, a test is due.",
    what: "Functional Threshold Power is the power you could hold for about an hour. Zwift scales every workout file by its own FTP and ignores the FTP in the file, so the app reads Zwift's value from your rides.",
    how: "For each interval the ride file records the target watts ERG mode held, and the app knows the FTP fraction it wrote into the file: Zwift FTP ≈ average target watts ÷ average fraction. The app's own FTP follows it.",
    ranges: [
      ["Changed in the last 6 weeks", "Current"],
      ["Unchanged for 6 weeks or more", "A ramp test (or a race) is due on a fresh day"],
    ],
    coach: "The coach schedules a ramp test when one is due, and writes every workout in percentages of this FTP.",
    limits: "It is inferred from ERG rides, so it appears only after a structured Zwift ride. A genuine fitness gain won't show until you test.",
  },
  {
    id: "hrv",
    name: "HRV (7-day average)",
    short: "Heart-rate variability from your Garmin, averaged over the last 7 days and compared with your own 60-day baseline.",
    read: "Near your baseline is normal. 10% or more below it, for days, suggests fatigue, illness or stress.",
    what: "HRV reflects how ready your nervous system is for stress. It is personal, so only the change from your own baseline means anything, not the absolute number.",
    how: "The tile shows the 7-day mean in milliseconds; the line under it is the percentage difference from the median of the previous 60 days.",
    ranges: [
      ["Within ±5% of baseline", "Normal"],
      ["+5% or more", "Well recovered (or very rested)"],
      ["−10% or lower", "Flagged: possible accumulated fatigue, illness or stress"],
    ],
    coach: "A suppressed HRV is one of the warning signs behind Today's call and is passed to the coach during the weekly session.",
    interpret: (v, ctx) => {
      const pct = ctx?.changePct;
      if (pct == null) return null;
      if (pct <= -10) return `${signed(pct)}% vs baseline: suppressed`;
      if (pct >= 5) return `${signed(pct)}% vs baseline: well recovered`;
      return `${signed(pct)}% vs baseline: normal`;
    },
    limits: "Wearable HRV is noisy night to night, which is why the app looks at a week at a time.",
  },
  {
    id: "sleep",
    name: "Sleep (7-day average)",
    short: "Average hours of sleep per night over the last 7 days.",
    read: "7 hours or more is the aim. Under 7 for a week is flagged as sleep debt.",
    what: "Sleep is when most adaptation happens, so a week of short nights undoes some of the benefit of hard training.",
    how: "Mean nightly sleep from your Garmin data over the last 7 days.",
    ranges: [
      ["8 hours or more", "Well rested"],
      ["7 to 8 hours", "Good"],
      ["Under 7 hours", "Flagged as sleep debt"],
    ],
    coach: "Short sleep is one of the warning signs behind Today's call, and the coach reads it before planning the week.",
    interpret: (v) => {
      if (v == null) return null;
      if (v >= 8) return "Well rested";
      if (v >= 7) return "Good";
      return "Sleep debt: prioritise rest";
    },
    limits: "It counts time asleep, not quality; deep and REM sleep matter too.",
  },
  {
    id: "execution",
    name: "Execution score",
    short: "How closely a structured ride matched its prescribed intervals, out of 10, measured from the ride file.",
    read: "10 means every work interval landed inside its power band. Lower scores mean intervals were off target.",
    what: "The score is calculated, not judged by the AI. Each work interval is compared with its target band using the lap markers Zwift records, and the score is weighted by interval length.",
    how: "Deviation is 0 inside the band and otherwise the percentage beyond the nearest edge. Points per interval: within 5% = 1.0, within 10% = 0.7, within 20% = 0.3, otherwise 0. The score is 10 × the duration-weighted average. If every interval misses the same way by 2% or more, that is an FTP mismatch, and it is removed before scoring.",
    ranges: [
      ["9 to 10", "On target"],
      ["6 to 9", "Mostly on target"],
      ["Below 6", "Intervals drifted or were cut short"],
    ],
    coach: "The coach and the ride write-up receive the number as a fact, so a perfect ERG ride can't be marked down by the narrative.",
    limits: "Only structured rides with lap markers (Zwift ERG) get a score; outdoor rides do not.",
  },
  {
    id: "consistency",
    name: "Consistency",
    short: "How many recent weeks you landed within 15% of the plan's TSS band, and the current streak.",
    read: "A gold pip is a week inside the band; copper is a miss. The streak counts hit weeks in a row.",
    what: "Consistency, more than any single session, is what builds fitness. This tracks whether the training you did matched the training that was planned.",
    how: "A week hits when its TSS is between 85% of the plan's minimum and 115% of its maximum. Weeks with no saved plan are shown as a dashed pip and don't count.",
    ranges: [
      ["Hit", "Within 15% of the planned band"],
      ["Miss", "Too little or too much, including overshooting a recovery week"],
    ],
    coach: "Misses are context for the weekly conversation, not a verdict.",
    limits: "It judges volume only. A week can hit the TSS band and still miss the key session.",
  },
];

export const metricById = (id) => METRICS.find((m) => m.id === id);
