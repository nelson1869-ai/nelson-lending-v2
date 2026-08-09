import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/owner_reports_api_client.dart';
import '../domain/dashboard_models.dart';

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
                _money('Original principal (active + paid)',
                    dashboard.portfolio.totalOriginalPrincipal),
                _money('Active outstanding principal',
                    dashboard.portfolio.outstandingPrincipal),
                _money('Active accrued interest',
                    dashboard.portfolio.accruedInterest),
                ...dashboard.portfolio.statusCounts
                    .map((item) => _count(item.status, item.count)),
              ],
            ),
          if (!invalidRange)
            _section(
              'Collections (${dashboard.collections.fromDate} to ${dashboard.collections.toDate})',
              [
                _money(
                    'Total payments', dashboard.collections.totalPaymentAmount),
                _money('Principal', dashboard.collections.principalAllocation),
                _money('Interest', dashboard.collections.interestAllocation),
                _money('Unapplied credit',
                    dashboard.collections.unappliedCreditAllocation),
              ],
            ),
          if (!invalidRange)
            _section(
              'Accounting balances',
              dashboard.accountingBalances
                  .map((item) =>
                      _money('${item.code} ${item.name}', item.balance))
                  .toList(),
            ),
          if (!invalidRange)
            _section(
              'Loan requests',
              dashboard.loanRequestStatusCounts
                  .map((item) => _count(item.status, item.count))
                  .toList(),
            ),
        ],
      ),
    );
  }

  Widget _section(String title, List<Widget> rows) {
    return Card(
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

  Widget _money(String label, String value) => ListTile(
        dense: true,
        title: Text(label),
        trailing: Text('₱$value'),
      );

  Widget _count(String label, int value) => ListTile(
        dense: true,
        title: Text(label.replaceAll('_', ' ')),
        trailing: Text('$value'),
      );
}
