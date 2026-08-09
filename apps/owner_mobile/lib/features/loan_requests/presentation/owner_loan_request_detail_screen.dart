import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../loans/presentation/owner_loans_controller.dart';
import '../domain/owner_loan_request_models.dart';
import 'owner_loan_requests_controller.dart';

class OwnerLoanRequestDetailScreen extends ConsumerStatefulWidget {
  final OwnerLoanRequestDetailModel request;

  const OwnerLoanRequestDetailScreen({super.key, required this.request});

  @override
  ConsumerState<OwnerLoanRequestDetailScreen> createState() =>
      _OwnerLoanRequestDetailScreenState();
}

class _OwnerLoanRequestDetailScreenState
    extends ConsumerState<OwnerLoanRequestDetailScreen> {
  final _noteController = TextEditingController();

  @override
  void dispose() {
    _noteController.dispose();
    super.dispose();
  }

  Color _getStatusColor(String status) {
    switch (status.toLowerCase()) {
      case 'approved':
        return Colors.green;
      case 'rejected':
        return Colors.red;
      case 'cancelled':
        return Colors.grey;
      case 'pending':
      default:
        return Colors.orange;
    }
  }

  Future<void> _handleAction(bool isApprove) async {
    final note = await showDialog<String>(
      context: context,
      builder: (ctx) {
        _noteController.clear();
        return AlertDialog(
          title:
              Text(isApprove ? 'Accept Loan Request' : 'Reject Loan Request'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                isApprove
                    ? 'Accept loan request for ${widget.request.borrowerFullName}? (Note: Loan activation is deferred to M11)'
                    : 'Reject loan request for ${widget.request.borrowerFullName}?',
              ),
              const SizedBox(height: 16),
              TextField(
                controller: _noteController,
                decoration: const InputDecoration(
                  labelText: 'Owner Review Note (Optional)',
                  border: OutlineInputBorder(),
                ),
                maxLines: 2,
              ),
            ],
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(ctx, null),
              child: const Text('Cancel'),
            ),
            ElevatedButton(
              onPressed: () => Navigator.pop(ctx, _noteController.text.trim()),
              style: ElevatedButton.styleFrom(
                backgroundColor: isApprove ? Colors.green : Colors.red,
                foregroundColor: Colors.white,
              ),
              child: Text(isApprove ? 'Accept' : 'Reject'),
            ),
          ],
        );
      },
    );

    if (note != null && mounted) {
      final notifier = ref.read(ownerLoanRequestsControllerProvider.notifier);
      final success = isApprove
          ? await notifier.approveRequest(widget.request.id, ownerNote: note)
          : await notifier.rejectRequest(widget.request.id, ownerNote: note);

      if (success && mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(isApprove
                ? 'Loan request accepted successfully'
                : 'Loan request rejected'),
          ),
        );
        Navigator.pop(context);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final req = widget.request;
    final quote = req.quotePreview;
    final state = ref.watch(ownerLoanRequestsControllerProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Loan Request Review'),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(24.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Card(
              child: Padding(
                padding: const EdgeInsets.all(20.0),
                child: Column(
                  children: [
                    Text(
                      '₱${req.requestedPrincipal.toStringAsFixed(2)}',
                      style: TextStyle(
                        fontSize: 32,
                        fontWeight: FontWeight.bold,
                        color: Theme.of(context).colorScheme.primary,
                      ),
                    ),
                    const SizedBox(height: 8),
                    Container(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 16, vertical: 6),
                      decoration: BoxDecoration(
                        color:
                            _getStatusColor(req.status).withValues(alpha: 0.1),
                        borderRadius: BorderRadius.circular(16),
                      ),
                      child: Text(
                        req.status.toUpperCase(),
                        style: TextStyle(
                          color: _getStatusColor(req.status),
                          fontWeight: FontWeight.bold,
                          fontSize: 14,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 16),
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16.0),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      'Borrower Profile',
                      style:
                          TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                    ),
                    const Divider(height: 20),
                    _buildRow('Full Name', req.borrowerFullName),
                    _buildRow('National ID', req.borrowerNationalId),
                    _buildRow('Phone Number', req.borrowerPhoneNumber),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 16),
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16.0),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      'Requested Loan Parameters',
                      style:
                          TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                    ),
                    const Divider(height: 20),
                    _buildRow('Monthly Rate',
                        '${(req.requestedMonthlyRate * 100).toStringAsFixed(2)}%'),
                    _buildRow(
                        'Term Months', '${req.requestedTermMonths} months'),
                    _buildRow('Frequency', req.requestedPaymentFrequency),
                    _buildRow('First Due Date', req.requestedFirstDueDate),
                    _buildRow('Submitted At', _formatDateTime(req.submittedAt)),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 16),
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16.0),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Calculated Quote & Schedule',
                      style: TextStyle(
                        fontSize: 16,
                        fontWeight: FontWeight.bold,
                        color: Theme.of(context).colorScheme.primary,
                      ),
                    ),
                    const Divider(height: 20),
                    _buildRow('Periodic Payment',
                        '₱${quote.periodicPayment.toStringAsFixed(2)}'),
                    _buildRow(
                        'Total Payments', '${quote.numberOfPayments} payments'),
                    _buildRow('Total Interest',
                        '₱${quote.totalInterest.toStringAsFixed(2)}'),
                    _buildRow('Total Amount',
                        '₱${quote.totalAmount.toStringAsFixed(2)}'),
                    const SizedBox(height: 12),
                    const Text('Schedule Projection',
                        style: TextStyle(fontWeight: FontWeight.bold)),
                    const SizedBox(height: 8),
                    ...quote.schedule.map(
                      (item) => Padding(
                        padding: const EdgeInsets.symmetric(vertical: 6),
                        child: Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Expanded(
                              child: Text(
                                '#${item.paymentNumber}\n${item.dueDate}',
                              ),
                            ),
                            const SizedBox(width: 12),
                            Expanded(
                              child: Text(
                                '₱${item.paymentAmount.toStringAsFixed(2)}\nInterest: ₱${item.interestPaid.toStringAsFixed(2)}',
                                textAlign: TextAlign.end,
                                style: const TextStyle(
                                  fontWeight: FontWeight.w500,
                                ),
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ),
            if (req.ownerNote != null && req.ownerNote!.isNotEmpty) ...[
              const SizedBox(height: 16),
              Card(
                color: Colors.blue.shade50,
                child: Padding(
                  padding: const EdgeInsets.all(16.0),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Owner Note',
                        style: TextStyle(
                          fontSize: 14,
                          fontWeight: FontWeight.bold,
                          color: Colors.blue.shade900,
                        ),
                      ),
                      const SizedBox(height: 6),
                      Text(
                        req.ownerNote!,
                        style: TextStyle(color: Colors.blue.shade900),
                      ),
                    ],
                  ),
                ),
              ),
            ],
            if (req.status == 'approved' && req.loanId == null) ...[
              const SizedBox(height: 24),
              SizedBox(
                width: double.infinity,
                child: ElevatedButton.icon(
                  onPressed: state.isLoading
                      ? null
                      : () async {
                          final loan = await ref
                              .read(ownerLoansControllerProvider.notifier)
                              .createLoanFromRequest(req.id);
                          if (!context.mounted) return;
                          if (loan != null) {
                            ScaffoldMessenger.of(context).showSnackBar(
                              const SnackBar(
                                content:
                                    Text('Loan contract created successfully!'),
                              ),
                            );
                            Navigator.pop(context);
                          } else {
                            final error =
                                ref.read(ownerLoansControllerProvider).error;
                            ScaffoldMessenger.of(context).showSnackBar(
                              SnackBar(
                                content: Text(
                                  'Unable to create loan${error == null ? '' : ': $error'}',
                                ),
                                backgroundColor: Colors.red,
                              ),
                            );
                          }
                        },
                  style: ElevatedButton.styleFrom(
                    backgroundColor: Colors.blue,
                    foregroundColor: Colors.white,
                    padding: const EdgeInsets.symmetric(vertical: 16),
                  ),
                  icon: const Icon(Icons.add_task),
                  label: const Text(
                    'Create Loan',
                    style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
                  ),
                ),
              ),
            ],
            if (req.status == 'approved' && req.loanId != null) ...[
              const SizedBox(height: 24),
              const Card(
                child: Padding(
                  padding: EdgeInsets.all(16),
                  child: Row(
                    children: [
                      Icon(Icons.check_circle, color: Colors.green),
                      SizedBox(width: 12),
                      Expanded(child: Text('Loan contract already created.')),
                    ],
                  ),
                ),
              ),
            ],
            if (req.status == 'pending') ...[
              const SizedBox(height: 24),
              Row(
                children: [
                  Expanded(
                    child: ElevatedButton.icon(
                      onPressed:
                          state.isLoading ? null : () => _handleAction(true),
                      style: ElevatedButton.styleFrom(
                        backgroundColor: Colors.green,
                        foregroundColor: Colors.white,
                        padding: const EdgeInsets.symmetric(vertical: 16),
                      ),
                      icon: const Icon(Icons.check),
                      label: const Text('Accept Loan Request',
                          style: TextStyle(fontWeight: FontWeight.bold)),
                    ),
                  ),
                  const SizedBox(width: 16),
                  Expanded(
                    child: ElevatedButton.icon(
                      onPressed:
                          state.isLoading ? null : () => _handleAction(false),
                      style: ElevatedButton.styleFrom(
                        backgroundColor: Colors.red,
                        foregroundColor: Colors.white,
                        padding: const EdgeInsets.symmetric(vertical: 16),
                      ),
                      icon: const Icon(Icons.close),
                      label: const Text('Reject',
                          style: TextStyle(fontWeight: FontWeight.bold)),
                    ),
                  ),
                ],
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4.0),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Expanded(
            flex: 2,
            child: Text(label, style: const TextStyle(color: Colors.grey)),
          ),
          const SizedBox(width: 12),
          Expanded(
            flex: 3,
            child: Text(
              value,
              textAlign: TextAlign.end,
              style: const TextStyle(fontWeight: FontWeight.bold),
            ),
          ),
        ],
      ),
    );
  }

  String _formatDateTime(String raw) {
    final parsed = DateTime.tryParse(raw);
    if (parsed == null) return raw;
    final local = parsed.toLocal();
    final date =
        '${local.year}-${local.month.toString().padLeft(2, '0')}-${local.day.toString().padLeft(2, '0')}';
    final time =
        '${local.hour.toString().padLeft(2, '0')}:${local.minute.toString().padLeft(2, '0')}';
    return '$date $time';
  }
}
