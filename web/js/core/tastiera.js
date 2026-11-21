function insetTastiera() {
  const viewport = window.visualViewport;
  if (!viewport) return 0;
  return Math.max(0, Math.round(window.innerHeight - viewport.height - viewport.offsetTop));
}

export function initTastieraVirtuale() {
  const aggiorna = () => {
    document.documentElement.style.setProperty("--keyboard-inset", `${insetTastiera()}px`);
  };
  aggiorna();
  window.visualViewport?.addEventListener("resize", aggiorna);
  window.visualViewport?.addEventListener("scroll", aggiorna);
  window.addEventListener("resize", aggiorna);

  document.addEventListener("focusin", (event) => {
    const campo = event.target;
    if (!(campo instanceof HTMLElement) || !campo.matches("input, select, textarea")) return;
    if (campo.type === "checkbox" || campo.type === "radio") return;
    window.setTimeout(() => {
      campo.scrollIntoView({ block: "center", inline: "nearest" });
    }, 280);
  });
}
