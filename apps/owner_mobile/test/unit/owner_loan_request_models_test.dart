import 'package:flutter_test/flutter_test.dart';
import 'package:owner_mobile/features/loan_requests/domain/owner_loan_request_models.dart';

void main() {
  test('parses the canonical backend owner loan-request response', () {
    final model = OwnerLoanRequestDetailModel.fromJson({
      'id': 'request-1',
      'borrowerId': 'borrower-1',
      'requestedPrincipal': '1000.00',
      'requestedMonthlyRate': '0.100000',
      'requestedTermMonths': 1,
      'requestedPaymentFrequency': 'monthly',
      'requestedFirstDueDate': '2026-09-01',
      'status': 'approved',
      'submittedAt': '2026-08-09T03:15:11Z',
      'reviewedAt': '2026-08-09T03:16:00Z',
      'reviewedByOwnerId': 'owner-1',
      'ownerNote': null,
      'createdAt': '2026-08-09T03:15:11Z',
      'updatedAt': '2026-08-09T03:16:00Z',
      'borrowerFirstName': 'Nelson',
      'borrowerLastName': 'Fernandez',
      'borrowerNationalId': 'ID-12345678',
      'borrowerPhoneNumber': '+639171234567',
      'quotePreview': {
        'principal': '1000.00',
        'monthlyRate': '0.100000',
        'termMonths': 1,
        'paymentFrequency': 'monthly',
        'numberOfPayments': 1,
        'periodRate': '0.100000',
        'scheduledPayment': '1100.00',
        'totalScheduledInterest': '100.00',
        'totalScheduledRepayment': '1100.00',
        'firstDueDate': '2026-09-01',
        'finalDueDate': '2026-09-01',
        'schedule': [
          {
            'installmentNumber': 1,
            'dueDate': '2026-09-01',
            'openingPrincipal': '1000.00',
            'interestDue': '100.00',
            'scheduledPrincipal': '1000.00',
            'scheduledPayment': '1100.00',
            'closingPrincipal': '0.00',
          },
        ],
      },
    });

    expect(model.status, 'approved');
    expect(model.quotePreview.periodicPayment, 1100.00);
    expect(model.quotePreview.totalInterest, 100.00);
    expect(model.quotePreview.totalAmount, 1100.00);
    expect(model.quotePreview.schedule.single.paymentNumber, 1);
    expect(model.quotePreview.schedule.single.remainingPrincipal, 0.00);
  });
}
