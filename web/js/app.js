import { initAuth } from "./core/auth.js";
import { initNavigation } from "./core/navigation.js";
import { initAdmin } from "./features/admin.js";
import { initAnagrafiche } from "./features/anagrafiche.js";
import { initDashboard } from "./features/dashboard.js";
import { initIngressoMerce } from "./features/ingresso-merce.js";
import { initPrinting } from "./features/printing.js";
import { initProgressivi } from "./features/progressivi.js";

document.addEventListener("DOMContentLoaded", () => {
  const showLanding = initNavigation();
  initAuth(showLanding);
  initDashboard();
  initAnagrafiche();
  initIngressoMerce();
  initPrinting();
  initProgressivi();
  initAdmin();
});
