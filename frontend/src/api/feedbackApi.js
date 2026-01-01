import { api } from "./generated/index.js";

const feedbackApi = {
  submit: (payload) => api.feedback.submit(payload),
  listMine: (params = {}) => api.feedback.listMine(params),
};

export default feedbackApi;
