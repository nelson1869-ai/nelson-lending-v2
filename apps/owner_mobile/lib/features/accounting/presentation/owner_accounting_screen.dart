import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/owner_accounting_api_client.dart';
import '../domain/accounting_models.dart';

final ownerAccountsProvider =
    FutureProvider.autoDispose<List<AccountModel>>((ref) async {
  final client = ref.watch(ownerAccountingApiClientProvider);
  return client.fetchAccounts();
});

final ownerJournalsProvider =
    FutureProvider.autoDispose<List<JournalTransactionModel>>((ref) async {
  final client = ref.watch(ownerAccountingApiClientProvider);
  return client.fetchJournals();
});

class OwnerAccountingScreen extends ConsumerStatefulWidget {
  const OwnerAccountingScreen({super.key});

  @override
  ConsumerState<OwnerAccountingScreen> createState() =>
      _OwnerAccountingScreenState();
}

class _OwnerAccountingScreenState extends ConsumerState<OwnerAccountingScreen>
    with SingleTickerProviderStateMixin {
  late TabController _tabController;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 2, vsync: this);
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('General Ledger'),
        bottom: TabBar(
          controller: _tabController,
          tabs: const [
            Tab(icon: Icon(Icons.account_balance), text: 'Chart of Accounts'),
            Tab(icon: Icon(Icons.receipt_long), text: 'Journal Transactions'),
          ],
        ),
      ),
      body: TabBarView(
        controller: _tabController,
        children: const [
          _AccountsTab(),
          _JournalsTab(),
        ],
      ),
    );
  }
}

class _AccountsTab extends ConsumerWidget {
  const _AccountsTab();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final accountsAsync = ref.watch(ownerAccountsProvider);

    return accountsAsync.when(
      data: (accounts) {
        if (accounts.isEmpty) {
          return const Center(child: Text('No accounts seeded.'));
        }
        return RefreshIndicator(
          onRefresh: () async => ref.refresh(ownerAccountsProvider.future),
          child: ListView.separated(
            padding: const EdgeInsets.all(16.0),
            itemCount: accounts.length,
            separatorBuilder: (_, __) => const SizedBox(height: 8.0),
            itemBuilder: (context, index) {
              final acc = accounts[index];
              return Card(
                elevation: 2,
                child: ListTile(
                  leading: CircleAvatar(
                    child: Text(
                      acc.code,
                      style: const TextStyle(
                          fontWeight: FontWeight.bold, fontSize: 12),
                    ),
                  ),
                  title: Text(
                    acc.name,
                    style: const TextStyle(fontWeight: FontWeight.bold),
                  ),
                  subtitle: Text('Type: ${acc.type.toUpperCase()}'),
                  trailing: Container(
                    padding:
                        const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                    decoration: BoxDecoration(
                      color: Theme.of(context).colorScheme.primaryContainer,
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: Text(
                      'Normal: ${acc.normalBalance.toUpperCase()}',
                      style: TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.w600,
                        color: Theme.of(context).colorScheme.onPrimaryContainer,
                      ),
                    ),
                  ),
                ),
              );
            },
          ),
        );
      },
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (err, stack) => Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Text('Error loading accounts: $err'),
            const SizedBox(height: 12),
            ElevatedButton(
              onPressed: () => ref.refresh(ownerAccountsProvider),
              child: const Text('Retry'),
            ),
          ],
        ),
      ),
    );
  }
}

class _JournalsTab extends ConsumerWidget {
  const _JournalsTab();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final journalsAsync = ref.watch(ownerJournalsProvider);

