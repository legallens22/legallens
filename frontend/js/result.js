
document.addEventListener("DOMContentLoaded", () => {
    const storedReport = sessionStorage.getItem("legallensReport");
 
    const checklistEl = document.getElementById("ruleChecklist");
    const verdictEl = document.getElementById("verdictText");
    const summaryEl = document.getElementById("verdictSummaryText");
    const badgeEl = document.getElementById("passFailBadge");
 
    if (!storedReport) {
        if (summaryEl) {
            summaryEl.textContent = "No scan report found. Please scan a label first.";
        }
        if (checklistEl) {
            checklistEl.innerHTML = `<p class="font-body-sm text-on-surface-variant">
                No report data — go back and scan a label.
            </p>`;
        }
        console.error("No LegalLens report found.");
        return;
    }
 
    let report;
    try {
        report = JSON.parse(storedReport);
    } catch (error) {
        console.error("Failed to parse LegalLens report:", error);
        if (summaryEl) summaryEl.textContent = "Could not read the scan report (bad data).";
        return;
    }
 
    console.log("REAL REPORT RECEIVED:", report);
    window.legalLensReport = report; // for debugging in devtools
 
    // -----------------------------------------------------------------
    // The backend's exact field names for each checklist row haven't
    // been confirmed yet, so this pulls from several likely key names.
    // If rows show up blank/wrong, open devtools -> Console, look at
    // "REAL REPORT RECEIVED", and tell me the actual key names used
    // inside report.fields — this mapping takes 30 seconds to fix once
    // we know them.
    // -----------------------------------------------------------------
    function pick(obj, keys, fallback = undefined) {
        for (const k of keys) {
            if (obj && obj[k] !== undefined && obj[k] !== null && obj[k] !== "") {
                return obj[k];
            }
        }
        return fallback;
    }
 
    function normalizeFields(fields) {
        if (!fields) return [];
        // Backend might return an array of field objects, or a dict keyed by field name.
        const list = Array.isArray(fields)
            ? fields
            : Object.entries(fields).map(([key, val]) => ({ name: key, ...val }));
 
        return list.map((f) => {
            const name = pick(f, ["name", "field", "field_name", "label", "title"], "Unnamed field");
            const rule = pick(f, ["rule", "rule_ref", "rule_id", "section", "clause"], "");
            const note = pick(f, ["note", "reason", "message", "details", "remark", "explanation"], "");
 
            let passed = pick(f, ["passed", "compliant", "ok", "is_valid"]);
            if (passed === undefined) {
                const status = pick(f, ["status", "result", "verdict"], "");
                if (typeof status === "string") {
                    passed = ["pass", "ok", "compliant", "true", "valid"].includes(status.toLowerCase());
                }
            }
 
            return { name, rule, note, passed: !!passed };
        });
    }
 
    function renderChecklist(fields) {
        if (!checklistEl) return;
 
        if (!fields.length) {
            checklistEl.innerHTML = `<p class="font-body-sm text-on-surface-variant">
                No per-field results were returned by the scan.
            </p>`;
            return;
        }
 
        checklistEl.innerHTML = fields.map((f) => {
            if (f.passed) {
                return `
                <div class="bg-surface-container-lowest p-space-md shadow-sm flex flex-col gap-space-xs">
                    <div class="flex items-start justify-between gap-space-sm">
                        <div class="flex items-start gap-space-sm min-w-0">
                            <div class="w-7 h-7 bg-primary/10 text-primary flex items-center justify-center flex-shrink-0 mt-space-2xs">
                                <span class="material-symbols-outlined text-[18px]" style="font-variation-settings: 'FILL' 1;">check_circle</span>
                            </div>
                            <div class="min-w-0">
                                <span class="font-title-md text-title-md text-on-surface block font-semibold leading-tight">${escapeHtml(f.name)}</span>
                                ${f.rule ? `<span class="font-code-md text-label-sm text-on-surface-variant">${escapeHtml(f.rule)}</span>` : ""}
                            </div>
                        </div>
                        <span class="font-code-md text-label-sm bg-surface-container-high text-primary px-space-xs py-space-2xs uppercase font-bold flex-shrink-0">PASS &#10003;</span>
                    </div>
                    ${f.note ? `<p class="font-body-sm text-on-surface-variant pl-9 leading-relaxed">${escapeHtml(f.note)}</p>` : ""}
                </div>`;
            }
 
            return `
            <div class="bg-error-container text-on-error-container p-space-md shadow-md flex flex-col gap-space-xs">
                <div class="flex items-start justify-between gap-space-sm">
                    <div class="flex items-start gap-space-sm min-w-0">
                        <div class="w-7 h-7 bg-tertiary text-on-tertiary flex items-center justify-center flex-shrink-0 mt-space-2xs">
                            <span class="material-symbols-outlined text-[18px]" style="font-variation-settings: 'FILL' 1;">cancel</span>
                        </div>
                        <div class="min-w-0">
                            <span class="font-title-md text-title-md text-on-error-container block font-bold leading-tight">${escapeHtml(f.name)}</span>
                            ${f.rule ? `<span class="font-code-md text-label-sm text-tertiary font-bold">${escapeHtml(f.rule)}</span>` : ""}
                        </div>
                    </div>
                    <span class="font-code-md text-label-sm bg-tertiary text-on-tertiary px-space-xs py-space-2xs uppercase font-bold flex-shrink-0">FAIL &#10007;</span>
                </div>
                ${f.note ? `<p class="font-body-sm text-on-error-container pl-9 font-medium leading-relaxed">${escapeHtml(f.note)}</p>` : ""}
            </div>`;
        }).join("");
    }
 
    function escapeHtml(str) {
        return String(str)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;");
    }
 
    // -----------------------------
    // Overall verdict
    // -----------------------------
    if (verdictEl) {
        verdictEl.textContent = report.overall_verdict || "UNKNOWN";
    }
 
    // -----------------------------
    // Fields -> checklist + pass/fail badge + summary line
    // -----------------------------
    const fields = normalizeFields(report.fields);
    renderChecklist(fields);
 
    const passCount = fields.filter((f) => f.passed).length;
    const failCount = fields.length - passCount;
 
    if (badgeEl) {
        badgeEl.textContent = `${passCount} PASS / ${failCount} FAIL`;
    }
 
    if (summaryEl) {
        summaryEl.textContent = report.summary
            || (failCount > 0
                ? `${failCount} mandatory declaration${failCount === 1 ? "" : "s"} missing or non-conforming.`
                : "All mandatory declarations conform.");
    }
 
    console.table(report.fields);
});
 