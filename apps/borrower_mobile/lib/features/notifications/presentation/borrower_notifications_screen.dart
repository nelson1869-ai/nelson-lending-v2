import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../data/borrower_notifications_api_client.dart';
import '../domain/notification_models.dart';

final borrowerNotificationsListProvider =
    FutureProvider.autoDispose<List<BorrowerNotification>>((ref) async {
  final client = ref.watch(borrowerNotificationsApiClientProvider);
  return client.listNotifications();
});

final borrowerUnreadCountProvider =
    FutureProvider.autoDispose<int>((ref) async {
  final client = ref.watch(borrowerNotificationsApiClientProvider);
  return client.getUnreadCount();
});

class BorrowerNotificationsScreen extends ConsumerWidget {
  const BorrowerNotificationsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final notificationsAsync = ref.watch(borrowerNotificationsListProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Notifications'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () {
              ref.invalidate(borrowerNotificationsListProvider);
              ref.invalidate(borrowerUnreadCountProvider);
            },
          ),
        ],
      ),
      body: notificationsAsync.when(
        data: (notifications) {
          if (notifications.isEmpty) {
            return const Center(
              child: Text(
                'No notifications yet.',
                style: TextStyle(fontSize: 14, color: Colors.grey),
              ),
            );
          }
          return RefreshIndicator(
            onRefresh: () async {
              ref.invalidate(borrowerNotificationsListProvider);
              ref.invalidate(borrowerUnreadCountProvider);
            },
            child: ListView.separated(
              padding: const EdgeInsets.all(16.0),
              itemCount: notifications.length,
              separatorBuilder: (_, __) => const Divider(height: 1),
              itemBuilder: (context, index) {
                final item = notifications[index];
                return ListTile(
                  leading: Icon(
                    item.isRead
                        ? Icons.notifications_none
                        : Icons.notifications_active,
                    color: item.isRead ? Colors.grey : Colors.blue.shade700,
                  ),
                  title: Text(
                    item.title,
                    style: TextStyle(
                      fontWeight:
                          item.isRead ? FontWeight.normal : FontWeight.bold,
                    ),
                  ),
                  subtitle: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const SizedBox(height: 4),
                      Text(item.body),
                      const SizedBox(height: 4),
                      Text(
                        item.createdAt.toLocal().toString().split('.')[0],
                        style:
                            const TextStyle(fontSize: 11, color: Colors.grey),
                      ),
                    ],
                  ),
                  onTap: () async {
                    if (!item.isRead) {
                      await ref
                          .read(borrowerNotificationsApiClientProvider)
                          .markRead(item.id);
                      ref.invalidate(borrowerNotificationsListProvider);
                      ref.invalidate(borrowerUnreadCountProvider);
                    }
                  },
                );
              },
            ),
          );
        },
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (err, stack) => Center(
          child: Text('Failed to load notifications: $err'),
        ),
      ),
    );
  }
}
