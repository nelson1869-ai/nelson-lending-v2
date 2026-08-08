import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/api_client.dart';
import '../domain/owner_loan_request_models.dart';

final ownerLoanRequestsApiClientProvider =
    Provider<OwnerLoanRequestsApiClient>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return OwnerLoanRequestsApiClient(apiClient.dio);
});

class OwnerLoanRequestsApiClient {
  final Dio _dio;

  OwnerLoanRequestsApiClient(this._dio);

  Future<List<OwnerLoanRequestDetailModel>> listRequests(
      {String? statusFilter}) async {
    final response = await _dio.get(
      '/owner/loan-requests',
      queryParameters: statusFilter != null && statusFilter.isNotEmpty
          ? {'status_filter': statusFilter}
          : null,
    );
    final list = response.data as List<dynamic>;
    return list
        .map((e) =>
            OwnerLoanRequestDetailModel.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  Future<OwnerLoanRequestDetailModel> getRequestDetail(String requestId) async {
    final response = await _dio.get('/owner/loan-requests/$requestId');
    return OwnerLoanRequestDetailModel.fromJson(
        response.data as Map<String, dynamic>);
  }

  Future<void> approveRequest(String requestId, {String? ownerNote}) async {
    await _dio.post(
      '/owner/loan-requests/$requestId/approve',
      data: ownerNote != null && ownerNote.isNotEmpty
          ? {'ownerNote': ownerNote}
          : {},
    );
  }

  Future<void> rejectRequest(String requestId, {String? ownerNote}) async {
    await _dio.post(
      '/owner/loan-requests/$requestId/reject',
      data: ownerNote != null && ownerNote.isNotEmpty
          ? {'ownerNote': ownerNote}
          : {},
    );
  }
}
