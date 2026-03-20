#!/usr/bin/env node
/**
 * generate_run_report.js
 *
 * Reads a JSON data file produced by pptx_report.py and generates a
 * styled PPTX run report using PptxGenJS.
 *
 * Usage: node pptx/generate_run_report.js <data.json> <output.pptx>
 */

const fs = require("fs");
const path = require("path");
const pptxgen = require("pptxgenjs");

// ── Color Palette (Teal Trust — matches existing ArgusBot presentation) ──
const C = {
  navy: "1B2A4A",
  ice: "C8E6F5",
  white: "FFFFFF",
  dark: "0D1B2E",
  accent: "0891B2",
  muted: "64748B",
  lightBg: "F0F9FF",
  cardBg: "FFFFFF",
  green: "059669",
  orange: "D97706",
  red: "DC2626",
  teal: "0D9488",
  purple: "7C3AED",
  yellow: "EAB308",
};

const FONT = "Calibri";
const FONT_BOLD = "Calibri";
const FONT_MONO = "Consolas";

function mkShadow() {
  return { type: "outer", color: "000000", blur: 4, offset: 2, angle: 135, opacity: 0.10 };
}

function defineMasters(pres) {
  pres.defineSlideMaster({ title: "DARK", background: { color: C.dark } });
  pres.defineSlideMaster({ title: "LIGHT", background: { color: C.lightBg } });
  pres.defineSlideMaster({ title: "WHITE", background: { color: C.white } });
}

function addSlideNum(slide, num, total, dark = false) {
  slide.addText(`${num} / ${total}`, {
    x: 8.8, y: 5.2, w: 1, h: 0.3,
    fontSize: 9, fontFace: FONT, color: dark ? "7BA3C4" : "94A3B8",
    align: "right",
  });
}

function truncate(str, maxLen) {
  if (!str) return "";
  return str.length > maxLen ? str.slice(0, maxLen - 3) + "..." : str;
}

function statusColor(status) {
  if (status === "done") return C.green;
  if (status === "blocked") return C.red;
  return C.orange;
}

