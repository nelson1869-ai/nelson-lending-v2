import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/api_client.dart';
import '../domain/outbox_models.dart';

final ownerNotificationsApiClientProvider =
    Provider<OwnerNotificationsApiClient>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return OwnerNotificationsApiClient(apiClient.dio);
});

class OwnerNotificationsApiClient {
  final Dio _dio;

  OwnerNotificationsApiClient(this._dio);

  Future<OutboxListModel> fetchOutbox({String? status}) async {
    final queryParams = <String, dynamic>{};
    if (status != null && status.isNotEmpty) {
      queryParams['status'] = status;
    }
    final response = await _dio.get(
      '/api/v1/owner/notifications/outbox',
      queryParameters: queryParams,
    );
    return OutboxListModel.fromJson(response.data as Map<String, dynamic>);
  }

  Future<OutboxItemModel> retryOutbox(String outboxId) async {
    final response =
        await _dio.post('/api/v1/owner/notifications/outbox/$outboxId/retry');
    return OutboxItemModel.fromJson(response.data as Map<String, dynamic>);
  }
}
