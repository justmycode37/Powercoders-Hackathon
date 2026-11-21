import { render } from "preact";
import { App } from "./app";
import { resumeGeo } from "./state";
import "./styles/app.css";

const root = document.getElementById("app")!;
root.textContent = "";
render(<App />, root);
performance.mark("kante:shell");
resumeGeo();

if ("serviceWorker" in navigator && import.meta.env.PROD) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/sw.js").catch(() => undefined);
  });
}
