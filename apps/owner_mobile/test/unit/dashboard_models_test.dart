import 'package:flutter_test/flutter_test.dart';
import 'package:owner_mobile/features/reports/domain/dashboard_models.dart';

void main() {
  test('dashboard model parses exact decimal strings and canonical ordering',
      () {
    final dashboard = OwnerDashboardModel.fromJson({
      'portfolio': {
        'status_counts': [
          {'status': 'pending_disbursement', 'count': 1},
          {'status': 'active', 'count': 2},
          {'status': 'paid', 'count': 3},
          {'status': 'cancelled', 'count': 4},
          {'status': 'defaulted', 'count': 5},
        ],
        'total_original_principal': '1500.00',
        'outstanding_principal': '600.00',
        'accrued_interest': '25.50',
        'active_loan_count': 2,
        'paid_loan_count': 3,
      },
      'collections': {
        'from_date': '2026-08-01',
        'to_date': '2026-08-31',
        'total_payment_amount': '1000.00',
        'principal_allocation': '775.00',
        'interest_allocation': '125.00',
        'unapplied_credit_allocation': '100.00',
      },
      'accounting_balances': [
        {
          'code': '1000',
          'name': 'Cash',
          'normal_balance': 'debit',
          'balance': '1000.00',
        },
      ],
      'loan_requests': {
        'status_counts': [
          {'status': 'pending', 'count': 1},
          {'status': 'approved', 'count': 2},
          {'status': 'rejected', 'count': 3},
          {'status': 'cancelled', 'count': 4},
        ],
      },
    });

    expect(dashboard.portfolio.outstandingPrincipal, '600.00');
    expect(dashboard.collections.principalAllocation, '775.00');
    expect(dashboard.accountingBalances.single.normalBalance, 'debit');
    expect(dashboard.loanRequestStatusCounts.last.status, 'cancelled');
    expect(dashboard.isEmpty, isFalse);
  });
}
