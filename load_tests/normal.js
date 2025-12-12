import { loginScenario, crudScenario, reportsScenario, portalScenario } from "./common.js";

export const options = {
  scenarios: {
    login: { executor: "constant-vus", vus: 5, duration: "1m", exec: "loginScenario" },
    crud: { executor: "constant-vus", vus: 5, duration: "1m", exec: "crudScenario" },
    reports: { executor: "constant-vus", vus: 5, duration: "1m", exec: "reportsScenario" },
    portal: { executor: "constant-vus", vus: 5, duration: "1m", exec: "portalScenario" },
  },
};

export { loginScenario, crudScenario, reportsScenario, portalScenario };
