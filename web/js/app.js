import { initAuth } from "./core/auth.js";
import { initNavigation } from "./core/navigation.js?v=20261114-3";
import { initAdmin } from "./features/admin.js";
import { initAnagrafiche } from "./features/anagrafiche.js";
import { initDashboard } from "./features/dashboard.js";
import { initIngressoMerce } from "./features/ingresso-merce.js";
import { initMenu } from "./features/menu.js?v=20261114-3";
import { initPrinting } from "./features/printing.js";
import { initProgressivi } from "./features/progressivi.js";
import { initTracciabilita } from "./features/tracciabilita.js";
import { initVendite } from "./features/vendite.js?v=20261114-3";

document.addEventListener("DOMContentLoaded", () => {
  const showLanding = initNavigation();
  initAuth(showLanding);
  initDashboard();
  initAnagrafiche();
  initIngressoMerce();
  initPrinting();
  initProgressivi();
  initTracciabilita();
  initMenu();
  initVendite();
  initAdmin();
});
