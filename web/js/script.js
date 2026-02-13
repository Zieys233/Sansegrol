document.addEventListener("DOMContentLoaded", () => {
    const btn = document.getElementById("welcomeBtn");
    if (btn) {
        btn.addEventListener("click", () => {
            alert("Welcome to Sansegrol!");
        });
    }

    console.log("Sansegrol has been loaded and is ready to go.");
});