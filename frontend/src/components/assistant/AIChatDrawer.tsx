import { useEffect, useRef, useState } from 'react'
import {
  ActionIcon,
  Button,
  Drawer,
  Group,
  Loader,
  ScrollArea,
  Stack,
  Text,
  Textarea,
  Tooltip,
} from '@mantine/core'
import { useMutation } from '@tanstack/react-query'
import { IconEraser, IconInfoCircle, IconSend, IconSparkles } from '@tabler/icons-react'
import { sendChatMessage, type ChatMessage } from '@/api/assistant'
import ChatMessageBubble from './ChatMessage'

const SUGGESTION_PROMPTS = [
  'How does my gross margin in the running month compare to all-time?',
  "What draft purchase orders do I have open, and what's the total cost of inventory still waiting to be received?",
  'Walk me through everything that happened with Espresso Beans last month — purchases, sales, and net stock change.',
]

// Keep at most this many messages in history sent to the backend.
const MAX_HISTORY = 20

interface Props {
  opened: boolean
  onClose: () => void
  messages: ChatMessage[]
  setMessages: (messages: ChatMessage[]) => void
}

export default function AIChatDrawer({ opened, onClose, messages, setMessages }: Props) {
  const [input, setInput] = useState('')
  const bottomRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const mutation = useMutation({
    mutationFn: sendChatMessage,
    onSuccess: (data, variables) => {
      setMessages([...variables, { role: 'assistant', content: data.reply }])
    },
    onError: (_err, variables) => {
      setMessages([
        ...variables,
        { role: 'assistant', content: 'Something went wrong — please try again.' },
      ])
    },
  })

  const isPending = mutation.isPending

  // Scroll to the latest message whenever messages or loading state changes.
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isPending])

  // Focus the textarea when the drawer opens.
  useEffect(() => {
    if (opened) {
      const timer = setTimeout(() => textareaRef.current?.focus(), 150)
      return () => clearTimeout(timer)
    }
  }, [opened])

  const send = (text: string) => {
    const trimmed = text.trim()
    if (!trimmed || isPending) return

    // Cap history before appending the new user turn.
    const history = messages.slice(-(MAX_HISTORY - 1))
    const next: ChatMessage[] = [...history, { role: 'user', content: trimmed }]
    setMessages(next)
    setInput('')
    mutation.mutate(next)
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      send(input)
    }
  }

  return (
    <Drawer
      opened={opened}
      onClose={onClose}
      title={
        <Group gap="xs" justify="space-between" style={{ flex: 1 }}>
          <Group gap="xs">
            <IconSparkles size={18} stroke={1.5} color="var(--mantine-color-blue-6)" />
            <Text fw={600} size="sm">Ask about your data</Text>
            <Tooltip
              label="Conversations are not stored. History is only kept for the current session."
              multiline
              w={220}
              withArrow
              position="bottom"
            >
              <IconInfoCircle size={14} stroke={1.5} color="var(--mantine-color-dimmed)" style={{ cursor: 'default' }} />
            </Tooltip>
          </Group>
          {messages.length > 0 && (
            <Tooltip label="Clear conversation" withArrow position="bottom">
              <ActionIcon
                variant="subtle"
                color="gray"
                size="sm"
                onClick={() => setMessages([])}
                disabled={isPending}
                aria-label="Clear conversation"
              >
                <IconEraser size={14} stroke={1.5} />
              </ActionIcon>
            </Tooltip>
          )}
        </Group>
      }
      position="right"
      size="400px"
      styles={{
        body: {
          display: 'flex',
          flexDirection: 'column',
          height: 'calc(100% - 60px)',
          padding: 0,
          overflow: 'hidden',
        },
      }}
    >
      {/* Message list */}
      <ScrollArea style={{ flex: 1 }} px="md" py="sm">
        {messages.length === 0 ? (
          <Stack gap="sm" pt="lg" align="stretch">
            <Text size="sm" c="dimmed" ta="center">
              Ask anything about your products, stock, orders, or financials.
            </Text>
            <Stack gap="xs" mt="xs">
              {SUGGESTION_PROMPTS.map((prompt) => (
                <Button
                  key={prompt}
                  variant="default"
                  size="compact-sm"
                  fullWidth
                  onClick={() => send(prompt)}
                  disabled={isPending}
                  justify="flex-start"
                  styles={{
                    root: {
                      height: 'auto',
                      minHeight: 'var(--button-height-compact-sm)',
                      paddingBlock: 'var(--mantine-spacing-xs)',
                      alignItems: 'flex-start',
                    },
                    inner: {
                      justifyContent: 'flex-start',
                    },
                    label: {
                      whiteSpace: 'normal',
                      textAlign: 'left',
                      lineHeight: 1.45,
                    },
                  }}
                >
                  {prompt}
                </Button>
              ))}
            </Stack>
          </Stack>
        ) : (
          <Stack gap="xs" pb="xs">
            {messages.map((msg, i) => (
              <ChatMessageBubble key={i} message={msg} />
            ))}
            {isPending && (
              <ChatMessageBubble
                message={{ role: 'assistant', content: '' }}
                isLoading
              />
            )}
            <div ref={bottomRef} />
          </Stack>
        )}
      </ScrollArea>

      {/* Input */}
      <Group
        gap="xs"
        px="md"
        py="sm"
        align="flex-end"
        wrap="nowrap"
        style={{ borderTop: '1px solid var(--mantine-color-gray-2)', flexShrink: 0 }}
      >
        <Textarea
          ref={textareaRef}
          style={{ flex: 1 }}
          placeholder="Ask a question…"
          value={input}
          onChange={(e) => setInput(e.currentTarget.value)}
          onKeyDown={handleKeyDown}
          autosize
          minRows={1}
          maxRows={4}
          disabled={isPending}
          size="sm"
        />
        <ActionIcon
          onClick={() => send(input)}
          disabled={!input.trim() || isPending}
          variant="filled"
          size="lg"
          mb={1}
          aria-label="Send message"
        >
          {isPending ? <Loader size="xs" color="white" /> : <IconSend size={16} />}
        </ActionIcon>
      </Group>
    </Drawer>
  )
}
