import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'loan_request_detail_screen.dart';
import 'loan_request_form_screen.dart';
import 'loan_requests_controller.dart';

class LoanRequestsListScreen extends ConsumerStatefulWidget {
  const LoanRequestsListScreen({super.key});

  @override
  ConsumerState<LoanRequestsListScreen> createState() =>
      _LoanRequestsListScreenState();
}

class _LoanRequestsListScreenState
    extends ConsumerState<LoanRequestsListScreen> {
  @override
  void initState() {
    super.initState();
    Future.microtask(() {
      ref.read(loanRequestsControllerProvider.notifier).fetchRequests();
    });
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

  String _formatTimestamp(String value) {
    final date = DateTime.tryParse(value)?.toLocal();
    if (date == null) return value;
    return '${date.year}-${date.month.toString().padLeft(2, '0')}-${date.day.toString().padLeft(2, '0')} '
        '${date.hour.toString().padLeft(2, '0')}:${date.minute.toString().padLeft(2, '0')}';
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(loanRequestsControllerProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('My Loan Requests'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () {
              ref.read(loanRequestsControllerProvider.notifier).fetchRequests();
            },
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () async {
          await Navigator.of(context).push(
            MaterialPageRoute(builder: (_) => const LoanRequestFormScreen()),
          );
          ref.read(loanRequestsControllerProvider.notifier).fetchRequests();
        },
        icon: const Icon(Icons.add),
        label: const Text('Request Loan'),
      ),
      body: RefreshIndicator(
        onRefresh: () async {
          await ref
              .read(loanRequestsControllerProvider.notifier)
              .fetchRequests();
        },
        child: state.isLoading
            ? const Center(child: CircularProgressIndicator())
            : state.errorMessage != null
                ? Center(
                    child: Padding(
                      padding: const EdgeInsets.all(24.0),
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Text(
                            state.errorMessage!,
                            textAlign: TextAlign.center,
                            style: const TextStyle(color: Colors.red),
                          ),
                          const SizedBox(height: 16),
                          ElevatedButton(
                            onPressed: () {
                              ref
                                  .read(loanRequestsControllerProvider.notifier)
                                  .fetchRequests();
                            },
                            child: const Text('Retry'),
                          ),
                        ],
                      ),
                    ),
                  )
                : state.requests.isEmpty
                    ? Center(
                        child: Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            const Icon(Icons.request_quote_outlined,
                                size: 64, color: Colors.grey),
                            const SizedBox(height: 16),
                            const Text(
                              'No loan requests submitted yet',
                              style:
                                  TextStyle(fontSize: 16, color: Colors.grey),
                            ),
                            const SizedBox(height: 16),
                            ElevatedButton.icon(
                              onPressed: () {
                                Navigator.of(context).push(
                                  MaterialPageRoute(
                                      builder: (_) =>
                                          const LoanRequestFormScreen()),
                                );
                              },
                              icon: const Icon(Icons.add),
                              label: const Text('Submit Your First Request'),
                            ),
                          ],
                        ),
                      )
                    : ListView.builder(
                        padding: const EdgeInsets.all(16.0),
                        itemCount: state.requests.length,
                        itemBuilder: (context, index) {
                          final req = state.requests[index];
                          return Card(
                            margin: const EdgeInsets.only(bottom: 12.0),
                            child: ListTile(
                              contentPadding: const EdgeInsets.all(16.0),
                              title: Row(
                                mainAxisAlignment:
                                    MainAxisAlignment.spaceBetween,
                                children: [
                                  Text(
                                    '₱${req.requestedPrincipal.toStringAsFixed(2)}',
                                    style: const TextStyle(
                                      fontSize: 18,
                                      fontWeight: FontWeight.bold,
                                    ),
                                  ),
                                  Chip(
                                    label: Text(
                                      req.status.toUpperCase(),
                                      style: TextStyle(
                                        color: _getStatusColor(req.status),
                                        fontWeight: FontWeight.bold,
                                        fontSize: 12,
                                      ),
                                    ),
                                    backgroundColor: _getStatusColor(req.status)
                                        .withValues(alpha: 0.1),
                                  ),
                                ],
                              ),
                              subtitle: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  const SizedBox(height: 8),
                                  Text(
                                    '${req.requestedTermMonths} months @ ${(req.requestedMonthlyRate * 100).toStringAsFixed(1)}%/mo (${req.requestedPaymentFrequency})',
                                  ),
                                  if (req.quotePreview != null)
                                    Text(
                                      '${req.quotePreview!.numberOfPayments} total payments',
                                      style: const TextStyle(
                                          fontWeight: FontWeight.w600),
                                    ),
                                  const SizedBox(height: 4),
                                  Text(
                                    'Submitted: ${_formatTimestamp(req.submittedAt)}',
                                    style: const TextStyle(
                                        fontSize: 12, color: Colors.grey),
                                  ),
                                ],
                              ),
                              onTap: () {
                                Navigator.of(context).push(
                                  MaterialPageRoute(
                                    builder: (_) =>
                                        LoanRequestDetailScreen(request: req),
                                  ),
                                );
                              },
                            ),
                          );
                        },
                      ),
      ),
    );
  }
}