function main() {
  const args = process.argv.slice(2);
  if (args.length < 2) {
    console.error("Usage: node generate_run_report.js <data.json> <output.pptx>");
    process.exit(1);
  }

  const dataPath = args[0];
  const outputPath = args[1];
  const raw = fs.readFileSync(dataPath, "utf-8");
  const data = JSON.parse(raw);

  const pres = new pptxgen();
  pres.layout = "LAYOUT_16x9";
  pres.author = "ArgusBot";
  pres.title = `ArgusBot Run Report — ${data.objective_short || "Run Report"}`;
  defineMasters(pres);

  const hasOperatorMessages = data.operator_messages && data.operator_messages.length > 0;
  const TOTAL = hasOperatorMessages ? 8 : 7;
  let sn = 0;

  // ════════════════════════════════════════
  // SLIDE 1: Title
  // ════════════════════════════════════════
  sn++;
  {
    const s = pres.addSlide({ masterName: "DARK" });
    addSlideNum(s, sn, TOTAL, true);
    s.addText("ArgusBot Run Report", {
      x: 0.8, y: 1.2, w: 8.4, h: 1.0,
      fontSize: 42, fontFace: FONT_BOLD, color: C.white, bold: true,
    });
    s.addText(truncate(data.objective || "", 200), {
      x: 0.8, y: 2.3, w: 8.4, h: 0.8,
      fontSize: 16, fontFace: FONT, color: C.ice,
    });
    const meta = [];
    if (data.date) meta.push(data.date);
    if (data.session_id) meta.push(`Session: ${truncate(data.session_id, 40)}`);
    s.addText(meta.join("  |  "), {
      x: 0.8, y: 3.5, w: 8.4, h: 0.4,
      fontSize: 12, fontFace: FONT, color: C.muted,
    });
    // Status badge
    const badge = data.success ? "SUCCESS" : "INCOMPLETE";
    const badgeColor = data.success ? C.green : C.orange;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
      x: 0.8, y: 4.2, w: 1.8, h: 0.45,
      fill: { color: badgeColor }, rectRadius: 0.1,
    });
    s.addText(badge, {
      x: 0.8, y: 4.2, w: 1.8, h: 0.45,
      fontSize: 14, fontFace: FONT_BOLD, color: C.white, bold: true,
      align: "center", valign: "middle",
    });
  }

  // ════════════════════════════════════════
  // SLIDE 2: Executive Summary
  // ════════════════════════════════════════
  sn++;
  {
    const s = pres.addSlide({ masterName: "LIGHT" });
    addSlideNum(s, sn, TOTAL);
    s.addText("Executive Summary", {
      x: 0.8, y: 0.3, w: 8.4, h: 0.7,
      fontSize: 32, fontFace: FONT_BOLD, color: C.navy, bold: true,
    });

    // Stat boxes
    const stats = [
      ["Total Rounds", String(data.total_rounds || 0), C.accent],
      ["Final Status", data.success ? "Success" : "Incomplete", data.success ? C.green : C.orange],
      ["Checks Passed", `${data.checks_passed || 0}/${data.checks_total || 0}`, data.checks_passed === data.checks_total ? C.green : C.red],
      ["Reviewer", data.reviewer_verdict || "N/A", statusColor(data.reviewer_verdict)],
    ];
    stats.forEach(([label, value, color], i) => {
      const xx = 0.5 + i * 2.3;
      s.addShape(pres.shapes.RECTANGLE, {
        x: xx, y: 1.3, w: 2.05, h: 1.4,
        fill: { color: C.cardBg }, shadow: mkShadow(),
      });
      s.addShape(pres.shapes.RECTANGLE, {
        x: xx, y: 1.3, w: 2.05, h: 0.08,
        fill: { color },
      });
      s.addText(value, {
        x: xx, y: 1.5, w: 2.05, h: 0.7,
        fontSize: 22, fontFace: FONT_BOLD, color, bold: true,
        align: "center", valign: "middle",
      });
      s.addText(label, {
        x: xx, y: 2.2, w: 2.05, h: 0.4,
        fontSize: 12, fontFace: FONT, color: C.muted,
        align: "center",
      });
    });

    // Stop reason
    s.addShape(pres.shapes.RECTANGLE, {
      x: 0.8, y: 3.0, w: 8.4, h: 0.7,
      fill: { color: C.cardBg }, shadow: mkShadow(),
    });
    s.addText("Stop Reason", {
      x: 1.0, y: 3.05, w: 2, h: 0.3,
      fontSize: 11, fontFace: FONT_BOLD, color: C.muted, bold: true,
    });
    s.addText(truncate(data.stop_reason || "N/A", 200), {
      x: 1.0, y: 3.35, w: 8.0, h: 0.3,
      fontSize: 12, fontFace: FONT, color: "444444",
    });

    // Objective recap
    s.addShape(pres.shapes.RECTANGLE, {
      x: 0.8, y: 3.9, w: 8.4, h: 1.3,
      fill: { color: C.cardBg }, shadow: mkShadow(),
    });
    s.addText("Objective", {
      x: 1.0, y: 3.95, w: 2, h: 0.3,
      fontSize: 11, fontFace: FONT_BOLD, color: C.muted, bold: true,
    });
    s.addText(truncate(data.objective || "", 400), {
      x: 1.0, y: 4.25, w: 8.0, h: 0.85,
      fontSize: 11, fontFace: FONT, color: "444444",
    });
  }

  // ════════════════════════════════════════
  // SLIDE 3: Round Timeline
  // ════════════════════════════════════════
  sn++;
  {
    const s = pres.addSlide({ masterName: "WHITE" });
    addSlideNum(s, sn, TOTAL);
    s.addText("Round Timeline", {
      x: 0.8, y: 0.3, w: 8.4, h: 0.7,
      fontSize: 28, fontFace: FONT_BOLD, color: C.navy, bold: true,
    });
    s.addText("Visual pipeline of round execution and reviewer decisions", {
      x: 0.8, y: 0.95, w: 8.4, h: 0.35,
      fontSize: 14, fontFace: FONT, color: C.muted, italic: true,
    });

    const rounds = data.rounds || [];
    // Show up to 12 rounds in a grid (3 rows x 4 cols)
    const maxDisplay = 12;
    const displayed = rounds.slice(0, maxDisplay);
    const cols = 4;
    displayed.forEach((r, i) => {
      const col = i % cols;
      const row = Math.floor(i / cols);
      const xx = 0.5 + col * 2.35;
      const yy = 1.5 + row * 1.15;
      const color = statusColor(r.review_status);

      s.addShape(pres.shapes.RECTANGLE, {
        x: xx, y: yy, w: 2.1, h: 0.95,
        fill: { color: C.cardBg }, shadow: mkShadow(),
      });
      s.addShape(pres.shapes.RECTANGLE, {
        x: xx, y: yy, w: 2.1, h: 0.06,
        fill: { color },
      });
      s.addText(`Round ${r.round_index}`, {
        x: xx + 0.1, y: yy + 0.1, w: 1.2, h: 0.3,
        fontSize: 12, fontFace: FONT_BOLD, color: C.navy, bold: true, margin: 0,
      });
      // Status badge
      s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
        x: xx + 1.2, y: yy + 0.12, w: 0.8, h: 0.25,
        fill: { color }, rectRadius: 0.05,
      });
      s.addText(r.review_status || "?", {
        x: xx + 1.2, y: yy + 0.12, w: 0.8, h: 0.25,
        fontSize: 9, fontFace: FONT_BOLD, color: C.white, bold: true,
        align: "center", valign: "middle",
      });
      // Check result
      const checkText = r.checks_passed ? "checks: pass" : "checks: fail";
      const checkColor = r.checks_passed ? C.green : C.red;
      s.addText(checkText, {
        x: xx + 0.1, y: yy + 0.5, w: 1.9, h: 0.2,
        fontSize: 9, fontFace: FONT, color: checkColor, margin: 0,
      });
      // Confidence
      if (r.review_confidence !== undefined) {
        s.addText(`confidence: ${(r.review_confidence * 100).toFixed(0)}%`, {
          x: xx + 0.1, y: yy + 0.7, w: 1.9, h: 0.2,
          fontSize: 9, fontFace: FONT, color: C.muted, margin: 0,
        });
      }
    });

    if (rounds.length > maxDisplay) {
      s.addText(`+ ${rounds.length - maxDisplay} more rounds not shown`, {
        x: 0.8, y: 5.0, w: 8.4, h: 0.3,
        fontSize: 11, fontFace: FONT, color: C.muted, italic: true, align: "center",
      });
    }
  }

  // ════════════════════════════════════════
  // SLIDE 4: Acceptance Checks
  // ════════════════════════════════════════
  sn++;
  {
    const s = pres.addSlide({ masterName: "LIGHT" });
    addSlideNum(s, sn, TOTAL);
    s.addText("Acceptance Checks", {
      x: 0.8, y: 0.3, w: 8.4, h: 0.7,
      fontSize: 28, fontFace: FONT_BOLD, color: C.navy, bold: true,
    });
    s.addText("Final round check command results", {
      x: 0.8, y: 0.95, w: 8.4, h: 0.35,
      fontSize: 14, fontFace: FONT, color: C.muted, italic: true,
    });

    const checks = data.final_checks || [];
    if (checks.length === 0) {
      s.addText("No acceptance checks configured for this run.", {
        x: 0.8, y: 2.0, w: 8.4, h: 0.5,
        fontSize: 16, fontFace: FONT, color: C.muted, align: "center",
      });
    } else {
      // Table header
      s.addShape(pres.shapes.RECTANGLE, {
        x: 0.8, y: 1.5, w: 8.4, h: 0.45,
        fill: { color: C.navy },
      });
      s.addText("Command", {
        x: 0.8, y: 1.5, w: 5.5, h: 0.45,
        fontSize: 12, fontFace: FONT_BOLD, color: C.white, bold: true,
        valign: "middle", margin: [0, 0, 0, 10],
      });
      s.addText("Exit Code", {
        x: 6.3, y: 1.5, w: 1.4, h: 0.45,
        fontSize: 12, fontFace: FONT_BOLD, color: C.white, bold: true,
        align: "center", valign: "middle",
      });
      s.addText("Result", {
        x: 7.7, y: 1.5, w: 1.5, h: 0.45,
        fontSize: 12, fontFace: FONT_BOLD, color: C.white, bold: true,
        align: "center", valign: "middle",
      });

      checks.slice(0, 8).forEach((check, i) => {
        const yy = 2.0 + i * 0.45;
        const bg = i % 2 === 0 ? C.cardBg : C.lightBg;
        s.addShape(pres.shapes.RECTANGLE, {
          x: 0.8, y: yy, w: 8.4, h: 0.42,
          fill: { color: bg },
        });
        s.addText(truncate(check.command || "", 60), {
          x: 0.8, y: yy, w: 5.5, h: 0.42,
          fontSize: 11, fontFace: FONT_MONO, color: "444444",
          valign: "middle", margin: [0, 0, 0, 10],
        });
        s.addText(String(check.exit_code), {
          x: 6.3, y: yy, w: 1.4, h: 0.42,
          fontSize: 11, fontFace: FONT_MONO, color: "444444",
          align: "center", valign: "middle",
        });
        const passed = check.passed;
        s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
          x: 7.9, y: yy + 0.06, w: 1.1, h: 0.3,
          fill: { color: passed ? C.green : C.red }, rectRadius: 0.05,
        });
        s.addText(passed ? "PASS" : "FAIL", {
          x: 7.9, y: yy + 0.06, w: 1.1, h: 0.3,
          fontSize: 10, fontFace: FONT_BOLD, color: C.white, bold: true,
          align: "center", valign: "middle",
        });
      });
    }
  }

  // ════════════════════════════════════════
  // SLIDE 5: Reviewer & Planner Summary
  // ════════════════════════════════════════
  sn++;
  {
    const s = pres.addSlide({ masterName: "WHITE" });
    addSlideNum(s, sn, TOTAL);
    s.addText("Reviewer & Planner Summary", {
      x: 0.8, y: 0.3, w: 8.4, h: 0.7,
      fontSize: 28, fontFace: FONT_BOLD, color: C.navy, bold: true,
    });

    // Reviewer card
    s.addShape(pres.shapes.RECTANGLE, {
      x: 0.8, y: 1.2, w: 4.0, h: 3.5,
      fill: { color: C.cardBg }, shadow: mkShadow(),
    });
    s.addShape(pres.shapes.RECTANGLE, {
      x: 0.8, y: 1.2, w: 4.0, h: 0.08,
      fill: { color: C.orange },
    });
    s.addText("Reviewer", {
      x: 1.1, y: 1.35, w: 3.4, h: 0.4,
      fontSize: 18, fontFace: FONT_BOLD, color: C.navy, bold: true,
    });
    const reviewerLines = [
      `Verdict: ${data.reviewer_verdict || "N/A"}`,
      `Reason: ${truncate(data.reviewer_reason || "N/A", 150)}`,
      `Next Action: ${truncate(data.reviewer_next_action || "N/A", 150)}`,
    ];
    s.addText(reviewerLines.join("\n\n"), {
      x: 1.1, y: 1.85, w: 3.4, h: 2.6,
      fontSize: 11, fontFace: FONT, color: "555555",
    });

    // Planner card
    s.addShape(pres.shapes.RECTANGLE, {
      x: 5.2, y: 1.2, w: 4.0, h: 3.5,
      fill: { color: C.cardBg }, shadow: mkShadow(),
    });
    s.addShape(pres.shapes.RECTANGLE, {
      x: 5.2, y: 1.2, w: 4.0, h: 0.08,
      fill: { color: C.purple },
    });
    s.addText("Planner", {
      x: 5.5, y: 1.35, w: 3.4, h: 0.4,
      fontSize: 18, fontFace: FONT_BOLD, color: C.navy, bold: true,
    });
    const plannerLines = [
      `Follow-up Required: ${data.planner_follow_up_required !== undefined ? data.planner_follow_up_required : "N/A"}`,
      `Next Explore: ${truncate(data.planner_next_explore || "N/A", 150)}`,
      `Main Instruction: ${truncate(data.planner_main_instruction || "N/A", 150)}`,
    ];
    s.addText(plannerLines.join("\n\n"), {
      x: 5.5, y: 1.85, w: 3.4, h: 2.6,
      fontSize: 11, fontFace: FONT, color: "555555",
    });
  }

  // ════════════════════════════════════════
  // SLIDE 6: Key Metrics
  // ════════════════════════════════════════
  sn++;
  {
    const s = pres.addSlide({ masterName: "LIGHT" });
    addSlideNum(s, sn, TOTAL);
    s.addText("Key Metrics", {
      x: 0.8, y: 0.3, w: 8.4, h: 0.7,
      fontSize: 28, fontFace: FONT_BOLD, color: C.navy, bold: true,
    });

    const metrics = [
      [String(data.total_rounds || 0), "Total Rounds", C.accent],
      [String(data.checks_passed || 0), "Checks Passed", C.green],
      [String(data.checks_failed || 0), "Checks Failed", data.checks_failed > 0 ? C.red : C.muted],
      [data.plan_mode || "off", "Plan Mode", C.purple],
    ];
    metrics.forEach(([value, label, color], i) => {
      const xx = 0.5 + i * 2.3;
      s.addShape(pres.shapes.RECTANGLE, {
        x: xx, y: 1.3, w: 2.05, h: 2.0,
        fill: { color: C.cardBg }, shadow: mkShadow(),
      });
      s.addText(value, {
        x: xx, y: 1.5, w: 2.05, h: 1.0,
        fontSize: 36, fontFace: FONT_BOLD, color, bold: true,
        align: "center", valign: "middle",
      });
      s.addText(label, {
        x: xx, y: 2.5, w: 2.05, h: 0.5,
        fontSize: 14, fontFace: FONT, color: C.muted,
        align: "center", valign: "middle",
      });
    });

    // Duration if available
    if (data.duration_display) {
      s.addShape(pres.shapes.RECTANGLE, {
        x: 0.8, y: 3.6, w: 8.4, h: 0.6,
        fill: { color: C.cardBg }, shadow: mkShadow(),
      });
      s.addText(`Duration: ${data.duration_display}`, {
        x: 0.8, y: 3.6, w: 8.4, h: 0.6,
        fontSize: 16, fontFace: FONT, color: C.navy,
        align: "center", valign: "middle",
      });
    }
  }

  // ════════════════════════════════════════
  // SLIDE 7 (optional): Operator Messages
  // ════════════════════════════════════════
  if (hasOperatorMessages) {
    sn++;
    const s = pres.addSlide({ masterName: "WHITE" });
    addSlideNum(s, sn, TOTAL);
    s.addText("Operator Messages", {
      x: 0.8, y: 0.3, w: 8.4, h: 0.7,
      fontSize: 28, fontFace: FONT_BOLD, color: C.navy, bold: true,
    });
    s.addText("Messages sent during the run via control channels", {
      x: 0.8, y: 0.95, w: 8.4, h: 0.35,
      fontSize: 14, fontFace: FONT, color: C.muted, italic: true,
    });

    const msgs = data.operator_messages.slice(0, 10);
    msgs.forEach((msg, i) => {
      const yy = 1.5 + i * 0.42;
      const bg = i % 2 === 0 ? C.cardBg : C.lightBg;
      s.addShape(pres.shapes.RECTANGLE, {
        x: 0.8, y: yy, w: 8.4, h: 0.38,
        fill: { color: bg },
      });
      s.addText(truncate(msg, 120), {
        x: 1.0, y: yy, w: 8.0, h: 0.38,
        fontSize: 10, fontFace: FONT, color: "444444",
        valign: "middle",
      });
    });

    if (data.operator_messages.length > 10) {
      s.addText(`+ ${data.operator_messages.length - 10} more messages not shown`, {
        x: 0.8, y: 5.0, w: 8.4, h: 0.3,
        fontSize: 11, fontFace: FONT, color: C.muted, italic: true, align: "center",
      });
    }
  }

  // ════════════════════════════════════════
  // SLIDE 8: Conclusion
  // ════════════════════════════════════════
  sn++;
  {
    const s = pres.addSlide({ masterName: "DARK" });
    addSlideNum(s, sn, TOTAL, true);
    s.addText("Conclusion", {
      x: 0.8, y: 0.5, w: 8.4, h: 0.8,
      fontSize: 36, fontFace: FONT_BOLD, color: C.white, bold: true,
    });

    const finalStatus = data.success ? "Run Completed Successfully" : "Run Did Not Complete";
    const finalColor = data.success ? C.green : C.orange;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, {
      x: 0.8, y: 1.5, w: 8.4, h: 0.6,
      fill: { color: finalColor }, rectRadius: 0.1,
    });
    s.addText(finalStatus, {
      x: 0.8, y: 1.5, w: 8.4, h: 0.6,
      fontSize: 20, fontFace: FONT_BOLD, color: C.white, bold: true,
      align: "center", valign: "middle",
    });

    // Summary items
    const items = [
      `Stop Reason: ${truncate(data.stop_reason || "N/A", 100)}`,
      `Rounds Executed: ${data.total_rounds || 0}`,
      `Final Reviewer Status: ${data.reviewer_verdict || "N/A"}`,
      `Checks: ${data.checks_passed || 0} passed, ${data.checks_failed || 0} failed`,
    ];
    if (data.planner_next_explore && data.planner_next_explore !== "N/A") {
      items.push(`Planner Next Explore: ${truncate(data.planner_next_explore, 80)}`);
    }

    s.addText(items.map((t, i) => ({
      text: t, options: { bullet: true, breakLine: i < items.length - 1, color: "C8E6F5" }
    })), {
      x: 0.8, y: 2.4, w: 8.4, h: 2.5,
      fontSize: 14, fontFace: FONT, color: C.ice, paraSpaceAfter: 10,
    });

    s.addText("Generated by ArgusBot", {
      x: 0.8, y: 5.0, w: 8.4, h: 0.3,
      fontSize: 10, fontFace: FONT, color: C.muted, align: "center",
    });
  }

  // ── Save ──
  pres.writeFile({ fileName: outputPath }).then(() => {
    console.log("PPTX report generated:", outputPath);
  }).catch(err => {
    console.error("Failed to write PPTX:", err);
    process.exit(1);
  });
}

main();
