import { Affix, ActionIcon, Tooltip } from '@mantine/core'
import { IconSparkles } from '@tabler/icons-react'
import type { ChatMessage } from '@/api/assistant'
import AIChatDrawer from './AIChatDrawer'

interface Props {
  opened: boolean
  onOpen: () => void
  onClose: () => void
  messages: ChatMessage[]
  setMessages: (messages: ChatMessage[]) => void
}

export default function AssistantFab({
  opened,
  onOpen,
  onClose,
  messages,
  setMessages,
}: Props) {
  return (
    <>
      <AIChatDrawer
        opened={opened}
        onClose={onClose}
        messages={messages}
        setMessages={setMessages}
      />

      {!opened && (
        <Affix position={{ bottom: 24, right: 24 }}>
          <Tooltip label="Ask about your data" position="left" withArrow>
            <ActionIcon
              onClick={onOpen}
              size={52}
              radius="xl"
              variant="filled"
              aria-label="AI assistant"
            >
              <IconSparkles size={24} stroke={1.5} />
            </ActionIcon>
          </Tooltip>
        </Affix>
      )}
    </>
  )
}
