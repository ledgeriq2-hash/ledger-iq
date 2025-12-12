import { useState } from "react";
import aiApi from "../api/aiApi";

const useAIInsights = () => {
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  const forecast = async (payload) => {
    setLoading(true);
    setError(null);
    try {
      const { data } = await aiApi.forecast(payload);
      setData(data);
      return data;
    } catch (err) {
      setError(err);
      throw err;
    } finally {
      setLoading(false);
    }
  };

  const anomalies = async (payload) => {
    setLoading(true);
    setError(null);
    try {
      const { data } = await aiApi.anomalies(payload);
      setData(data);
      return data;
    } catch (err) {
      setError(err);
      throw err;
    } finally {
      setLoading(false);
    }
  };

  return { loading, data, error, forecast, anomalies };
};

export default useAIInsights;
