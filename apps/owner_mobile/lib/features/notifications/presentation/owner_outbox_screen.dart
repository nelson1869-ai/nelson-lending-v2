import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/owner_notifications_api_client.dart';
import '../domain/outbox_models.dart';

final ownerOutboxListProvider = FutureProvider.family
    .autoDispose<OutboxListModel, String?>((ref, statusFilter) async {
  final client = ref.watch(ownerNotificationsApiClientProvider);
  return client.fetchOutbox(status: statusFilter);
});

class OwnerOutboxScreen extends ConsumerStatefulWidget {
  const OwnerOutboxScreen({super.key});

  @override
  ConsumerState<OwnerOutboxScreen> createState() => _OwnerOutboxScreenState();
}

class _OwnerOutboxScreenState extends ConsumerState<OwnerOutboxScreen> {
  String? _selectedStatus;

  @override
  Widget build(BuildContext context) {
    final outboxAsync = ref.watch(ownerOutboxListProvider(_selectedStatus));

    return Scaffold(
      appBar: AppBar(
        title: const Text('Notification Outbox Monitor'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () {
              ref.invalidate(ownerOutboxListProvider(_selectedStatus));
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
                  _buildFilterChip('All', null),
                  const SizedBox(width: 8),
                  _buildFilterChip('Pending', 'pending'),
                  const SizedBox(width: 8),
                  _buildFilterChip('Delivered', 'delivered'),
                  const SizedBox(width: 8),
                  _buildFilterChip('Failed', 'failed'),
                  const SizedBox(width: 8),
                  _buildFilterChip('Dead Letter', 'dead_letter'),
                ],
              ),
            ),
          ),
          const Divider(height: 1),
          Expanded(
            child: outboxAsync.when(
              data: (outboxList) {
                if (outboxList.items.isEmpty) {
                  return const Center(
                    child: Text(
                      'No outbox entries found.',
                      style: TextStyle(color: Colors.grey),
                    ),
                  );
                }
                return ListView.separated(
                  padding: const EdgeInsets.all(16.0),
                  itemCount: outboxList.items.length,
                  separatorBuilder: (_, __) => const SizedBox(height: 8),
                  itemBuilder: (context, index) {
                    final item = outboxList.items[index];
                    return Card(
                      child: Padding(
                        padding: const EdgeInsets.all(12.0),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Row(
                              children: [
                                Text(
                                  item.eventType,
                                  style: const TextStyle(
                                    fontWeight: FontWeight.bold,
                                    fontSize: 14,
                                  ),
                                ),
                                const Spacer(),
                                _buildStatusBadge(item.status),
                              ],
                            ),
                            const SizedBox(height: 6),
                            Text(
                              'Recipient: ${item.recipientType} (${item.recipientId})',
                              style: const TextStyle(fontSize: 12),
                            ),
                            Text(
                              'Channel: ${item.channel}  |  Template: ${item.templateKey}',
                              style: const TextStyle(fontSize: 12),
                            ),
                            Text(
                              'Attempts: ${item.attemptCount} / ${item.maxAttempts}',
                              style: const TextStyle(fontSize: 12),
                            ),
                            if (item.lastError != null) ...[
                              const SizedBox(height: 4),
                              Text(
                                'Last Error: ${item.lastError}',
                                style: TextStyle(
                                  fontSize: 11,
                                  color: Colors.red.shade700,
                                ),
                              ),
                            ],
                            if (item.isDeadLetter) ...[
                              const SizedBox(height: 8),
                              Align(
                                alignment: Alignment.centerRight,
                                child: OutlinedButton.icon(
                                  icon: const Icon(Icons.replay, size: 14),
                                  label: const Text('Retry Delivery'),
                                  onPressed: () async {
                                    await ref
                                        .read(
                                            ownerNotificationsApiClientProvider)
                                        .retryOutbox(item.id);
                                    ref.invalidate(ownerOutboxListProvider(
                                        _selectedStatus));
                                  },
                                ),
                              ),
                            ],
                          ],
                        ),
                      ),
                    );
                  },
                );
              },
              loading: () => const Center(child: CircularProgressIndicator()),
              error: (err, stack) => Center(
                child: Text('Failed to load outbox: $err'),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildFilterChip(String label, String? value) {
    final isSelected = _selectedStatus == value;
    return FilterChip(
      label: Text(label),
      selected: isSelected,
      onSelected: (_) {
        setState(() {
          _selectedStatus = value;
        });
      },
    );
  }

  Widget _buildStatusBadge(String status) {
    Color bg;
    Color fg = Colors.white;
    switch (status) {
      case 'delivered':
        bg = Colors.green.shade700;
        break;
      case 'pending':
        bg = Colors.orange.shade700;
        break;
      case 'failed':
        bg = Colors.amber.shade800;
        break;
      case 'dead_letter':
        bg = Colors.red.shade700;
        break;
      default:
        bg = Colors.grey;
    }
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
      decoration: BoxDecoration(
        color: bg,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Text(
        status.toUpperCase(),
        style: TextStyle(
          color: fg,
          fontSize: 10,
          fontWeight: FontWeight.bold,
        ),
      ),
    );
  }
}
