import React from "react";
import { createRoot } from "react-dom/client";
import { act } from "react";
import { describe, expect, it } from "vitest";
import { CoachAvatar } from "./CoachLogo";

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

function render(node) {
  const el = document.createElement("div");
  act(() => createRoot(el).render(node));
  return el;
}

describe("CoachAvatar", () => {
  it("only animates while the coach is speaking", () => {
    expect(render(<CoachAvatar />).querySelector(".coach-avatar").classList.contains("speaking")).toBe(false);
    expect(render(<CoachAvatar speaking />).querySelector(".coach-avatar").classList.contains("speaking")).toBe(true);
  });
});
