import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../domain/loan_request_models.dart';
import 'loan_requests_controller.dart';

class LoanRequestDetailScreen extends ConsumerWidget {
  final LoanRequestModel request;

  const LoanRequestDetailScreen({super.key, required this.request});

  String _formatTimestamp(String value) {
    final date = DateTime.tryParse(value)?.toLocal();
    if (date == null) return value;
    return '${date.year}-${date.month.toString().padLeft(2, '0')}-${date.day.toString().padLeft(2, '0')} '
        '${date.hour.toString().padLeft(2, '0')}:${date.minute.toString().padLeft(2, '0')}';
  }

  String _statusExplanation(String status) {
    switch (status.toLowerCase()) {
      case 'approved':
        return 'Approved by the Owner. Loan creation and disbursement may still be pending.';
      case 'rejected':
        return 'This request was rejected by the Owner.';
      case 'cancelled':
        return 'This request was cancelled.';
      default:
        return 'This request is waiting for Owner review.';
    }
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

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final state = ref.watch(loanRequestsControllerProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Loan Request Details'),
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
                      '₱${request.requestedPrincipal.toStringAsFixed(2)}',
                      style: TextStyle(
                        fontSize: 32,
                        fontWeight: FontWeight.bold,
                        color: Theme.of(context).colorScheme.primary,
                      ),
                    ),
                    const SizedBox(height: 12),
                    Text(_statusExplanation(request.status),
                        textAlign: TextAlign.center,
                        style: const TextStyle(color: Colors.grey)),
                    const SizedBox(height: 8),
                    Container(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 16, vertical: 6),
                      decoration: BoxDecoration(
                        color: _getStatusColor(request.status)
                            .withValues(alpha: 0.1),
                        borderRadius: BorderRadius.circular(16),
                      ),
                      child: Text(
                        request.status.toUpperCase(),
                        style: TextStyle(
                          color: _getStatusColor(request.status),
                          fontWeight: FontWeight.bold,
                          fontSize: 14,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 20),
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16.0),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      'Request Terms',
                      style:
                          TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                    ),
                    const Divider(height: 20),
                    _buildRow('Monthly Rate',
                        '${(request.requestedMonthlyRate * 100).toStringAsFixed(2)}%'),
                    _buildRow(
                        'Term Months', '${request.requestedTermMonths} months'),
                    _buildRow('Frequency', request.requestedPaymentFrequency),
                    _buildRow('First Due Date', request.requestedFirstDueDate),
                    _buildRow('Submitted At', _formatTimestamp(request.submittedAt)),
                  ],
                ),
              ),
            ),
            if (request.quotePreview != null) ...[
              const SizedBox(height: 20),
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16.0),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Estimated Repayment',
                        style: TextStyle(
                          fontSize: 16,
                          fontWeight: FontWeight.bold,
                          color: Theme.of(context).colorScheme.primary,
                        ),
                      ),
                      const Divider(height: 20),
                      _buildRow(
                        'Number of Payments',
                        '${request.quotePreview!.numberOfPayments} payments',
                      ),
                      _buildRow(
                        'Periodic Payment',
                        '₱${request.quotePreview!.periodicPayment.toStringAsFixed(2)}',
                      ),
                      _buildRow(
                        'Total Interest',
                        '₱${request.quotePreview!.totalInterest.toStringAsFixed(2)}',
                      ),
                      _buildRow(
                        'Total Repayable',
                        '₱${request.quotePreview!.totalAmount.toStringAsFixed(2)}',
                      ),
                    ],
                  ),
                ),
              ),
            ],
            if (request.status == 'pending') ...[
              const SizedBox(height: 24),
              OutlinedButton.icon(
                onPressed: state.isLoading
                    ? null
                    : () async {
                        final confirm = await showDialog<bool>(
                          context: context,
                          builder: (ctx) => AlertDialog(
                            title: const Text('Cancel Request'),
                            content: const Text(
                                'Are you sure you want to cancel this pending loan request?'),
                            actions: [
                              TextButton(
                                onPressed: () => Navigator.pop(ctx, false),
                                child: const Text('No'),
                              ),
                              ElevatedButton(
                                onPressed: () => Navigator.pop(ctx, true),
                                style: ElevatedButton.styleFrom(
                                    backgroundColor: Colors.red),
                                child: const Text('Yes, Cancel'),
                              ),
                            ],
                          ),
                        );
                        if (confirm == true) {
                          final ok = await ref
                              .read(loanRequestsControllerProvider.notifier)
                              .cancelRequest(request.id);
                          if (ok && context.mounted) {
                            ScaffoldMessenger.of(context).showSnackBar(
                              const SnackBar(
                                  content: Text('Request cancelled')),
                            );
                            Navigator.pop(context);
                          }
                        }
                      },
                icon: const Icon(Icons.cancel, color: Colors.red),
                label: const Text('Cancel Request',
                    style: TextStyle(color: Colors.red)),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6.0),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label, style: const TextStyle(color: Colors.grey)),
          const SizedBox(width: 16),
          Flexible(
            child: Text(value, textAlign: TextAlign.end,
                style: const TextStyle(fontWeight: FontWeight.w600)),
          ),
        ],
      ),
    );
  }
}
