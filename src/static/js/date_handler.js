/**
 * Gets the timezone offset in hours.
 * @returns {number} The timezone offset in hours.
 */
function getTimezoneOffsetHours() {
    const today = new Date();
    const timezoneOffset = today.getTimezoneOffset();

    // Calculate offset hours
    const offsetHours = timezoneOffset / 60;
    return -offsetHours;
}

function getFormDateInputs() {
    return document.querySelectorAll("input[type='date'], input[data-role='datetimepicker'], input[data-role='datepicker']");
}

function correctDateInputValue(dateInput, isSubmit) {
    const date = dateInput.value;
    const parsedDate = moment(date);
    if (correctedDate.toString() === "Invalid date") {
        return;
    }
    const offsetHours = getTimezoneOffsetHours();
    // Subtract if we submit to convert back to UTC
    // Add to convert from UTC to local time
    const correctedDate = parsedDate.add(isSubmit ? -offsetHours : offsetHours, "hours");
    const targetDateFormat = dateInput.getAttribute("data-date-format") || "YYYY-MM-DD HH:mm:ss";
    dateInput.value = correctedDate.format(targetDateFormat);
}

function correctDateInputValues(isSubmit) {
    const dateInputs = getFormDateInputs();
    dateInputs.forEach(dateInput => {
        correctDateInputValue(dateInput, isSubmit);
    });
}

document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll("td").forEach(date => {
        const parsedDate = moment(date.innerHTML, "YYYY-MM-DD HH:mm:ss", true);
        if (parsedDate.toString().includes("Invalid date")) {
            return;
        }
        // Add timezone offset hours to parsed date
        const correctedDate = parsedDate.add(getTimezoneOffsetHours(), "hours");
        date.innerText = correctedDate.format("DD-MM-YYYY HH:mm:ss");
    });
    correctDateInputValues();
});

document.addEventListener("submit", event => {
    correctDateInputValues(true);
});