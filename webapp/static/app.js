(() => {
  "use strict";

  const $ = (id) => document.getElementById(id);
  const state = {
    puzzle: null,
    key: null,
    recoveredMessage: null,
    lastRoute: null,
    transitions: 3,
    explorerIndex: 0,
  };

  const viewNames = {
    dashboard: "Dashboard",
    create: "Create puzzle",
    solve: "Solve puzzle",
    explorer: "Encryption explorer",
    settings: "Settings",
  };

  const explorerStages = [
    {
      icon: "⌕",
      title: "Input detection",
      description: "CipherKeys checks the characters in your message. Hangul-only text uses the Korean 2-beolsik route; English, mixed scripts, punctuation and other text use UTF-8 directly.",
      example: "안녕 → Korean route\nHello! → UTF-8 route",
      note: "This is routing logic, not encryption. It makes sure the original text can be restored correctly.",
    },
    {
      icon: "⌨",
      title: "Text preparation",
      description: "Korean-only input is converted to standard 2-beolsik keystrokes. Other input is kept as entered. The resulting text is then encoded as UTF-8 bytes.",
      example: "안녕 → dkssud\nHello → Hello",
      note: "The Korean conversion is a reversible keyboard-input representation. It is not a secret and does not provide security.",
    },
    {
      icon: "▣",
      title: "AES-256-GCM",
      description: "A fresh random 96-bit nonce and a 256-bit secret key are used by AES-GCM. The algorithm encrypts the prepared bytes and produces an authentication tag.",
      example: "Plaintext bytes + key + nonce → ciphertext + tag",
      note: "This is the cryptographic security layer. The tag lets the recipient detect a wrong key or modified authenticated data.",
    },
    {
      icon: "⌁",
      title: "Base32 encoding",
      description: "The binary ciphertext and authentication tag are represented using Base32 characters so the next puzzle transformation can operate on text.",
      example: "Binary data → a-z and 2-7 characters",
      note: "Base32 is an encoding, not encryption. Anyone can reverse it when they know the encoding.",
    },
    {
      icon: "⌨",
      title: "Keyboard layouts",
      description: "CipherKeys applies a random sequence of physical key-position mappings among QWERTY, Dvorak and AZERTY. The sequence is recorded in the current puzzle manifest.",
      example: "QWERTY → DVORAK → AZERTY",
      note: "These reversible mappings add puzzle mechanics only. The layout sequence is currently visible in the JSON metadata.",
    },
    {
      icon: "▤",
      title: "Puzzle package",
      description: "The final JSON contains the transformed puzzle text, public metadata and nonce. The AES key is kept separate and downloaded as a separate .key file.",
      example: "puzzle.json  +  shared.key",
      note: "Share the files through separate channels. The key is secret; the nonce and puzzle metadata are not.",
    },
  ];

  function showToast(message) {
    const toast = $("toast");
    toast.textContent = message;
    toast.classList.add("show");
    window.clearTimeout(showToast.timer);
    showToast.timer = window.setTimeout(() => toast.classList.remove("show"), 2800);
  }

  function setSidebarOpen(open) {
    $("sidebar").classList.toggle("open", open);
    $("mobileMenu").setAttribute("aria-expanded", String(open));
  }

  function navigate(view) {
    if (!viewNames[view]) return;
    document.querySelectorAll(".view").forEach((node) => {
      node.classList.toggle("active", node.id === `view-${view}`);
    });
    document.querySelectorAll("[data-view]").forEach((node) => {
      node.classList.toggle("active", node.dataset.view === view);
      if (node.dataset.view === view) node.setAttribute("aria-current", "page");
      else node.removeAttribute("aria-current");
    });
    $("pageTitle").textContent = viewNames[view];
    setSidebarOpen(false);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  document.querySelectorAll("[data-view]").forEach((node) => {
    node.addEventListener("click", () => navigate(node.dataset.view));
  });
  document.querySelectorAll("[data-go]").forEach((node) => {
    node.addEventListener("click", () => navigate(node.dataset.go));
  });
  document.querySelectorAll("[data-view-link]").forEach((node) => {
    node.addEventListener("click", (event) => {
      event.preventDefault();
      navigate(node.dataset.viewLink);
    });
  });
  $("mobileMenu").addEventListener("click", () => setSidebarOpen(!$("sidebar").classList.contains("open")));
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && $("sidebar").classList.contains("open")) {
      setSidebarOpen(false);
      $("mobileMenu").focus();
    }
  });

  // Preferences are optional conveniences. Defaults are applied without being
  // written to storage, so "follow the system theme" stays in effect until the
  // person actually chooses something.
  function setTheme(theme, persist = true) {
    const safeTheme = theme === "light" ? "light" : "dark";
    document.documentElement.dataset.theme = safeTheme;
    $("themeSelect").value = safeTheme;
    if (!persist) return;
    try { localStorage.setItem("cipherkeys-theme", safeTheme); } catch (_) { /* Preferences are optional. */ }
  }

  function setTransitions(value, persist = true) {
    const parsed = Number(value);
    state.transitions = Number.isInteger(parsed) && parsed >= 2 && parsed <= 4 ? parsed : 3;
    $("transitionSelect").value = String(state.transitions);
    $("defaultTransitions").value = String(state.transitions);
    if (!persist) return;
    try { localStorage.setItem("cipherkeys-transitions", String(state.transitions)); } catch (_) { /* Preferences are optional. */ }
  }

  function systemTheme() {
    try {
      return window.matchMedia && window.matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark";
    } catch (_) {
      return "dark";
    }
  }

  let savedTheme = null;
  let savedTransitions = null;
  try {
    savedTheme = localStorage.getItem("cipherkeys-theme");
    savedTransitions = localStorage.getItem("cipherkeys-transitions");
  } catch (_) { /* App remains usable when storage is disabled. */ }
  setTheme(savedTheme === "light" || savedTheme === "dark" ? savedTheme : systemTheme(), false);
  setTransitions(savedTransitions === null ? 3 : savedTransitions, false);
  $("themeSelect").addEventListener("change", (event) => {
    setTheme(event.target.value);
    $("settingsSaved").textContent = "Theme preference saved in this browser.";
  });
  $("defaultTransitions").addEventListener("change", (event) => {
    setTransitions(event.target.value);
    $("settingsSaved").textContent = "Default puzzle preference saved in this browser.";
  });
  $("transitionSelect").addEventListener("change", (event) => setTransitions(event.target.value));
  $("themeQuickToggle").addEventListener("click", () => setTheme(document.documentElement.dataset.theme === "dark" ? "light" : "dark"));

  // Mirrors cipher_game.puzzle.detect_text_mode. The server makes the final
  // decision and the result panel reports exactly what it chose.
  function detectRoute(message) {
    if (!message) return null;
    const chars = Array.from(message);
    const hasHangul = chars.some((char) => {
      const cp = char.codePointAt(0);
      return cp >= 0xac00 && cp <= 0xd7a3;
    });
    const hangulOnly = chars.every((char) => {
      const cp = char.codePointAt(0);
      return char === " " || (cp >= 0xac00 && cp <= 0xd7a3);
    });
    return hasHangul && hangulOnly ? "korean-2beolsik" : "utf-8";
  }

  function updateRoutePreview() {
    const message = $("messageInput").value;
    const route = detectRoute(message);
    $("charCount").textContent = `${Array.from(message).length.toLocaleString()} / 20,000 characters`;
    const badge = $("routeBadge");
    badge.className = "route-badge";
    if (!route) {
      badge.textContent = "AWAITING INPUT";
      badge.classList.add("neutral");
      $("routeExplainer").textContent = "Enter Hangul-only text for the Korean 2-beolsik route. English, mixed text, symbols and other scripts use UTF-8 directly.";
      $("miniRoute").textContent = "Waiting for message";
      $("miniPreparation").textContent = "Automatic conversion";
    } else if (route === "korean-2beolsik") {
      badge.textContent = "KOREAN · 2-BEOLSIK";
      badge.classList.add("korean");
      $("routeExplainer").textContent = "Hangul-only input will be converted to standard Korean 2-beolsik keystrokes before encryption.";
      $("miniRoute").textContent = "Korean 2-beolsik";
      $("miniPreparation").textContent = "Hangul → keystrokes → UTF-8";
    } else {
      badge.textContent = "UTF-8 ROUTE";
      badge.classList.add("utf8");
      $("routeExplainer").textContent = "This input will be preserved as UTF-8. This route supports English, mixed languages, punctuation, numbers and emoji.";
      $("miniRoute").textContent = "UTF-8 text";
      $("miniPreparation").textContent = "Original text preserved";
    }
  }
  $("messageInput").addEventListener("input", updateRoutePreview);
  updateRoutePreview();

  async function postJson(url, body) {
    const response = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      credentials: "same-origin",
      cache: "no-store",
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok || data.ok === false) {
      throw new Error(data.error || `Request failed (${response.status}).`);
    }
    return data;
  }

  function setError(id, message) {
    const node = $(id);
    node.textContent = message;
    node.hidden = !message;
  }

  function downloadFile(filename, content, mimeType) {
    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = filename;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  function prettyPuzzle(envelope) {
    return JSON.stringify(envelope, null, 2) + "\n";
  }

  $("encryptButton").addEventListener("click", async () => {
    setError("encryptError", "");
    $("encryptResult").hidden = true;
    const message = $("messageInput").value;
    if (!message.trim()) {
      setError("encryptError", "Enter a message before creating a puzzle.");
      $("messageInput").focus();
      return;
    }
    const button = $("encryptButton");
    button.disabled = true;
    button.querySelector("span").textContent = "Encrypting locally…";
    try {
      const result = await postJson("/api/encrypt", {
        message,
        transitions: state.transitions,
      });
      state.puzzle = result.envelope;
      state.key = result.key;
      state.lastRoute = result.route;

      $("resultRoute").textContent = result.route_label;
      $("resultSequence").textContent = result.envelope.layout_sequence.map((v) => v.toUpperCase()).join(" → ");
      const puzzleText = result.envelope.puzzle_text;
      $("cipherPreview").textContent = puzzleText.length > 240 ? puzzleText.slice(0, 240) + "…" : puzzleText;
      $("keyPreview").textContent = "••••••••••••••••••••••••••••••••••••••••••••";
      $("revealKeyButton").textContent = "Reveal key";
      $("keyPreview").dataset.revealed = "false";
      $("encryptResult").hidden = false;
      $("encryptResult").scrollIntoView({ behavior: "smooth", block: "start" });
      showToast("Puzzle created. Download the puzzle and key separately.");
    } catch (error) {
      setError("encryptError", error.message);
    } finally {
      button.disabled = false;
      button.querySelector("span").textContent = "Generate puzzle";
    }
  });

  $("revealKeyButton").addEventListener("click", () => {
    if (!state.key) return;
    const revealed = $("keyPreview").dataset.revealed === "true";
    $("keyPreview").textContent = revealed ? "••••••••••••••••••••••••••••••••••••••••••••" : state.key;
    $("keyPreview").dataset.revealed = revealed ? "false" : "true";
    $("revealKeyButton").textContent = revealed ? "Reveal key" : "Hide key";
  });
  $("downloadPuzzleButton").addEventListener("click", () => {
    if (!state.puzzle) return;
    downloadFile("puzzle.json", prettyPuzzle(state.puzzle), "application/json");
    showToast("Puzzle file downloaded.");
  });
  $("downloadKeyButton").addEventListener("click", () => {
    if (!state.key) return;
    downloadFile("shared.key", state.key + "\n", "text/plain");
    showToast("Secret key downloaded separately.");
  });
  $("copyPuzzleButton").addEventListener("click", async () => {
    if (!state.puzzle) return;
    try {
      await navigator.clipboard.writeText(state.puzzle.puzzle_text);
      showToast("Ciphertext copied.");
    } catch (_) {
      showToast("Clipboard access was unavailable. Download the puzzle instead.");
    }
  });

  let loadedEnvelope = null;
  $("puzzleFileInput").addEventListener("change", async (event) => {
    setError("decryptError", "");
    const file = event.target.files && event.target.files[0];
    loadedEnvelope = null;
    if (!file) {
      $("puzzleFileName").textContent = "No file selected";
      return;
    }
    try {
      if (file.size > 500_000) throw new Error("Puzzle files must be smaller than 500 KB.");
      const parsed = JSON.parse(await file.text());
      if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) throw new Error("The selected file is not a puzzle JSON object.");
      loadedEnvelope = parsed;
      $("puzzleFileName").textContent = file.name;
      showToast("Puzzle file loaded.");
    } catch (error) {
      $("puzzleFileName").textContent = "Invalid puzzle file";
      setError("decryptError", error.message || "Unable to read the puzzle file.");
    }
    // Allow re-selecting the same file after fixing it on disk.
    event.target.value = "";
  });

  $("keyFileInput").addEventListener("change", async (event) => {
    const file = event.target.files && event.target.files[0];
    if (!file) {
      $("keyFileName").textContent = "No key file selected";
      return;
    }
    try {
      if (file.size > 10_000) throw new Error("Key file is unexpectedly large.");
      // Strip a possible BOM so files saved by some Windows editors still work.
      $("keyInput").value = (await file.text()).replace(/^\uFEFF/, "").trim();
      $("keyFileName").textContent = file.name;
      showToast("Secret key loaded into this page.");
    } catch (error) {
      setError("decryptError", error.message);
    }
    event.target.value = "";
  });

  $("decryptButton").addEventListener("click", async () => {
    setError("decryptError", "");
    $("decryptResult").hidden = true;
    if (!loadedEnvelope) {
      setError("decryptError", "Choose a valid puzzle JSON file first.");
      return;
    }
    const key = $("keyInput").value.trim();
    if (!key) {
      setError("decryptError", "Paste or load the matching secret key.");
      $("keyInput").focus();
      return;
    }
    const button = $("decryptButton");
    button.disabled = true;
    button.querySelector("span").textContent = "Authenticating and decrypting…";
    try {
      const result = await postJson("/api/decrypt", { envelope: loadedEnvelope, key });
      state.recoveredMessage = result.message;
      $("recoveredMessage").textContent = result.message;
      $("decryptResult").hidden = false;
      $("decryptResult").scrollIntoView({ behavior: "smooth", block: "start" });
      showToast("Authentication passed. Message recovered.");
    } catch (error) {
      setError("decryptError", error.message);
    } finally {
      button.disabled = false;
      button.querySelector("span").textContent = "Decrypt puzzle";
    }
  });

  $("copyMessageButton").addEventListener("click", async () => {
    if (state.recoveredMessage === null) return;
    try {
      await navigator.clipboard.writeText(state.recoveredMessage);
      showToast("Recovered message copied.");
    } catch (_) {
      showToast("Clipboard access was unavailable.");
    }
  });
  $("saveMessageButton").addEventListener("click", () => {
    if (state.recoveredMessage === null) return;
    downloadFile("recovered-message.txt", state.recoveredMessage, "text/plain;charset=utf-8");
  });

  function renderExplorer(index) {
    const safeIndex = Math.max(0, Math.min(explorerStages.length - 1, index));
    const stage = explorerStages[safeIndex];
    document.querySelectorAll(".explorer-step").forEach((button) => {
      const selected = Number(button.dataset.step) === safeIndex;
      button.classList.toggle("selected", selected);
      if (selected) button.setAttribute("aria-current", "step");
      else button.removeAttribute("aria-current");
    });
    $("explorerNumber").textContent = `STAGE ${String(safeIndex + 1).padStart(2, "0")} / 06`;
    $("explorerIcon").textContent = stage.icon;
    $("explorerTitle").textContent = stage.title;
    $("explorerDescription").textContent = stage.description;
    $("explorerExample").textContent = stage.example;
    $("explorerNote").textContent = stage.note;
    $("prevStepButton").disabled = safeIndex === 0;
    $("nextStepButton").disabled = safeIndex === explorerStages.length - 1;
    state.explorerIndex = safeIndex;
  }
  document.querySelectorAll(".explorer-step").forEach((button) => {
    button.addEventListener("click", () => renderExplorer(Number(button.dataset.step)));
  });
  $("prevStepButton").addEventListener("click", () => renderExplorer(state.explorerIndex - 1));
  $("nextStepButton").addEventListener("click", () => renderExplorer(state.explorerIndex + 1));
  renderExplorer(0);

  // Drag-and-drop convenience for the puzzle JSON file.
  const dropZone = $("puzzleDropZone");
  ["dragenter", "dragover"].forEach((eventName) => dropZone.addEventListener(eventName, (event) => {
    event.preventDefault();
    dropZone.classList.add("dragover");
  }));
  ["dragleave", "drop"].forEach((eventName) => dropZone.addEventListener(eventName, (event) => {
    event.preventDefault();
    dropZone.classList.remove("dragover");
  }));
  dropZone.addEventListener("drop", (event) => {
    const file = event.dataTransfer && event.dataTransfer.files[0];
    if (!file) return;
    const transfer = new DataTransfer();
    transfer.items.add(file);
    $("puzzleFileInput").files = transfer.files;
    $("puzzleFileInput").dispatchEvent(new Event("change"));
  });

  // The file inputs are hidden, so make their labels keyboard-operable.
  [["puzzleDropZone", "puzzleFileInput"], ["keyFileLabel", "keyFileInput"]].forEach(([labelId, inputId]) => {
    const label = $(labelId);
    label.tabIndex = 0;
    label.setAttribute("role", "button");
    label.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        $(inputId).click();
      }
    });
  });

  // Do not place message contents or keys in localStorage, cookies, or logs.
  window.addEventListener("pagehide", () => {
    state.key = null;
    state.puzzle = null;
    state.recoveredMessage = null;
    $("keyInput").value = "";
  });
})();
