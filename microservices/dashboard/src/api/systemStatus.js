import axios from "axios";

const controlClient = axios.create({
  baseURL: import.meta.env.VITE_CONTROL_API_URL || "/control-api",
  timeout: 8000,
});

const toError = (err) => {
  const status = err.response?.status ?? null;
  const detail = err.response?.data?.detail;
  const message =
    (typeof detail === "string" && detail) ||
    (status
      ? `Error ${status} del System Controller`
      : "No se pudo contactar al System Controller");
  return Object.assign(new Error(message), { status });
};

export const getSystemStatus = async () => {
  try {
    const { data } = await controlClient.get("/status");
    return data;
  } catch (err) {
    throw toError(err);
  }
};

export const restartComponent = async (name) => {
  try {
    const { data } = await controlClient.post(
      `/components/${encodeURIComponent(name)}/restart`,
    );
    return data;
  } catch (err) {
    throw toError(err);
  }
};
