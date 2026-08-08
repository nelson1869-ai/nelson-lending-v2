import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'borrower_loans_controller.dart';

class BorrowerLoanDetailScreen extends ConsumerWidget {
  final String loanId;

  const BorrowerLoanDetailScreen({super.key, required this.loanId});

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
    final loanAsync = ref.watch(borrowerLoanDetailProvider(loanId));

    return Scaffold(
      appBar: AppBar(
        title: const Text('My Loan Contract'),
      ),
      body: loanAsync.when(
        data: (loan) => SingleChildScrollView(
          padding: const EdgeInsets.all(16.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16.0),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          const Text(
                            'Status',
                            style: TextStyle(fontWeight: FontWeight.bold),
                          ),
                          Chip(
                            label: Text(
                              _formatStatusLabel(loan.status),
                              style: const TextStyle(color: Colors.white),
                            ),
                            backgroundColor: _getStatusColor(loan.status),
                          ),
                        ],
                      ),
                      const SizedBox(height: 8),
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          const Text('Original Principal:'),
                          Text(
                            '₱${loan.originalPrincipal}',
                            style: const TextStyle(fontWeight: FontWeight.bold),
                          ),
                        ],
                      ),
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          const Text('Outstanding Balance:'),
                          Text(
                            '₱${loan.outstandingPrincipal}',
                            style: const TextStyle(
                              fontWeight: FontWeight.bold,
                              fontSize: 16,
                              color: Colors.blue,
                            ),
                          ),
                        ],
                      ),
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          const Text('Monthly Interest Rate:'),
                          Text(
                              '${(double.parse(loan.monthlyRate) * 100).toStringAsFixed(2)}%'),
                        ],
                      ),
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          const Text('Term & Frequency:'),
                          Text(
                              '${loan.termMonths} mos (${loan.paymentFrequency})'),
                        ],
                      ),
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          const Text('First Due Date:'),
                          Text(loan.firstDueDate),
                        ],
                      ),
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          const Text('Final Due Date:'),
                          Text(loan.finalDueDate),
                        ],
                      ),
                      if (loan.disbursedAt != null) ...[
                        const SizedBox(height: 4),
                        Text(
                          'Disbursed On: ${loan.disbursedAt}',
                          style:
                              const TextStyle(fontSize: 12, color: Colors.grey),
                        ),
                      ],
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 16),
              const Text(
                'Repayment Schedule',
                style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 8),
              SingleChildScrollView(
                scrollDirection: Axis.horizontal,
                child: DataTable(
                  columns: const [
                    DataColumn(label: Text('#')),
                    DataColumn(label: Text('Due Date')),
                    DataColumn(label: Text('Principal')),
                    DataColumn(label: Text('Interest')),
                    DataColumn(label: Text('Total Payment')),
                    DataColumn(label: Text('Ending Balance')),
                  ],
                  rows: loan.quotePreview.schedule.map((item) {
                    return DataRow(cells: [
                      DataCell(Text(item.installmentNumber.toString())),
                      DataCell(Text(item.dueDate)),
                      DataCell(Text('₱${item.scheduledPrincipal}')),
                      DataCell(Text('₱${item.interestDue}')),
                      DataCell(Text('₱${item.scheduledPayment}')),
                      DataCell(Text('₱${item.closingPrincipal}')),
                    ]);
                  }).toList(),
                ),
              ),
            ],
          ),
        ),
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (err, _) => Center(child: Text('Error loading loan: $err')),
      ),
    );
  }
}
