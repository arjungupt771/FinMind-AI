import axios from "axios";

const API_URL = "http://localhost:8000";

export async function askAdvisor(
  userId,
  question
) {
  const response = await axios.post(
    `${API_URL}/advisor/chat`,
    {
      user_id: userId,
      question: question,
    }
  );

  return response.data;
}