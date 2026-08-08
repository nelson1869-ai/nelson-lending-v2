import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'owner_loans_controller.dart';


class OwnerLoanDetailScreen extends ConsumerWidget {
  final String loanId;

  const OwnerLoanDetailScreen({super.key, required this.loanId});

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

  Future<void> _handleDisburse(BuildContext context, WidgetRef ref) async {
    final confirm = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Confirm Disbursement'),
        content: const Text(
          'Are you sure you want to confirm disbursement of funds to the borrower? This will transition the loan status to Active.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Confirm Release'),
          ),
        ],
      ),
    );

    if (confirm != true) return;

    final controller = ref.read(ownerLoansControllerProvider.notifier);
    final result = await controller.disburseLoan(loanId);
    if (context.mounted && result != null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
            content: Text('Loan disbursed successfully and is now Active!')),
      );
    }
  }

  Future<void> _handleCancel(BuildContext context, WidgetRef ref) async {
    final confirm = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Cancel Loan'),
        content: const Text(
          'Are you sure you want to cancel this loan contract before disbursement?',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('Back'),
          ),
          ElevatedButton(
            style: ElevatedButton.styleFrom(backgroundColor: Colors.red),
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Cancel Loan'),
          ),
        ],
      ),
    );

    if (confirm != true) return;

    final controller = ref.read(ownerLoansControllerProvider.notifier);
    final result = await controller.cancelLoan(loanId);
    if (context.mounted && result != null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Loan contract cancelled.')),
      );
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final loanAsync = ref.watch(ownerLoanDetailProvider(loanId));
    final controllerState = ref.watch(ownerLoansControllerProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Loan Contract Details'),
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
                      Text(
                        'Borrower: ${loan.borrower?.fullName ?? "Borrower ${loan.borrowerId.substring(0, 8)}"}',
                        style: const TextStyle(
                            fontSize: 16, fontWeight: FontWeight.bold),
                      ),
                      Text(
                          'Phone: ${loan.borrower?.phoneNumberNormalized ?? "N/A"}'),
                      const Divider(),
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
                          const Text('Outstanding Principal:'),
                          Text(
                            '₱${loan.outstandingPrincipal}',
                            style: const TextStyle(fontWeight: FontWeight.bold),
                          ),
                        ],
                      ),
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          const Text('Monthly Rate:'),
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
                          'Disbursed: ${loan.disbursedAt}',
                          style:
                              const TextStyle(fontSize: 12, color: Colors.grey),
                        ),
                      ],
                      if (loan.cancelledAt != null) ...[
                        const SizedBox(height: 4),
                        Text(
                          'Cancelled: ${loan.cancelledAt}',
                          style:
                              const TextStyle(fontSize: 12, color: Colors.grey),
                        ),
                      ],
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 16),
              if (loan.status == 'pending_disbursement') ...[
                Row(
                  children: [
                    Expanded(
                      child: ElevatedButton.icon(
                        icon: const Icon(Icons.check_circle),
                        label: const Text('Confirm Disbursement'),
                        style: ElevatedButton.styleFrom(
                          backgroundColor: Colors.green,
                          foregroundColor: Colors.white,
                          padding: const EdgeInsets.symmetric(vertical: 14),
                        ),
                        onPressed: controllerState.isLoading
                            ? null
                            : () => _handleDisburse(context, ref),
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: OutlinedButton.icon(
                        icon: const Icon(Icons.cancel),
                        label: const Text('Cancel Loan'),
                        style: OutlinedButton.styleFrom(
                          foregroundColor: Colors.red,
                          padding: const EdgeInsets.symmetric(vertical: 14),
                        ),
                        onPressed: controllerState.isLoading
                            ? null
                            : () => _handleCancel(context, ref),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 16),
              ],
              const Text(
                'Planned Repayment Schedule',
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
                    DataColumn(label: Text('Payment')),
                    DataColumn(label: Text('Balance')),
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
