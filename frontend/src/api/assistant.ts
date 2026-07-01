import api from './client'

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
}

export async function sendChatMessage(messages: ChatMessage[]): Promise<{ reply: string }> {
  const response = await api.post<{ reply: string }>('/assistant/chat/', { messages })
  return response.data
}
