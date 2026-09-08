
// Auto-detect the backend host from whatever host served this page.
// Works whether you're on the laptop (localhost) or a phone on the same
// WiFi (LAN IP) — no manual IP editing needed. Backend must run on port 8000.
const API_BASE_URL = `${window.location.protocol}//${window.location.hostname}:8000`;

/**
 * Send a product image/document to the LegalLens backend.
 * Backend endpoint: POST /api/scan
 */
async function scanDocument(file, debug = false) {
    if (!file) {
        throw new Error("No file selected.");
    }

    const formData = new FormData();

    // IMPORTANT:
    // Backend expects the multipart field to be named "file".
    formData.append("file", file);

    const url = debug
        ? `${API_BASE_URL}/api/scan?debug=true`
        : `${API_BASE_URL}/api/scan`;

    const response = await fetch(url, {
        method: "POST",
        body: formData
    });

    let data;

    try {
        data = await response.json();
    } catch {
        throw new Error(
            `Backend returned a non-JSON response (HTTP ${response.status}).`
        );
    }

    if (!response.ok) {
        const message =
            data?.detail ||
            `Scan failed with HTTP ${response.status}.`;

        throw new Error(message);
    }

    return data;
}