import 'package:flutter_test/flutter_test.dart';
import 'package:owner_mobile/features/accounting/domain/accounting_models.dart';

void main() {
  test('account model parses backend snake_case response', () {
    final account = AccountModel.fromJson({
      'id': 'account-1',
      'code': '1000',
      'name': 'Cash',
      'account_type': 'asset',
      'normal_balance': 'debit',
      'is_active': true,
      'created_at': '2026-08-09T12:00:00Z',
      'updated_at': '2026-08-09T12:00:00Z',
    });

    expect(account.type, 'asset');
    expect(account.normalBalance, 'debit');
  });

  test('journal model parses backend snake_case response and entries', () {
    final journal = JournalTransactionModel.fromJson({
      'id': 'journal-1',
      'event_type': 'payment',
      'source_id': 'payment-1',
      'description': 'Payment for Loan loan-1',
      'effective_date': '2026-08-09',
      'posted_at': '2026-08-09T12:00:00Z',
      'reversal_of_id': null,
      'total_debit': '700.00',
      'total_credit': '700.00',
      'is_balanced': true,
      'entries': [
        {
          'id': 'entry-1',
          'journal_transaction_id': 'journal-1',
          'account_id': 'account-1',
          'account_code': '1000',
          'account_name': 'Cash',
          'debit': '700.00',
          'credit': '0.00',
        },
      ],
    });

    expect(journal.eventType, 'payment');
    expect(journal.sourceId, 'payment-1');
    expect(journal.totalDebit, '700.00');
    expect(journal.isBalanced, isTrue);
    expect(journal.entries.single.accountCode, '1000');
    expect(journal.entries.single.journalTransactionId, 'journal-1');
  });
}
