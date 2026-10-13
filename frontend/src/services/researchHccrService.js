import api from "./api";

export async function getHccrResearchAnalytics() {
  const response = await api.get("/analytics/hccr-research");
  return response.data;
}

export async function getHccrReservationDecision(parameters) {
  const response = await api.get("/analytics/hccr-research/decision", { params: parameters });
  return response.data;
}

export async function downloadHccrArtifact(filename) {
  const response = await api.get(`/analytics/hccr-research/download/${encodeURIComponent(filename)}`, {
    responseType: "blob",
  });
  const objectUrl = URL.createObjectURL(response.data);
  const link = document.createElement("a");
  link.href = objectUrl;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(objectUrl);
}
