import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import ChatBubble from '../components/chat/chat-bubble';
import { mockUserMessage, mockAssistantMessage, mockProposalMessage } from './fixtures';
import type { Message } from '@/lib/types';

// ── Mock heavy dependencies ───────────────────────────────────────────────────

vi.mock('react-markdown', () => ({
  default: ({ children }: { children: string }) => <div data-testid="markdown">{children}</div>,
}));

vi.mock('remark-gfm', () => ({ default: vi.fn() }));

vi.mock('react-syntax-highlighter', () => ({
  Prism: ({ children }: { children: string }) => <pre>{children}</pre>,
}));
vi.mock('react-syntax-highlighter/dist/esm/styles/prism', () => ({
  materialDark: {},
}));

vi.mock('lucide-react', () => ({
  Copy: () => <span>Copy</span>,
  Check: () => <span>Check</span>,
}));

vi.mock('../components/chat/chat-bubble.module.scss', () => ({
  default: {
    bubble: 'bubble',
    bubbleUser: 'bubbleUser',
    bubbleAssistant: 'bubbleAssistant',
    avatar: 'avatar',
    avatarUser: 'avatarUser',
    avatarAssistant: 'avatarAssistant',
    content: 'content',
    contentUser: 'contentUser',
    messageBody: 'messageBody',
    userBody: 'userBody',
    assistantBody: 'assistantBody',
    markdown: 'markdown',
    typingDots: 'typingDots',
    timestamp: 'timestamp',
    timestampUser: 'timestampUser',
  },
}));

// Mock BookingProposal (it's a complex component, we test it separately)
vi.mock('../components/bookings/booking-proposal', () => ({
  default: ({ payload }: { payload: any }) => (
    <div data-testid="booking-proposal">{payload.room_name}</div>
  ),
}));

describe('ChatBubble', () => {
  it('renders user message content', () => {
    render(<ChatBubble message={mockUserMessage} />);
    expect(screen.getByText('Hello, how do I book a room?')).toBeInTheDocument();
  });

  it('renders assistant message via markdown', () => {
    render(<ChatBubble message={mockAssistantMessage} />);
    expect(screen.getByTestId('markdown')).toBeInTheDocument();
    expect(screen.getByText('Sure! I can help you book a room. Which lab do you need?')).toBeInTheDocument();
  });

  it('shows "U" avatar for user messages by default', () => {
    render(<ChatBubble message={mockUserMessage} />);
    expect(screen.getByText('U')).toBeInTheDocument();
  });

  it('shows custom userInitials when provided', () => {
    render(<ChatBubble message={mockUserMessage} userInitials="JD" />);
    expect(screen.getByText('JD')).toBeInTheDocument();
  });

  it('shows "AI" avatar for assistant messages', () => {
    render(<ChatBubble message={mockAssistantMessage} />);
    expect(screen.getByText('AI')).toBeInTheDocument();
  });

  it('renders typing dots when content is empty and no interactive_type', () => {
    const emptyAssistant: Message = {
      ...mockAssistantMessage,
      content: '',
      interactive_type: null,
    };
    const { container } = render(<ChatBubble message={emptyAssistant} />);
    // typingDots div should be present
    expect(container.querySelector('.typingDots')).toBeTruthy();
  });

  it('does not show typing dots for user messages', () => {
    const { container } = render(<ChatBubble message={mockUserMessage} />);
    expect(container.querySelector('.typingDots')).toBeNull();
  });

  it('renders a timestamp for each message', () => {
    render(<ChatBubble message={mockUserMessage} />);
    // Timestamp should be formatted — at minimum, some time-like string is shown
    // We look for the timestamp container
    const { container } = render(<ChatBubble message={mockUserMessage} />);
    expect(container.querySelector('.timestamp')).toBeTruthy();
  });
});
