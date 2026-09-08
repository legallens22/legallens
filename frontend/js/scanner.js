document.addEventListener("DOMContentLoaded", () => {
    const uploadBtn = document.getElementById("uploadBtn");

    if (!uploadBtn) {
        console.error("Upload button not found.");
        return;
    }

    // Create a hidden file picker
    const fileInput = document.createElement("input");
    fileInput.type = "file";
    fileInput.accept = "image/jpeg,image/png,image/webp,application/pdf";
    fileInput.style.display = "none";

    document.body.appendChild(fileInput);

    // Upload Photo button
    uploadBtn.addEventListener("click", () => {
        fileInput.click();
    });

    // Shutter button — this UI has no live camera feed wired up (getUserMedia),
    // so on click it just opens the same native camera/gallery picker as
    // Upload Photo. The flash animation (handled separately in scanner.html)
    // still plays for visual feedback.
    const shutterBtn = document.getElementById("shutterBtn");
    if (shutterBtn) {
        shutterBtn.addEventListener("click", () => {
            fileInput.click();
        });
    }

    // When the user selects a file
    fileInput.addEventListener("change", async () => {
        const file = fileInput.files[0];

        if (!file) {
            return;
        }

        console.log("Selected file:", file.name);

        // Maximum 10 MB
        if (file.size > 10 * 1024 * 1024) {
            alert("File is too large. Maximum allowed size is 10 MB.");
            fileInput.value = "";
            return;
        }

        const originalContent = uploadBtn.innerHTML;

        // Show loading state
        uploadBtn.disabled = true;
        uploadBtn.innerHTML = `
            <span class="material-symbols-outlined animate-spin">
                progress_activity
            </span>
            <span>Scanning...</span>
        `;

        try {
            // Send file to FastAPI
            const response = await scanDocument(file);

            console.log("LegalLens API response:", response);

            // Store the REAL report
            sessionStorage.setItem(
                "legallensReport",
                JSON.stringify(response.report)
            );

            // Go to result page
            window.location.href = "result.html";

        } catch (error) {
            console.error("Scan failed:", error);

            alert(
                "Scan failed.\n\n" +
                error.message +
                "\n\nMake sure your FastAPI server is running."
            );

            uploadBtn.disabled = false;
            uploadBtn.innerHTML = originalContent;
        }
    });
});