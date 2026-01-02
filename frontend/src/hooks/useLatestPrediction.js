import { useQuery } from "@tanstack/react-query";

import mlApi from "../api/mlApi.js";

export const useLatestPrediction = (predictionType, modelVersion, { enabled = true, ...options } = {}) => {
  const queryFn = async () => {
    try {
      return await mlApi.getLatestPrediction(predictionType, modelVersion);
    } catch (err) {
      if (err?.status === 404) {
        return null;
      }
      throw err;
    }
  };

  return useQuery({
    queryKey: ["ml", "predictions", "latest", { predictionType, modelVersion }],
    queryFn,
    enabled: Boolean(predictionType) && enabled,
    ...options,
  });
};
