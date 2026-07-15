import { render, screen, fireEvent, act } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import BookingProposal from '../components/bookings/booking-proposal';
import { mockBooking } from './fixtures';

const mockPayload = {
  room_id: 'dlt_8',
  room_name: 'DLT-8',
  title: 'CS F111 Lecture',
  start_time: '2026-07-13T11:00:00+05:30',
  end_time: '2026-07-13T12:00:00+05:30',
  description: 'Regular class',
};

describe('BookingProposal', () => {
  let defaultProps: any;

  beforeEach(() => {
    vi.clearAllMocks();
    defaultProps = {
      payload: mockPayload,
      bookings: [],
      isLatestDraft: true,
      onCreateBooking: vi.fn().mockResolvedValue(mockBooking),
      onLockBooking: vi.fn().mockResolvedValue(mockBooking),
      onUnlockBooking: vi.fn().mockResolvedValue(mockBooking),
      onUpdateBooking: vi.fn().mockResolvedValue(mockBooking),
    };
  });


  it('renders booking details correctly in draft state', () => {
    render(<BookingProposal {...defaultProps} />);
    expect(screen.getByText('DLT-8')).toBeInTheDocument();
    expect(screen.getByText('CS F111 Lecture')).toBeInTheDocument();
    expect(screen.getByText('Regular class')).toBeInTheDocument();
    expect(screen.getByText('Submit Request')).toBeInTheDocument();
  });

  it('shows DRAFT PROPOSAL badge in draft state', () => {
    render(<BookingProposal {...defaultProps} />);
    expect(screen.getByText('DRAFT PROPOSAL')).toBeInTheDocument();
  });

  it('calls onCreateBooking when Submit Request is clicked', async () => {
    render(<BookingProposal {...defaultProps} />);

    await act(async () => {
      fireEvent.click(screen.getByText('Submit Request'));
    });

    expect(defaultProps.onCreateBooking).toHaveBeenCalledWith(
      expect.objectContaining({
        room_id: mockPayload.room_id,
        room_name: mockPayload.room_name,
        title: mockPayload.title,
        description: mockPayload.description,
      })
    );
  });

  it('shows PENDING APPROVAL badge and hides Submit button when booking is pending', () => {
    const pendingBooking = { ...mockBooking, status: 'pending' as const };
    render(<BookingProposal {...defaultProps} bookings={[pendingBooking]} />);

    expect(screen.getByText('PENDING APPROVAL')).toBeInTheDocument();
    expect(screen.queryByText('Submit Request')).not.toBeInTheDocument();
  });

  it('shows APPROVED badge when booking is approved', () => {
    const approvedBooking = { ...mockBooking, status: 'approved' as const };
    render(<BookingProposal {...defaultProps} bookings={[approvedBooking]} />);
    expect(screen.getByText('APPROVED')).toBeInTheDocument();
  });

  it('shows REJECTED badge when booking is rejected', () => {
    const rejectedBooking = { ...mockBooking, status: 'rejected' as const };
    render(<BookingProposal {...defaultProps} bookings={[rejectedBooking]} />);
    expect(screen.getByText('REJECTED')).toBeInTheDocument();
  });

  it('shows EXPIRED badge when isLatestDraft is false and no matching booking', () => {
    render(<BookingProposal {...defaultProps} isLatestDraft={false} bookings={[]} />);
    expect(screen.getByText('EXPIRED')).toBeInTheDocument();
  });

  it('shows Edit button in draft state', () => {
    render(<BookingProposal {...defaultProps} />);
    expect(screen.getByText('Edit')).toBeInTheDocument();
  });

  it('shows Edit button in pending state', () => {
    const pendingBooking = { ...mockBooking, status: 'pending' as const };
    render(<BookingProposal {...defaultProps} bookings={[pendingBooking]} />);
    expect(screen.getByText('Edit')).toBeInTheDocument();
  });

  it('does not show Edit button in approved state', () => {
    const approvedBooking = { ...mockBooking, status: 'approved' as const };
    render(<BookingProposal {...defaultProps} bookings={[approvedBooking]} />);
    expect(screen.queryByText('Edit')).not.toBeInTheDocument();
  });
});
