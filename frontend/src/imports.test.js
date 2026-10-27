import { describe, expect, it } from "vitest";
import { ESLint } from "eslint";

// A removed import once broke saving and the interval charts in production while the build and tests passed.
describe("source files", () => {
  it("never use a variable or component that isn't defined or imported", async () => {
    const eslint = new ESLint();
    const results = await eslint.lintFiles(["src/**/*.{js,jsx}"]);
    const problems = results.flatMap((r) => r.messages.filter((m) => m.severity === 2).map((m) => `${r.filePath.split("/src/")[1]}:${m.line} ${m.message}`));
    expect(problems).toEqual([]);
  }, 60000);
});