    return journalsAsync.when(
      data: (journals) {
        if (journals.isEmpty) {
          return RefreshIndicator(
            onRefresh: () async => ref.refresh(ownerJournalsProvider.future),
            child: ListView(
              children: const [
                SizedBox(height: 100),
                Center(child: Text('No journal transactions recorded.')),
              ],
            ),
          );
        }
        return RefreshIndicator(
          onRefresh: () async => ref.refresh(ownerJournalsProvider.future),
          child: ListView.separated(
            padding: const EdgeInsets.all(16.0),
            itemCount: journals.length,
            separatorBuilder: (_, __) => const SizedBox(height: 12.0),
            itemBuilder: (context, index) {
              final tx = journals[index];
              final isReversal =
                  tx.eventType == 'reversal' || tx.reversalOfId != null;

              return Card(
                elevation: 3,
                child: Padding(
                  padding: const EdgeInsets.all(16.0),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Wrap(
                        spacing: 8,
                        runSpacing: 6,
                        crossAxisAlignment: WrapCrossAlignment.center,
                        children: [
                          Container(
                            padding: const EdgeInsets.symmetric(
                                horizontal: 8, vertical: 4),
                            decoration: BoxDecoration(
                              color: isReversal
                                  ? Colors.orange.shade100
                                  : Colors.blue.shade100,
                              borderRadius: BorderRadius.circular(6),
                            ),
                            child: Text(
                              tx.eventType.toUpperCase(),
                              style: TextStyle(
                                fontWeight: FontWeight.bold,
                                fontSize: 12,
                                color: isReversal
                                    ? Colors.orange.shade900
                                    : Colors.blue.shade900,
                              ),
                            ),
                          ),
                          if (tx.isBalanced)
                            Container(
                              padding: const EdgeInsets.symmetric(
                                  horizontal: 8, vertical: 4),
                              decoration: BoxDecoration(
                                color: Colors.green.shade100,
                                borderRadius: BorderRadius.circular(6),
                              ),
                              child: Row(
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  Icon(Icons.check_circle,
                                      size: 14, color: Colors.green.shade900),
                                  const SizedBox(width: 4),
                                  Text(
                                    'BALANCED',
                                    style: TextStyle(
                                      fontWeight: FontWeight.bold,
                                      fontSize: 11,
                                      color: Colors.green.shade900,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          Text(tx.effectiveDate,
                              style: Theme.of(context).textTheme.bodySmall),
                        ],
                      ),
                      const SizedBox(height: 8),
                      Text(
                        tx.description,
                        style: const TextStyle(
                            fontWeight: FontWeight.bold, fontSize: 15),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        'Total Debit: ₱${tx.totalDebit}  |  Total Credit: ₱${tx.totalCredit}',
                        style: TextStyle(
                          color: Theme.of(context).colorScheme.onSurfaceVariant,
                          fontSize: 13,
                        ),
                      ),
                      const Divider(height: 20),
                      Text(
                        'Entries (${tx.entries.length}):',
                        style: const TextStyle(
                            fontWeight: FontWeight.w600, fontSize: 13),
                      ),
                      const SizedBox(height: 6),
                      ...tx.entries.map((entry) {
                        final isDebit = double.tryParse(entry.debit) != null &&
                            double.parse(entry.debit) > 0;
                        return Padding(
                          padding: const EdgeInsets.symmetric(vertical: 2.0),
                          child: Row(
                            children: [
                              Text(
                                '${entry.accountCode} - ${entry.accountName}',
                                style: const TextStyle(fontSize: 13),
                              ),
                              const Spacer(),
                              Text(
                                isDebit
                                    ? 'DR ₱${entry.debit}'
                                    : 'CR ₱${entry.credit}',
                                style: TextStyle(
                                  fontSize: 13,
                                  fontWeight: FontWeight.w600,
                                  color: isDebit
                                      ? Colors.green.shade700
                                      : Colors.blue.shade700,
                                ),
                              ),
                            ],
                          ),
                        );
                      }),
                      if (tx.eventType == 'payment' ||
                          tx.eventType == 'loan_disbursement') ...[
                        const SizedBox(height: 12),
                        Align(
                          alignment: Alignment.centerRight,
                          child: Text(
                            'System-generated business event (Managed by loan workflow)',
                            style: TextStyle(
                              fontSize: 11,
                              fontStyle: FontStyle.italic,
                              color: Theme.of(context)
                                  .colorScheme
                                  .onSurfaceVariant,
                            ),
                          ),
                        ),
                      ] else if (tx.eventType != 'reversal' &&
                          tx.reversalOfId == null) ...[
                        const SizedBox(height: 12),
                        Align(
                          alignment: Alignment.centerRight,
                          child: OutlinedButton.icon(
                            icon: const Icon(Icons.undo, size: 16),
                            label: const Text('Reverse Transaction'),
                            style: OutlinedButton.styleFrom(
                              foregroundColor: Colors.red.shade700,
                            ),
                            onPressed: () =>
                                _showReversalDialog(context, ref, tx),
                          ),
                        ),
                      ],
                    ],
                  ),
                ),
              );
            },
          ),
        );
      },
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (err, stack) => Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Text('Error loading journals: $err'),
            const SizedBox(height: 12),
            ElevatedButton(
              onPressed: () => ref.refresh(ownerJournalsProvider),
              child: const Text('Retry'),
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _showReversalDialog(
    BuildContext context,
    WidgetRef ref,
    JournalTransactionModel tx,
  ) async {
    final reasonController = TextEditingController();
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Confirm Compensating Reversal'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Reversing transaction "${tx.description}". '
              'This will post a new balanced compensating entry (swapping debits and credits).',
              style: const TextStyle(fontSize: 14),
            ),
            const SizedBox(height: 16),
            TextField(
              controller: reasonController,
              decoration: const InputDecoration(
                labelText: 'Reversal Reason (Optional)',
                border: OutlineInputBorder(),
              ),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(false),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            style:
                ElevatedButton.styleFrom(backgroundColor: Colors.red.shade700),
            onPressed: () => Navigator.of(ctx).pop(true),
            child: const Text('Post Reversal',
                style: TextStyle(color: Colors.white)),
          ),
        ],
      ),
    );

    if (confirmed == true) {
      try {
        final client = ref.read(ownerAccountingApiClientProvider);
        await client.reverseJournal(tx.id,
            reason: reasonController.text.trim());
        ref.invalidate(ownerJournalsProvider);
        if (context.mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
                content: Text(
                    'Compensating reversal transaction posted successfully.')),
          );
        }
      } catch (e) {
        if (context.mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('Failed to reverse transaction: $e')),
          );
        }
      }
    }
  }
}
