import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'owner_loan_detail_screen.dart';
import 'owner_loans_controller.dart';

class OwnerLoansListScreen extends ConsumerWidget {
  const OwnerLoansListScreen({super.key});

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
        return 'Active';
      case 'cancelled':
        return 'Cancelled';
      case 'paid':
        return 'Paid';
      case 'defaulted':
        return 'Defaulted';
      default:
        return status;
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final loansAsync = ref.watch(ownerLoansListProvider);
    final currentFilter = ref.watch(ownerLoansFilterProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Loan Contracts'),
      ),
      body: Column(
        children: [
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
            child: Row(
              children: [
                FilterChip(
                  label: const Text('All'),
                  selected: currentFilter == null,
                  onSelected: (_) =>
                      ref.read(ownerLoansFilterProvider.notifier).state = null,
                ),
                const SizedBox(width: 8),
                FilterChip(
                  label: const Text('Pending Disbursement'),
                  selected: currentFilter == 'pending_disbursement',
                  onSelected: (_) => ref
                      .read(ownerLoansFilterProvider.notifier)
                      .state = 'pending_disbursement',
                ),
                const SizedBox(width: 8),
                FilterChip(
                  label: const Text('Active'),
                  selected: currentFilter == 'active',
                  onSelected: (_) => ref
                      .read(ownerLoansFilterProvider.notifier)
                      .state = 'active',
                ),
                const SizedBox(width: 8),
                FilterChip(
                  label: const Text('Cancelled'),
                  selected: currentFilter == 'cancelled',
                  onSelected: (_) => ref
                      .read(ownerLoansFilterProvider.notifier)
                      .state = 'cancelled',
                ),
              ],
            ),
          ),
          Expanded(
            child: loansAsync.when(
              data: (loans) {
                if (loans.isEmpty) {
                  return const Center(child: Text('No loan contracts found.'));
                }
                return RefreshIndicator(
                  onRefresh: () async {
                    ref.invalidate(ownerLoansListProvider);
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
                            'Borrower: ${loan.borrower?.fullName ?? "Borrower ${loan.borrowerId.substring(0, 8)}"}',
                            style: const TextStyle(fontWeight: FontWeight.bold),
                          ),
                          subtitle: Text(
                            'Principal: ₱${loan.originalPrincipal} • ${loan.termMonths} mos (${loan.paymentFrequency})',
                          ),
                          trailing: Column(
                            mainAxisAlignment: MainAxisAlignment.center,
                            crossAxisAlignment: CrossAxisAlignment.end,
                            children: [
                              Chip(
                                label: Text(
                                  _formatStatusLabel(loan.status),
                                  style: const TextStyle(
                                    color: Colors.white,
                                    fontSize: 10,
                                  ),
                                ),
                                backgroundColor: _getStatusColor(loan.status),
                                padding: EdgeInsets.zero,
                              ),
                            ],
                          ),
                          onTap: () {
                            Navigator.push(
                              context,
                              MaterialPageRoute(
                                builder: (_) =>
                                    OwnerLoanDetailScreen(loanId: loan.id),
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
              error: (err, _) =>
                  Center(child: Text('Error loading loans: $err')),
            ),
          ),
        ],
      ),
    );
  }
}
