import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'owner_loan_request_detail_screen.dart';
import 'owner_loan_requests_controller.dart';

class OwnerLoanRequestsListScreen extends ConsumerStatefulWidget {
  const OwnerLoanRequestsListScreen({super.key});

  @override
  ConsumerState<OwnerLoanRequestsListScreen> createState() =>
      _OwnerLoanRequestsListScreenState();
}

class _OwnerLoanRequestsListScreenState
    extends ConsumerState<OwnerLoanRequestsListScreen> {
  @override
  void initState() {
    super.initState();
    Future.microtask(() {
      ref.read(ownerLoanRequestsControllerProvider.notifier).fetchRequests();
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

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(ownerLoanRequestsStateNotifier);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Review Loan Requests'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () {
              ref
                  .read(ownerLoanRequestsControllerProvider.notifier)
                  .fetchRequests();
            },
          ),
        ],
      ),
      body: Column(
        children: [
          Padding(
            padding:
                const EdgeInsets.symmetric(horizontal: 16.0, vertical: 8.0),
            child: SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              child: Row(
                children: [
                  _buildFilterChip('Pending', 'pending', state.selectedFilter),
                  const SizedBox(width: 8),
                  _buildFilterChip('All Requests', 'all', state.selectedFilter),
                  const SizedBox(width: 8),
                  _buildFilterChip(
                      'Approved', 'approved', state.selectedFilter),
                  const SizedBox(width: 8),
                  _buildFilterChip(
                      'Rejected', 'rejected', state.selectedFilter),
                ],
              ),
            ),
          ),
          Expanded(
            child: RefreshIndicator(
              onRefresh: () async {
                await ref
                    .read(ownerLoanRequestsControllerProvider.notifier)
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
                                        .read(
                                            ownerLoanRequestsControllerProvider
                                                .notifier)
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
                                  const Icon(Icons.check_circle_outline,
                                      size: 64, color: Colors.grey),
                                  const SizedBox(height: 16),
                                  Text(
                                    'No ${state.selectedFilter} loan requests found',
                                    style: const TextStyle(
                                        fontSize: 16, color: Colors.grey),
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
                                        Expanded(
                                          child: Column(
                                            crossAxisAlignment:
                                                CrossAxisAlignment.start,
                                            children: [
                                              Text(
                                                req.borrowerFullName,
                                                style: const TextStyle(
                                                  fontSize: 16,
                                                  fontWeight: FontWeight.bold,
                                                ),
                                              ),
                                              Text(
                                                'National ID: ${req.borrowerNationalId}',
                                                style: const TextStyle(
                                                    fontSize: 12,
                                                    color: Colors.grey),
                                              ),
                                            ],
                                          ),
                                        ),
                                        Chip(
                                          label: Text(
                                            req.status.toUpperCase(),
                                            style: TextStyle(
                                              color:
                                                  _getStatusColor(req.status),
                                              fontWeight: FontWeight.bold,
                                              fontSize: 12,
                                            ),
                                          ),
                                          backgroundColor:
                                              _getStatusColor(req.status)
                                                  .withValues(alpha: 0.1),
                                        ),
                                      ],
                                    ),
                                    subtitle: Column(
                                      crossAxisAlignment:
                                          CrossAxisAlignment.start,
                                      children: [
                                        const SizedBox(height: 8),
                                        Text(
                                          'Requested: ₱${req.requestedPrincipal.toStringAsFixed(2)} (${req.requestedTermMonths} mos @ ${(req.requestedMonthlyRate * 100).toStringAsFixed(1)}%)',
                                          style: const TextStyle(
                                              fontWeight: FontWeight.w600),
                                        ),
                                        const SizedBox(height: 4),
                                        Text(
                                          'Submitted: ${req.submittedAt}',
                                          style: const TextStyle(
                                              fontSize: 12, color: Colors.grey),
                                        ),
                                      ],
                                    ),
                                    onTap: () async {
                                      await Navigator.of(context).push(
                                        MaterialPageRoute(
                                          builder: (_) =>
                                              OwnerLoanRequestDetailScreen(
                                                  request: req),
                                        ),
                                      );
                                      ref
                                          .read(
                                              ownerLoanRequestsControllerProvider
                                                  .notifier)
                                          .fetchRequests();
                                    },
                                  ),
                                );
                              },
                            ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildFilterChip(String label, String value, String currentSelected) {
    final isSelected = currentSelected == value;
    return ChoiceChip(
      label: Text(label),
      selected: isSelected,
      onSelected: (selected) {
        if (selected) {
          ref
              .read(ownerLoanRequestsControllerProvider.notifier)
              .fetchRequests(value);
        }
      },
    );
  }
}

// Convenient getter alias for cleaner riverpod state reading
final ownerLoanRequestsStateNotifier = ownerLoanRequestsControllerProvider;
