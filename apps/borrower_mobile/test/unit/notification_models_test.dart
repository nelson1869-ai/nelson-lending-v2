import 'package:borrower_mobile/features/notifications/domain/notification_models.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('notification model parses unread and read state', () {
    final unread = BorrowerNotification.fromJson({
      'id': 'notification-1',
      'title': 'Payment Received',
      'body': 'We recorded your payment of ₱700.00.',
      'event_type': 'payment_received',
      'source_id': 'payment-1',
      'read_at': null,
      'created_at': '2026-08-09T12:00:00Z',
    });
    final read = BorrowerNotification.fromJson({
      'id': 'notification-1',
      'title': 'Payment Received',
      'body': 'We recorded your payment of ₱700.00.',
      'event_type': 'payment_received',
      'source_id': 'payment-1',
      'read_at': '2026-08-09T12:05:00Z',
      'created_at': '2026-08-09T12:00:00Z',
    });

    expect(unread.isRead, isFalse);
    expect(read.isRead, isTrue);
    expect(unread.eventType, 'payment_received');
  });
}
