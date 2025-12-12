import { loginScenario, crudScenario, reportsScenario, portalScenario } from "./common.js";

export const options = {
  scenarios: {
    login: { executor: "constant-vus", vus: 1, duration: "30s", exec: "loginScenario" },
    crud: { executor: "constant-vus", vus: 1, duration: "30s", exec: "crudScenario" },
    reports: { executor: "constant-vus", vus: 1, duration: "30s", exec: "reportsScenario" },
    portal: { executor: "constant-vus", vus: 1, duration: "30s", exec: "portalScenario" },
  },
};

export { loginScenario, crudScenario, reportsScenario, portalScenario };
