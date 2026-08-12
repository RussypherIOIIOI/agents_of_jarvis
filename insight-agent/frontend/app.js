(function () {
  "use strict";

  const fileInput = document.getElementById("fileInput");
  const datasetInfo = document.getElementById("datasetInfo");
  const messages = document.getElementById("messages");
  const askForm = document.getElementById("askForm");
  const questionInput = document.getElementById("questionInput");
  const askButton = document.getElementById("askButton");
  const sampleList = document.getElementById("sampleQuestions");

  let datasetId = null;

  function addMessage(text, cls) {
    const div = document.createElement("div");
    div.className = "msg " + cls;
    div.textContent = text;
    messages.appendChild(div);
    messages.scrollTop = messages.scrollHeight;
    return div;
  }

  function addAgentMessage(data) {
    const div = document.createElement("div");
    div.className = "msg " + (data.error ? "error" : "agent");

    const answer = document.createElement("div");
    answer.textContent = data.error ? "Error: " + data.error : data.answer;
    div.appendChild(answer);

    if (data.chart_png_base64) {
      const img = document.createElement("img");
      img.src = "data:image/png;base64," + data.chart_png_base64;
      img.alt = "Generated chart";
      div.appendChild(img);
    }

    if (data.code) {
      const details = document.createElement("details");
      const summary = document.createElement("summary");
      summary.textContent = "View generated code";
      const pre = document.createElement("pre");
      pre.textContent = data.code;
      details.appendChild(summary);
      details.appendChild(pre);
      div.appendChild(details);
    }

    messages.appendChild(div);
    messages.scrollTop = messages.scrollHeight;
  }

  fileInput.addEventListener("change", async function () {
    const file = fileInput.files[0];
    if (!file) return;
    addMessage("Uploading " + file.name + "...", "system");

    const form = new FormData();
    form.append("file", file);
    try {
      const resp = await fetch("/upload", { method: "POST", body: form });
      const data = await resp.json();
      if (!resp.ok) throw new Error(data.detail || "upload failed");

      datasetId = data.dataset_id;
      datasetInfo.classList.remove("hidden");
      datasetInfo.innerHTML =
        "<strong>" + data.name + "</strong><br>" +
        data.rows + " rows, " + data.columns.length + " columns" +
        '<div class="cols">' + data.columns.join(", ") + "</div>";

      questionInput.disabled = false;
      askButton.disabled = false;
      addMessage("Loaded '" + data.name + "'. Ask a question below.", "system");
    } catch (err) {
      addMessage("Upload error: " + err.message, "error");
    }
  });

  async function ask(question) {
    if (!datasetId) {
      addMessage("Please upload a CSV first.", "system");
      return;
    }
    addMessage(question, "user");
    questionInput.value = "";
    askButton.disabled = true;
    const typing = addMessage("Analyzing...", "typing");

    try {
      const resp = await fetch("/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ dataset_id: datasetId, question: question }),
      });
      const data = await resp.json();
      typing.remove();
      if (!resp.ok) throw new Error(data.detail || "request failed");
      addAgentMessage(data);
    } catch (err) {
      typing.remove();
      addMessage("Error: " + err.message, "error");
    } finally {
      askButton.disabled = false;
    }
  }

  askForm.addEventListener("submit", function (e) {
    e.preventDefault();
    const q = questionInput.value.trim();
    if (q) ask(q);
  });

  sampleList.addEventListener("click", function (e) {
    if (e.target.tagName === "LI" && !questionInput.disabled) {
      ask(e.target.textContent);
    }
  });
})();
