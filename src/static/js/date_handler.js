document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll("td").forEach(date => {
        const parsedDate = moment(date.innerHTML);
        // Add 3 hours to the date to account for the time zone difference
        const correctedDate = parsedDate.add(3, "hours");
        if (correctedDate.toString() === "Invalid date") {
            return;
        }
        date.innerText = correctedDate.format("DD-MM-YYYY HH:mm:ss");
    });
});