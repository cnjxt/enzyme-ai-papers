const searchInput = document.querySelector("#paper-search");
const filterButtons = Array.from(document.querySelectorAll("[data-filter]"));
const cards = Array.from(document.querySelectorAll(".paper-card"));
let activeFilter = "all";

function applyFilters() {
  const query = searchInput ? searchInput.value.trim().toLowerCase() : "";
  for (const card of cards) {
    const searchText = card.dataset.search || "";
    const tags = card.dataset.tags || "";
    const matchesQuery = !query || searchText.includes(query);
    const matchesFilter = activeFilter === "all" || tags.split(" ").includes(activeFilter);
    card.hidden = !(matchesQuery && matchesFilter);
  }
}

if (searchInput) {
  searchInput.addEventListener("input", applyFilters);
}

for (const button of filterButtons) {
  button.addEventListener("click", () => {
    activeFilter = button.dataset.filter || "all";
    for (const item of filterButtons) {
      item.classList.toggle("is-active", item === button);
    }
    applyFilters();
  });
}

const submitForm = document.querySelector("#paper-submit-form");

function hostLabel(value) {
  try {
    return new URL(value).hostname.replace(/^www\./, "");
  } catch (_error) {
    return "paper";
  }
}

function issueBody(fields) {
  return [
    "### Paper URL",
    "",
    fields.url,
    "",
    "### Paper title",
    "",
    fields.title || "_No response_",
    "",
    "### Why this paper matters",
    "",
    fields.note || "_No response_",
    "",
    "### Suggested tags",
    "",
    fields.tags || "_No response_",
    "",
    "### Code or project link",
    "",
    fields.code || "_No response_",
  ].join("\n");
}

if (submitForm) {
  submitForm.addEventListener("submit", (event) => {
    event.preventDefault();
    const formData = new FormData(submitForm);
    const fields = {
      url: String(formData.get("url") || "").trim(),
      title: String(formData.get("title") || "").trim(),
      note: String(formData.get("note") || "").trim(),
      tags: String(formData.get("tags") || "").trim(),
      code: String(formData.get("code") || "").trim(),
    };
    const status = document.querySelector("#submit-form-status");
    if (!fields.url) {
      if (status) status.textContent = "Paper URL is required.";
      return;
    }
    let target;
    try {
      target = new URL(submitForm.dataset.issueUrl || "");
    } catch (_error) {
      if (status) status.textContent = "Submission link is not configured.";
      return;
    }
    target.searchParams.set("title", `[Paper]: ${fields.title || hostLabel(fields.url)}`);
    target.searchParams.set("body", issueBody(fields));
    window.open(target.toString(), "_blank", "noopener");
    if (status) status.textContent = "Opening GitHub submission...";
  });
}
