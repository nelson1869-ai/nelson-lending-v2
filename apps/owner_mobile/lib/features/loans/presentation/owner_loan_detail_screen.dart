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

  Future<void> _handleRecordPayment(BuildContext context, WidgetRef ref) async {
    final now = DateTime.now();
    final defaultDate =
        "${now.year}-${now.month.toString().padLeft(2, '0')}-${now.day.toString().padLeft(2, '0')}";

    final amountController = TextEditingController();
    final dateController = TextEditingController(text: defaultDate);
    final refController = TextEditingController();
    final noteController = TextEditingController();
    final formKey = GlobalKey<FormState>();

    final inputResult = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Record Payment'),
        content: Form(
          key: formKey,
          child: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                TextFormField(
                  controller: amountController,
                  keyboardType:
                      const TextInputType.numberWithOptions(decimal: true),
                  decoration: const InputDecoration(
                    labelText: 'Payment Amount (₱)',
                    hintText: 'e.g. 500.00',
                  ),
                  validator: (val) {
                    if (val == null || val.trim().isEmpty) {
                      return 'Amount is required';
                    }
                    final num = double.tryParse(val.trim());
                    if (num == null || num <= 0) {
                      return 'Amount must be greater than 0';
                    }
                    return null;
                  },
                ),
                const SizedBox(height: 12),
                TextFormField(
                  controller: dateController,
                  decoration: const InputDecoration(
                    labelText: 'Payment Date (YYYY-MM-DD)',
                  ),
                  validator: (val) {
                    if (val == null || val.trim().isEmpty) {
                      return 'Date is required';
                    }
                    return null;
                  },
                ),
                const SizedBox(height: 12),
                TextFormField(
                  controller: refController,
                  decoration: const InputDecoration(
                    labelText: 'Reference (optional)',
                    hintText: 'e.g. Cash Receipt #123, GCash ref',
                  ),
                ),
                const SizedBox(height: 12),
                TextFormField(
                  controller: noteController,
                  decoration: const InputDecoration(
                    labelText: 'Note (optional)',
                    hintText: 'e.g. Over-the-counter payment',
                  ),
                ),
              ],
            ),
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () {
              if (formKey.currentState?.validate() == true) {
                Navigator.pop(ctx, true);
              }
            },
            child: const Text('Continue'),
          ),
        ],
      ),
    );

    if (inputResult != true) return;

    final amountStr = amountController.text.trim();
    final dateStr = dateController.text.trim();
    final referenceStr = refController.text.trim();
    final noteStr = noteController.text.trim();

    if (!context.mounted) return;

    final confirm = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Confirm Payment Submission'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Amount: ₱$amountStr'),
            Text('Date: $dateStr'),
            if (referenceStr.isNotEmpty) Text('Reference: $referenceStr'),
            if (noteStr.isNotEmpty) Text('Note: $noteStr'),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('Back'),
          ),
          ElevatedButton(
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Submit Payment'),
          ),
        ],
      ),
    );

    if (confirm != true) return;

    final controller = ref.read(ownerLoansControllerProvider.notifier);
    final payment = await controller.postPayment(
      loanId: loanId,
      amount: amountStr,
      paymentDate: dateStr,
      reference: referenceStr.isNotEmpty ? referenceStr : null,
      note: noteStr.isNotEmpty ? noteStr : null,
    );

    if (context.mounted && payment != null) {
      await showDialog(
        context: context,
        builder: (ctx) => AlertDialog(
          title: const Text('Payment Allocation Result'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('Payment Amount: ₱${payment.amount}',
                  style: const TextStyle(fontWeight: FontWeight.bold)),
              const Divider(),
              Text('Interest Paid: ₱${payment.interestPaid}'),
              Text('Principal Paid: ₱${payment.principalPaid}'),
              Text('Remaining Principal: ₱${payment.remainingPrincipal}',
                  style: const TextStyle(fontWeight: FontWeight.bold)),
              if (double.tryParse(payment.unappliedCredit) != null &&
                  double.parse(payment.unappliedCredit) > 0)
                Text('Unapplied Credit: ₱${payment.unappliedCredit}',
                    style: const TextStyle(color: Colors.green)),
            ],
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(ctx),
              child: const Text('Close'),
            ),
          ],
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final loanAsync = ref.watch(ownerLoanDetailProvider(loanId));
    final paymentsAsync = ref.watch(ownerLoanPaymentsProvider(loanId));
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
                      if (loan.paidAt != null) ...[
                        const SizedBox(height: 4),
                        Text(
                          'Paid at: ${loan.paidAt}',
                          style:
                              const TextStyle(fontSize: 12, color: Colors.teal),
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
              if (loan.status == 'active' || loan.status == 'defaulted') ...[
                SizedBox(
                  width: double.infinity,
                  child: ElevatedButton.icon(
                    icon: const Icon(Icons.payment),
                    label: const Text('Record Payment'),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: Colors.teal,
                      foregroundColor: Colors.white,
                      padding: const EdgeInsets.symmetric(vertical: 14),
                    ),
                    onPressed: controllerState.isLoading
                        ? null
                        : () => _handleRecordPayment(context, ref),
                  ),
                ),
                const SizedBox(height: 16),
              ],
              const Text(
                'Payment History',
                style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 8),
              paymentsAsync.when(
                data: (payments) {
                  if (payments.isEmpty) {
                    return const Padding(
                      padding: EdgeInsets.symmetric(vertical: 8.0),
                      child: Text('No payments posted yet.',
                          style: TextStyle(color: Colors.grey)),
                    );
                  }
                  return SingleChildScrollView(
                    scrollDirection: Axis.horizontal,
                    child: DataTable(
                      columns: const [
                        DataColumn(label: Text('Date')),
                        DataColumn(label: Text('Amount')),
                        DataColumn(label: Text('Interest')),
                        DataColumn(label: Text('Principal')),
                        DataColumn(label: Text('Balance')),
                        DataColumn(label: Text('Unapplied')),
                        DataColumn(label: Text('Reference')),
                      ],
                      rows: payments.map((p) {
                        return DataRow(cells: [
                          DataCell(Text(p.paymentDate)),
                          DataCell(Text('₱${p.amount}')),
                          DataCell(Text('₱${p.interestPaid}')),
                          DataCell(Text('₱${p.principalPaid}')),
                          DataCell(Text('₱${p.remainingPrincipal}')),
                          DataCell(Text('₱${p.unappliedCredit}')),
                          DataCell(Text(p.reference ?? '-')),
                        ]);
                      }).toList(),
                    ),
                  );
                },
                loading: () => const Center(child: CircularProgressIndicator()),
                error: (e, _) => Text('Error loading payments: $e'),
              ),
              const SizedBox(height: 16),
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
