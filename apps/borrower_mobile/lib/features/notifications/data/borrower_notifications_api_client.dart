import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/api_client.dart';
import '../domain/notification_models.dart';

final borrowerNotificationsApiClientProvider =
    Provider<BorrowerNotificationsApiClient>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return BorrowerNotificationsApiClient(apiClient.dio);
});

class BorrowerNotificationsApiClient {
  final Dio _dio;

  BorrowerNotificationsApiClient(this._dio);

  Future<List<BorrowerNotification>> listNotifications() async {
    final response = await _dio.get('/borrower/notifications');
    final list = response.data as List<dynamic>;
    return list
        .map((e) => BorrowerNotification.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  Future<int> getUnreadCount() async {
    final response = await _dio.get('/borrower/notifications/unread-count');
    final data = response.data as Map<String, dynamic>;
    return data['unread_count'] as int;
  }

  Future<BorrowerNotification> markRead(String notificationId) async {
    final response =
        await _dio.post('/borrower/notifications/$notificationId/read');
    return BorrowerNotification.fromJson(response.data as Map<String, dynamic>);
  }
}
