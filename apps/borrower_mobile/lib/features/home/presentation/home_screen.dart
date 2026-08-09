import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/api_client.dart';
import '../../auth/presentation/auth_controller.dart';
import '../../loan_requests/presentation/loan_request_form_screen.dart';
import '../../loan_requests/presentation/loan_requests_list_screen.dart';
import '../../loans/presentation/borrower_loans_list_screen.dart';
import '../../loans/presentation/borrower_loans_controller.dart';
import '../../notifications/presentation/borrower_notifications_screen.dart';

class HomeScreen extends ConsumerStatefulWidget {
  const HomeScreen({super.key});

  @override
  ConsumerState<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends ConsumerState<HomeScreen> {
  bool _isCheckingHealth = false;
  bool? _isBackendReady;

  @override
  void initState() {
    super.initState();
    _checkHealth();
  }

  Future<void> _checkHealth() async {
    setState(() {
      _isCheckingHealth = true;
      _isBackendReady = null;
    });

    try {
      final apiClient = ref.read(apiClientProvider);
      final response = await apiClient.dio.get('/health/ready');
      setState(() {
        _isCheckingHealth = false;
        _isBackendReady = response.statusCode == 200;
      });
    } on DioException catch (_) {
      setState(() {
        _isCheckingHealth = false;
        _isBackendReady = false;
      });
    } catch (_) {
      setState(() {
        _isCheckingHealth = false;
        _isBackendReady = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final authState = ref.watch(authControllerProvider);
    final profile = authState.borrower;
    final loansAsync = ref.watch(borrowerLoansListProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Borrower Portal'),
        actions: [
          IconButton(
            icon: const Icon(Icons.logout),
            tooltip: 'Sign Out',
            onPressed: () {
              ref.read(authControllerProvider.notifier).logout();
            },
          ),
        ],
      ),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Card(
                color: Theme.of(context).colorScheme.primaryContainer,
                child: Padding(
                  padding: const EdgeInsets.all(20.0),
                  child: Column(
                    children: [
                      CircleAvatar(
                        radius: 36,
                        backgroundColor: Theme.of(context).colorScheme.primary,
                        child: Text(
                          profile != null && profile.firstName.isNotEmpty
                              ? profile.firstName[0].toUpperCase()
                              : 'B',
                          style: TextStyle(
                            fontSize: 32,
                            fontWeight: FontWeight.bold,
                            color: Theme.of(context).colorScheme.onPrimary,
                          ),
                        ),
                      ),
                      const SizedBox(height: 12),
                      Text(
                        profile != null
                            ? 'Welcome, ${profile.fullName}'
                            : 'Welcome, Borrower',
                        style: TextStyle(
                          fontSize: 20,
                          fontWeight: FontWeight.bold,
                          color:
                              Theme.of(context).colorScheme.onPrimaryContainer,
                        ),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        profile?.phoneNumber ?? '',
                        style: TextStyle(
                          fontSize: 14,
                          color: Theme.of(context)
                              .colorScheme
                              .onPrimaryContainer
                              .withValues(alpha: 0.8),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 24),
              loansAsync.when(
                loading: () => const Card(
                  child: Padding(
                    padding: EdgeInsets.all(20),
                    child: Center(child: CircularProgressIndicator()),
                  ),
                ),
                error: (_, __) => const SizedBox.shrink(),
                data: (loans) {
                  final active = loans.where((loan) => loan.status == 'active').toList();
                  if (active.isEmpty) return const SizedBox.shrink();
                  active.sort((a, b) =>
                      (a.nextInterestDueDate ?? a.firstDueDate)
                          .compareTo(b.nextInterestDueDate ?? b.firstDueDate));
                  final balance = active.fold<double>(
                    0,
                    (sum, loan) => sum + (double.tryParse(loan.outstandingPrincipal) ?? 0),
                  );
                  final totalNextPayment = active.fold<double>(
                    0,
                    (sum, loan) =>
                        sum + (double.tryParse(loan.nextPaymentAmount ?? '') ?? 0),
                  );
                  final totalNextInterest = active.fold<double>(
                    0,
                    (sum, loan) =>
                        sum + (double.tryParse(loan.nextInterestAmount ?? '') ?? 0),
                  );
                  final today = DateTime.now();
                  final overdue = active.where((loan) {
                    final due = DateTime.tryParse(
                        loan.nextInterestDueDate ?? loan.firstDueDate);
                    return due != null && due.isBefore(DateTime(today.year, today.month, today.day));
                  }).length;
                  return Card(
                    color: Theme.of(context).colorScheme.secondaryContainer,
                    child: Padding(
                      padding: const EdgeInsets.all(20),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text('Loan Summary', style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold)),
                          const Divider(height: 24),
                          _buildInfoRow('Outstanding balance', '₱${balance.toStringAsFixed(2)}'),
                          const SizedBox(height: 10),
                          _buildInfoRow('Active loans', '${active.length}'),
                          const SizedBox(height: 16),
                          const Divider(),
                          const SizedBox(height: 8),
                          const Text(
                            'Active Loan Payments',
                            style: TextStyle(fontWeight: FontWeight.bold),
                          ),
                          const SizedBox(height: 8),
                          _buildInfoRow(
                            'Total next payment amount',
                            '₱${totalNextPayment.toStringAsFixed(2)}',
                            Theme.of(context).colorScheme.primary,
                          ),
                          const SizedBox(height: 6),
                          _buildInfoRow(
                            'Total interest portion',
                            '₱${totalNextInterest.toStringAsFixed(2)}',
                          ),
                          for (var i = 0; i < active.length; i++) ...[
                            if (i > 0) ...[
                              const SizedBox(height: 12),
                              const Divider(height: 1),
                            ],
                            const SizedBox(height: 10),
                            Text(
                              'Active Loan ${i + 1}',
                              style:
                                  const TextStyle(fontWeight: FontWeight.bold),
                            ),
                            const Divider(height: 12),
                            _buildInfoRow(
                                'Next payment',
                                active[i].nextInterestDueDate ??
                                    active[i].firstDueDate),
                            const SizedBox(height: 6),
                            _buildInfoRow(
                              'Payment amount',
                              '₱${active[i].nextPaymentAmount ?? 'N/A'}',
                              Theme.of(context).colorScheme.primary,
                            ),
                            const SizedBox(height: 8),
                            const Divider(height: 1),
                            const SizedBox(height: 8),
                            _buildInfoRow(
                              'Interest due',
                              '₱${active[i].nextInterestAmount ?? 'N/A'}',
                            ),
                          ],
                          if (overdue > 0) ...[
                            const SizedBox(height: 12),
                            _buildInfoRow('Overdue loans', '$overdue', Colors.red),
                          ],
                        ],
                      ),
                    ),
                  );
                },
              ),
              const SizedBox(height: 16),
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16.0),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'Account Information',
                        style: TextStyle(
                            fontSize: 16, fontWeight: FontWeight.bold),
                      ),
                      const Divider(height: 24),
                      _buildInfoRow(
                          'Account Status',
                          profile?.accountStatus.toUpperCase() ?? 'ACTIVE',
                          Colors.green),
                      const SizedBox(height: 12),
                      _buildInfoRow(
                          'Borrower ID', profile?.borrowerId ?? 'N/A'),
                      const SizedBox(height: 12),
                      _buildInfoRow('Account ID', profile?.accountId ?? 'N/A'),
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
                        'Loan Actions',
                        style: TextStyle(
                            fontSize: 16, fontWeight: FontWeight.bold),
                      ),
                      const Divider(height: 24),
                      Row(
                        children: [
                          Expanded(
                            child: ElevatedButton.icon(
                              onPressed: () {
                                Navigator.of(context).push(
                                  MaterialPageRoute(
                                    builder: (_) =>
                                        const LoanRequestFormScreen(),
                                  ),
                                );
                              },
                              icon: const Icon(Icons.add_card),
                              label: const Text('Apply for Loan'),
                            ),
                          ),
                          const SizedBox(width: 12),
                          Expanded(
                            child: OutlinedButton.icon(
                              onPressed: () {
                                Navigator.of(context).push(
                                  MaterialPageRoute(
                                    builder: (_) =>
                                        const LoanRequestsListScreen(),
                                  ),
                                );
                              },
                              icon: const Icon(Icons.list_alt),
                              label: const Text('My Requests'),
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 12),
                      SizedBox(
                        width: double.infinity,
                        child: OutlinedButton.icon(
                          onPressed: () {
                            Navigator.of(context).push(
                              MaterialPageRoute(
                                builder: (_) => const BorrowerLoansListScreen(),
                              ),
                            );
                          },
                          icon: const Icon(Icons.account_balance),
                          label: const Text('My Loan Contracts'),
                        ),
                      ),
                      const SizedBox(height: 12),
                      SizedBox(
                        width: double.infinity,
                        child: OutlinedButton.icon(
                          onPressed: () {
                            Navigator.of(context).push(
                              MaterialPageRoute(
                                builder: (_) =>
                                    const BorrowerNotificationsScreen(),
                              ),
                            );
                          },
                          icon: const Icon(Icons.notifications),
                          label: const Text('Notifications'),
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
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          const Text(
                            'System Connection',
                            style: TextStyle(
                                fontSize: 16, fontWeight: FontWeight.bold),
                          ),
                          IconButton(
                            icon: const Icon(Icons.refresh, size: 20),
                            onPressed: _isCheckingHealth ? null : _checkHealth,
                          ),
                        ],
                      ),
                      const SizedBox(height: 8),
                      Row(
                        children: [
                          Icon(
                            _isBackendReady == true
                                ? Icons.check_circle
                                : _isBackendReady == false
                                    ? Icons.error
                                    : Icons.hourglass_empty,
                            color: _isBackendReady == true
                                ? Colors.green
                                : _isBackendReady == false
                                    ? Colors.red
                                    : Colors.orange,
                            size: 20,
                          ),
                          const SizedBox(width: 8),
                          Text(
                            _isCheckingHealth
                                ? 'Checking system readiness...'
                                : _isBackendReady == true
                                    ? 'Backend & Database Ready'
                                    : 'System Connection Unavailable',
                            style: const TextStyle(fontSize: 14),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 24),
              OutlinedButton.icon(
                onPressed: () {
                  ref.read(authControllerProvider.notifier).logout();
                },
                icon: const Icon(Icons.logout),
                label: const Text('Sign Out'),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildInfoRow(String label, String value, [Color? valueColor]) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Text(
          label,
          style: const TextStyle(fontSize: 14, color: Colors.grey),
        ),
        Flexible(
          child: Text(
            value,
            textAlign: TextAlign.end,
            style: TextStyle(
              fontSize: 14,
              fontWeight: FontWeight.bold,
              color: valueColor,
            ),
          ),
        ),
      ],
    );
  }
}
