import 'package:flutter_test/flutter_test.dart';
import 'package:owner_mobile/features/notifications/domain/outbox_models.dart';

void main() {
  test('outbox model parses operational status without payload', () {
    final item = OutboxItemModel.fromJson({
      'id': 'outbox-1',
      'event_type': 'payment_received',
      'aggregate_type': 'payment',
      'aggregate_id': 'payment-1',
      'recipient_type': 'borrower',
      'recipient_id': 'borrower-1',
      'channel': 'in_app',
      'template_key': 'payment_received',
      'status': 'dead_letter',
      'attempt_count': 5,
      'max_attempts': 5,
      'next_attempt_at': null,
      'last_attempt_at': '2026-08-09T12:00:00Z',
      'delivered_at': null,
      'last_error': 'Notification provider delivery failed',
      'created_at': '2026-08-09T11:00:00Z',
      'updated_at': '2026-08-09T12:00:00Z',
    });

    expect(item.isDeadLetter, isTrue);
    expect(item.attemptCount, 5);
    expect(item.channel, 'in_app');
  });
}
