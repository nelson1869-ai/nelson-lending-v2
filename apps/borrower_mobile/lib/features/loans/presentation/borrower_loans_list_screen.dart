import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'borrower_loan_detail_screen.dart';
import 'borrower_loans_controller.dart';

class BorrowerLoansListScreen extends ConsumerWidget {
  const BorrowerLoansListScreen({super.key});

  Color _getStatusColor(String status) {
    switch (status.toLowerCase()) {
      case 'active':
        return Colors.green;
      case 'pending_disbursement':
        return Colors.blue;
      case 'cancelled':
        return Colors.grey;
      case 'paid':
        return Colors.teal;
      case 'defaulted':
        return Colors.red;
      default:
        return Colors.orange;
    }
  }

  String _formatStatusLabel(String status) {
    switch (status.toLowerCase()) {
      case 'pending_disbursement':
        return 'Pending Disbursement';
      case 'active':
        return 'Active Contract';
      case 'cancelled':
        return 'Cancelled';
      case 'paid':
        return 'Fully Paid';
      case 'defaulted':
        return 'Defaulted';
      default:
        return status;
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final loansAsync = ref.watch(borrowerLoansListProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('My Loans'),
      ),
      body: loansAsync.when(
        data: (loans) {
          if (loans.isEmpty) {
            return const Center(child: Text('You have no loan contracts yet.'));
          }
          return RefreshIndicator(
            onRefresh: () async {
              ref.invalidate(borrowerLoansListProvider);
            },
            child: ListView.builder(
              itemCount: loans.length,
              itemBuilder: (ctx, index) {
                final loan = loans[index];
                return Card(
                  margin: const EdgeInsets.symmetric(
                    horizontal: 16,
                    vertical: 6,
                  ),
                  child: ListTile(
                    title: Text(
                      'Principal: ₱${loan.originalPrincipal}',
                      style: const TextStyle(fontWeight: FontWeight.bold),
                    ),
                    subtitle: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'Outstanding: ₱${loan.outstandingPrincipal} • '
                          '${loan.termMonths} mos • '
                          '${loan.numberOfPayments} total payments',
                        ),
                        if (loan.nextPaymentAmount != null)
                          Text(
                            'Next payment: ₱${loan.nextPaymentAmount} '
                            '(Interest: ₱${loan.nextInterestAmount ?? '0.00'})',
                            style: const TextStyle(fontWeight: FontWeight.w600),
                          ),
                      ],
                    ),
                    trailing: Chip(
                      label: Text(
                        _formatStatusLabel(loan.status),
                        style: const TextStyle(
                          color: Colors.white,
                          fontSize: 10,
                        ),
                      ),
                      backgroundColor: _getStatusColor(loan.status),
                    ),
                    onTap: () {
                      Navigator.push(
                        context,
                        MaterialPageRoute(
                          builder: (_) =>
                              BorrowerLoanDetailScreen(loanId: loan.id),
                        ),
                      );
                    },
                  ),
                );
              },
            ),
          );
        },
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (err, _) => Center(child: Text('Error loading loans: $err')),
      ),
    );
  }
}
