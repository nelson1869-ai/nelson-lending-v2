import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/owner_reports_api_client.dart';
import '../domain/dashboard_models.dart';
import '../../borrowers/presentation/owner_borrowers_screen.dart';
import '../../accounting/presentation/owner_accounting_screen.dart';
import '../../loans/presentation/owner_loans_list_screen.dart';
import '../../loans/presentation/owner_loans_controller.dart';
import '../../loan_requests/presentation/owner_loan_requests_controller.dart';
import '../../loan_requests/presentation/owner_loan_requests_list_screen.dart';

class OwnerDashboardScreen extends ConsumerStatefulWidget {
  final DateTime? initialDate;

  const OwnerDashboardScreen({super.key, this.initialDate});

  @override
  ConsumerState<OwnerDashboardScreen> createState() =>
      _OwnerDashboardScreenState();
}

class _OwnerDashboardScreenState extends ConsumerState<OwnerDashboardScreen> {
  late DateTime _fromDate;
  late DateTime _toDate;
  late Future<OwnerDashboardModel> _dashboard;
  bool _isAccruingInterest = false;

  @override
  void initState() {
    super.initState();
    final now = widget.initialDate ?? DateTime.now();
    _fromDate = DateTime(now.year, now.month, 1);
    _toDate = DateTime(now.year, now.month + 1, 0);
    _dashboard = _load();
  }

  Future<OwnerDashboardModel> _load() {
    return ref.read(ownerReportsApiClientProvider).fetchDashboard(
          fromDate: _fromDate,
          toDate: _toDate,
        );
  }

  void _refresh() {
    if (_fromDate.isAfter(_toDate)) return;
    final nextDashboard = _load();
    setState(() {
      _dashboard = nextDashboard;
    });
  }

