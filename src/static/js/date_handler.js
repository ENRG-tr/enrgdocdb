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


document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll("td").forEach(date => {
        const parsedDate = moment(date.innerHTML);
        // Add timezone offset hours to parsed date
        const correctedDate = parsedDate.add(getTimezoneOffsetHours(), "hours");
        if (correctedDate.toString() === "Invalid date") {
            return;
        }
        date.innerText = correctedDate.format("DD-MM-YYYY HH:mm:ss");
    });
});