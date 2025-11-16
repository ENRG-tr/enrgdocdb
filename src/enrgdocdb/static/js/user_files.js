const MAX_FILE_SIZE = 1024 * 1024 * 50;
const MAX_FILE_COUNT = 10;

function initializeUserFiles(formId, fileToken, documentTokens, uploadUrl) {
    const form = document.getElementById(formId);
    const filesInput = form.querySelector("#files");
    const submitButton = form.querySelector("[type='submit']");

    if (!filesInput) {
        console.error("No file input found in form");
        return;
    }

    if (!submitButton) {
        console.error("No submit button found in form");
        return;
    }

    // We will hide the file input and add a button to select files
    const filesInputButton = document.createElement("button");
    filesInputButton.type = "button";
    filesInputButton.classList.add("btn", "btn-primary", "d-flex");
    filesInputButton.innerText = "Select Files";
    filesInputButton.addEventListener("click", () => filesInput.click());

    const filesInputText = document.createElement("span");
    filesInputText.classList.add("d-inline-block", "mx-2");

    const filesPseudoInputContainer = document.createElement("div");
    filesPseudoInputContainer.classList.add("d-flex", "gap-2", "align-items-center");
    filesInput.parentNode.insertBefore(filesPseudoInputContainer, filesInput);
    filesPseudoInputContainer.appendChild(filesInputButton);
    filesPseudoInputContainer.appendChild(filesInputText);


    // We won't be sending files to the server the traditional way, so we don't
    // need to set the name attribute of the file input
    filesInput.name = "";

    const fileTokenElement = document.createElement("input");
    fileTokenElement.type = "hidden";
    fileTokenElement.name = "file_token";
    fileTokenElement.value = fileToken;
    form.appendChild(fileTokenElement);

    const tokenToFileElement = document.createElement("input");
    tokenToFileElement.type = "hidden";
    tokenToFileElement.name = "token_to_file";
    tokenToFileElement.value = "{}";
    form.appendChild(tokenToFileElement);

    let tokenToFile = {};
    let documentTokenIndex = 0;
    let uploadedFileCount = 0;

    const uploadedFiles = new Set();
    const ignoredFiles = new Set();

    function uploadFileChunk(file, chunkIndex, documentToken, callback) {
        const formData = new FormData();
        formData.append("file_name", file.name);
        formData.append("file_token", fileToken);
        formData.append("document_token", documentToken);
        // Slice file into chunks
        const chunkSize = 1024 * 1024 * 1; // 1 MB
        const fileSlice = file.slice(chunkIndex * chunkSize, (chunkIndex + 1) * chunkSize);
        // Convert fileSlice to base64
        const reader = new FileReader();
        reader.readAsDataURL(fileSlice);
        reader.onloadend = () => {
            const base64 = reader.result.split(",")[1];
            if (!base64.length) {
                // Upload has finished, no more chunks to upload
                callback();
                return;
            }
            formData.append("file", base64);
            // Send the form data
            fetch(uploadUrl, {
                method: "POST",
                body: formData
            }).then(response => {
                if (response.status === 204) {
                    uploadFileChunk(file, chunkIndex + 1, documentToken, callback);
                } else if (response.status === 410) {
                    alert("This new document form has expired, please refresh the page and try again.");
                    updateForm(true);
                } else if (response.status === 413) {
                    alert("File size exceeds the maximum file size.");
                    updateForm(true);
                } else {
                    throw new Error();
                }
            }).catch(() => {
                alert(`Upload of ${file.name} failed, please try again.`);
                updateForm(true);
            });

        };
    }

    function updateForm(failed = false) {
        const disabled = uploadedFileCount < Object.keys(tokenToFile).length || failed;
        submitButton.disabled = disabled;
        const loadingIcon = `<i class="fas fa-spinner fa-spin fa-fw"></i>`;
        filesInputText.innerHTML = `
            ${disabled ? loadingIcon : ""}
            <strong>Selected Files (${uploadedFileCount}):</strong> ${Array.from(uploadedFiles).join(" · ")}
        `;
        if (failed) {
            submitButton.value = "Upload failed, please refresh the page";
            filesInputText.innerText = "Upload failed"
        } else if (disabled) {
            submitButton.value = `Uploading ${uploadedFileCount + 1} of ${Object.keys(tokenToFile).length}...`;
        } else {
            submitButton.value = "Submit";
        }
    }

    function fileUploadCallback() {
        uploadedFileCount++;
        updateForm();
    }

    filesInput.addEventListener("change", (event) => {
        const files = Array.from(event.target.files);
        let filesToBeDeleted = [];
        // For each file selected, convert them to base64 and add them to the form
        for (let i = 0; i < files.length; i++) {
            const file = files[i];
            if (uploadedFiles.has(file.name) || ignoredFiles.has(file.name)) {
                continue;
            }
            if (documentTokenIndex >= MAX_FILE_COUNT) {
                alert("Can't upload more files.");
                filesToBeDeleted.push(file);
                break;
            }
            if (file.size > MAX_FILE_SIZE) {
                alert(`File size exceeds the maximum file size (${MAX_FILE_SIZE / 1024 / 1024} MB). This file will not be uploaded.`);
                ignoredFiles.add(file.name);
                continue;
            }
            // Skip files that are already added
            if (form.querySelector(`[data-file-name='${file.name}']`)) {
                continue;
            }

            const documentToken = documentTokens[documentTokenIndex];
            tokenToFile[documentToken] = file.name;

            uploadFileChunk(file, 0, documentTokens[documentTokenIndex], fileUploadCallback);
            documentTokenIndex++;
            uploadedFiles.add(file.name);
            updateForm();
        }
        for (const file of filesToBeDeleted) {
            filesInput.value = filesInput.value.replace(file.name, "");
        }
        form.querySelector("[name='token_to_file']").value = JSON.stringify(tokenToFile);
    });

    form.addEventListener("submit", () => {
        // Remove files from the form
        filesInput.value = "";
    });
}