  Future<void> _accrueInterest() async {
    setState(() => _isAccruingInterest = true);
    try {
      final updated = await ref
          .read(ownerReportsApiClientProvider)
          .accrueDueInterest();
      if (!mounted) return;
      _refresh();
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('$updated loan(s) updated with due interest.')),
      );
    } catch (_) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Unable to accrue due interest.')),
      );
    } finally {
      if (mounted) setState(() => _isAccruingInterest = false);
    }
  }

  Future<void> _selectDate({required bool from}) async {
    final selected = await showDatePicker(
      context: context,
      initialDate: from ? _fromDate : _toDate,
      firstDate: DateTime(2000),
      lastDate: DateTime(2100),
      helpText: from ? 'Collection start date' : 'Collection end date',
    );
    if (selected == null || !mounted) return;
    setState(() {
      if (from) {
        _fromDate = selected;
      } else {
        _toDate = selected;
      }
      if (!_fromDate.isAfter(_toDate)) _dashboard = _load();
    });
  }

  String _date(DateTime value) =>
      '${value.year}-${value.month.toString().padLeft(2, '0')}-${value.day.toString().padLeft(2, '0')}';

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Reports & Dashboard'),
        actions: [
          IconButton(
            tooltip: 'Refresh dashboard',
            onPressed: _fromDate.isAfter(_toDate) ? null : _refresh,
            icon: const Icon(Icons.refresh),
          ),
          IconButton(
            tooltip: 'Accrue due interest',
            onPressed: _isAccruingInterest ? null : _accrueInterest,
            icon: _isAccruingInterest
                ? const SizedBox(
                    width: 18,
                    height: 18,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : const Icon(Icons.percent),
          ),
        ],
      ),
      body: FutureBuilder<OwnerDashboardModel>(
        future: _dashboard,
        builder: (context, snapshot) {
          if (snapshot.connectionState != ConnectionState.done) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snapshot.hasError) {
            return Center(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  const Text('Unable to load dashboard metrics.'),
                  const SizedBox(height: 12),
                  ElevatedButton(
                      onPressed: _refresh, child: const Text('Retry')),
                ],
              ),
            );
          }
          return _content(snapshot.requireData);
        },
      ),
    );
  }

  Widget _content(OwnerDashboardModel dashboard) {
    final invalidRange = _fromDate.isAfter(_toDate);
    return RefreshIndicator(
      onRefresh: () async => _refresh(),
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Text('Collections period',
              style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 8),
          Row(
            children: [
              Expanded(
                child: OutlinedButton.icon(
                  onPressed: () => _selectDate(from: true),
                  icon: const Icon(Icons.calendar_today),
                  label: Text('From ${_date(_fromDate)}'),
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: OutlinedButton.icon(
                  onPressed: () => _selectDate(from: false),
                  icon: const Icon(Icons.event),
                  label: Text('To ${_date(_toDate)}'),
                ),
              ),
            ],
          ),
          if (invalidRange)
            const Text(
              'Start date must be on or before end date.',
              style: TextStyle(color: Colors.red),
            ),
          if (invalidRange)
            const Card(
              child: Padding(
                padding: EdgeInsets.all(16),
                child: Text('Choose a valid period to load dashboard metrics.'),
              ),
            ),
          if (!invalidRange && dashboard.isEmpty)
            const Card(
              child: Padding(
                padding: EdgeInsets.all(16),
                child: Text('No report activity for the selected period.'),
              ),
            ),
          if (!invalidRange)
            _section(
              'Portfolio',
              [
                _money('Total money borrowed',
                    dashboard.portfolio.totalOriginalPrincipal,
                    onTap: _openLoans),
                _money('Total scheduled interest',
                    dashboard.portfolio.totalScheduledInterest),
                _money('Total scheduled repayment',
                    dashboard.portfolio.totalScheduledRepayment),
                _money('Next scheduled interest due',
                    dashboard.portfolio.nextInterestDue),
                _money('Active outstanding principal',
                    dashboard.portfolio.outstandingPrincipal,
                    onTap: _openLoans),
                _money('Active accrued interest',
                    dashboard.portfolio.accruedInterest),
                _borrowerCountButton(dashboard.portfolio.borrowerCount),
                _count('Due today', dashboard.portfolio.dueTodayCount,
                    onTap: _openLoans),
                _count('Overdue loans', dashboard.portfolio.overdueLoanCount,
                    onTap: _openLoans),
                _money('Overdue outstanding principal',
                    dashboard.portfolio.overdueOutstandingPrincipal,
                    onTap: _openLoans),
                _count('Due in next 7 days',
                    dashboard.portfolio.dueNext7DaysCount,
                    onTap: _openLoans),
                _money('Due next 7 days outstanding principal',
                    dashboard.portfolio.dueNext7DaysOutstandingPrincipal,
                    onTap: _openLoans),
                _count('Overdue 1–7 days',
                    dashboard.portfolio.overdue1To7DaysCount,
                    onTap: _openLoans),
                _count('Overdue 8–30 days',
                    dashboard.portfolio.overdue8To30DaysCount,
                    onTap: _openLoans),
                _count('Overdue 30+ days',
                    dashboard.portfolio.overdue30PlusDaysCount,
                    onTap: _openLoans),
                ...dashboard.portfolio.statusCounts
                    .map((item) => _count(item.status, item.count,
                        onTap: () => _openLoans(status: item.status))),
              ],
            ),
          if (!invalidRange)
            _section(
              'Collections (${dashboard.collections.fromDate} to ${dashboard.collections.toDate})',
              [
                _money(
                    'Total payments', dashboard.collections.totalPaymentAmount,
                    onTap: _openAccounting),
                _money('Principal', dashboard.collections.principalAllocation,
                    onTap: _openAccounting),
                _money('Interest collected', dashboard.collections.interestAllocation,
                    onTap: _openAccounting),
                _money('Unapplied credit',
                    dashboard.collections.unappliedCreditAllocation,
                    onTap: _openAccounting),
              ],
            ),
          if (!invalidRange)
            _section(
              'Accounting balances',
              dashboard.accountingBalances
                  .map((item) =>
                      _money('${item.code} ${item.name}', item.balance,
                          onTap: _openAccounting))
                  .toList(),
            ),
          if (!invalidRange)
            _section(
              'Loan requests',
              dashboard.loanRequestStatusCounts
                  .map((item) => _count(item.status, item.count,
                      onTap: () => _openRequests(item.status)))
                  .toList(),
            ),
        ],
      ),
    );
  }

  Widget _section(String title, List<Widget> rows) {
    return Card(
      margin: const EdgeInsets.only(bottom: 16),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(title, style: Theme.of(context).textTheme.titleMedium),
            const Divider(),
            ...rows,
          ],
        ),
      ),
    );
  }

  void _openLoans({String? status}) {
    ref.read(ownerLoansFilterProvider.notifier).state = status;
    Navigator.of(context).push(
      MaterialPageRoute(builder: (_) => const OwnerLoansListScreen()),
    );
  }

  void _openAccounting() {
    Navigator.of(context).push(
      MaterialPageRoute(builder: (_) => const OwnerAccountingScreen()),
    );
  }

  void _openRequests(String status) {
    ref.read(ownerLoanRequestsControllerProvider.notifier).fetchRequests(status);
    Navigator.of(context).push(
      MaterialPageRoute(builder: (_) => const OwnerLoanRequestsListScreen()),
    );
  }

  Widget _money(String label, String value, {VoidCallback? onTap}) => ListTile(
        dense: true,
        title: Text(label),
        trailing: _valueWithChevron('₱$value', onTap, _metricColor(label)),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        onTap: onTap,
      );

  Widget _count(String label, int value, {VoidCallback? onTap}) => ListTile(
        dense: true,
        title: Text(label.replaceAll('_', ' ')),
        trailing: _valueWithChevron('$value', onTap, _metricColor(label)),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        onTap: onTap,
      );

  Widget _valueWithChevron(String value, VoidCallback? onTap, [Color? color]) => Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(value,
              style: TextStyle(
                  fontWeight: FontWeight.w600, color: color)),
          if (onTap != null) ...[
            const SizedBox(width: 8),
            const Icon(Icons.chevron_right, size: 20),
          ],
        ],
      );

  Color? _metricColor(String label) {
    final normalized = label.toLowerCase();
    if (normalized.contains('overdue') ||
        normalized.contains('rejected') ||
        normalized.contains('defaulted')) {
      return Colors.red.shade700;
    }
    if (normalized.contains('interest') || normalized.contains('due')) {
      return Colors.orange.shade800;
    }
    if (normalized.contains('payment') ||
        normalized.contains('collected') ||
        normalized.contains('paid') ||
        normalized.contains('approved') ||
        normalized.contains('active')) {
      return Colors.green.shade700;
    }
    if (normalized.contains('principal') ||
        normalized.contains('borrowed') ||
        normalized.contains('balance')) {
      return Theme.of(context).colorScheme.primary;
    }
    if (normalized.contains('unapplied')) {
      return Colors.deepPurple.shade700;
    }
    return null;
  }

  Widget _borrowerCountButton(int value) => ListTile(
        dense: true,
        title: const Text('Total borrowers'),
        trailing: _valueWithChevron('$value', () {}),
        leading: const Icon(Icons.people),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        onTap: () => Navigator.of(context).push(
          MaterialPageRoute(builder: (_) => const OwnerBorrowersScreen()),
        ),
      );
}
