import { loginScenario, crudScenario, reportsScenario, portalScenario } from "./common.js";

export const options = {
  scenarios: {
    login: {
      executor: "ramping-vus",
      startVUs: 1,
      stages: [
        { duration: "1m", target: 10 },
        { duration: "1m", target: 0 },
      ],
      exec: "loginScenario",
    },
    crud: {
      executor: "ramping-vus",
      startVUs: 1,
      stages: [
        { duration: "1m", target: 10 },
        { duration: "1m", target: 0 },
      ],
      exec: "crudScenario",
    },
    reports: {
      executor: "ramping-vus",
      startVUs: 1,
      stages: [
        { duration: "1m", target: 8 },
        { duration: "1m", target: 0 },
      ],
      exec: "reportsScenario",
    },
    portal: {
      executor: "ramping-vus",
      startVUs: 1,
      stages: [
        { duration: "1m", target: 6 },
        { duration: "1m", target: 0 },
      ],
      exec: "portalScenario",
    },
  },
};

export { loginScenario, crudScenario, reportsScenario, portalScenario };
