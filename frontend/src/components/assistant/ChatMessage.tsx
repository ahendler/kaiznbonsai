import { Box, Loader, Text } from '@mantine/core'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import type { ChatMessage } from '@/api/assistant'

interface Props {
  message: ChatMessage
  isLoading?: boolean
}

export default function ChatMessage({ message, isLoading = false }: Props) {
  const isUser = message.role === 'user'

  return (
    <div className={`flex min-w-0 ${isUser ? 'justify-end' : 'justify-start'}`}>
      <Box
        maw="85%"
        miw={0}
        px="sm"
        py={6}
        style={{
          borderRadius: isUser ? '12px 12px 2px 12px' : '12px 12px 12px 2px',
          backgroundColor: isUser
            ? 'var(--mantine-color-blue-6)'
            : 'var(--mantine-color-gray-3)',
        }}
      >
        {isLoading ? (
          <Loader size="xs" color="gray" type="dots" />
        ) : isUser ? (
          <Text
            size="sm"
            c="white"
            style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}
          >
            {message.content}
          </Text>
        ) : (
          <div className="min-w-0 max-w-full text-sm [&>*:first-child]:mt-0 [&>*:last-child]:mb-0 [&>p]:my-1 [&>ul]:my-1 [&>ol]:my-1 [&>ul]:pl-4 [&>ol]:pl-4 [&>li]:my-0.5 [&>h1]:text-base [&>h2]:text-sm [&>h3]:text-sm [&>strong]:font-semibold [&>code]:bg-gray-200 [&>code]:px-1 [&>code]:rounded [&>pre]:bg-gray-200 [&>pre]:p-2 [&>pre]:rounded [&>pre]:overflow-x-auto [&>pre>code]:bg-transparent [&>pre>code]:p-0 [&>blockquote]:border-l-2 [&>blockquote]:border-gray-400 [&>blockquote]:pl-2 [&>blockquote]:text-gray-600">
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
                table: ({ children }) => (
                  <div className="my-2 max-w-full overflow-x-auto">
                    <table className="w-max min-w-full border-collapse">{children}</table>
                  </div>
                ),
                th: ({ children }) => (
                  <th className="border border-gray-400 bg-gray-200 px-2 py-1 text-left text-xs font-semibold whitespace-nowrap">
                    {children}
                  </th>
                ),
                td: ({ children }) => (
                  <td className="border border-gray-400 px-2 py-1 text-xs whitespace-nowrap">
                    {children}
                  </td>
                ),
              }}
            >
              {message.content}
            </ReactMarkdown>
          </div>
        )}
      </Box>
    </div>
  )
}
