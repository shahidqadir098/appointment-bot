async function send(customValue = null) {
    let input = document.getElementById("msg");
    let msg = customValue || input.value;

    if (!msg.trim()) return;

    let chat = document.getElementById("chat");

    chat.innerHTML += `<div class="message user">${msg}</div>`;

    let res = await fetch("/chat", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({ message: msg, user_id: "user1" })
    });

    let data = await res.json();

    chat.innerHTML += `<div class="message bot">${data.reply}</div>`;

    input.value = "";
    chat.scrollTop = chat.scrollHeight;

    // 🎯 SHOW PICKERS BASED ON BOT MESSAGE
    if (data.reply.includes("date")) {
        document.getElementById("datePicker").style.display = "block";
    }

    if (data.reply.includes("time")) {
        document.getElementById("timePicker").style.display = "block";
    }
}

document.getElementById("msg").addEventListener("keypress", function(e) {
    if (e.key === "Enter") send();
});

document.getElementById("datePicker").addEventListener("change", function() {
    let date = this.value;
    
    // Convert YYYY-MM-DD → DD-MM-YYYY
    let parts = date.split("-");
    let formatted = `${parts[2]}-${parts[1]}-${parts[0]}`;
    
    this.style.display = "none";
    send(formatted);
});

document.getElementById("timePicker").addEventListener("change", function() {
    let time = this.value;

    this.style.display = "none";
    send(time);
});